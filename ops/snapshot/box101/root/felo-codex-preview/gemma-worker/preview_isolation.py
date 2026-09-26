"""Fail-closed policy for the upcoming per-project preview gateway.

This module does not start listeners or modify Tailscale. It is deliberately
separate from the current worker until the gateway and migration are verified.
"""
from dataclasses import dataclass
import re
from urllib.parse import urlsplit, unquote, quote

JOB = re.compile(r'^[a-f0-9]{32}$')
PROJECT = re.compile(r'^[a-z][a-z0-9_-]{0,79}$')
PUBLIC = {'.html','.css','.js','.json','.svg','.png','.jpg','.jpeg','.webp','.ico','.woff','.woff2'}

class IsolationDenied(ValueError):
    pass

@dataclass(frozen=True)
class Target:
    project: str
    origin: str
    job: str
    path: str
    data_app: str | None
    data_request: bool
    backend_job: bool = False
    backend_request: bool = False

def exact_origin(value):
    if not isinstance(value,str):raise IsolationDenied('Invalid preview origin')
    try:u=urlsplit(value);port=u.port
    except ValueError:raise IsolationDenied('Invalid preview origin')
    if (u.scheme!='https' or u.username or u.password or not (u.hostname or '').endswith('.ts.net')
        or port is None or not 1024<=port<=65535 or u.path or u.query or u.fragment
        or value!='https://'+u.hostname+':'+str(port)):
        raise IsolationDenied('Use an exact private HTTPS preview origin with a dedicated port')
    return value

class PreviewIsolation:
    def __init__(self,document):
        if not isinstance(document,dict) or set(document)!={'version','manager_origin','projects'} or type(document['version']) is not int or document['version'] not in (1,2):
            raise IsolationDenied('Invalid preview registry')
        self.manager=exact_origin(document['manager_origin'])
        entries=document['projects']
        if not isinstance(entries,list) or not 0<=len(entries)<=100:raise IsolationDenied('Invalid preview registry size')
        self.by_job={};self.by_host={};self.backend_jobs=set();projects=set();apps=set()
        for entry in entries:
            fields={'project','origin','data_app','jobs'}|({'backend_jobs'} if document['version']==2 else set())
            if not isinstance(entry,dict) or set(entry)!=fields:raise IsolationDenied('Invalid preview assignment')
            project=entry['project'];origin=exact_origin(entry['origin']);app=entry['data_app'];jobs=entry['jobs']
            if not isinstance(project,str) or not PROJECT.fullmatch(project) or project in projects:raise IsolationDenied('Invalid or duplicate project')
            host=urlsplit(origin).netloc
            if host in self.by_host or urlsplit(origin).hostname==urlsplit(self.manager).hostname:raise IsolationDenied('Preview origins must be unique and use a host separate from the manager')
            if app is not None and (not isinstance(app,str) or not PROJECT.fullmatch(app) or app in apps):raise IsolationDenied('Each data namespace belongs to one project')
            if not isinstance(jobs,list) or not 1<=len(jobs)<=1000:raise IsolationDenied('Invalid project jobs')
            backend=entry.get('backend_jobs',[])
            if not isinstance(backend,list) or backend and (backend!=jobs or app is not None):raise IsolationDenied('Backend projects require an explicit independent runtime assignment')
            for job in jobs:
                if not isinstance(job,str) or not JOB.fullmatch(job) or job in self.by_job:raise IsolationDenied('Each job belongs to one project')
                self.by_job[job]=(project,origin,app)
                if backend:self.backend_jobs.add(job)
            projects.add(project);apps.add(app) if app is not None else None
            self.by_host[host]=(project,origin,app)

    @staticmethod
    def path(raw):
        if not isinstance(raw,str) or len(raw)>4096 or any(ord(c)<32 for c in raw):raise IsolationDenied('Invalid preview path')
        parsed=urlsplit(raw)
        if parsed.scheme or parsed.netloc or parsed.fragment or parsed.query:raise IsolationDenied('Only direct preview paths are allowed')
        decoded=unquote(parsed.path,errors='strict')
        if any(ord(c)<32 or ord(c)==127 for c in decoded) or '%' in decoded or '\\' in decoded or not decoded.startswith('/preview/') or any(p in ('','.','..') or p.startswith('.') for p in decoded.strip('/').split('/')):
            raise IsolationDenied('Invalid preview path')
        parts=decoded.strip('/').split('/')
        if len(parts)<3 or not JOB.fullmatch(parts[1]):raise IsolationDenied('Invalid preview job path')
        return decoded,parts

    def resolve(self,host,raw_path,method,request_origin=None):
        """Call only after verifying the local proxy and owner identity.

        Host/Origin checks add project isolation; they do not authenticate a
        client. A gateway must not expose this function on a public listener.
        """
        if host not in self.by_host:raise IsolationDenied('This preview host is not registered')
        decoded,parts=self.path(raw_path);job=parts[1]
        assignment=self.by_job.get(job)
        if assignment!=self.by_host[host]:raise IsolationDenied('This job does not belong to this preview address')
        project,origin,app=assignment
        if request_origin is not None and request_origin!=origin:raise IsolationDenied('Cross-project requests are not allowed')
        data=parts[2:4]==['api','data']
        backend=parts[2:4]==['api','backend']
        if backend:
            if job not in self.backend_jobs or method not in ('GET','POST','PUT','PATCH','DELETE') or len(parts)<5 or any(not re.fullmatch('[A-Za-z0-9_.-]+',p) for p in parts[4:]) or len('/'.join(parts[4:]))>299:raise IsolationDenied('Invalid backend preview operation')
            if method!='GET' and request_origin!=origin:raise IsolationDenied('Backend writes require the exact preview origin')
        elif data:
            if not app or method not in ('GET','POST','PUT') or len(parts) not in (5,6):raise IsolationDenied('Invalid project data operation')
            if method in ('GET','POST') and len(parts)!=5 or method=='PUT' and len(parts)!=6:raise IsolationDenied('Invalid project data operation')
            if not PROJECT.fullmatch(parts[4]) or len(parts)==6 and not JOB.fullmatch(parts[5]):raise IsolationDenied('Invalid project data identifier')
            if method!='GET' and request_origin!=origin:raise IsolationDenied('Project writes require the exact preview origin')
        else:
            suffix='.'+parts[-1].rsplit('.',1)[-1].lower()
            if method not in ('GET','HEAD') or suffix not in PUBLIC:raise IsolationDenied('Only public preview files may be read')
        return Target(project,origin,job,decoded,app,data,job in self.backend_jobs,backend)

    def canonical_url(self,raw_path):
        decoded,parts=self.path(raw_path)
        assignment=self.by_job.get(parts[1])
        if assignment is None:raise IsolationDenied('This preview needs an explicit project assignment')
        self.resolve(urlsplit(assignment[1]).netloc,decoded,'GET')
        return assignment[1]+quote(decoded,safe='/')

    def headers(self,target):
        connection="'self'" if target.data_app or target.backend_job else "'none'"
        return {
            'Cache-Control':'private, no-store',
            'X-Content-Type-Options':'nosniff',
            'Referrer-Policy':'no-referrer',
            'Origin-Agent-Cluster':'?1',
            'Cross-Origin-Opener-Policy':'same-origin',
            'Cross-Origin-Resource-Policy':'same-origin',
            'Permissions-Policy':'document-domain=(), camera=(), microphone=(), geolocation=()',
            'Content-Security-Policy':"default-src 'self' data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src "+connection+"; frame-src 'none'; form-action 'none'; object-src 'none'; base-uri 'none'; frame-ancestors "+self.manager,
        }

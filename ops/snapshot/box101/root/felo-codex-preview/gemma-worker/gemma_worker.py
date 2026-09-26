"""Isolated preview coding worker. No production credentials or workspaces."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse
import mimetypes
import sqlite3
from html.parser import HTMLParser

ROOT = Path(os.environ['FELO_WORKER_ROOT']).resolve()
TOKEN = os.environ['FELO_WORKER_TOKEN']
MODEL = os.environ.get('FELO_WORKER_MODEL', 'felo-gemma-worker')
OLLAMA = os.environ['FELO_OLLAMA_URL'].rstrip('/')
IMAGE = os.environ.get('FELO_WORKER_IMAGE', 'nikolaik/python-nodejs:python3.11-nodejs20')
CODEX_URL = os.environ.get('FELO_CODEX_URL', '').rstrip('/')
CODEX_TOKEN = os.environ.get('FELO_CODEX_TOKEN', '')
ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
LOCK = threading.RLock()
ID = re.compile(r'^[a-f0-9]{32}$')
PUBLIC = {'.html', '.css', '.js', '.json', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.ico', '.woff', '.woff2'}
DATA_NAME = re.compile(r'^[a-z][a-z0-9_-]{0,79}$')
PREVIEW_ORIGIN = os.environ.get('FELO_PREVIEW_PUBLIC_ORIGIN','http://100.94.252.30:8082')
OWNER_ACCESS = os.environ.get('FELO_PREVIEW_OWNER_AUTH') == '1'
OWNER_LOGIN = os.environ.get('FELO_OWNER_LOGIN','').strip().lower()
MANAGER_ORIGIN = os.environ.get('FELO_MANAGER_ORIGIN','http://100.81.117.27:8081')
if OWNER_ACCESS:
    origin = urlparse(PREVIEW_ORIGIN)
    manager = urlparse(MANAGER_ORIGIN)
    if not OWNER_LOGIN or any(c.isspace() for c in OWNER_LOGIN) or ',' in OWNER_LOGIN or any(x.scheme!='https' or not (x.hostname or '').endswith('.ts.net') or x.path or x.query or x.fragment or x.username for x in [origin,manager]):
        raise ValueError('Secure preview requires an owner and exact Tailscale HTTPS origins')
PROJECT_ACCESS = None
PROJECT_REGISTRY = None
if os.environ.get('FELO_PREVIEW_ISOLATION_REGISTRY'):
    if not OWNER_ACCESS:
        raise ValueError('Project isolation requires owner authentication')
    from preview_worker_access import WorkerProjectAccess
    PROJECT_ACCESS = WorkerProjectAccess(os.environ['FELO_PREVIEW_ISOLATION_REGISTRY'],
        os.environ.get('FELO_PREVIEW_GATEWAY_TOKEN',''), TOKEN, PREVIEW_ORIGIN, MANAGER_ORIGIN, OWNER_LOGIN)
    from project_registry import ProjectRegistry
    pool_path=Path(os.environ['FELO_PREVIEW_ORIGIN_POOL'])
    with pool_path.open('rb') as pool_file:
        pool_bytes=pool_file.read(20001)
    if len(pool_bytes)>20000:raise ValueError('Project origin pool exceeds its limit')
    PROJECT_REGISTRY=ProjectRegistry(os.environ['FELO_PREVIEW_ISOLATION_REGISTRY'],MANAGER_ORIGIN,json.loads(pool_bytes))
    if any(urlparse(o).hostname!=urlparse(PREVIEW_ORIGIN).hostname or o==PREVIEW_ORIGIN for o in PROJECT_REGISTRY.origins):
        raise ValueError('Project origins must use dedicated ports on this worker host')
DATA_SDK = '''/* Felo preview data v1. Server-managed; do not edit. */
(() => {
  const base = new URL('api/data/', document.currentScript.src).href;
  async function call(collection, method = 'GET', body, id = '') {
    if (!/^[a-z][a-z0-9_-]{0,79}$/.test(collection)) throw new Error('Invalid collection');
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 10000);
    let response;
    try {
      response = await fetch(base + collection + (id ? '/' + encodeURIComponent(id) : ''), {
        method, signal:controller.signal, headers: {'Content-Type':'application/json','X-Felo-Data':'1'},
        ...(body ? {body:JSON.stringify(body)} : {})
      });
    } catch (_) {
      throw new Error(method === 'GET' ? 'Server data could not be loaded. Try Refresh.' : 'Save could not be confirmed. Refresh before retrying.');
    } finally { clearTimeout(timer); }
    const result = await response.json();
    if (!response.ok) { const error = new Error(result.error || 'Server storage unavailable'); error.status = response.status; throw error; }
    return result;
  }
  window.FeloData = Object.freeze({
    list: async collection => (await call(collection)).records,
    create: (collection, data, id = Array.from(crypto.getRandomValues(new Uint8Array(16)), x => x.toString(16).padStart(2,'0')).join('')) => call(collection, 'POST', {id,data}),
    update: (collection, record, data) => call(collection, 'PUT', {version:record.version,data}, record.id)
  });
})();
'''

class DataError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def validate_runtime(runtime):
    if runtime is None:
        return None
    if not isinstance(runtime, dict) or set(runtime) != {'type', 'app'} or runtime['type'] != 'server-records-v1' or not isinstance(runtime['app'], str) or not DATA_NAME.fullmatch(runtime['app']):
        raise ValueError('Invalid preview runtime')
    return runtime

def records(app, collection, method, payload=None, record_id=None):
    """Bounded test data only. Namespaces prevent accidental mixing, not user authentication."""
    if not DATA_NAME.fullmatch(app) or not DATA_NAME.fullmatch(collection):
        raise DataError('Invalid data namespace')
    if record_id is not None and not ID.fullmatch(record_id):
        raise DataError('Invalid record ID')
    db = sqlite3.connect(ROOT / 'preview-data.sqlite', timeout=5)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS records (app TEXT, collection TEXT, id TEXT, version INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(app,collection,id))')
        if method == 'GET':
            rows = db.execute('SELECT id,version,data FROM records WHERE app=? AND collection=? ORDER BY rowid LIMIT 1001', (app,collection)).fetchall()
            return {'records':[{'id':r[0],'version':r[1],'data':json.loads(r[2])} for r in rows]}
        expected = {'id','data'} if method == 'POST' else {'version','data'}
        if method not in ('POST','PUT') or not isinstance(payload,dict) or set(payload) != expected or not isinstance(payload['data'],dict):
            raise DataError('Invalid data operation')
        data = json.dumps(payload['data'], sort_keys=True, allow_nan=False, ensure_ascii=False)
        if len(data.encode('utf-8')) > 16000:
            raise DataError('Record exceeds the 16 KB test limit',413)
        db.execute('BEGIN IMMEDIATE')
        if method == 'POST':
            record_id = payload['id']
            if not isinstance(record_id,str) or not ID.fullmatch(record_id):
                raise DataError('Invalid record ID')
            previous = db.execute('SELECT version,data FROM records WHERE app=? AND collection=? AND id=?',(app,collection,record_id)).fetchone()
            if previous:
                if previous[1] != data:
                    raise DataError('That record ID already exists; refresh before retrying.',409)
                return {'id':record_id,'version':previous[0],'data':json.loads(previous[1])}
            count = db.execute('SELECT count(*) FROM records WHERE app=?',(app,)).fetchone()[0]
            if count >= 1000:
                raise DataError('This test project reached its 1000-record limit.',409)
            version = 1
            db.execute('INSERT INTO records VALUES(?,?,?,?,?)',(app,collection,record_id,version,data))
        else:
            if not record_id or type(payload['version']) is not int or payload['version'] < 1:
                raise DataError('A current record version is required')
            version = payload['version'] + 1
            changed = db.execute('UPDATE records SET version=?,data=? WHERE app=? AND collection=? AND id=? AND version=?',
                (version,data,app,collection,record_id,payload['version'])).rowcount
            if changed != 1:
                raise DataError('This record changed or is missing. Refresh before saving again.',409)
        db.commit()
        return {'id':record_id,'version':version,'data':json.loads(data)}
    finally:
        db.close()

class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and not attrs.get('src') and attrs.get('type', '') in ('', 'module', 'text/javascript', 'application/javascript'):
            self.current = [attrs.get('type') == 'module', '']
    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data
    def handle_endtag(self, tag):
        if tag == 'script' and self.current is not None:
            self.scripts.append(self.current)
            self.current = None

class MarkupChecks(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.lines = source.splitlines()
        self.errors = []
        self.document = False
        self.body = False
        self.closed_document = False
        self.closed_body = False
    def handle_starttag(self, tag, attrs):
        self.document = self.document or tag == 'html'
        self.body = self.body or tag == 'body'
    def finish(self):
        if self.document and not self.closed_document:
            self.errors.append('Full HTML document is missing its closing html tag')
        if self.body and not self.closed_body:
            self.errors.append('HTML page is missing its closing body tag')
    def handle_endtag(self, tag):
        self.closed_document = self.closed_document or tag == 'html'
        self.closed_body = self.closed_body or tag == 'body'
        line, column = self.getpos()
        raw = '\n'.join(self.lines[line-1:])[column:]
        if not re.match(r'</[A-Za-z][\w:-]*\s*>', raw):
            self.errors.append('Malformed closing tag near line ' + str(line))
    def handle_startendtag(self, tag, attrs):
        if tag in ('button', 'textarea', 'select', 'script'):
            self.errors.append(tag + ' needs an explicit closing tag')

class References(HTMLParser):
    """Check literal HTML references; dynamic JS/CSS URLs still need browser review."""
    def __init__(self):
        super().__init__()
        self.urls = []
        self.modules = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        field = 'href' if tag in ('a', 'link') else 'src' if tag in ('script', 'img', 'iframe', 'source', 'audio', 'video') else None
        if field and attrs.get(field):
            self.urls.append(attrs[field])
        if tag == 'script' and attrs.get('src') and attrs.get('type') == 'module':
            self.modules.append(attrs['src'])


def reference_target(workspace, page, url):
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme == 'data':
            return None
        raise ValueError('Only relative local references are supported: ' + url[:120])
    name = unquote(parsed.path)
    if not name:  # Same-page fragment or query.
        return None
    if name.startswith('/') or '\\' in name:
        raise ValueError('Use a relative project path: ' + url[:120])
    target = (page.parent / name).resolve()
    if not target.is_relative_to(workspace.resolve()) or not target.is_file() or target.suffix.lower() not in PUBLIC:
        raise ValueError('Missing or unsupported local file: ' + url[:120])
    return target


def check_frontend(job):
    workspace = ROOT / job / 'workspace'
    checks = ROOT / job / 'checks'
    checks.mkdir(exist_ok=True)
    results, sources, modules = [], [], set()
    for page in sorted(p for p in workspace.rglob('*') if p.suffix.lower() == '.html' and p.is_file()):
        name = page.relative_to(workspace).as_posix()
        html = page.read_text(encoding='utf-8')
        parser, markup, refs = Scripts(), MarkupChecks(html), References()
        parser.feed(html)
        markup.feed(html)
        markup.finish()
        refs.feed(html)
        modal = bool(re.search(r'\b(?:alert|confirm|prompt)\s*\(', html))
        results.append({'file': name + ' modal-dialog policy', 'passed': not modal,
                        'detail': 'Use inline feedback instead of blocking browser dialogs.' if modal else ''})
        results.append({'file': name + ' closing-tag checks', 'passed': not markup.errors, 'detail': '; '.join(markup.errors)})
        errors = []
        for url in refs.urls:
            try:
                target = reference_target(workspace, page, url)
                if target and url in refs.modules:
                    modules.add(target)
            except ValueError as error:
                errors.append(str(error))
        results.append({'file': name + ' local references', 'passed': not errors, 'detail': '; '.join(errors)[:1500]})
        sources += [(name + ':inline-' + str(i), code, module) for i, (module, code) in enumerate(parser.scripts)]
    for path in sorted(p for p in workspace.rglob('*') if p.suffix.lower() == '.js' and p.is_file()):
        name = path.relative_to(workspace).as_posix()
        source = path.read_text(encoding='utf-8')
        modal = bool(re.search(r'\b(?:alert|confirm|prompt)\s*\(', source))
        results.append({'file': name + ' modal-dialog policy', 'passed': not modal,
                        'detail': 'Use inline feedback instead of blocking browser dialogs.' if modal else ''})
        sources.append((name, source, path.resolve() in modules))
    for index, (name, source, module) in enumerate(sources):
        filename = str(index) + ('-module.mjs' if module else '-script.js')
        (checks / filename).write_text(source, encoding='utf-8')
        result = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--pids-limit', '64', '--memory', '256m', '--cpus', '1',
                                 '--mount', 'type=bind,src=' + str(checks) + ',dst=/checks,readonly', IMAGE, 'node', '--check', '/checks/' + filename],
                                capture_output=True, text=True, timeout=20)
        results.append({'file': name, 'passed': result.returncode == 0, 'detail': result.stderr[-1500:]})
    return results

def state_path(job):
    if not isinstance(job, str) or not ID.fullmatch(job):
        raise ValueError('Invalid job ID')
    return ROOT / job / 'state.json'

def save(state):
    dest = state_path(state['id'])
    temp = dest.with_suffix('.tmp')
    temp.write_text(json.dumps(state), encoding='utf-8')
    temp.replace(dest)

def read(job):
    return json.loads(state_path(job).read_text(encoding='utf-8'))

def artifacts(job):
    workspace = ROOT / job / 'workspace'
    output = []
    total = 0
    for path in sorted(workspace.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlinks cannot be published')
        if not path.is_file():
            continue
        rel = path.relative_to(workspace)
        if any(p.startswith('.') or p in ('node_modules', '__pycache__') for p in rel.parts):
            continue
        if path.suffix.lower() in ('.key', '.pem', '.crt'):
            continue
        if path.stat().st_size > 2_000_000:
            raise ValueError('Artifact size exceeds the preview limit')
        data = path.read_bytes()
        total += len(data)
        if len(data) > 2_000_000 or total > 12_000_000 or len(output) >= 200:
            raise ValueError('Artifact size exceeds the preview limit')
        output.append({'path': rel.as_posix(), 'sha256': hashlib.sha256(data).hexdigest(), 'data': base64.b64encode(data).decode()})
    return output

def validate_routing(routing):
    if routing is None:
        return None
    if not isinstance(routing,dict) or set(routing) != {'agent','version','primary','fallback'} or routing['agent'] != 'frontend' or type(routing['version']) is not int or routing['version']<1:
        raise ValueError('Invalid agent routing')
    for role in ('primary','fallback'):
        item=routing[role]
        if role=='fallback' and item is None:
            continue
        if not isinstance(item,dict) or set(item)!={'provider','model','think'} or type(item['think']) is not bool or item['provider'] not in ('ollama','codex') or not isinstance(item['model'],str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,119}',item['model']):
            raise ValueError('Invalid agent model')
        if item['provider']=='codex' and (item['model']!='gpt-6-astra' or not item['think']):
            raise ValueError('Codex worker supports Astra High')
    return routing

def generation_request(brief, existing, correction=None, selected=None):
    schema = {'type': 'object', 'required': ['summary', 'files', 'edits'], 'properties': {
        'summary': {'type': 'string'},
        'edits': {'type': 'array', 'maxItems': 30, 'items': {'type': 'object',
            'required': ['path', 'find', 'replace'], 'properties': {
                'path': {'type': 'string'}, 'find': {'type': 'string'}, 'replace': {'type': 'string'}}, 'additionalProperties': False}},
        'files': {'type': 'array', 'maxItems': 12, 'items': {
            'type': 'object', 'required': ['path', 'content', 'base_sha256'],
            'properties': {'path': {'type': 'string'}, 'content': {'type': 'string'}, 'base_sha256': {'type':['string','null'], 'enum':[None]+[hashlib.sha256(v.encode('utf-8')).hexdigest() for k,v in existing.items() if k != 'felo-data.js']}},
            'additionalProperties': False}}}, 'additionalProperties': False}
    editable = [p for p in existing if p != 'felo-data.js']
    if editable:
        schema['properties']['edits']['items']['properties']['path']['enum'] = editable
        schema['properties']['edits']['items']['properties']['find']['maxLength'] = 4096
    else:
        schema['properties']['files']['minItems'] = 1
        schema['properties']['edits']['maxItems'] = 0
    prompt = ('You are Felo\'s dedicated frontend agent. Own the browser interface: implement the requested branding, responsive layout, semantic controls, keyboard access, clear loading/errors, and accurate data rendering. '
        'Preserve the existing visual style unless the approved brief requests a change. Check your code against every current phase acceptance criterion. '
        'You are coding a web prototype. Return JSON with files and edits. '
        'For each edit, find must be an exact nonempty unique substring copied from the existing file, and replace is its replacement. '
        'Use minimal targeted edits when practical; preserve all code outside the requested change. '
        'For a larger function change you may return a complete existing file in files ONLY with base_sha256 copied exactly from source_hashes for that path. '
        'For new files set base_sha256 to null. Use either a complete guarded file replacement OR edits for a given file, not both. '
        'You may add new pages, styles or scripts in later phases. '
        'Link new pages and assets using relative paths, including ../ when needed inside subfolders. Every linked local file must exist. '
        'Keep reasoning brief and focus on the requested change. '
        'Keep added pages concise and complete, with closing body and html tags. Avoid decorative content unrelated to the acceptance criteria. '
        'Use empty files or edits arrays when unnecessary. Return actual code, '
        'not instructions, markdown fences, patches, or claims that tools were run. The server will write these files. '
        'Use index.html as the entry point; only relative local assets, HTML/CSS/JavaScript, no packages or network calls. '
        'Implement ONLY the current phase and every requested correction. Preserve earlier working behavior and saved data, '
        'including older localStorage formats. Do not invent demo records or implement future phases. '
        'Existing source and the brief are supplied below. Output only files that need changing. '
        'Use visible labels, keyboard controls, safe text rendering and inline validation; never alert/confirm/prompt. '
        'The summary describes your edits only. Do not claim you tested them. Do not write report.md; the server writes its own execution record.')
    if 'felo-data.js' in existing:
        prompt += (' SERVER DATA MODE replaces the offline-storage constraint: use the supplied felo-data.js SDK for all application records. '
            'Include <script src="felo-data.js"></script> before your own script (adjust relative path on subpages). Never edit felo-data.js. '
            'await FeloData.list("tasks") returns an array of {id,version,data}; await FeloData.create("tasks",{text,done:false}) returns one record; '
            'await FeloData.update("tasks",record,{...record.data,done:true}) returns the updated record. Keep returned id and version. '
            'Collections use lowercase letters, digits, hyphens or underscores. No localStorage fallback for application data. '
            'Disable submit while saving; show success only after server response. Show visible loading and inline save errors. '
            'On a 409 error, show a conflict message and refresh data; never overwrite blindly. Provide a Refresh button. '
            'Use only this same-origin API, no other network calls. This is shared TEST data without user accounts or production authentication.')
    request = {'model': selected['model'] if selected else MODEL, 'think': selected['think'] if selected else True, 'stream': False, 'format': schema,
        'options': {'temperature': 0.1, 'num_ctx': 32768, 'num_predict': 12000},
        'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': json.dumps({
            'approved_phase': brief, 'existing_files': existing,
            'source_hashes':{k:hashlib.sha256(v.encode('utf-8')).hexdigest() for k,v in existing.items() if k != 'felo-data.js'},
            'check_feedback': correction})}]}
    return request

def generate_files(brief, existing, correction=None, selected=None):
    import urllib.request
    request = generation_request(brief, existing, correction, selected)
    req = urllib.request.Request(OLLAMA + '/api/chat', data=json.dumps(request).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=240) as response:
        result = json.load(response)
    return json.loads(result['message']['content'])

def generate_codex(job, brief, existing, correction):
    import urllib.request
    if not CODEX_URL or not CODEX_TOKEN:
        raise ValueError('Codex subscription worker is not connected')
    request = generation_request(brief, existing, correction)
    # Historical feedback may quote outdated snippets; only existing_files is source.
    request['format']['properties']['edits']['maxItems'] = 0
    request['format']['properties']['files']['minItems'] = 1
    request['messages'][0]['content'] += (' CODEX CORRECTION RULE: Return complete corrected files, not text edits; edits must be empty. '
        'For every existing file use its exact source_hashes value as base_sha256. '
        'Only existing_files contains current source. Historical feedback may quote obsolete code. '
        'The current phase and latest requestedFix take precedence over historical corrections from earlier work. '
        'Review the entire affected function for runtime errors; do not just repeat the suggested snippet.')
    payload = {'id':job, 'instruction':request['messages'][0]['content'],
               'context':json.loads(request['messages'][1]['content']), 'schema':request['format']}
    req = urllib.request.Request(CODEX_URL + '/correct', data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+CODEX_TOKEN})
    with urllib.request.urlopen(req, timeout=660) as response:
        return json.load(response)


def resolve_generation(result, existing):
    if not isinstance(result, dict) or not isinstance(result.get('summary'), str):
        raise ValueError('The model did not return a valid file response')
    new_files = result.get('files', [])
    edits = result.get('edits', [])
    if not isinstance(new_files, list) or not isinstance(edits, list) or len(new_files) > 12 or len(edits) > 30:
        raise ValueError('Invalid generated edit batch')
    changed = {}
    replacements = set()
    for raw_item in new_files:
        if not isinstance(raw_item,dict) or set(raw_item)-{'path','content','base_sha256'}:
            raise ValueError('Invalid generated file')
        item = {k:v for k,v in raw_item.items() if k != 'base_sha256'}
        validate_generation({'summary':'', 'files':[item]})
        name = item['path']
        if name == 'felo-data.js' or name in changed:
            raise ValueError('Managed or duplicate file cannot be replaced')
        if raw_item.get('base_sha256') is not None:
            if name not in existing or raw_item['base_sha256'] != hashlib.sha256(existing[name].encode('utf-8')).hexdigest():
                raise ValueError('File replacement requires its exact current source hash')
            changed[name] = item['content']
            replacements.add(name)
            continue
        # Some small models echo a full file alongside its exact edits. Never apply
        # that rewrite: only the independently validated edits may change it.
        if item['path'] in existing and item['path'] != 'felo-data.js' and any(isinstance(e,dict) and e.get('path') == item['path'] for e in edits):
            continue
        if item['path'] == 'felo-data.js' or item['path'] in existing or item['path'] in changed:
            raise ValueError('Use exact edits for existing files instead of replacing the entire file')
        changed[item['path']] = item['content']
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {'path', 'find', 'replace'} or any(not isinstance(v, str) for v in edit.values()):
            raise ValueError('Invalid generated edit')
        name, old, new = edit['path'], edit['find'], edit['replace']
        if name in replacements:
            raise ValueError('Use a guarded replacement or exact edits for a file, not both')
        if len(old) > 4096:
            raise ValueError('Edit find text exceeds 4096 characters. Split the change into smaller exact edits.')
        if name == 'felo-data.js' or name not in existing or not old:
            raise ValueError('Edit must reference an existing file and nonempty exact text')
        content = changed.get(name, existing[name])
        if content.count(old) != 1:
            raise ValueError('Edit text must match exactly once in ' + name + '; copy the exact current source')
        changed[name] = content.replace(old, new, 1)
    files = validate_generation({'summary':result['summary'], 'files':[{'path':k, 'content':v} for k,v in changed.items()]})
    # Reject file/directory conflicts before writing any part of the batch.
    names = set(existing) | set(changed)
    for name in names:
        if any(parent.as_posix() in names for parent in Path(name).parents if parent.as_posix() != '.'):
            raise ValueError('A generated path conflicts with an existing file or folder')
    return files


def validate_generation(result):
    if not isinstance(result, dict) or not isinstance(result.get('summary'), str):
        raise ValueError('The model did not return a valid file response')
    files = result.get('files')
    if not isinstance(files, list) or not 1 <= len(files) <= 12:
        raise ValueError('The model did not return one to twelve changed files')
    seen = set()
    total = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {'path', 'content'}:
            raise ValueError('Invalid generated file')
        name, content = item['path'], item['content']
        if not isinstance(name, str) or not isinstance(content, str):
            raise ValueError('Generated paths and contents must be text')
        if not re.fullmatch(r'[A-Za-z0-9_./-]+', name) or name.startswith('/') or any(x in ('', '.', '..') or x.startswith('.') for x in name.split('/')):
            raise ValueError('Generated path is outside the allowed workspace')
        if name in seen or name.lower() == 'report.md' or Path(name).suffix.lower() not in {'.html', '.css', '.js', '.json', '.svg', '.md', '.txt'}:
            raise ValueError('Generated file is duplicate or unsupported')
        total += len(content.encode('utf-8'))
        if len(content.encode('utf-8')) > 100000 or total > 300000:
            raise ValueError('Generated files exceed the prototype size limit')
        seen.add(name)
    return files


def run(job):
    state = read(job)
    base = ROOT / job
    workspace = base / 'workspace'
    workspace.mkdir(exist_ok=True)
    if state.get('templateSeed'):
        if state.get('parent'):
            raise ValueError('Template seed cannot inherit an existing project')
        from template_seed import copy_seed
        copy_seed(state['templateSeed'], workspace)
    parent_files = artifacts(state['parent']) if state.get('parent') else []
    previous = {}
    for artifact in parent_files:
        if artifact['path'] == 'report.md':
            continue
        dest = workspace / artifact['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(artifact['data']))
        previous[artifact['path']] = artifact['sha256']
    if state.get('runtime'):
        (workspace / 'felo-data.js').write_text(DATA_SDK, encoding='utf-8')
    state.update(status='running', started=time.time(), mode='structured_files')
    save(state)
    checks = []
    summary = ''
    routing=validate_routing(state.get('routing'))
    if routing:
        primary=routing['primary'];fallback=routing['fallback']
        selections=[fallback] if state.get('useFallback') else ([primary] if primary['provider']=='codex' else [primary,primary]+([fallback] if fallback else []))
    else:
        gemma={'provider':'ollama','model':MODEL,'think':True};codex={'provider':'codex','model':'gpt-6-astra','think':True}
        selections=[codex] if state.get('provider')=='codex' else [gemma,gemma]+([codex] if CODEX_URL and CODEX_TOKEN else [])
    state['attempts'] = []
    for attempt, selected in enumerate(selections):
        provider='codex' if selected['provider']=='codex' else 'gemma' if 'gemma' in selected['model'] else 'ollama'
        existing = {}
        for p in sorted(workspace.rglob('*')):
            if p.is_file() and p.suffix in ('.html', '.css', '.js', '.json', '.svg', '.md', '.txt'):
                existing[p.relative_to(workspace).as_posix()] = p.read_text(encoding='utf-8')
        if sum(len(s) for s in existing.values()) > 100000:
            raise ValueError('Project exceeds the current coding context limit')
        state['active_provider'] = provider
        state['active_model'] = selected['model']
        state['agent'] = 'frontend'
        state['attempts'].append({'provider':provider,'model':selected['model'],'agent':'frontend','started':time.time()})
        save(state)
        try:
            result = (generate_codex(job,state['brief'],existing,checks) if provider == 'codex'
                      else generate_files(state['brief'],existing,checks if attempt else None,selected))
            (base / ('model-output-' + str(attempt) + '.json')).write_text(json.dumps(result), encoding='utf-8')
            files = resolve_generation(result, existing)  # Resolve and validate the whole batch before any write.
        except Exception as error:
            detail = ('Codex correction could not finish; inspect its connection, subscription limits and local diagnostics.'
                      if provider == 'codex' and not isinstance(error,ValueError) else str(error)[:500])
            checks = [{'file':provider + ' correction', 'passed':False, 'detail':detail}]
            state['attempts'][-1].update(passed=False,detail=detail)
            save(state)
            continue
        for item in files:
            dest = workspace / item['path']
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(item['content'], encoding='utf-8')
            if dest.read_text(encoding='utf-8') != item['content']:
                raise ValueError('Generated file verification failed')
        summary = result['summary'][:6000]
        checks = check_frontend(job) if (workspace / 'index.html').is_file() else [{'file':'index.html','passed':False,'detail':'No frontend entry point was produced'}]
        state['attempts'][-1].update(passed=all(c['passed'] for c in checks),finished=time.time())
        save(state)
        if all(c['passed'] for c in checks):
            break
    files = artifacts(job)
    changed = [f['path'] for f in files if previous.get(f['path']) != f['sha256']]
    state['checks'] = checks
    state['changed_files'] = changed
    if not [name for name in changed if name != 'felo-data.js']:
        state['error'] = 'The worker did not produce any changed project files. Its completion claim was not accepted.'
    if any(not c['passed'] for c in checks):
        state['error'] = 'The generated frontend failed independent checks.'
    report = '# Build execution record\n\nGenerated by the worker controller from actual file results.\n\n'
    report += 'Agent: frontend. Model settings version: '+str(routing['version'] if routing else 'legacy')+'.\n\n'
    report += 'Model attempts: ' + ', '.join(x['model'] + (' (checks passed)' if x.get('passed') else ' (failed)') for x in state['attempts']) + '\n\n'
    report += 'Changed and read-back verified files:\n' + '\n'.join('- ' + name for name in changed)
    report += '\n\nIndependent checks:\n' + '\n'.join('- ' + c['file'] + ': ' + ('PASS' if c['passed'] else 'FAIL: ' + c['detail']) for c in checks)
    report += '\n\nBrowser behavior has NOT been tested by this worker. Frontend review is required. No phase was approved.\n\n'
    report += '## Model description (not test evidence)\n\n' + summary
    (workspace / 'report.md').write_text(report, encoding='utf-8')
    state.update(report=report, finished=time.time(), status='failed' if state.get('error') else 'done')
    state['files'] = [{k: v for k, v in f.items() if k != 'data'} for f in artifacts(job)]
    save(state)


def recover_interrupted():
    # Interrupted work is never silently replayed after a worker restart.
    for path in ROOT.glob('*/state.json'):
        state = json.loads(path.read_text())
        if state['status'] == 'running':
            state_path(state['id'])
            ids = subprocess.check_output(['docker', 'ps', '-aq', '--filter', 'label=felo-preview-job=' + state['id']], text=True).split()
            if ids:
                subprocess.run(['docker', 'rm', '-f', *ids], check=True, capture_output=True)
            state.update(status='failed', error='Worker restarted during this task. Review and retry explicitly.')
            save(state)

def loop():
    recover_interrupted()
    backend=None
    planning=None
    if os.environ.get('FELO_BACKEND_BUILDS_ROOT'):
        from backend_build_api import instance,scheduler_initialized
        backend=instance();backend.recover();scheduler_initialized()
        from planning_rescue import instance as planning_instance
        planning=planning_instance();planning.recover()
    while True:
        with LOCK:
            queued = [json.loads(p.read_text()) for p in ROOT.glob('*/state.json')]
            queued = sorted((s for s in queued if s['status'] == 'queued'), key=lambda s: s['created'])
        if queued:
            job = queued[0]['id']
            try:
                run(job)
            except Exception as error:
                state = read(job)
                state.update(status='failed', finished=time.time(), error='Worker failed: ' + str(error)[:300])
                save(state)
        else:
            if planning:
                try:
                    if planning.tick():continue
                except Exception:print('Planning queue needs attention; no plan was accepted.',flush=True)
            if backend:
                try:backend.tick()
                except Exception:
                    # Preserve the durable build and keep frontend scheduling alive.
                    print('Backend build queue needs attention; no frontend job was changed.',flush=True)
            time.sleep(2)

def read_preview_state(job):
    if PROJECT_ACCESS and job in PROJECT_ACCESS.policy().backend_jobs:
        from backend_build_api import bridge
        return bridge(PROJECT_REGISTRY).state(job)
    return read(job)

class Handler(BaseHTTPRequestHandler):
    @property
    def backend_registry(self):return PROJECT_REGISTRY
    def respond(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        values = self.headers.get_all('Authorization', []) if hasattr(self.headers, 'get_all') else [self.headers.get('Authorization', '')]
        return (len(values) == 1 and values[0].isascii()
                and not self.headers.get('X-Felo-Project-Origin')
                and hmac.compare_digest(values[0], 'Bearer ' + TOKEN))

    def preview_access(self):
        self.project_target = None
        self.project_headers = None
        if PROJECT_ACCESS and unquote(urlparse(self.path).path).startswith('/preview/'):
            from preview_isolation import IsolationDenied
            try:
                if not self.headers.get('X-Felo-Project-Origin'):
                    target=PROJECT_ACCESS.legacy_redirect(self.headers,self.client_address[0],self.path,self.command,read_preview_state)
                    self.send_response(307);self.send_header('Location',target);self.send_header('Content-Length','0');self.send_header('Cache-Control','private, no-store');self.send_header('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'");self.end_headers()
                    return False
                self.project_target, self.project_headers = PROJECT_ACCESS.authorize(
                    self.headers, self.client_address[0], self.path, self.command, read_preview_state)
                if self.project_target.backend_job:
                    from backend_build_api import bridge
                    bridge(PROJECT_REGISTRY).serve(self)
                    return False
                return True
            except (IsolationDenied, ValueError, UnicodeError):
                self.respond(403, {'error':'Open this app through its assigned project address.'})
                return False
        if not OWNER_ACCESS or not unquote(urlparse(self.path).path).startswith('/preview/'):
            return True
        valid = (self.client_address[0] == '127.0.0.1'
                 and self.headers.get('Host') == urlparse(PREVIEW_ORIGIN).netloc
                 and self.headers.get('Tailscale-User-Login','').strip().lower() == OWNER_LOGIN)
        if self.command not in ('GET','HEAD','OPTIONS'):
            valid = valid and self.headers.get('Origin') == PREVIEW_ORIGIN
        if not valid:
            self.respond(403,{'error':'Open this preview through its private HTTPS address using the authorized Tailscale account.'})
        return valid

    def data_request(self):
        parts = unquote(urlparse(self.path).path).strip('/').split('/')
        if len(parts) < 4 or parts[0] != 'preview' or parts[2:4] != ['api','data']:
            return False
        try:
            if len(parts) not in (5,6) or urlparse(self.path).query:
                raise DataError('Invalid data route')
            if self.headers.get('X-Felo-Data') != '1' or self.headers.get('Origin',PREVIEW_ORIGIN) != PREVIEW_ORIGIN:
                raise DataError('This data request is not allowed.',403)
            state = read(parts[1])
            runtime = validate_runtime(state.get('runtime'))
            if self.project_target and (not runtime or runtime['app'] != self.project_target.data_app):
                raise DataError('Project data assignment changed.',403)
            if state['status'] != 'done' or not runtime:
                raise DataError('Server data is unavailable for this preview.',404)
            method = self.command
            if (method in ('GET','POST') and len(parts)!=5) or (method=='PUT' and len(parts)!=6):
                raise DataError('Invalid data operation')
            payload = None
            if method != 'GET':
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 20000 or self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                    raise DataError('Use a JSON request within the test data limit',413)
                payload = json.loads(self.rfile.read(length),parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid number')))
            body = records(runtime['app'],parts[4],method,payload,parts[5] if len(parts)==6 else None)
            self.respond(200,body)
        except DataError as error:
            self.respond(error.status,{'error':str(error)})
        except (ValueError,KeyError,TypeError,FileNotFoundError):
            self.respond(400,{'error':'Invalid preview data request'})
        except sqlite3.Error:
            self.respond(503,{'error':'Server data is temporarily unavailable. Refresh before retrying.'})
        return True

    def do_PUT(self):
        if not self.preview_access():return
        if not self.data_request():
            self.respond(404,{'error':'Unknown endpoint'})

    def do_PATCH(self):
        if self.preview_access():self.respond(404,{'error':'Unknown endpoint'})

    def do_DELETE(self):
        if self.preview_access():self.respond(404,{'error':'Unknown endpoint'})

    def do_POST(self):
        if not self.preview_access():return
        if self.data_request():
            return
        if not self.authorized():
            return self.respond(401, {'error': 'Unauthorized'})
        if self.path.startswith('/planning-rescues'):
            from planning_rescue import handle
            return handle(self)
        if self.path.startswith('/backend-builds'):
            from backend_build_api import handle
            return handle(self)
        if self.path.startswith('/backend-checks'):
            from backend_proxy import handle
            if handle(self):return
        if self.path != '/jobs':
            return self.respond(404, {'error': 'Unknown endpoint'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length < 384000:
                raise ValueError('Invalid request length')
            data = json.loads(self.rfile.read(length))
            job, brief, parent = data['id'], data['brief'], data.get('parent')
            project_key=data.get('projectKey')
            if project_key is not None and (not isinstance(project_key,str) or not DATA_NAME.fullmatch(project_key)):
                raise ValueError('Invalid stable project key')
            from template_seed import validate_seed
            template_seed = validate_seed(data.get('templateSeed'))
            if template_seed and parent:
                raise ValueError('A template seed cannot have a parent')
            runtime = validate_runtime(data.get('runtime'))
            provider = data.get('provider','gemma')
            if provider not in ('gemma','ollama','codex'):
                raise ValueError('Invalid coding provider')
            routing=validate_routing(data.get('routing'))
            use_fallback=data.get('useFallback',False)
            if type(use_fallback) is not bool or (use_fallback and (not routing or not routing['fallback'])):
                raise ValueError('Invalid fallback selection')
            path = state_path(job)
            if not isinstance(brief, str) or not 20 <= len(brief) <= 30000:
                raise ValueError('Invalid brief')
            if parent and read(parent)['status'] != 'done':
                raise ValueError('Parent must be a completed worker job')
            if parent and read(parent).get('runtime') != runtime:
                raise ValueError('Later phases must retain the same data namespace')
            if parent and read(parent).get('projectKey') is not None and read(parent)['projectKey'] != project_key:
                raise ValueError('Later phases must retain the same project identity')
            identity = {'brief':brief,'parent':parent}
            if project_key is not None:
                identity['projectKey']=project_key
            if template_seed:
                identity['templateSeed'] = template_seed
            if provider != 'gemma':
                identity['provider'] = provider
            if routing:
                identity.update(routing=routing,useFallback=use_fallback)
            if runtime:
                identity['runtime'] = runtime
            digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
            with LOCK:
                if path.exists():
                    existing = read(job)
                    if existing['digest'] != digest:
                        return self.respond(409, {'error': 'Job ID already belongs to another request'})
                    assignment=PROJECT_REGISTRY.describe(job) if PROJECT_REGISTRY else {}
                    return self.respond(200, {'id': job, 'status': existing['status'],**assignment})
                assignment=PROJECT_REGISTRY.register_job(project_key,job,runtime,parent) if PROJECT_REGISTRY else {}
                path.parent.mkdir(mode=0o700,exist_ok=True)
                save({'id': job, 'brief': brief, 'parent': parent, 'projectKey':project_key, 'templateSeed':template_seed, 'runtime':runtime, 'provider':provider, 'routing':routing,'useFallback':use_fallback, 'digest': digest, 'status': 'queued', 'created': time.time()})
            self.respond(202, {'id': job, 'status': 'queued',**assignment})
        except (ValueError, TypeError, KeyError, FileNotFoundError):
            self.respond(400, {'error': 'Invalid job request'})

    def do_GET(self):
        if self.path=='/browser-storage-export' and PROJECT_ACCESS:
            try:
                PROJECT_ACCESS.owner_navigation(self.headers,self.client_address[0],'GET')
                from browser_storage_export import HTML
                raw=HTML.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','private, no-store');self.send_header('Cross-Origin-Opener-Policy','same-origin');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");self.end_headers();self.wfile.write(raw)
            except ValueError:self.respond(403,{'error':'Use the private owner browser session.'})
            return
        if not self.preview_access():return
        if self.data_request():
            return
        path = unquote(urlparse(self.path).path)
        if path.startswith('/preview/'):
            parts = path.split('/', 3)
            try:
                job = parts[2]
                state_path(job)
                if read(job)['status'] != 'done':
                    return self.respond(404, {'error': 'Preview is not ready'})
                name = parts[3] if len(parts) > 3 and parts[3] else 'index.html'
                if any(p in ('..', '.') or p.startswith('.') for p in name.split('/')) or '\\' in name:
                    raise ValueError('Invalid preview path')
                root = ROOT / job / 'workspace'
                file = (root / name).resolve()
                if not file.is_relative_to(root) or file.suffix.lower() not in PUBLIC or not file.is_file():
                    return self.respond(404, {'error': 'File not found'})
                raw = file.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
                self.send_header('Content-Length', str(len(raw)))
                if self.project_headers:
                    for key,value in self.project_headers.items():self.send_header(key,value)
                else:
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.send_header('Cache-Control', 'private, no-store')
                    self.send_header('Referrer-Policy', 'same-origin')
                    connection = "'self'" if read(job).get('runtime') else "'none'"
                    self.send_header('Content-Security-Policy', "default-src 'self' data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src " + connection + "; form-action 'none'; object-src 'none'; base-uri 'none'; frame-ancestors " + MANAGER_ORIGIN)
                self.end_headers()
                self.wfile.write(raw)
            except (ValueError, FileNotFoundError):
                self.respond(404, {'error': 'Preview not found'})
            return
        if not self.authorized():
            return self.respond(401, {'error': 'Unauthorized'})
        if self.path.startswith('/planning-rescues'):
            from planning_rescue import handle
            return handle(self)
        if self.path.startswith('/backend-builds'):
            from backend_build_api import handle
            return handle(self)
        if self.path.startswith('/backend-checks'):
            from backend_proxy import handle
            if handle(self):return
        if path == '/connections':
            online=False
            if CODEX_URL and CODEX_TOKEN:
                try:
                    import urllib.request
                    req=urllib.request.Request(CODEX_URL+'/health',headers={'Authorization':'Bearer '+CODEX_TOKEN})
                    with urllib.request.urlopen(req,timeout=5) as response:
                        health=json.load(response);online=health.get('service')=='felo-codex-corrections' and health.get('model')=='gpt-6-astra' and health.get('executableReady',True) is True
                except Exception:
                    pass
            return self.respond(200,{'codex':online})
        try:
            parts = path.strip('/').split('/')
            if len(parts) == 2 and parts[0] == 'jobs':
                state = read(parts[1])
                assignment=PROJECT_REGISTRY.describe(parts[1]) if PROJECT_REGISTRY else {}
                return self.respond(200, {**{k: v for k, v in state.items() if k not in ('brief', 'digest')},**assignment})
            if len(parts) == 3 and parts[0] == 'jobs' and parts[2] == 'artifacts':
                if read(parts[1])['status'] != 'done':
                    return self.respond(409, {'error': 'Job is not complete'})
                return self.respond(200, {'files': artifacts(parts[1])})
            self.respond(404, {'error': 'Unknown endpoint'})
        except (ValueError, FileNotFoundError):
            self.respond(404, {'error': 'Job not found'})

    def log_message(self, *_):
        pass

if __name__ == '__main__':
    threading.Thread(target=loop, daemon=True).start()
    if OWNER_ACCESS:
        threading.Thread(target=ThreadingHTTPServer(('127.0.0.1',8082),Handler).serve_forever,daemon=True).start()
    ThreadingHTTPServer(('100.94.252.30', 8082), Handler).serve_forever()

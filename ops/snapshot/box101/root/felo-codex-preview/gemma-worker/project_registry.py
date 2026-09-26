"""Atomic assignment of jobs to pre-provisioned private project origins.

This does not open ports, modify Tailscale, copy data or execute jobs. Only the
authenticated controller may reach the worker call sites that use this store.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import threading
try:
    import fcntl
except ImportError:  # Windows tests use the shared in-process lock below.
    fcntl = None
from preview_isolation import PreviewIsolation, IsolationDenied, exact_origin, PROJECT, JOB

_locks = {}
_locks_guard = threading.Lock()


def read_document(path, manager):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(1_000_001)
        if len(raw) > 1_000_000:
            raise IsolationDenied('Project registry exceeds its limit')
        document = json.loads(raw)
        policy = PreviewIsolation(document)
        if policy.manager != manager:
            raise IsolationDenied('Project manager origin does not match')
        return document
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise IsolationDenied('Project registry is unavailable or invalid') from error


class ProjectRegistry:
    def __init__(self, path, manager, origins):
        self.path = Path(path).resolve()
        self.manager = exact_origin(manager)
        if not isinstance(origins, list) or not 1 <= len(origins) <= 100:
            raise ValueError('Declare a bounded pre-provisioned origin pool')
        self.origins = [exact_origin(origin) for origin in origins]
        if len(set(self.origins)) != len(self.origins):
            raise ValueError('Duplicate origin pool entries')
        # Validate separation from the manager even before the pool is used.
        PreviewIsolation({'version': 1, 'manager_origin': self.manager, 'projects': [
            {'project': 'pool-' + str(i), 'origin': origin, 'data_app': None,
             'jobs': [format(i, '032x')]} for i, origin in enumerate(self.origins)]})
        self.read()
        with _locks_guard:
            self.lock = _locks.setdefault(str(self.path), threading.RLock())

    def read(self):
        document = read_document(self.path, self.manager)
        if any(entry['origin'] not in self.origins for entry in document['projects']):
            raise IsolationDenied('Registry contains an origin outside the provisioned pool')
        return document

    @contextmanager
    def locked(self):
        with self.lock:
            fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
            try:
                if fcntl:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                if fcntl:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    def write(self, document):
        PreviewIsolation(document)
        raw = (json.dumps(document, sort_keys=True, separators=(',', ':')) + '\n').encode()
        if len(raw) > 1_000_000:
            raise IsolationDenied('Project registry exceeds its limit')
        fd, name = tempfile.mkstemp(prefix='.registry-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            if os.name == 'posix':
                directory = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def describe(self, job):
        assignment = PreviewIsolation(self.read()).by_job.get(job)
        if assignment is None:
            raise IsolationDenied('Job has no registered project address')
        project, origin, _ = assignment
        return {'projectKey': project, 'previewOrigin': origin,
                'previewURL': origin + '/preview/' + job + '/index.html'}

    def register_job(self, project, job, runtime=None, parent=None, profile='frontend'):
        if profile not in ('frontend','node-http-v1') or profile=='node-http-v1' and runtime is not None:
            raise IsolationDenied('Invalid preview runtime profile')
        if not isinstance(project, str) or not PROJECT.fullmatch(project):
            raise IsolationDenied('A valid stable project key is required')
        if not isinstance(job, str) or not JOB.fullmatch(job):
            raise IsolationDenied('A valid job ID is required')
        if parent is not None and (not isinstance(parent, str) or not JOB.fullmatch(parent) or parent == job):
            raise IsolationDenied('Invalid parent job')
        if runtime is not None and (not isinstance(runtime, dict) or set(runtime) != {'type', 'app'} or
                runtime['type'] != 'server-records-v1' or not isinstance(runtime['app'], str) or not PROJECT.fullmatch(runtime['app'])):
            raise IsolationDenied('Invalid project runtime')
        app = runtime['app'] if runtime else None
        with self.locked():
            document = self.read()
            policy = PreviewIsolation(document)
            entry = next((p for p in document['projects'] if p['project'] == project), None)
            existing = policy.by_job.get(job)
            if existing is not None and (job in policy.backend_jobs)!=(profile=='node-http-v1'):
                raise IsolationDenied('A job cannot change its runtime profile')
            if entry is not None and bool(entry.get('backend_jobs'))!=(profile=='node-http-v1'):
                raise IsolationDenied('Existing projects cannot silently change runtime profile')
            if existing is not None and (existing[0] != project or existing[2] != app):
                raise IsolationDenied('Job already belongs to a different project')
            if parent is not None:
                source = policy.by_job.get(parent)
                if source is None or source[0] != project or source[2] != app:
                    raise IsolationDenied('A parent must belong to this project and data namespace')
                if (parent in policy.backend_jobs)!=(profile=='node-http-v1'):
                    raise IsolationDenied('A parent must use the same runtime profile')
            if profile=='node-http-v1' and document['version']==1:
                document['version']=2
                for previous in document['projects']:previous['backend_jobs']=[]
            if entry is not None and entry['data_app'] != app:
                raise IsolationDenied('A project cannot switch its data namespace')
            if entry is None:
                if app is not None and app != project:
                    raise IsolationDenied('New projects require their own data namespace')
                used = {p['origin'] for p in document['projects']}
                origin = next((origin for origin in self.origins if origin not in used), None)
                if origin is None:
                    raise IsolationDenied('No provisioned project address is available')
                entry = {'project': project, 'origin': origin, 'data_app': app, 'jobs': []}
                if document['version']==2:entry['backend_jobs']=[]
                document['projects'].append(entry)
            if job not in entry['jobs']:
                entry['jobs'].append(job)
                if profile=='node-http-v1':entry['backend_jobs'].append(job)
                self.write(document)
            return {'projectKey': project, 'previewOrigin': entry['origin'],
                    'previewURL': entry['origin'] + '/preview/' + job + '/index.html'}

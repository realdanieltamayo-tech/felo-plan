"""Worker-side authorization for explicitly enabled project gateways.

The gateway credential cannot be used as the worker-control credential. No
registry, listener, model job or existing workspace is created by this module.
"""
import hmac
import json
from pathlib import Path
from urllib.parse import urlsplit
from preview_isolation import PreviewIsolation, IsolationDenied, exact_origin


def one(headers, name, required=False):
    values = headers.get_all(name, []) if hasattr(headers, 'get_all') else [v for k, v in headers.items() if k.lower() == name.lower()]
    if len(values) > 1 or required and len(values) != 1:
        raise IsolationDenied('Missing or ambiguous gateway header')
    return values[0] if values else None


class WorkerProjectAccess:
    def __init__(self, registry_path, gateway_token, control_token, worker_origin, manager_origin, owner):
        if (not isinstance(gateway_token, str) or not 32 <= len(gateway_token) <= 256
                or any(not 33 <= ord(c) <= 126 for c in gateway_token)
                or hmac.compare_digest(gateway_token, control_token)):
            raise ValueError('Use a distinct dedicated gateway credential')
        self.worker = exact_origin(worker_origin)
        self.manager = exact_origin(manager_origin)
        self.owner = owner.strip().lower()
        if not self.owner or any(c.isspace() for c in self.owner) or ',' in self.owner:
            raise ValueError('One owner is required for the project gateway')
        self.path = Path(registry_path)
        self.token = gateway_token
        self.policy()  # Invalid or missing configuration prevents startup.

    def policy(self):
        try:
            with self.path.open('rb') as source:
                raw = source.read(1_000_001)
            if len(raw) > 1_000_000:
                raise IsolationDenied('Project registry exceeds its limit')
            policy = PreviewIsolation(json.loads(raw))
            if policy.manager != self.manager:
                raise IsolationDenied('Project manager origin does not match')
            return policy
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise IsolationDenied('Project registry is unavailable or invalid') from error

    def authorize(self, headers, peer, raw_path, method, read_state):
        if peer != '127.0.0.1':
            raise IsolationDenied('Use the local authenticated project gateway')
        credential = one(headers, 'Authorization', True)
        if not isinstance(credential, str) or not credential.isascii() or not hmac.compare_digest(credential, 'Bearer ' + self.token):
            raise IsolationDenied('Use the project gateway credential')
        if one(headers, 'Host', True) != urlsplit(self.worker).netloc:
            raise IsolationDenied('Invalid worker host')
        if one(headers, 'Tailscale-User-Login', True).strip().lower() != self.owner:
            raise IsolationDenied('Use the authorized owner')
        origin = exact_origin(one(headers, 'X-Felo-Project-Origin', True))
        forwarded_origin = one(headers, 'Origin')
        if forwarded_origin is not None and forwarded_origin != self.worker:
            raise IsolationDenied('Invalid gateway data origin')
        policy = self.policy()
        target = policy.resolve(urlsplit(origin).netloc, raw_path, method, origin)
        if target.data_request:
            if one(headers, 'X-Felo-Data', True) != '1' or forwarded_origin != self.worker:
                raise IsolationDenied('Use the project data gateway')
        if target.backend_request:
            if one(headers,'X-Felo-Backend',True)!='1' or forwarded_origin!=self.worker:
                raise IsolationDenied('Use the project backend gateway')
        if one(headers, 'Transfer-Encoding') is not None:
            raise IsolationDenied('Unsupported request framing')
        length = one(headers, 'Content-Length')
        if method in ('GET', 'HEAD'):
            if length not in (None, '0'):
                raise IsolationDenied('Unexpected read body')
        elif not length or not length.isascii() or not length.isdigit() or not 0 < int(length) <= 20000 or (one(headers, 'Content-Type', True) or '').split(';')[0] != 'application/json':
            raise IsolationDenied('Use a bounded JSON data request')
        try:
            state = read_state(target.job)
            runtime = state.get('runtime')
            expected = {'type': 'server-records-v1', 'app': target.data_app} if target.data_app else None
            if target.backend_job:expected={'type':'node-http-v1','app':target.project}
            if state.get('status') != 'done' or runtime != expected:
                raise IsolationDenied('Job and project data assignment do not match')
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise IsolationDenied('Project job is unavailable or does not match its assignment') from error
        return target, policy.headers(target)

    def owner_navigation(self, headers, peer, method):
        if peer!='127.0.0.1' or method not in ('GET','HEAD'):
            raise IsolationDenied('Legacy preview data and writes are disabled')
        if one(headers,'Host',True)!=urlsplit(self.worker).netloc or one(headers,'Tailscale-User-Login',True).strip().lower()!=self.owner:
            raise IsolationDenied('Use the authorized private preview entry')
        if one(headers,'Origin') not in (None,self.worker) or one(headers,'X-Felo-Project-Origin') is not None or one(headers,'Transfer-Encoding') is not None or one(headers,'Content-Length') not in (None,'0'):
            raise IsolationDenied('Invalid legacy navigation')
        return True

    def legacy_redirect(self, headers, peer, raw_path, method, read_state):
        """Old owner bookmarks may navigate; old content/data never execute here."""
        self.owner_navigation(headers,peer,method)
        policy=self.policy();decoded,parts=policy.path(raw_path)
        if parts[2:4] in (['api','data'],['api','backend']):
            raise IsolationDenied('Legacy preview data access is disabled')
        url=policy.canonical_url(decoded);assignment=policy.by_job[parts[1]]
        try:
            state=read_state(parts[1]);expected={'type':'server-records-v1','app':assignment[2]} if assignment[2] else None
            if parts[1] in policy.backend_jobs:expected={'type':'node-http-v1','app':assignment[0]}
            if state.get('status')!='done' or state.get('runtime')!=expected:raise IsolationDenied('Legacy build does not match its project')
        except (OSError,ValueError,KeyError,TypeError) as error:
            raise IsolationDenied('Legacy build is unavailable') from error
        return url

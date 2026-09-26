"""Versioned private backend contract. Identity is not an owner approval token."""
import base64,hashlib,json,re
from backend_checks import BackendCheckError,http_checks,source_files

PROFILES=('node-http-v1','node-http-records-v1')
def report_profile(profile):
 if profile not in PROFILES:raise BackendCheckError('Unsupported backend profile')
 return 'node-http-records-check-v1' if profile=='node-http-records-v1' else 'node-http-ephemeral-v1'

def contract(value):
 if not isinstance(value,dict) or set(value)!={'profile','projectKey','planRevision','planDigest','phase','checks'}:
  raise BackendCheckError('Invalid backend contract fields')
 if value['profile'] not in PROFILES:raise BackendCheckError('Unsupported backend profile')
 if not isinstance(value['projectKey'],str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,79}',value['projectKey']):raise BackendCheckError('Invalid backend project')
 if not isinstance(value['planRevision'],str) or not re.fullmatch(r'[a-f0-9]{32}',value['planRevision']):raise BackendCheckError('Invalid plan revision')
 if not isinstance(value['planDigest'],str) or not re.fullmatch(r'[a-f0-9]{64}',value['planDigest']):raise BackendCheckError('Invalid plan digest')
 if type(value['phase']) is not int or not 1<=value['phase']<=6:raise BackendCheckError('Invalid backend phase')
 return {**value,'checks':http_checks(value['checks'])}

def source_digest(files):
 return hashlib.sha256(''.join(n+'\0'+hashlib.sha256(b).hexdigest()+'\n' for n,b in sorted(source_files(files).items())).encode()).hexdigest()

def artifacts(files):
 return [{'path':n,'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for n,b in sorted(source_files(files).items())]

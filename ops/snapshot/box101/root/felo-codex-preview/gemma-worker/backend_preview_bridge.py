"""Narrow project-gateway bridge. No worker-control endpoint is exposed here."""
import base64,json,mimetypes,time
from backend_checks import BackendCheckError
from backend_builder import verify_result
from backend_contract import source_digest
from preview_isolation import IsolationDenied,PUBLIC

class BackendPreviewBridge:
 def __init__(self,builder,registry,rpc):self.builder=builder;self.registry=registry;self.rpc=rpc
 def verified(self,job):
  s=self.builder.load(job)
  if s['status']!='done' or not s.get('execution'):raise IsolationDenied('Backend build is not ready')
  verify_result(s['checkRequest'],s['execution'])
  if source_digest(s['files'])!=s['execution']['sourceDigest'] or s['request']['contract']!=s['execution']['contract']:raise IsolationDenied('Backend build source identity changed')
  return s
 def state(self,job):
  s=self.verified(job)
  return {'status':'done','runtime':{'type':'node-http-v1','app':s['request']['contract']['projectKey']}}
 def register(self,job):
  s=self.verified(job);files=s['files'];project=s['request']['contract']['projectKey']
  if not files.get('public/index.html'):raise BackendCheckError('A backend preview requires public/index.html')
  return {**self.registry.register_job(project,job,profile='node-http-v1'),'id':job,'ownerReviewRequired':True,'profile':s['request']['contract']['profile']}
 def serve(self,h):
  target=h.project_target
  if not target or not target.backend_job:return False
  try:
   s=self.verified(target.job)
   if s['request']['contract']['projectKey']!=target.project:raise IsolationDenied('Backend project changed')
   if target.backend_request:
    parts=target.path.strip('/').split('/');request={'method':h.command,'path':'/'+'/'.join(parts[4:]),'body':''}
    if h.command!='GET':
     length=int(h.headers['Content-Length']);deadline=time.monotonic()+3;raw=bytearray()
     while len(raw)<length:
      remaining=deadline-time.monotonic()
      if remaining<=0:raise TimeoutError('Backend request body timed out')
      h.connection.settimeout(remaining);part=h.rfile.read1(min(65536,length-len(raw)))
      if not part:raise BackendCheckError('Incomplete backend request body')
      raw.extend(part)
     request['body']=raw.decode('utf-8')
    opened=self.rpc({'op':'preview_open','id':s['execution']['id'],'project':target.project})
    if opened['status']!='active':
     self.reply(h,503,json.dumps({'error':'The backend preview is starting. No API request was sent; try again when it is ready.','previewState':opened['status']}).encode(),'application/json');return True
    result=self.rpc({'op':'preview_invoke','id':opened['run'],'project':target.project,'request':request})
    if result['sourceDigest']!=s['execution']['sourceDigest'] or result['run']!=opened['run']:raise IsolationDenied('Preview response identity changed')
    raw=base64.b64decode(result['body'],validate=True)
    if len(raw)>32768 or len(raw)!=result['bytes']:raise BackendCheckError('Preview response exceeded its limit')
    self.reply(h,result['status'],raw,'application/json; charset=utf-8')
   else:
    name=target.path.split('/',3)[3];extension='.'+name.rsplit('.',1)[-1].lower()
    # Only the designated browser folder is readable, even for .js/.json.
    if extension not in PUBLIC or 'public/'+name not in s['files']:
     self.reply(h,404,b'{"error":"Browser file not found"}','application/json');return True
    raw=s['files']['public/'+name].encode();self.reply(h,200,raw,mimetypes.guess_type(name)[0] or 'application/octet-stream')
  except (IsolationDenied,BackendCheckError,ValueError,KeyError,TypeError):
   self.reply(h,503,b'{"error":"The backend preview could not confirm this request. Check its current state before retrying."}','application/json')
  except OSError:
   self.reply(h,503,b'{"error":"The backend connection could not confirm this request. Do not repeat a write until its state is checked."}','application/json')
  return True
 @staticmethod
 def reply(h,status,raw,kind):
  h.send_response(status);h.send_header('Content-Type',kind);h.send_header('Content-Length',str(len(raw)))
  for k,v in h.project_headers.items():h.send_header(k,v)
  h.end_headers()
  if h.command!='HEAD':h.wfile.write(raw)
  h.close_connection=True

"""Bounded local Unix-socket RPC; no network listener or generated-code access."""
import json,os,socket,socketserver,stat,struct,threading,time
from pathlib import Path
from backend_checks import BackendCheckError,JOB
from backend_contract import contract

MAX_MESSAGE=1000000

def receive(sock,timeout=3):
 deadline=time.monotonic()+timeout
 def read(size):
  data=bytearray()
  while len(data)<size:
   remaining=deadline-time.monotonic()
   if remaining<=0:raise BackendCheckError('Backend message timed out')
   sock.settimeout(remaining)
   part=sock.recv(min(65536,size-len(data)))
   if not part:raise BackendCheckError('Incomplete backend message')
   data.extend(part)
  return bytes(data)
 size=struct.unpack('!I',read(4))[0]
 if not 0<size<=MAX_MESSAGE:raise BackendCheckError('Backend message exceeds its limit')
 def unique(pairs):
  obj={}
  for k,v in pairs:
   if k in obj:raise BackendCheckError('Duplicate backend fields')
   obj[k]=v
  return obj
 return json.loads(read(size).decode('utf-8'),object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(BackendCheckError('Invalid JSON number')))

def send(sock,value):
 raw=json.dumps(value,ensure_ascii=True,separators=(',',':')).encode()
 if len(raw)>MAX_MESSAGE:raise BackendCheckError('Backend message exceeds its limit')
 sock.sendall(struct.pack('!I',len(raw))+raw)

def call(path,request,timeout=8):
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
  sock.settimeout(timeout);sock.connect(str(path));send(sock,request);result=receive(sock,timeout)
 if not result.get('ok'):raise BackendCheckError(result.get('error','Backend request failed'))
 return result['result']

def dispatch(supervisor,request):
 if not isinstance(request,dict):raise BackendCheckError('Invalid backend request')
 op=request.get('op');fields={'submit':{'op','id','files','contract'},'status':{'op','id'},'artifacts':{'op','id'},'preview_open':{'op','id','project'},'preview_status':{'op','id','project'},'preview_stop':{'op','id','project'},'preview_invoke':{'op','id','project','request'}}
 if op not in fields or set(request)!=fields[op]:raise BackendCheckError('Invalid backend operation')
 if not isinstance(request['id'],str) or not JOB.fullmatch(request['id']):raise BackendCheckError('Invalid backend job ID')
 if op.startswith('preview_'):
  import re
  if not isinstance(request['project'],str) or not re.fullmatch('[a-z][a-z0-9_-]{0,79}',request['project']):raise BackendCheckError('Invalid preview project')
  runtime=getattr(supervisor,'previews',None)
  if runtime is None:raise BackendCheckError('Backend previews are not connected')
  operation={'preview_open':runtime.open,'preview_status':runtime.get,'preview_stop':runtime.stop,'preview_invoke':runtime.invoke}[op]
  return operation(request['id'],request['project'],*([request['request']] if op=='preview_invoke' else []))
 if op=='submit':
  spec=contract(request['contract'])
  return supervisor.submit(request['id'],request['files'],spec['checks'],context=spec)
 if op=='status':return supervisor.get(request['id'])
 return supervisor.artifacts(request['id'])

class Handler(socketserver.BaseRequestHandler):
 def handle(self):
  self.request.settimeout(3)
  try:
   # Socket permissions and peer identity both apply, including inherited FDs.
   _,uid,_=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
   if uid!=os.geteuid():raise BackendCheckError('Backend peer is not authorized')
   result=dispatch(self.server.supervisor,receive(self.request))
   send(self.request,{'ok':True,'result':result})
  except (BackendCheckError,ValueError,TypeError,KeyError) as error:
   try:send(self.request,{'ok':False,'error':str(error)[:240]})
   except OSError:pass
  except Exception:
   try:send(self.request,{'ok':False,'error':'Backend service is temporarily unavailable'})
   except OSError:pass

class LocalServer(getattr(socketserver,'UnixStreamServer',socketserver.BaseServer)):
 request_queue_size=8
 def handle_error(self,*_):pass

def serve(supervisor):
 """Caller holds the supervisor lock before replacing its own stale socket."""
 if os.name!='posix' or not supervisor.locked:raise BackendCheckError('Exclusive Linux supervisor ownership is required')
 path=supervisor.root/'control.sock'
 if path.exists() or path.is_symlink():
  info=path.lstat()
  if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.geteuid():raise BackendCheckError('Unexpected backend socket path')
  path.unlink()
 server=LocalServer(str(path),Handler);os.chmod(path,0o600);server.supervisor=supervisor
 threading.Thread(target=server.serve_forever,daemon=True).start()
 return server

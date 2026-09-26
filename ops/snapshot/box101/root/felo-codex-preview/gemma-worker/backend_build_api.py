"""Controller-only backend build queue; shares the existing worker scheduler."""
import json,os,re,time
from backend_builder import Builder
from backend_checks import BackendCheckError
from backend_generation import generate
from backend_rpc import call
SCHEDULER_INITIALIZED=False

def scheduler_initialized():
 global SCHEDULER_INITIALIZED
 SCHEDULER_INITIALIZED=True

def instance():
 root=os.environ.get('FELO_BACKEND_BUILDS_ROOT');socket=os.environ.get('FELO_BACKEND_SOCKET')
 if not root or not socket:raise BackendCheckError('Backend generation is not connected')
 config={'ollama_url':os.environ['FELO_OLLAMA_URL'],'codex_url':os.environ.get('FELO_CODEX_URL'),'codex_token':os.environ.get('FELO_CODEX_TOKEN')}
 return Builder(root,lambda *args:generate(config,*args),lambda request:call(socket,request))

def bridge(registry):
 if registry is None:raise BackendCheckError('Project preview isolation is not connected')
 from backend_preview_bridge import BackendPreviewBridge
 return BackendPreviewBridge(instance(),registry,lambda request:call(os.environ['FELO_BACKEND_SOCKET'],request,timeout=10))

def handle(h):
 if not h.authorized():h.respond(401,{'error':'Unauthorized'});return
 if not os.environ.get('FELO_BACKEND_BUILDS_ROOT'):h.respond(503,{'error':'Backend generation is not connected'});return
 try:
  b=instance()
  if h.command=='GET' and h.path=='/backend-builds':
   h.respond(200,{'profile':'node-http-v1','profiles':['node-http-v1','node-http-records-v1'],'schedulerInitialized':SCHEDULER_INITIALIZED,'ownerReviewRequired':True,'deployment':False,'persistentData':False})
  elif h.command=='POST' and (h.path=='/backend-builds' or re.fullmatch(r'/backend-builds/[a-f0-9]{32}/preview',h.path)):
   lengths=h.headers.get_all('Content-Length',[])
   if len(lengths)!=1 or not re.fullmatch('[0-9]{1,6}',lengths[0]) or h.headers.get_all('Transfer-Encoding',[]) or h.headers.get('Content-Type','').split(';')[0]!='application/json':raise BackendCheckError('Invalid backend build framing')
   length=int(lengths[0])
   if not 0<length<=350000:raise BackendCheckError('Backend build request exceeds its limit')
   deadline=time.monotonic()+3;raw=bytearray()
   while len(raw)<length:
    remaining=deadline-time.monotonic()
    if remaining<=0:raise BackendCheckError('Backend build request timed out')
    h.connection.settimeout(remaining);part=h.rfile.read1(min(65536,length-len(raw)))
    if not part:raise BackendCheckError('Incomplete backend build request')
    raw.extend(part)
   if h.path!='/backend-builds':
    if json.loads(raw)!={}:raise BackendCheckError('Preview registration has no mutable fields')
    h.respond(200,bridge(h.backend_registry).register(h.path.split('/')[2]))
   else:h.respond(202,b.submit(json.loads(raw)))
  elif h.command=='GET' and (match:=re.fullmatch(r'/backend-builds/([a-f0-9]{32})(/artifacts)?',h.path)):
   h.respond(200,b.artifacts(match[1]) if match[2] else b.get(match[1]))
  else:h.respond(404,{'error':'Unknown backend build endpoint'})
 except (BackendCheckError,ValueError,TypeError):h.respond(400,{'error':'Invalid or conflicting backend build request'})
 except Exception:h.respond(503,{'error':'Backend build queue is temporarily unavailable. Retain the same job ID when retrying.'})
 finally:h.close_connection=True

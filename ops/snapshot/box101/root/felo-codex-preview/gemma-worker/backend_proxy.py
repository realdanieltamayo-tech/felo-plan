"""Private controller-only transport. Never mounted in the project gateway."""
import json,os,re,time
from backend_rpc import call
from backend_checks import BackendCheckError

def handle(handler):
 path=handler.path
 if path!='/backend-checks' and not path.startswith('/backend-checks/'):return False
 # The HTTP worker must authenticate first; recheck at this boundary as well.
 if not handler.authorized():handler.respond(401,{'error':'Unauthorized'});return True
 socket_path=os.environ.get('FELO_BACKEND_SOCKET')
 if not socket_path:handler.respond(503,{'error':'Backend checks are not connected'});return True
 try:
  if handler.command=='POST' and path=='/backend-checks':
   lengths=handler.headers.get_all('Content-Length',[])
   if len(lengths)!=1 or not re.fullmatch('[0-9]{1,6}',lengths[0]) or handler.headers.get_all('Transfer-Encoding',[]):raise BackendCheckError('Invalid backend request framing')
   size=int(lengths[0])
   if not 0<size<=750000:raise BackendCheckError('Backend request exceeds its limit')
   if handler.headers.get('Content-Type','').split(';')[0]!='application/json':raise BackendCheckError('Backend request must be JSON')
   handler.connection.settimeout(3)
   # read1 avoids extending a deadline indefinitely with a trickled request.
   deadline=time.monotonic()+3;raw=bytearray()
   while len(raw)<size:
    remaining=deadline-time.monotonic()
    if remaining<=0:raise BackendCheckError('Backend request timed out')
    handler.connection.settimeout(remaining);part=handler.rfile.read1(min(65536,size-len(raw)))
    if not part:raise BackendCheckError('Incomplete backend request')
    raw.extend(part)
   data=json.loads(raw)
   if not isinstance(data,dict) or set(data)!={'id','files','contract'}:raise BackendCheckError('Invalid backend submission')
   result=call(socket_path,{'op':'submit',**data});handler.respond(202,result)
  elif handler.command=='GET' and (match:=re.fullmatch(r'/backend-checks/([a-f0-9]{32})(/artifacts)?',path)):
   result=call(socket_path,{'op':'artifacts' if match[2] else 'status','id':match[1]});handler.respond(200,result)
  else:handler.respond(404,{'error':'Unknown backend endpoint'})
 except (BackendCheckError,ValueError,TypeError):handler.respond(400,{'error':'Invalid or conflicting backend request'})
 except OSError:handler.respond(503,{'error':'Backend checker is temporarily unavailable; keep the same job ID when retrying'})
 finally:handler.close_connection=True
 return True

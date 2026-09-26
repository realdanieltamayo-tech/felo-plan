"""Private preview gateway. Not enabled until its registry is reviewed.

Run behind local Tailscale Serve. This process never invokes a model, changes
the registry, allocates ports or accepts worker-control requests.
"""
import argparse,http.client,json,os,socket,threading,time,urllib.error,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote,urlsplit
from preview_isolation import PreviewIsolation,IsolationDenied

def shutdown(sock):
    try:sock.shutdown(socket.SHUT_RDWR)
    except OSError:pass

class DeadlineResponse:
    def __init__(self,response,connection,abort_socket,timer,expired):
        self.response=response;self.connection=connection;self.abort_socket=abort_socket
        self.timer=timer;self.expired=expired;self.status=response.status;self.headers=response.headers
    def read(self,size):
        result=self.response.read(size)
        if self.expired.is_set():raise TimeoutError('Worker response deadline exceeded')
        return result
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):
        self.timer.cancel();self.response.close();self.connection.close();self.abort_socket.close()

def open_worker(request,timeout=15,connection_factory=http.client.HTTPConnection):
    """One fixed local hop, with a deadline spanning headers and body reads."""
    url=urlsplit(request.full_url)
    if url.scheme!='http' or url.netloc!='127.0.0.1:8082' or not url.path.startswith('/preview/') or url.query or url.fragment:
        raise ValueError('Invalid fixed worker target')
    started=time.monotonic();connection=connection_factory('127.0.0.1',8082,timeout=timeout)
    abort_socket=None;timer=None;expired=threading.Event()
    try:
        connection.connect()
        # Keep a socket reference even when HTTP/1.0 closes the connection's
        # normal reference after headers. Shutdown interrupts a slow body read.
        abort_socket=connection.sock.dup()
        def expire():expired.set();shutdown(abort_socket)
        remaining=timeout-(time.monotonic()-started)
        if remaining<=0:raise TimeoutError('Worker connection deadline exceeded')
        timer=threading.Timer(remaining,expire);timer.daemon=True;timer.start()
        connection.request(request.get_method(),url.path,body=request.data,headers=dict(request.header_items()))
        response=connection.getresponse()
        if expired.is_set():response.close();raise TimeoutError('Worker response deadline exceeded')
        return DeadlineResponse(response,connection,abort_socket,timer,expired)
    except BaseException:
        if timer:timer.cancel()
        if abort_socket:abort_socket.close()
        connection.close();raise

class BoundedServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,handler,max_connections=16):
        if type(max_connections) is not int or not 1<=max_connections<=64:raise ValueError('Invalid gateway connection limit')
        self.slots=threading.BoundedSemaphore(max_connections)
        super().__init__(address,handler)
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            try:request.settimeout(1);request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            except OSError:pass
            self.shutdown_request(request);return
        try:super().process_request(request,address)
        except BaseException:self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()

class Gateway:
    def __init__(self,registry,owner_login,worker_origin,gateway_token,fetcher=None,request_timeout=20,registry_path=None):
        self.policy=PreviewIsolation(registry)
        self.registry_path=registry_path
        self.owner=owner_login.strip().lower()
        if not self.owner or any(c.isspace() for c in self.owner) or ',' in self.owner:raise ValueError('One owner identity is required')
        self.worker_origin=worker_origin
        worker=urlsplit(worker_origin)
        if worker.scheme!='https' or not (worker.hostname or '').endswith('.ts.net') or worker.path or worker.query or worker.fragment or worker.username:raise ValueError('Invalid worker public origin')
        if not isinstance(gateway_token,str) or len(gateway_token)<32 or '\n' in gateway_token or '\r' in gateway_token:raise ValueError('A dedicated gateway credential is required')
        if not 0<request_timeout<=30:raise ValueError('Invalid gateway deadline')
        self.gateway_token=gateway_token;self.request_timeout=request_timeout
        self.fetcher=fetcher or open_worker

    def current_policy(self):
        if self.registry_path is None:return self.policy
        from project_registry import read_document
        return PreviewIsolation(read_document(self.registry_path,self.policy.manager))

    def handler(self):
        gateway=self
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def setup(self):
                super().setup();self.connection.settimeout(gateway.request_timeout)
                self.deadline_at=time.monotonic()+gateway.request_timeout
                self.deadline_expired=threading.Event()
                def expire():self.deadline_expired.set();shutdown(self.connection)
                self.deadline_timer=threading.Timer(gateway.request_timeout,expire);self.deadline_timer.daemon=True;self.deadline_timer.start()
            def finish(self):
                self.deadline_timer.cancel()
                super().finish()
            def handle(self):
                try:super().handle()
                except OSError:
                    # Deadline shutdown and client disconnects are normal
                    # connection endings, not application tracebacks.
                    self.close_connection=True
            def error(self,code,message):
                if self.deadline_expired.is_set():self.close_connection=True;return
                if code>=500 and self.command in ('POST','PUT','PATCH','DELETE'):
                    message='Save could not be confirmed. Refresh this project before retrying.'
                # A close with an unread small request body can reset the TCP
                # connection before the client receives its denial. Drain only
                # a bounded, declared body; never trust an unbounded length.
                if not getattr(self,'_body_read',False):
                    lengths=self.headers.get_all('Content-Length',[])
                    if len(lengths)==1 and lengths[0].isdigit() and 0<int(lengths[0])<=20000 and not self.headers.get('Transfer-Encoding'):
                        try:self.connection.settimeout(2);self.rfile.read(int(lengths[0]))
                        except OSError:pass
                    self._body_read=True
                raw=json.dumps({'error':message}).encode();self.send_response(code)
                self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.send_header('Connection','close');self.end_headers()
                if self.command!='HEAD':self.wfile.write(raw)
                self.close_connection=True
            def one(self,name,required=False):
                values=self.headers.get_all(name,[])
                if len(values)>1 or required and len(values)!=1:raise IsolationDenied('Ambiguous or missing request header')
                return values[0] if values else None
            def handle_request(self):
                self._body_read=False
                try:
                    if self.client_address[0]!='127.0.0.1':raise IsolationDenied('Use the private preview HTTPS address')
                    identity=self.one('Tailscale-User-Login',True)
                    if identity.strip().lower()!=gateway.owner:raise IsolationDenied('Use the authorized Tailscale account')
                    host=self.one('Host',True);origin=self.one('Origin')
                    policy=gateway.current_policy()
                    target=policy.resolve(host,self.path,self.command,origin)
                    # Reject bodies on reads and unsupported transfer encodings.
                    length=self.one('Content-Length');transfer=self.one('Transfer-Encoding')
                    if transfer is not None:raise IsolationDenied('Chunked request bodies are not supported')
                    if self.command in ('GET','HEAD') and length not in (None,'0'):raise IsolationDenied('Unexpected read body')
                    body=None
                    if target.data_request or target.backend_request:
                        header='X-Felo-Backend' if target.backend_request else 'X-Felo-Data'
                        if self.one(header,True)!='1':raise IsolationDenied('Use this project’s data interface')
                        if self.command!='GET':
                            if length is None or not length.isdigit() or not 0<int(length)<=20000:return self.error(413,'Use a JSON request within the preview limit')
                            if (self.one('Content-Type',True) or '').split(';')[0]!='application/json':raise IsolationDenied('Use a JSON data request')
                            body=self.rfile.read(int(length))
                            self._body_read=True
                            if len(body)!=int(length):raise IsolationDenied('Incomplete data request')
                    # Fixed upstream and explicit headers only. Cookies, caller
                    # Authorization and forwarding headers never cross this hop.
                    headers={'Host':urlsplit(gateway.worker_origin).netloc,'Tailscale-User-Login':gateway.owner,'Authorization':'Bearer '+gateway.gateway_token,'X-Felo-Project-Origin':target.origin}
                    if target.data_request:headers.update({'X-Felo-Data':'1','Origin':gateway.worker_origin,'Content-Type':'application/json'})
                    if target.backend_request:headers.update({'X-Felo-Backend':'1','Origin':gateway.worker_origin,'Content-Type':'application/json'})
                    request=urllib.request.Request('http://127.0.0.1:8082'+quote(target.path,safe='/'),data=body,headers=headers,method='GET' if self.command=='HEAD' else self.command)
                    remaining=self.deadline_at-time.monotonic()
                    if remaining<=0:self.close_connection=True;return
                    try:
                        response=gateway.fetcher(request,timeout=min(15,remaining))
                    except urllib.error.HTTPError as e:
                        # Preserve useful data errors without exposing arbitrary
                        # upstream response headers or redirect destinations.
                        if not (target.backend_request and 200<=e.code<=599) and e.code not in (400,403,404,409,413,503):e.close();return self.error(502,'The preview could not complete this request')
                        response=e
                    with response:
                        if not (target.backend_request and 200<=response.status<=599) and response.status not in (200,400,403,404,409,413,503):return self.error(502,'The preview could not complete this request')
                        limit=32768 if target.backend_request else 262144 if target.data_request else 2000000
                        if hasattr(response.headers,'get_all') and len(response.headers.get_all('Content-Length',[]))>1:return self.error(502,'The preview response had ambiguous length')
                        announced=response.headers.get('Content-Length')
                        if announced and (not announced.isdigit() or int(announced)>limit):return self.error(502,'The preview response exceeded its limit')
                        raw=response.read(limit+1)
                        if len(raw)>limit:return self.error(502,'The preview response exceeded its limit')
                        if announced and len(raw)!=int(announced):return self.error(502,'The preview response was incomplete')
                        status=response.status;content_type=response.headers.get('Content-Type','application/octet-stream')
                        if '\r' in content_type or '\n' in content_type:content_type='application/octet-stream'
                    if self.deadline_expired.is_set():self.close_connection=True;return
                    self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(raw)));self.send_header('Connection','close');self.close_connection=True
                    for name,value in policy.headers(target).items():self.send_header(name,value)
                    self.end_headers()
                    if self.command!='HEAD':self.wfile.write(raw)
                except IsolationDenied as e:self.error(403,str(e))
                except (ValueError,UnicodeError):self.error(400,'Invalid preview request')
                except (OSError,urllib.error.URLError,http.client.HTTPException):self.error(502,'The preview worker is unavailable. Retry after checking its status')
            do_GET=handle_request
            do_HEAD=handle_request
            do_POST=handle_request
            do_PUT=handle_request
            do_DELETE=handle_request
            do_PATCH=handle_request
            do_OPTIONS=handle_request
            def log_message(self,*args):pass
        return Handler

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--registry',required=True);parser.add_argument('--port',type=int,default=8093);args=parser.parse_args()
    if not 1024<=args.port<=65535:raise ValueError('Invalid local gateway port')
    registry=json.loads(Path(args.registry).read_text(encoding='utf-8'))
    gateway=Gateway(registry,os.environ['FELO_OWNER_LOGIN'],os.environ['FELO_PREVIEW_PUBLIC_ORIGIN'],os.environ['FELO_PREVIEW_GATEWAY_TOKEN'],registry_path=args.registry)
    BoundedServer(('127.0.0.1',args.port),gateway.handler()).serve_forever()

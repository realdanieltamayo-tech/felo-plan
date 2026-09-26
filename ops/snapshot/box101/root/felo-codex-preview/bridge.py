#!/usr/bin/env python3
import json,os,re,signal,subprocess,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
HOME='/root/felo-codex-preview/hermes-home'
lock=threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def send(self,status,data):
        raw=json.dumps(data).encode()
        self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers()
        try: self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError): pass
    def do_GET(self):
        self.send(200,{'data':[{'id':'felo-preview-chat','object':'model'}],'native_tools':0,'preview':True})
    def do_POST(self):
        if self.client_address[0] not in ['100.81.117.27','100.94.252.30','127.0.0.1']:
            return self.send(403,{'error':'preview caller not allowed'})
        if self.path!='/v1/chat/completions': return self.send(404,{'error':'unsupported preview route'})
        if not lock.acquire(blocking=False): return self.send(503,{'error':'preview model is busy'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=200000: return self.send(400,{'error':'invalid request length'})
            payload=json.loads(self.rfile.read(length))
            messages=payload.get('messages',[])
            if not isinstance(messages,list) or not messages: return self.send(400,{'error':'messages required'})
            prompt='\n\n'.join(str(m.get('role','user')).upper()+':\n'+str(m.get('content','')) for m in messages)
            env=os.environ.copy(); env['HERMES_HOME']=HOME; env['HERMES_IGNORE_RULES']='1'; env['HERMES_YOLO_MODE']='0'
            command=['/usr/local/bin/hermes','chat','--oneshot','-Q','--ignore-rules','--toolsets','none','--max-turns','1','--query-file','-']
            proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,cwd='/root/felo-codex-preview',start_new_session=True)
            try: stdout,stderr=proc.communicate(prompt,timeout=180)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL); proc.communicate()
                return self.send(504,{'error':'preview model timed out'})
            if proc.returncode!=0: return self.send(502,{'error':'preview model process failed','exit_code':proc.returncode})
            answer=re.sub(r'^session_id:.*$','',stdout,flags=re.M).strip()
            if not answer: return self.send(502,{'error':'preview model returned no answer'})
            self.send(200,{'choices':[{'message':{'role':'assistant','content':answer}}]})
        except Exception:
            self.send(500,{'error':'preview bridge request failed'})
        finally: lock.release()
    def log_message(self,*args): pass
ThreadingHTTPServer(('100.94.252.30',8001),Handler).serve_forever()

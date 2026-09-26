"""Durable planning-only correction queue. No generated files are executed."""
import hashlib,json,os,re,sqlite3,time
from pathlib import Path
from contextlib import contextmanager
from backend_generation import selection,post_json

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()

def validate(data):
 if not isinstance(data,dict) or set(data)!={'id','project','revision','selected','instruction','context','schema'}:raise ValueError('Invalid planning request')
 if not all(isinstance(data[k],str) and re.fullmatch('[a-f0-9]{32}',data[k]) for k in ('id','revision')):raise ValueError('Invalid planning identity')
 if not isinstance(data['project'],str) or not re.fullmatch('[a-z0-9][a-z0-9-]{0,100}',data['project']):raise ValueError('Invalid project')
 selection(data['selected'])
 if not isinstance(data['instruction'],str) or not 20<=len(data['instruction'])<=20000 or not isinstance(data['context'],dict) or not isinstance(data['schema'],dict):raise ValueError('Invalid planning context')
 if len(canonical(data).encode())>180000:raise ValueError('Planning request exceeds limit')
 return data

def generate(config,data):
 selected=data['selected'];instruction=data['instruction']
 if selected['provider']=='codex':
  # The existing subscription bridge returns source-document envelopes. A single
  # inert JSON document keeps its strict contract; it is never a coding job.
  schema={'type':'object','additionalProperties':False,'required':['summary','files','edits'],'properties':{
   'summary':{'type':'string'},'edits':{'type':'array','maxItems':0,'items':{'type':'string'}},
   'files':{'type':'array','minItems':1,'maxItems':1,'items':{'type':'object','additionalProperties':False,'required':['path','content','base_sha256'],
    'properties':{'path':{'type':'string','enum':['plan.json']},'content':{'type':'string'},'base_sha256':{'type':'null'}}}}}}
  payload={'id':data['id'],'instruction':'Correct a planning document only. Return exactly one new file named plan.json containing JSON matching context.planSchema; edits must be empty and base_sha256 null. Do not write application code, claim tests passed or grant approval. '+instruction,
   'context':{'planning':data['context'],'planSchema':data['schema']},'schema':schema}
  if not config.get('codex_url') or not config.get('codex_token'):raise ValueError('Subscription rescue is disconnected')
  output=post_json(config['codex_url'].rstrip('/')+'/correct',json.dumps(payload).encode(),{'Content-Type':'application/json','Authorization':'Bearer '+config['codex_token']},660)
  if not isinstance(output,dict) or set(output)!={'summary','files','edits'} or output['edits']!=[] or not isinstance(output['files'],list) or len(output['files'])!=1:raise ValueError('Invalid planning envelope')
  file=output['files'][0]
  if not isinstance(file,dict) or set(file)!={'path','content','base_sha256'} or file['path']!='plan.json' or file['base_sha256'] is not None or not isinstance(file['content'],str):raise ValueError('Unexpected planning document')
  result=json.loads(file['content'])
 else:
  payload={'model':selected['model'],'think':selected['think'],'stream':False,'format':data['schema'],'options':{'temperature':0.1,'num_ctx':32768,'num_predict':8000},'messages':[{'role':'system','content':instruction},{'role':'user','content':json.dumps(data['context'])}]}
  output=post_json(config['ollama_url'].rstrip('/')+'/api/chat',json.dumps(payload).encode(),{'Content-Type':'application/json'},240)
  result=json.loads(output['message']['content'])
 if not isinstance(result,dict) or len(canonical(result).encode())>150000:raise ValueError('Invalid planning result')
 return result

class Queue:
 def __init__(self,root,generator):
  self.root=Path(root)
  if not self.root.is_absolute() or self.root.is_symlink() or self.root.resolve()!=self.root:raise ValueError('Use a private planning root')
  self.root.mkdir(mode=0o700,parents=True,exist_ok=True);self.path=self.root/'planning.sqlite';self.generator=generator
  if self.path.is_symlink():raise ValueError('Invalid planning journal')
  with self.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,digest TEXT NOT NULL,request TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL,result TEXT,error TEXT)')
  self.path.chmod(0o600)
 @contextmanager
 def connect(self):
  db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
  try:
   with db:yield db
  finally:db.close()
 def submit(self,data):
  validate(data);fingerprint=digest(data)
  with self.connect() as db:
   db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT digest FROM jobs WHERE id=?',(data['id'],)).fetchone()
   if old:
    if old['digest']!=fingerprint:raise ValueError('Planning ID already used')
   else:
    if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]>=20:raise ValueError('Planning queue is full')
    db.execute('INSERT INTO jobs(id,digest,request,status,created) VALUES(?,?,?,?,?)',(data['id'],fingerprint,canonical(data),'queued',time.time()))
  return self.get(data['id'])
 def get(self,job):
  if not re.fullmatch('[a-f0-9]{32}',job):raise ValueError('Invalid planning ID')
  with self.connect() as db:row=db.execute('SELECT * FROM jobs WHERE id=?',(job,)).fetchone()
  if not row:raise ValueError('Unknown planning job')
  request=json.loads(row['request']);result=json.loads(row['result']) if row['result'] else None
  return {'id':job,'project':request['project'],'revision':request['revision'],'selected':request['selected'],'requestDigest':row['digest'],'status':row['status'],'result':result,'resultDigest':digest(result) if result else None,'error':row['error'],'ownerApproval':False}
 def recover(self):
  with self.connect() as db:db.execute("UPDATE jobs SET status='failed',error='Planning correction was interrupted. It was not replayed.' WHERE status='running'")
 def tick(self):
  with self.connect() as db:
   db.execute('BEGIN IMMEDIATE');row=db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
   if not row:return False
   db.execute("UPDATE jobs SET status='running' WHERE id=?",(row['id'],))
  try:
   result=self.generator(json.loads(row['request']))
   if not isinstance(result,dict) or len(canonical(result).encode())>150000:raise ValueError('Invalid planning result')
   with self.connect() as db:db.execute("UPDATE jobs SET status='done',result=? WHERE id=?",(canonical(result),row['id']))
  except Exception:
   with self.connect() as db:db.execute("UPDATE jobs SET status='failed',error='Planning correction failed. No plan was accepted and no build was started.' WHERE id=?",(row['id'],))
  return True

def instance():
 root=Path(os.environ['FELO_BACKEND_BUILDS_ROOT']).parent/'planning-rescues'
 config={'ollama_url':os.environ['FELO_OLLAMA_URL'],'codex_url':os.environ.get('FELO_CODEX_URL'),'codex_token':os.environ.get('FELO_CODEX_TOKEN')}
 return Queue(root,lambda request:generate(config,request))

def handle(h):
 if not h.authorized():return h.respond(401,{'error':'Unauthorized'})
 try:
  q=instance()
  if h.command=='POST' and h.path=='/planning-rescues':
   lengths=h.headers.get_all('Content-Length',[])
   if len(lengths)!=1 or not re.fullmatch('[0-9]{1,6}',lengths[0]) or h.headers.get_all('Transfer-Encoding',[]) or h.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Invalid framing')
   length=int(lengths[0])
   if not 0<length<=180000:raise ValueError('Invalid length')
   deadline=time.monotonic()+3;raw=bytearray()
   while len(raw)<length:
    remaining=deadline-time.monotonic()
    if remaining<=0:raise ValueError('Request timed out')
    h.connection.settimeout(remaining);part=h.rfile.read1(min(65536,length-len(raw)))
    if not part:raise ValueError('Incomplete request')
    raw.extend(part)
   h.respond(202,q.submit(json.loads(raw)))
  elif h.command=='GET' and (match:=re.fullmatch('/planning-rescues/([a-f0-9]{32})',h.path)):h.respond(200,q.get(match[1]))
  elif h.command=='GET' and h.path=='/planning-rescues':h.respond(200,{'planningOnly':True,'ownerReviewRequired':True})
  else:h.respond(404,{'error':'Unknown planning endpoint'})
 except (ValueError,TypeError,KeyError):h.respond(400,{'error':'Invalid or conflicting planning correction request'})
 except Exception:h.respond(503,{'error':'Planning queue unavailable. Retain the same request ID.'})
 finally:h.close_connection=True

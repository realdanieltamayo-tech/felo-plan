"""Durable single-worker backend checks; no public job-submission endpoint.

Persist ownership before Docker launch. Interrupted runs fail without replay.
Only known journal entries with matching container labels/names are removed.
"""
import argparse,hashlib,json,os,signal,socket,sqlite3,time,uuid,shutil,re
try:import fcntl
except ImportError:fcntl=None
from contextlib import contextmanager
from pathlib import Path
from backend_checks import BackendChecker,BackendCheckError,IMAGE,JOB,bounded_command,source_files,http_checks

class BackendSupervisor:
 def __init__(self,root,image,command=bounded_command):
  self.root=Path(root)
  if not self.root.is_absolute() or self.root.is_symlink() or self.root.resolve()!=self.root:raise BackendCheckError('Use a private absolute supervisor root')
  if not IMAGE.fullmatch(image):raise BackendCheckError('Use an immutable backend image')
  self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  self.image=image;self.command=command;self.locked=False
  path=self.root/'jobs.sqlite'
  if path.is_symlink():raise BackendCheckError('Journal cannot be a symlink')
  with self.db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,digest TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,run_id TEXT UNIQUE,created REAL NOT NULL,started REAL,finished REAL,report TEXT)')
   db.execute('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
   db.execute("INSERT OR IGNORE INTO meta VALUES('image',?)",(image,))
   if db.execute("SELECT value FROM meta WHERE key='image'").fetchone()[0]!=image:raise BackendCheckError('Image changed; review pending jobs before migration')
  path.chmod(0o600)

 @contextmanager
 def db(self):
  db=sqlite3.connect(self.root/'jobs.sqlite',timeout=5);db.row_factory=sqlite3.Row
  db.execute('PRAGMA synchronous=FULL')
  try:
   yield db;db.commit()
  except BaseException:db.rollback();raise
  finally:db.close()

 @contextmanager
 def exclusive(self):
  if fcntl is None:raise BackendCheckError('Backend supervision requires Linux')
  if self.locked:raise BackendCheckError('Supervisor lock is already held')
  path=self.root/'supervisor.lock'
  fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
  try:
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError as error:raise BackendCheckError('Another backend supervisor is active') from error
   self.locked=True
   yield
  finally:self.locked=False;os.close(fd)

 def submit(self,job,files,checks,context=None):
  if not isinstance(job,str) or not JOB.fullmatch(job):raise BackendCheckError('Invalid backend job ID')
  source_files(files);http_checks(checks)
  data={'files':files,'checks':checks}
  if context is not None:
   from backend_contract import contract
   data['contract']=contract(context)
   if data['contract']['checks']!=checks:raise BackendCheckError('Backend checks differ from the plan contract')
  payload=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=True)
  if len(payload.encode())>700000:raise BackendCheckError('Encoded backend request exceeds its limit')
  digest=hashlib.sha256(payload.encode()).hexdigest()
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   row=db.execute('SELECT digest,status FROM jobs WHERE id=?',(job,)).fetchone()
   if row:
    if row['digest']!=digest:raise BackendCheckError('Job ID already refers to different backend work')
    return {'id':job,'status':row['status'],'duplicate':True}
   if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running','cleanup_pending')").fetchone()[0]>=32:raise BackendCheckError('Backend queue is full')
   if db.execute('SELECT count(*) FROM jobs').fetchone()[0]>=1000:raise BackendCheckError('Archive old backend journal entries before adding more jobs')
   db.execute("INSERT INTO jobs(id,digest,payload,status,created) VALUES(?,?,?,'queued',?)",(job,digest,payload,time.time()))
  return {'id':job,'status':'queued','duplicate':False}

 def get(self,job):
  with self.db() as db:row=db.execute('SELECT id,digest,status,run_id,created,started,finished,report,payload FROM jobs WHERE id=?',(job,)).fetchone()
  if not row:raise BackendCheckError('Backend job not found')
  result=dict(row);result['report']=json.loads(result['report']) if result['report'] else None
  payload=json.loads(result.pop('payload'))
  if 'contract' in payload:
   from backend_contract import source_digest
   result['contract']=payload['contract'];result['sourceDigest']=source_digest(payload['files'])
  return result

 def artifacts(self,job):
  from backend_contract import artifacts
  with self.db() as db:row=db.execute('SELECT status,payload FROM jobs WHERE id=?',(job,)).fetchone()
  if not row:raise BackendCheckError('Backend job not found')
  if row['status'] not in ('done','failed'):raise BackendCheckError('Backend job is not terminal')
  return {'files':artifacts(json.loads(row['payload'])['files']),'receipt':self.get(job)}

 def docker(self,args):
  code,out,_=self.command(['docker',*args],body='',timeout=10)
  if code:raise BackendCheckError('Backend recovery could not reach Docker')
  return out.strip()

 def cleanup(self,row):
  run_id=row['run_id']
  if not JOB.fullmatch(run_id or ''):raise BackendCheckError('Invalid backend recovery journal')
  name='felo-backend-'+row['id'][:12]+'-'+run_id[:12]
  ids=self.docker(['ps','-aq','--filter','label=felo-backend-check='+run_id]).split()
  if len(ids)>1:raise BackendCheckError('Ambiguous backend container ownership')
  for cid in ids:
   if not __import__('re').fullmatch('[a-f0-9]{12,64}',cid):raise BackendCheckError('Invalid Docker identity')
   info=json.loads(self.docker(['inspect',cid]))[0]
   if info['Name']!='/'+name or info['Image']!=self.image or info['Config']['Labels'].get('felo-backend-check')!=run_id:
    raise BackendCheckError('Backend recovery ownership mismatch')
   self.docker(['rm','-f',cid])
  if self.docker(['ps','-aq','--filter','label=felo-backend-check='+run_id]):raise BackendCheckError('Backend container cleanup is not confirmed')

 def reconcile(self):
  """Call with exclusive ownership. Never launch or replay a running entry."""
  if not self.locked:raise BackendCheckError('Exclusive supervisor ownership is required')
  with self.db() as db:rows=db.execute("SELECT id,run_id,status FROM jobs WHERE run_id IS NOT NULL").fetchall()
  recovered=0
  # Every known run remains eligible for cleanup, including failed/done entries:
  # a delayed daemon create after host interruption must not escape the journal.
  active_ids=self.docker(['ps','-aq','--filter','label=felo-backend-check']).split()
  labels=set()
  for cid in active_ids:
   if not __import__('re').fullmatch('[a-f0-9]{12,64}',cid):raise BackendCheckError('Invalid Docker identity')
   info=json.loads(self.docker(['inspect',cid]))[0]
   labels.add(info['Config']['Labels'].get('felo-backend-check'))
  for row in rows:
   if row['status'] in ('running','cleanup_pending') or row['run_id'] in labels:
    try:self.cleanup(row)
    except Exception:
     with self.db() as db:db.execute("UPDATE jobs SET status='cleanup_pending',report=? WHERE id=?",(json.dumps({'passed':False,'cleanupVerified':False,'error':'Backend cleanup requires attention; work was not replayed'}),row['id']))
     raise
    if row['status'] in ('running','cleanup_pending'):
     with self.db() as db:db.execute("UPDATE jobs SET status='failed',finished=?,report=? WHERE id=?",(time.time(),json.dumps({'passed':False,'cleanupVerified':True,'interrupted':True,'error':'Backend run was interrupted. Review before submitting a new job ID.'}),row['id']))
     recovered+=1
  staging=self.root/'staging'
  if staging.exists():
   if staging.is_symlink() or staging.resolve()!=staging:raise BackendCheckError('Invalid backend staging directory')
   for folder in staging.iterdir():
    if folder.is_symlink() or not folder.is_dir() or not re.fullmatch('backend-check-[a-z0-9_]+',folder.name) or any(p.is_symlink() for p in folder.rglob('*')):
     raise BackendCheckError('Unexpected backend staging content; review before cleanup')
    shutil.rmtree(folder)
  return recovered

 def run_once(self):
  # The caller must hold exclusive() across recovery, claim and execution.
  if not self.locked:raise BackendCheckError('Exclusive supervisor ownership is required')
  self.reconcile()
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   row=db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created,id LIMIT 1").fetchone()
   if not row:return None
   run_id=uuid.uuid4().hex
   db.execute("UPDATE jobs SET status='running',run_id=?,started=? WHERE id=?",(run_id,time.time(),row['id']))
  payload=json.loads(row['payload'])
  options={'profile':payload['contract']['profile']} if payload.get('contract',{}).get('profile')=='node-http-records-v1' else {}
  report=BackendChecker(self.image,self.root/'staging',self.command).execute(row['id'],payload['files'],payload['checks'],run_id=run_id,**options)
  # Independently confirm the journal's container is gone before the final receipt.
  owned={'id':row['id'],'run_id':run_id}
  try:self.cleanup(owned)
  except Exception:
   report['passed']=False;report['cleanupVerified']=False;report['error']='Backend cleanup is pending'
  status=('done' if report['passed'] else 'failed') if report['cleanupVerified'] else 'cleanup_pending'
  with self.db() as db:db.execute('UPDATE jobs SET status=?,finished=?,report=? WHERE id=?',(status,time.time(),json.dumps(report),row['id']))
  return self.get(row['id'])

def notify(message):
 address=os.environ.get('NOTIFY_SOCKET')
 if not address:return
 if address.startswith('@'):address='\0'+address[1:]
 with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as sock:sock.connect(address);sock.sendall(message.encode())

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--image',required=True);p.add_argument('--once',action='store_true');a=p.parse_args()
 os.umask(0o077)
 supervisor=BackendSupervisor(a.root,a.image);stop=False
 def stopping(*_):
  nonlocal stop
  stop=True
 signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
 with supervisor.exclusive():
  supervisor.reconcile()
  from backend_preview import PreviewRuntime
  supervisor.previews=PreviewRuntime(supervisor);supervisor.previews.recover()
  from backend_rpc import serve
  server=serve(supervisor)
  notify('READY=1')
  while not stop:
   notify('WATCHDOG=1')
   result=supervisor.run_once()
   supervisor.previews.tick()
   if result:print(json.dumps({'job':result['id'],'status':result['status']}),flush=True)
   if a.once:break
   time.sleep(2)
  server.shutdown();server.server_close()
  supervisor.previews.recover()

if __name__=='__main__':main()

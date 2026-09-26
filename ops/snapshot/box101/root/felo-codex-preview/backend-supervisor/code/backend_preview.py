"""Private stateless preview lifecycle for source that passed backend checks.

No published ports, writable project data, outside network or model commands.
Durable ownership is recorded before start. Restart stops known runs, never
silently replays requests or restores in-memory application state.
"""
import base64,hashlib,json,os,re,shutil,sqlite3,stat,threading,time,uuid
from contextlib import contextmanager
from pathlib import Path
from backend_checks import BackendCheckError,JOB,CLIENT,container_command,http_checks,source_files
from backend_contract import source_digest,report_profile

class PreviewRuntime:
 def __init__(self,supervisor):
  self.supervisor=supervisor;self.command=supervisor.command;self.image=supervisor.image
  self.root=supervisor.root/'previews';self.lock=threading.RLock();self.brokers={}
  if self.root.is_symlink():raise BackendCheckError('Invalid preview root')
  self.root.mkdir(mode=0o700,exist_ok=True)
  if self.root.resolve()!=self.root or (self.root/'previews.sqlite').is_symlink():raise BackendCheckError('Invalid preview journal')
  with self.db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS previews(run TEXT PRIMARY KEY,job TEXT NOT NULL,project TEXT NOT NULL,digest TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL,last_used REAL NOT NULL,error TEXT)')
   if 'profile' not in [r[1] for r in db.execute('PRAGMA table_info(previews)')]:db.execute("ALTER TABLE previews ADD COLUMN profile TEXT NOT NULL DEFAULT 'node-http-v1'")
  (self.root/'previews.sqlite').chmod(0o600)
 @contextmanager
 def db(self):
  db=sqlite3.connect(self.root/'previews.sqlite',timeout=5);db.row_factory=sqlite3.Row;db.execute('PRAGMA synchronous=FULL')
  try:yield db;db.commit()
  except BaseException:db.rollback();raise
  finally:db.close()
 def approved_source(self,job,project):
  receipt=self.supervisor.get(job);spec=receipt.get('contract');report=receipt.get('report') or {}
  if receipt['status']!='done' or not spec or spec.get('projectKey')!=project or any(report.get(k) is not True for k in ['passed','runtimeVerified','cleanupVerified']):raise BackendCheckError('Preview requires passed checks for this project')
  actual=report.get('checks')
  if report.get('job')!=job or report.get('image')!=self.image or report.get('profile')!=report_profile(spec.get('profile')) or not isinstance(actual,list) or len(actual)!=len(spec['checks']):raise BackendCheckError('Preview check evidence is incomplete')
  if spec['profile']=='node-http-records-v1' and (report.get('storageScope')!='disposable-check' or report.get('persistentData') is not False):raise BackendCheckError('Preview requires isolated disposable storage checks')
  for wanted,got in zip(spec['checks'],actual):
   if got.get('passed') is not True or got.get('name')!=wanted['name'] or got.get('status')!=wanted['status'] or got.get('responseSha256')!=hashlib.sha256(wanted['response'].encode()).hexdigest() or got.get('responseBytes')!=len(wanted['response'].encode()):raise BackendCheckError('Preview check evidence differs from the approved contract')
  with self.supervisor.db() as db:row=db.execute('SELECT payload FROM jobs WHERE id=?',(job,)).fetchone()
  files=json.loads(row['payload'])['files'];digest=source_digest(files)
  if digest!=receipt['sourceDigest'] or digest!=report.get('sourceDigest'):raise BackendCheckError('Verified preview source changed')
  return files,digest
 def get(self,run,project):
  if not isinstance(run,str) or not JOB.fullmatch(run):raise BackendCheckError('Invalid preview run')
  with self.db() as db:row=db.execute('SELECT * FROM previews WHERE run=?',(run,)).fetchone()
  if not row or row['project']!=project:raise BackendCheckError('Preview does not belong to this project')
  return dict(row)|{'persistentData':row['profile']=='node-http-records-v1','deployment':False}
 def open(self,job,project):
  if not isinstance(job,str) or not JOB.fullmatch(job):raise BackendCheckError('Invalid preview check ID')
  _,digest=self.approved_source(job,project);profile=self.supervisor.get(job)['contract']['profile']
  with self.lock,self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   if db.execute('SELECT count(*) FROM previews WHERE project=? AND profile!=?',(project,profile)).fetchone()[0]:raise BackendCheckError('Changing a project storage profile requires an explicit migration')
   row=db.execute("SELECT run FROM previews WHERE job=? AND project=? AND status IN ('queued','starting','active') ORDER BY created DESC LIMIT 1",(job,project)).fetchone()
   if row:return self.get(row['run'],project)
   if db.execute("SELECT count(*) FROM previews WHERE status IN ('queued','starting','active','stop_requested','cleanup_pending')").fetchone()[0]>=4:raise BackendCheckError('Close an existing backend preview before opening another')
   if db.execute('SELECT count(*) FROM previews').fetchone()[0]>=1000:raise BackendCheckError('Archive the preview lifecycle journal before adding runs')
   run=uuid.uuid4().hex;now=time.time();db.execute("INSERT INTO previews(run,job,project,digest,status,created,last_used,error,profile) VALUES(?,?,?,?,'queued',?,?,NULL,?)",(run,job,project,digest,now,now,profile))
  return self.get(run,project)
 def stop(self,run,project):
  with self.lock:
   row=self.get(run,project)
   if row['status'] not in ('stopped','failed'):
    with self.db() as db:db.execute("UPDATE previews SET status='stop_requested' WHERE run=?",(run,))
  return self.get(run,project)
 def name(self,row):return 'felo-preview-backend-'+row['run']
 def socket_path(self,row):return self.supervisor.root/'rs'/row['run']
 def docker(self,args,body='',timeout=10):
  code,out,_=self.command(['docker',*args],body=body,timeout=timeout)
  if code:raise BackendCheckError('Preview container operation failed')
  return out
 def inspect(self,row):
  info=json.loads(self.docker(['inspect',self.name(row)]))[0]
  if info['Name']!='/'+self.name(row) or info['Image']!=self.image or info['Config']['Labels'].get('felo-backend-preview')!=row['run']:raise BackendCheckError('Preview container ownership mismatch')
  return info
 def cleanup(self,row):
  ids=self.docker(['ps','-aq','--filter','label=felo-backend-preview='+row['run']]).split()
  if len(ids)>1:raise BackendCheckError('Ambiguous preview ownership')
  for cid in ids:
   if not re.fullmatch('[a-f0-9]{12,64}',cid):raise BackendCheckError('Invalid preview container ID')
   info=self.inspect(row)
   if not info['Id'].startswith(cid):raise BackendCheckError('Preview identity mismatch')
   self.docker(['rm','-f',cid])
  if self.docker(['ps','-aq','--filter','label=felo-backend-preview='+row['run']]).strip():raise BackendCheckError('Preview cleanup is not confirmed')
  broker=self.brokers.get(row['run'])
  if broker:broker.close();del self.brokers[row['run']]
  path=self.socket_path(row)
  if path.exists() or path.is_symlink():
   if path.is_symlink() or not stat.S_ISSOCK(path.lstat().st_mode) or path.parent.resolve()!=path.parent:raise BackendCheckError('Unexpected stale records socket')
   path.unlink()
  folder=self.root/row['run']
  if folder.exists() or folder.is_symlink():
   if folder.is_symlink() or not folder.is_dir() or folder.resolve().parent!=self.root or any(p.is_symlink() for p in folder.rglob('*')):raise BackendCheckError('Unexpected preview source directory')
   shutil.rmtree(folder)
 def retire(self,row,error=None):
  try:
   self.cleanup(row)
   with self.db() as db:db.execute("UPDATE previews SET status='stopped',error=? WHERE run=?",(error,row['run']))
  except Exception:
   with self.db() as db:db.execute("UPDATE previews SET status='cleanup_pending',error='Preview cleanup requires attention' WHERE run=?",(row['run'],))
   raise
 def recover(self):
  """Startup only, under the supervisor's exclusive process ownership."""
  if not self.supervisor.locked:raise BackendCheckError('Exclusive supervisor ownership is required')
  with self.lock:
   with self.db() as db:rows=[dict(r) for r in db.execute('SELECT * FROM previews')]
   active=self.docker(['ps','-aq','--filter','label=felo-backend-preview']).split();labels=set()
   for cid in active:
    if not re.fullmatch('[a-f0-9]{12,64}',cid):raise BackendCheckError('Invalid preview container ID')
    labels.add(json.loads(self.docker(['inspect',cid]))[0]['Config']['Labels'].get('felo-backend-preview'))
   for row in rows:
    if row['status'] in ('starting','active','stop_requested','cleanup_pending') or row['run'] in labels:
     self.retire(row,'Preview process restarted. Open a new preview; earlier requests were not replayed.')
   return len(rows)
 def start(self,row):
  files,digest=self.approved_source(row['job'],row['project'])
  if digest!=row['digest']:raise BackendCheckError('Preview source digest changed')
  if row['profile']!=self.supervisor.get(row['job'])['contract']['profile']:raise BackendCheckError('Preview storage profile changed')
  folder=self.root/row['run'];folder.mkdir(mode=0o755);folder.chmod(0o755)
  for name,raw in source_files(files).items():
   p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o444)
  for p in folder.rglob('*'):
   if p.is_dir():p.chmod(0o755)
  args=container_command(self.name(row),row['run'],folder,self.image)
  records=row['profile']=='node-http-records-v1'
  if records:
   from backend_records import Records,Broker
   from backend_records_sdk import records_command,records_mounts_match
   path=self.socket_path(row);path.parent.mkdir(mode=0o700,exist_ok=True)
   broker=Broker(Records(self.supervisor.root/'records',row['project']),path);self.brokers[row['run']]=broker
   args=records_command(self.name(row),row['run'],folder,self.image,path)
  args[args.index('--label')+1]='felo-backend-preview='+row['run']
  self.docker(args[1:],timeout=20)
  info=self.inspect(row);host=info['HostConfig'];config=info['Config']
  if not (config['User']=='65534:65534' and host['NetworkMode']=='none' and host['ReadonlyRootfs'] and host['Privileged'] is False and host['CapDrop']==['ALL'] and host['Memory']==268435456 and host['MemorySwap']==268435456 and host['PidsLimit']==64 and host['NanoCpus']==500000000 and 'no-new-privileges:true' in host['SecurityOpt'] and (records_mounts_match(info,folder,path) if records else len(info['Mounts'])==1 and info['Mounts'][0]['Destination']=='/app' and not info['Mounts'][0]['RW'])):raise BackendCheckError('Preview runtime restrictions did not match')
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   result=self.http(row,{'method':'GET','path':'/','body':''})
   if 'status' in result:
    with self.db() as db:db.execute("UPDATE previews SET status='active',last_used=? WHERE run=?",(time.time(),row['run']))
    return
   if not self.inspect(row)['State']['Running']:break
   time.sleep(.2)
  raise BackendCheckError('Preview did not become ready')
 def http(self,row,request):
  return json.loads(self.docker(['exec','-i','--user','65534:65534',self.name(row),'/usr/bin/env','-i','PATH=/usr/local/bin:/usr/bin:/bin','node','-e',CLIENT],json.dumps(request),timeout=6))
 def invoke(self,run,project,request):
  if not isinstance(request,dict) or set(request)!={'method','path','body'}:raise BackendCheckError('Invalid preview request')
  http_checks([{'name':'preview request',**request,'status':200,'response':''}])
  with self.lock:
   row=self.get(run,project)
   if row['status']!='active':raise BackendCheckError('Preview is not active')
   if not self.inspect(row)['State']['Running']:raise BackendCheckError('Preview runtime stopped')
   with self.db() as db:db.execute('UPDATE previews SET last_used=? WHERE run=?',(time.time(),run))
   result=self.http(row,request)
   if 'error' in result:raise BackendCheckError(result['error'])
   body=base64.b64decode(result.get('body',''),validate=True)
   if type(result.get('status')) is not int or not 200<=result['status']<=599 or len(body)>32768:raise BackendCheckError('Invalid preview response')
   return {'status':result['status'],'body':base64.b64encode(body).decode(),'bytes':len(body),'sourceDigest':row['digest'],'run':run,'persistentData':row['persistentData']}
 def tick(self):
  if not self.supervisor.locked:raise BackendCheckError('Exclusive supervisor ownership is required')
  with self.lock:
   # A daemon may finish create after an interrupted CLI. Known terminal runs
   # remain eligible for cleanup; never remove another instance's containers.
   with self.db() as db:terminal={r['run']:dict(r) for r in db.execute("SELECT * FROM previews WHERE status IN ('stopped','failed')")}
   ids=self.docker(['ps','-aq','--filter','label=felo-backend-preview']).split()
   for cid in ids:
    if not re.fullmatch('[a-f0-9]{12,64}',cid):raise BackendCheckError('Invalid preview container ID')
    info=json.loads(self.docker(['inspect',cid]))[0];run=info['Config']['Labels'].get('felo-backend-preview')
    if run in terminal:self.retire(terminal[run],'Removed a delayed preview container');return
   with self.db() as db:
    row=db.execute("SELECT * FROM previews WHERE status IN ('stop_requested','cleanup_pending') OR (status='active' AND last_used<?) ORDER BY created LIMIT 1",(time.time()-900,)).fetchone()
   if row:self.retire(dict(row),'Preview closed or expired after 15 minutes idle');return
   with self.db() as db:
    row=db.execute("SELECT * FROM previews WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
    if row:db.execute("UPDATE previews SET status='starting' WHERE run=?",(row['run'],))
   if row:
    try:self.start(dict(row))
    except Exception:self.retire(dict(row),'Preview startup failed; review before reopening')

"""Durable backend generation/check cycle. Completion is not phase approval."""
import hashlib,json,os,sqlite3,time
from contextlib import contextmanager
from pathlib import Path
try:import fcntl
except ImportError:fcntl=None
from backend_checks import BackendCheckError,JOB,source_files
from backend_contract import contract,source_digest,artifacts,report_profile
from backend_generation import selection,resolve,ModelTransportError

FAILURES={
 'model_connection':'The latest backend attempt could not finish its model request. No passing build was produced.',
 'source_validation':'The latest backend attempt returned source that failed validation. No passing build was produced.',
 'execution_checks':'The generated backend failed independent execution checks. No passing build was produced.',
 'generation':'The latest backend generation attempt could not finish. No passing build was produced.'
}

def validate(data):
 if not isinstance(data,dict) or set(data)!={'id','brief','contract','files','routing'}:raise BackendCheckError('Invalid backend build fields')
 if not isinstance(data['id'],str) or not JOB.fullmatch(data['id']):raise BackendCheckError('Invalid backend build ID')
 if not isinstance(data['brief'],str) or not 20<=len(data['brief'])<=30000:raise BackendCheckError('Invalid backend build brief')
 contract(data['contract'])
 if not isinstance(data['files'],dict):raise BackendCheckError('Invalid backend starting source')
 if data['files']:source_files(data['files'])
 if sum(len(v.encode()) for v in data['files'].values())>100000:raise BackendCheckError('Backend source exceeds its context limit')
 r=data['routing']
 if not isinstance(r,dict) or set(r)!={'agent','version','primary','fallback'} or r['agent']!='backend' or type(r['version']) is not int or r['version']<1:raise BackendCheckError('Invalid backend routing snapshot')
 selection(r['primary'])
 if r['fallback'] is not None:selection(r['fallback'])
 return json.loads(json.dumps(data))

def verify_result(request,receipt):
 digest=source_digest(request['files']);r=receipt.get('report') or {}
 if receipt.get('id')!=request['id'] or receipt.get('contract')!=request['contract'] or receipt.get('sourceDigest')!=digest:raise BackendCheckError('Backend receipt identity does not match the submitted source and contract')
 if receipt.get('status')!='done' or any(r.get(k) is not True for k in ['passed','runtimeVerified','cleanupVerified']) or r.get('sourceDigest')!=digest or r.get('job')!=request['id'] or r.get('profile')!=report_profile(request['contract']['profile']):raise BackendCheckError('Backend runtime checks did not pass')
 if request['contract']['profile']=='node-http-records-v1' and (r.get('storageScope')!='disposable-check' or r.get('persistentData') is not False):raise BackendCheckError('Backend checks did not use disposable records')
 actual=r.get('checks')
 if not isinstance(actual,list) or len(actual)!=len(request['contract']['checks']):raise BackendCheckError('Backend checks are incomplete')
 for wanted,got in zip(request['contract']['checks'],actual):
  if got.get('name')!=wanted['name'] or got.get('passed') is not True or got.get('status')!=wanted['status'] or got.get('responseSha256')!=hashlib.sha256(wanted['response'].encode()).hexdigest() or got.get('responseBytes')!=len(wanted['response'].encode()):raise BackendCheckError('Backend HTTP response differs from the contract')

class Builder:
 def __init__(self,root,generate=None,checker=None):
  self.root=Path(root);self.generate=generate;self.checker=checker
  if not self.root.is_absolute() or self.root.is_symlink() or self.root.resolve()!=self.root:raise BackendCheckError('Use a private absolute build root')
  self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  if (self.root/'builds.sqlite').is_symlink():raise BackendCheckError('Invalid backend build journal')
  with self.db() as db:db.execute('CREATE TABLE IF NOT EXISTS builds(id TEXT PRIMARY KEY,digest TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL,data TEXT NOT NULL)')
  (self.root/'builds.sqlite').chmod(0o600)
 @contextmanager
 def db(self):
  db=sqlite3.connect(self.root/'builds.sqlite',timeout=5);db.row_factory=sqlite3.Row;db.execute('PRAGMA synchronous=FULL')
  try:yield db;db.commit()
  except BaseException:db.rollback();raise
  finally:db.close()
 @contextmanager
 def exclusive(self):
  if fcntl is None:raise BackendCheckError('Backend building requires Linux')
  fd=os.open(self.root/'build.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
  try:
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:raise BackendCheckError('Backend build worker is already active')
   yield
  finally:os.close(fd)
 def submit(self,data):
  data=validate(data);raw=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=True)
  if len(raw)>350000:raise BackendCheckError('Backend build request exceeds its limit')
  digest=hashlib.sha256(raw.encode()).hexdigest()
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT digest,status FROM builds WHERE id=?',(data['id'],)).fetchone()
   if row:
    if row['digest']!=digest:raise BackendCheckError('Build ID already belongs to different work')
    return {'id':data['id'],'status':row['status'],'duplicate':True}
   if db.execute("SELECT count(*) FROM builds WHERE status NOT IN ('done','failed')").fetchone()[0]>=16 or db.execute('SELECT count(*) FROM builds').fetchone()[0]>=500:raise BackendCheckError('Backend build queue needs review before accepting more work')
   state={'id':data['id'],'status':'queued','request':data,'files':data['files'],'attempts':[],'created':time.time()}
   db.execute('INSERT INTO builds VALUES(?,?,?,?,?)',(data['id'],digest,'queued',state['created'],json.dumps(state)))
  return {'id':data['id'],'status':'queued','duplicate':False}
 def load(self,job):
  if not isinstance(job,str) or not JOB.fullmatch(job):raise BackendCheckError('Invalid backend build ID')
  with self.db() as db:row=db.execute('SELECT data FROM builds WHERE id=?',(job,)).fetchone()
  if not row:raise BackendCheckError('Backend build not found')
  return json.loads(row['data'])
 def save(self,state):
  with self.db() as db:db.execute('UPDATE builds SET status=?,data=? WHERE id=?',(state['status'],json.dumps(state),state['id']))
 def get(self,job):
  s=self.load(job)
  # Explain older connection failures without rewriting their terminal journal.
  if s['status']=='failed' and s.get('error')=='Backend generation did not pass independent checks.' and s.get('attempts') and s['attempts'][-1].get('detail')=='The model connection could not finish this attempt.':
   s.update(failureStage='model_connection',error=FAILURES['model_connection'])
  return {k:v for k,v in s.items() if k not in ['request','files','checkRequest','feedback']}|{'contract':s['request']['contract'],'sourceDigest':source_digest(s['files']) if s['files'] else None,'ownerReviewRequired':True,'deployment':False,'persistentData':False}
 def artifacts(self,job):
  s=self.load(job)
  if s['status'] not in ('done','failed'):raise BackendCheckError('Backend build is not terminal')
  return {'files':artifacts(s['files']) if s['files'] else [],'receipt':self.get(job)}
 def recover(self):
  with self.exclusive():
   with self.db() as db:rows=db.execute("SELECT data FROM builds WHERE status='generating'").fetchall()
   for row in rows:
    s=json.loads(row['data']);s.update(status='failed',finished=time.time(),error='Worker restarted during generation. Review before requesting a new build ID.');self.save(s)
   return len(rows)
 def choices(self,s):
  routing=s['request']['routing'];primary=routing['primary'];fallback=routing['fallback']
  return [primary] if primary['provider']=='codex' else [primary,primary]+([fallback] if fallback else [])
 def failed_attempt(self,s,message,stage):
  s['attempts'][-1].update(passed=False,finished=time.time(),detail=message[:500],failureStage=stage);s['feedback']=message[:1500]
  s['status']='queued' if len(s['attempts'])<len(self.choices(s)) else 'failed'
  if s['status']=='failed':s.update(error=FAILURES[stage],failureStage=stage,finished=time.time())
  self.save(s)
 def tick(self):
  with self.exclusive():
   with self.db() as db:row=db.execute("SELECT data FROM builds WHERE status IN ('queued','checking') ORDER BY created,id LIMIT 1").fetchone()
   if not row:return None
   s=json.loads(row['data']);q=s['request']
   if s['status']=='checking':
    try:
     self.checker({'op':'submit',**s['checkRequest']});receipt=self.checker({'op':'status','id':s['checkRequest']['id']})
    except (OSError,TimeoutError):return self.get(s['id'])
    except BackendCheckError:
     s.update(status='failed',finished=time.time(),error='Backend checker rejected the durable request. Review before retrying.');self.save(s);return self.get(s['id'])
    if receipt['status'] in ('queued','running','cleanup_pending'):return self.get(s['id'])
    if receipt['status']=='failed':
     if (receipt.get('report') or {}).get('interrupted'):
      s.update(status='failed',finished=time.time(),error='Backend checks were interrupted. Review before retrying.');self.save(s)
     else:self.failed_attempt(s,'Independent backend checks failed: '+json.dumps(receipt.get('report',{})),'execution_checks')
     return self.get(s['id'])
    try:verify_result(s['checkRequest'],receipt)
    except BackendCheckError:
     s.update(status='failed',finished=time.time(),error='Backend receipt verification failed. Review the checker before retrying.');self.save(s);return self.get(s['id'])
    s['attempts'][-1].update(passed=True,finished=time.time());s.update(status='done',finished=time.time(),execution=receipt);self.save(s);return self.get(s['id'])
   attempt=len(s['attempts']);selected=self.choices(s)[attempt]
   attempt_id=hashlib.sha256((s['id']+':generation:'+str(attempt)).encode()).hexdigest()[:32]
   s.update(status='generating',activeModel=selected['model'],activeProvider=selected['provider']);s['attempts'].append({'id':attempt_id,'model':selected['model'],'provider':selected['provider'],'started':time.time()});self.save(s)
   try:
    output=self.generate(attempt_id,q['brief'],q['contract'],s['files'],selected,s.get('feedback'))
   except Exception as error:
    stage='model_connection' if isinstance(error,(ModelTransportError,OSError)) else ('source_validation' if isinstance(error,(BackendCheckError,ValueError,KeyError,TypeError)) else 'generation')
    detail=str(error) if isinstance(error,BackendCheckError) else ('The model returned invalid structured source.' if stage=='source_validation' else ('The model connection could not finish this attempt.' if stage=='model_connection' else 'Backend generation could not finish this attempt.'))
    self.failed_attempt(s,detail,stage);return self.get(s['id'])
   try:files=resolve(output,s['files'])
   except Exception as error:
    detail=str(error) if isinstance(error,BackendCheckError) else 'The model returned invalid structured source.'
    self.failed_attempt(s,detail,'source_validation');return self.get(s['id'])
   check_id=hashlib.sha256((s['id']+':check:'+str(attempt)).encode()).hexdigest()[:32]
   s.update(files=files,status='checking',modelDescription=output['summary'],checkRequest={'id':check_id,'files':files,'contract':q['contract']});self.save(s)
   return self.get(s['id'])

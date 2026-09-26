"""Host-owned records. Generated code receives a single-project Unix capability.

No database files, credentials, namespace selection, SQL, delete or restore API
are exposed to generated code. This module does not activate a runtime profile.
"""
import hashlib,json,math,os,re,socket,socketserver,sqlite3,stat,struct,threading,time
from contextlib import contextmanager,closing
from pathlib import Path

PROFILE='project-records-v1'
PROJECT=re.compile(r'[a-z][a-z0-9_-]{0,79}')
KEY=re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}')
REQUEST=re.compile(r'[a-f0-9]{32}')
MAX_VALUE=16384
MAX_MESSAGE=65536
MAX_RECORDS=1000
MAX_RECEIPTS=10000

class RecordError(ValueError):
 def __init__(self,code,message):self.code=code;super().__init__(message)

def fail(code,message):raise RecordError(code,message)

def encoded(value):
 # Reject unsupported numbers/types/depth before touching storage. JSON data is
 # never evaluated as Python, JavaScript, SQL or a filesystem path.
 def check(v,depth=0):
  if depth>20:fail('invalid','Record nesting exceeds its limit')
  if v is None or type(v) in (str,bool,int):return
  if type(v) is float and math.isfinite(v):return
  if type(v) is list:
   for x in v:check(x,depth+1)
   return
  if type(v) is dict and all(type(k) is str for k in v):
   for x in v.values():check(x,depth+1)
   return
  fail('invalid','Record value must be JSON data')
 check(value)
 try:return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
 except (ValueError,UnicodeError):fail('invalid','Record value must be valid UTF-8 JSON')

class Records:
 def __init__(self,root,project):
  if not isinstance(project,str) or not PROJECT.fullmatch(project):fail('invalid','Invalid project identity')
  self.root=Path(root);self.project=project
  if not self.root.is_absolute() or self.root.is_symlink() or self.root.resolve()!=self.root:fail('invalid','Use a private absolute records root')
  self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  self.path=self.root/(hashlib.sha256(project.encode()).hexdigest()+'.sqlite')
  for p in [self.path,Path(str(self.path)+'-journal'),Path(str(self.path)+'-wal'),Path(str(self.path)+'-shm')]:
   if p.is_symlink():fail('invalid','Unexpected records storage path')
  # A root-owned service is the only process that opens this directory. The
  # generated container gets the broker socket, never this directory or file.
  if not self.path.exists():
   try:fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
   except FileExistsError:pass
   else:os.close(fd)
  self.path.chmod(0o600)
  with self.db() as db:
   db.execute('CREATE TABLE IF NOT EXISTS identity(id INTEGER PRIMARY KEY CHECK(id=1),profile TEXT NOT NULL,project TEXT NOT NULL)')
   db.execute('INSERT OR IGNORE INTO identity VALUES(1,?,?)',(PROFILE,project))
   if db.execute('SELECT profile,project FROM identity').fetchall()!=[(PROFILE,project)]:fail('invalid','Records belong to another project or storage version')
   db.execute('CREATE TABLE IF NOT EXISTS records(key TEXT PRIMARY KEY,version INTEGER NOT NULL,value TEXT NOT NULL)')
   db.execute('CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,digest TEXT NOT NULL,receipt TEXT NOT NULL)')

 @contextmanager
 def db(self):
  if self.path.is_symlink() or not self.path.is_file():fail('invalid','Unexpected records database')
  db=sqlite3.connect(self.path,timeout=3)
  try:
   db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA journal_mode=DELETE')
   if db.execute('PRAGMA page_size').fetchone()[0]!=4096:fail('invalid','Unexpected records page size')
   db.execute('PRAGMA max_page_count=8192')
   yield db;db.commit()
  except BaseException:db.rollback();raise
  finally:db.close()

 def dispatch(self,q):
  if not isinstance(q,dict):fail('invalid','Invalid records request')
  op=q.get('op');fields={'get':{'op','key'},'list':{'op','after','limit'},'put':{'op','key','value','expectedVersion','requestId'}}
  if op not in fields or set(q)!=fields[op]:fail('invalid','Unsupported records operation or fields')
  if op=='list':
   if type(q['limit']) is not int or not 1<=q['limit']<=25 or (q['after'] is not None and (not isinstance(q['after'],str) or not KEY.fullmatch(q['after']))):fail('invalid','Invalid records page')
  elif not isinstance(q['key'],str) or not KEY.fullmatch(q['key']):fail('invalid','Invalid record key')
  if op=='put':
   if type(q['expectedVersion']) is not int or not 0<=q['expectedVersion']<2147483647 or not isinstance(q['requestId'],str) or not REQUEST.fullmatch(q['requestId']):fail('invalid','A record version and stable request ID are required')
   raw=encoded(q['value'])
   if len(raw)>MAX_VALUE:fail('invalid','Record exceeds 16 KB')
   digest=hashlib.sha256(encoded(q)).hexdigest()
  with self.db() as db:
   if op=='get':
    row=db.execute('SELECT key,version,value FROM records WHERE key=?',(q['key'],)).fetchone()
    return {'record':None if row is None else {'key':row[0],'version':row[1],'value':json.loads(row[2])}}
   if op=='list':
    rows=db.execute('SELECT key,version,value FROM records WHERE key>? ORDER BY key LIMIT ?',(q['after'] or '',q['limit']+1)).fetchall();result=[];size=0
    for row in rows[:q['limit']]:
     item={'key':row[0],'version':row[1],'value':json.loads(row[2])};n=len(encoded(item))
     if size+n>24000:break
     result.append(item);size+=n
    return {'records':result,'nextAfter':result[-1]['key'] if len(rows)>len(result) else None}
   db.execute('BEGIN IMMEDIATE')
   previous=db.execute('SELECT digest,receipt FROM receipts WHERE id=?',(q['requestId'],)).fetchone()
   if previous:
    if previous[0]!=digest:fail('conflict','This request ID belongs to a different write')
    return json.loads(previous[1])
   row=db.execute('SELECT version FROM records WHERE key=?',(q['key'],)).fetchone();version=row[0] if row else 0
   if version!=q['expectedVersion']:fail('conflict','The record changed; reload it before editing')
   if not row and db.execute('SELECT count(*) FROM records').fetchone()[0]>=MAX_RECORDS:fail('capacity','Project record limit reached')
   if db.execute('SELECT count(*) FROM receipts').fetchone()[0]>=MAX_RECEIPTS:fail('capacity','Project write journal needs archival before more writes')
   receipt={'key':q['key'],'version':version+1,'requestId':q['requestId'],'committed':True}
   db.execute('INSERT INTO records VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET version=excluded.version,value=excluded.value',(q['key'],version+1,raw.decode()))
   db.execute('INSERT INTO receipts VALUES(?,?,?)',(q['requestId'],digest,encoded(receipt).decode()))
   return receipt

 def snapshot(self,destination):
  """Trusted host recovery operation; never reachable over the records socket."""
  destination=Path(destination)
  if not destination.is_absolute() or destination.resolve()!=destination or destination.exists():fail('invalid','Use a new absolute snapshot file')
  fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
  with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(destination)) as target:
   source.execute('BEGIN');source.execute('SELECT count(*) FROM records').fetchone()
   expected=fingerprint(source);source.backup(target)
   if fingerprint(target)!=expected:fail('unavailable','Snapshot verification failed')
  return expected

def fingerprint(db):
 if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':fail('unavailable','Records integrity check failed')
 tables={name:[list(row) for row in db.execute('SELECT * FROM '+name+' ORDER BY '+key)] for name,key in [('identity','project'),('records','key'),('receipts','id')]}
 return {'sha256':hashlib.sha256(encoded(tables)).hexdigest(),'records':len(tables['records']),'receipts':len(tables['receipts'])}

def read_message(sock):
 deadline=time.monotonic()+4
 def read(n):
  out=bytearray()
  while len(out)<n:
   left=deadline-time.monotonic()
   if left<=0:fail('invalid','Records request timed out')
   sock.settimeout(left);part=sock.recv(n-len(out))
   if not part:fail('invalid','Incomplete records request')
   out.extend(part)
  return bytes(out)
 n=struct.unpack('!I',read(4))[0]
 if not 0<n<=MAX_MESSAGE:fail('invalid','Records request exceeds its limit')
 def unique(pairs):
  obj={}
  for k,v in pairs:
   if k in obj:fail('invalid','Duplicate request fields')
   obj[k]=v
  return obj
 return json.loads(read(n).decode('utf-8'),object_pairs_hook=unique,parse_constant=lambda _:fail('invalid','Invalid JSON number'))

class RecordHandler(socketserver.BaseRequestHandler):
 def handle(self):
  try:
   _,uid,_=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
   if uid!=self.server.peer_uid:fail('denied','Records peer is not authorized')
   result={'ok':True,'data':self.server.store.dispatch(read_message(self.request))}
  except RecordError as e:result={'ok':False,'code':e.code,'error':str(e)}
  except (ValueError,TypeError,UnicodeError,RecursionError):result={'ok':False,'code':'invalid','error':'Invalid records request'}
  except Exception:result={'ok':False,'code':'uncertain','error':'The records operation could not be confirmed. Retain its request ID and check before retrying.'}
  raw=encoded(result)
  try:self.request.settimeout(2);self.request.sendall(struct.pack('!I',len(raw))+raw)
  except OSError:pass

class RecordServer(socketserver.ThreadingMixIn,socketserver.UnixStreamServer if hasattr(socketserver,'UnixStreamServer') else socketserver.TCPServer):
 daemon_threads=False
 block_on_close=True
 request_queue_size=8
 def process_request(self,request,client_address):
  if not self.slots.acquire(False):request.close();return
  try:super().process_request(request,client_address)
  except BaseException:self.slots.release();raise
 def process_request_thread(self,request,client_address):
  try:super().process_request_thread(request,client_address)
  finally:self.slots.release()

class Broker:
 def __init__(self,store,path,peer_uid=65534):
  if os.name!='posix':fail('invalid','Records broker requires Linux')
  self.path=Path(path)
  if not self.path.is_absolute() or self.path.resolve()!=self.path or self.path.exists() or self.path.is_symlink():fail('invalid','Use a new private records socket path')
  self.server=RecordServer(str(self.path),RecordHandler);self.server.store=store;self.server.peer_uid=peer_uid;self.server.slots=threading.BoundedSemaphore(16)
  self.path.chmod(0o600)
  try:os.chown(self.path,peer_uid,-1)
  except Exception:self.server.server_close();self.path.unlink();raise
  self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.1},daemon=True);self.thread.start()
 def close(self):
  self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
  if self.path.exists():
   if not stat.S_ISSOCK(self.path.lstat().st_mode):fail('invalid','Unexpected broker socket replacement')
   self.path.unlink()

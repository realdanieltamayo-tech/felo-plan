"""Read-only inventory of existing component recovery evidence on fixed Felo hosts.

Does not create backups, restore databases, start workers or authorize cutover.
"""
from pathlib import Path
import datetime,hashlib,importlib.util,json,re,sqlite3,sys
ROOT=Path('/root/felo-codex-preview')
STAMP=r'\d{8}T\d{6}Z-[a-f0-9]{8}'
def digest(path):
 if path.is_symlink() or not path.is_file():raise ValueError('Unexpected archive file')
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def latest(root,pattern):
 if root.is_symlink() or not root.is_dir():raise ValueError('Recovery directory unavailable')
 entries=list(root.iterdir())
 if len(entries)>1000:raise ValueError('Recovery directory exceeds inspection limit')
 matches=sorted((p for p in entries if re.fullmatch(pattern,p.name)),reverse=True)
 if not matches:raise ValueError('No component recovery evidence')
 folder=matches[0]
 if folder.is_symlink() or not folder.is_dir() or folder.resolve().parent!=root.resolve():raise ValueError('Unexpected recovery directory')
 return folder
def receipt(folder):
 p=folder/'verification.json'
 if p.is_symlink() or p.stat().st_size>2*1024*1024:raise ValueError('Invalid recovery receipt')
 data=json.loads(p.read_text())
 if data.get('verified') is not True:raise ValueError('Latest component recovery did not verify')
 return data
def file_check(folder,name,expected):
 if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected):raise ValueError('Missing archive fingerprint')
 target=folder/name
 if not target.resolve().is_relative_to(folder.resolve()):raise ValueError('Archive path escaped its component directory')
 if digest(target)!=expected:raise ValueError('Archive no longer matches its verified receipt')
def database_archive(root,original=False):
 folder=latest(root,STAMP);proof=receipt(folder)
 if proof.get('production_changed') is not False or proof.get('restored_offline') is not True or proof.get('temporary_restore_removed') is not True:raise ValueError('Incomplete offline database recovery evidence')
 name='original.dump' if original else 'controller.dump';file_check(folder,name,proof.get('sha256'))
 if original and (proof.get('jobs_replayed') is not False or proof.get('sequence_capture_stable') is not True):raise ValueError('Original archive safety evidence missing')
 return {'component':'original_database' if original else 'controller_database','backup':str(folder),'verifiedAt':proof.get('finished_at'),'artifactIntact':True,'tables':len(proof['tables']),'records':sum(t['rows'] for t in proof['tables'].values()),'currentStateCompared':False,'scope':'Historically verified offline restore; dump fingerprint checked now. Later live writes are not covered.'}
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def frontend(root):
 worker=root/'gemma-worker';folder=latest(worker/'recovery',STAMP);proof=receipt(folder)
 if proof.get('jobs_executed') is not False:raise ValueError('Frontend no-replay proof missing')
 file_check(folder,'worker-artifacts.tar.gz',proof.get('archive_sha256'));file_check(folder,'preview-data.sqlite',proof.get('sqlite_sha256'))
 # Existing verifier functions only read/hash artifacts and open SQLite mode=ro.
 helper=module(root/'scripts/verify-preview-worker-backup.py','frontend_recovery_reader')
 manifest_path=folder/'artifact-manifest.json'
 if manifest_path.is_symlink() or manifest_path.stat().st_size>4*1024*1024:raise ValueError('Invalid artifact manifest')
 saved=json.loads(manifest_path.read_text());current=helper.artifact_manifest()
 drift={'addedFiles':len(current.keys()-saved.keys()),'missingFiles':len(saved.keys()-current.keys()),'changedFiles':sum(current[n]!=saved[n] for n in current.keys()&saved.keys())}
 restored=helper.db_fingerprint(folder/'preview-data.sqlite');assert restored==proof['sqlite'],'Saved frontend database differs'
 current_db=helper.db_fingerprint(worker/'jobs/preview-data.sqlite')
 return {'component':'frontend_artifacts','backup':str(folder),'verifiedAt':proof.get('started_at'),'artifactIntact':True,'currentStateCompared':True,'matchesCurrent':not any(drift.values()) and current_db==restored,'artifactDrift':drift,'savedRecords':restored['rows'],'currentRecords':current_db['rows'],'scope':'Saved artifact archive and SQLite hashes checked; current artifacts and logical records compared without replay.'}
def journal(path,table):
 if path.is_symlink() or not path.is_file():raise ValueError('Unexpected journal file')
 with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
  if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Journal integrity failed')
  if db.execute('SELECT count(*) FROM '+table+" WHERE status NOT IN ('done','failed','stopped')").fetchone()[0]:raise ValueError('Worker has active work; coherence not assessed')
  schema=db.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name').fetchall()
  rows=db.execute('SELECT * FROM '+table+' ORDER BY '+('run' if table=='previews' else 'id')).fetchall()
  meta=db.execute('SELECT * FROM meta ORDER BY key').fetchall() if db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='meta'").fetchone()[0] else []
  return {'rows':len(rows),'sha256':hashlib.sha256(json.dumps([schema,rows,meta],ensure_ascii=False).encode()).hexdigest()}
def backend(root):
 folder=latest(root/'gemma-worker/recovery',r'backend-build-\d{8}T\d{6}Z');proof=receipt(folder)
 for key in ('crossJournalReceiptsVerified','recordsRestoredWithReceipts','planningRestoredWithoutReplay','privateWorkerConfigBackedUp','gatewayConfigBackedUp'):
  if proof.get(key) is not True:raise ValueError('Incomplete backend recovery evidence')
 if proof.get('jobsReplayed') is not False:raise ValueError('Backend no-replay evidence missing')
 journals={'builds.sqlite':('gemma-worker/backend-builds/builds.sqlite','builds'),'checks.sqlite':('backend-supervisor/state/jobs.sqlite','jobs'),'previews.sqlite':('backend-supervisor/state/previews/previews.sqlite','previews'),'planning.sqlite':('gemma-worker/planning-rescues/planning.sqlite','jobs')}
 drift=[]
 for name,(path,table) in journals.items():
  expected=proof['journals'][name]
  if journal(folder/name,table)!=expected:raise ValueError('Saved backend journal differs')
  if journal(root/path,table)!=expected:drift.append(name)
 changed_sources=0
 for name,expected in proof['sourceHashes'].items():
  if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unexpected source receipt path')
  file_check(folder/'source',name,expected)
  if digest(root/name)!=expected:changed_sources+=1
 changed_config=0
 for name in ('worker.env','gateway.env','project-registry.json','project-origins.json'):
  # Hash comparison only: private configuration values never enter this report.
  if digest(folder/'private'/name)!=digest(root/'gemma-worker'/name):changed_config+=1
 sys.path.insert(0,str(root/'backend-supervisor/code'))
 from backend_records import fingerprint
 records_match=True;total_records=0;total_receipts=0
 for project,expected in proof['projectRecords'].items():
  name=expected['file']
  if not re.fullmatch('[a-f0-9]{64}\\.sqlite',name) or name!=hashlib.sha256(project.encode()).hexdigest()+'.sqlite':raise ValueError('Unexpected record archive')
  compare={k:v for k,v in expected.items() if k!='file'}
  for location,saved in ((folder/'records'/name,True),(root/'backend-supervisor/state/records'/name,False)):
   if location.is_symlink() or not location.is_file():raise ValueError('Missing project record storage')
   with sqlite3.connect(location.as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row;actual=fingerprint(db)
   if saved and actual!=compare:raise ValueError('Saved project records differ')
   if not saved and actual!=compare:records_match=False
  total_records+=compare['records'];total_receipts+=compare['receipts']
 saved_names={v['file'] for v in proof['projectRecords'].values()}
 current_names={p.name for p in (root/'backend-supervisor/state/records').iterdir()}
 if current_names!=saved_names:records_match=False
 return {'component':'backend_journals','backup':str(folder),'verifiedAt':folder.name.removeprefix('backend-build-'),'artifactIntact':True,'currentStateCompared':True,'matchesCurrent':not drift and not changed_sources and not changed_config and records_match,'journalDrift':drift,'changedSourceFiles':changed_sources,'changedPrivateConfigFiles':changed_config,'projectRecordsMatch':records_match,'savedRecords':total_records,'savedReceipts':total_receipts,'scope':'Saved logical journals, records and source verified; current journals, records, source and private configuration compared. Configuration equality is not an independent credential recovery test.'}
def collect(host):
 readers=[('original_database',lambda:database_archive(ROOT/'original-archives',True)),('controller_database',lambda:database_archive(ROOT/'recovery'))] if host=='100' else [('frontend_artifacts',lambda:frontend(ROOT)),('backend_journals',lambda:backend(ROOT))]
 result=[]
 for key,read in readers:
  try:result.append(read())
  except Exception as e:result.append({'component':key,'artifactIntact':False,'inspectionError':type(e).__name__,'scope':'Could not verify this component; inspect its private receipt before any cutover.'})
 return {'capturedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':host,'readOnly':True,'jobsReplayed':False,'components':result,'cutoverReady':False,'limitations':['Separate component checks are not a common recovery point.','Nextcloud files, Windows coding runtime and account login, independent backup location, client-service associations and a coordinated release/rollback rehearsal remain required.']}
if __name__=='__main__':
 if len(sys.argv)!=2 or sys.argv[1] not in ('100','101'):raise SystemExit('Expected fixed component host 100 or 101')
 print(json.dumps(collect(sys.argv[1])))

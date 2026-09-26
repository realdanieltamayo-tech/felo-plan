"""Coherent, inert restore of backend build and execution journals on worker 101."""
from pathlib import Path
import datetime,hashlib,json,os,re,shutil,sqlite3,sys
from contextlib import closing

def main():
 os.umask(0o077);base=Path('/root/felo-codex-preview');worker=base/'gemma-worker';supervisor=base/'backend-supervisor'
 dest=worker/'recovery'/('backend-build-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));dest.mkdir(parents=True,mode=0o700)
 sources={'builds.sqlite':worker/'backend-builds/builds.sqlite','checks.sqlite':supervisor/'state/jobs.sqlite'}
 if (supervisor/'state/previews/previews.sqlite').exists():sources['previews.sqlite']=supervisor/'state/previews/previews.sqlite'
 tables={'builds.sqlite':'builds','checks.sqlite':'jobs','previews.sqlite':'previews','planning.sqlite':'jobs'}
 if (worker/'planning-rescues/planning.sqlite').exists():sources['planning.sqlite']=worker/'planning-rescues/planning.sqlite'
 def fingerprint(path,table):
  with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
   assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
   assert db.execute('SELECT count(*) FROM '+table+" WHERE status NOT IN ('done','failed','stopped')").fetchone()[0]==0,'Wait for backend work and previews to stop'
   schema=db.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name').fetchall()
   rows=db.execute('SELECT * FROM '+table+' ORDER BY '+('run' if table=='previews' else 'id')).fetchall()
   metadata=db.execute('SELECT * FROM meta ORDER BY key').fetchall() if db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='meta'").fetchone()[0] else []
   return {'rows':len(rows),'sha256':hashlib.sha256(json.dumps([schema,rows,metadata],ensure_ascii=False).encode()).hexdigest()}
 expected={}
 for name,path in sources.items():
  table=tables[name];expected[name]=fingerprint(path,table)
  with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(dest/name)) as target:source.backup(target)
  assert fingerprint(dest/name,table)==expected[name]
 # Cross-journal links must resolve to the very same verified source and report.
 with closing(sqlite3.connect(dest/'builds.sqlite')) as builds,closing(sqlite3.connect(dest/'checks.sqlite')) as checks:
  for raw, in builds.execute("SELECT data FROM builds WHERE status='done'"):
   build=json.loads(raw);receipt=build['execution'];row=checks.execute('SELECT status,payload,report FROM jobs WHERE id=?',(receipt['id'],)).fetchone()
   assert row and row[0]=='done'
   assert json.loads(row[1])['contract']==receipt['contract'] and json.loads(row[2])==receipt['report']
  if 'previews.sqlite' in sources:
   with closing(sqlite3.connect(dest/'previews.sqlite')) as previews:
    for job,project,digest in previews.execute('SELECT job,project,digest FROM previews'):
     row=checks.execute('SELECT status,payload,report FROM jobs WHERE id=?',(job,)).fetchone();assert row and row[0]=='done'
     assert json.loads(row[1])['contract']['projectKey']==project and json.loads(row[2])['sourceDigest']==digest
 # Records and their idempotence journal restore together. No generated process
 # may still be active while this coherent multi-database snapshot is taken.
 records={};record_root=supervisor/'state/records'
 if record_root.exists():
  assert not record_root.is_symlink() and record_root.resolve()==record_root
  sys.path.insert(0,str(supervisor/'code'))
  from backend_records import Records,fingerprint as record_fingerprint,PROFILE
  saved_records=dest/'records';saved_records.mkdir(mode=0o700)
  for path in record_root.iterdir():
   assert not path.is_symlink() and path.is_file() and re.fullmatch('[a-f0-9]{64}\\.sqlite',path.name),'Unexpected records storage entry'
   with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
    rows=db.execute('SELECT profile,project FROM identity').fetchall();assert len(rows)==1 and rows[0][0]==PROFILE
    project=rows[0][1]
   assert path.stem==hashlib.sha256(project.encode()).hexdigest()
   with closing(sqlite3.connect(dest/'previews.sqlite')) as previews:
    assert previews.execute("SELECT count(*) FROM previews WHERE project=? AND profile='node-http-records-v1'",(project,)).fetchone()[0]>0
   store=Records(record_root,project);proof=store.snapshot(saved_records/path.name)
   records[project]={'file':path.name,**proof}
 restored=dest/'restored';restored.mkdir()
 for name in sources:
  shutil.copy2(dest/name,restored/name);table=tables[name];assert fingerprint(restored/name,table)==expected[name];assert fingerprint(sources[name],table)==expected[name]
 for project,proof in records.items():
  store=Records(restored/'records',project);shutil.copy2(dest/'records'/proof['file'],store.path)
  with store.db() as db:assert record_fingerprint(db)=={k:v for k,v in proof.items() if k!='file'}
 files=[worker/n for n in ['gemma_worker.py','planning_rescue.py','backend_checks.py','backend_records.py','backend_records_sdk.py','backend_contract.py','backend_rpc.py','backend_proxy.py','backend_generation.py','backend_builder.py','backend_build_api.py','backend_preview_bridge.py','preview_isolation.py','preview_worker_access.py','preview_gateway.py','project_registry.py']]+list((supervisor/'code').glob('*.py'))
 hashes={}
 for path in files:
  relative=path.relative_to(base);saved=dest/'source'/relative;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,saved);hashes[str(relative)]=hashlib.sha256(saved.read_bytes()).hexdigest()
 private=dest/'private';private.mkdir(mode=0o700)
 config={name:(worker/name).read_bytes() for name in ['worker.env','gateway.env','project-registry.json','project-origins.json']}
 for name,raw in config.items():
  (private/name).write_bytes(raw);(private/name).chmod(0o600)
 # Parse restored policy and prove every backend assignment resolves to its
 # successful build. Frontend assignments are retained but belong to a separate
 # source/data recovery set; this is not an independent disaster recovery image.
 sys.path.insert(0,str(dest/'source/gemma-worker'))
 from preview_isolation import PreviewIsolation
 if 'planning.sqlite' in sources:
  from planning_rescue import Queue,validate,digest
  def forbidden(_):raise AssertionError('Restore must not generate a plan')
  restored_plans=Queue(restored,forbidden)
  with restored_plans.connect() as db:
   for job,request_json,request_digest,status,result in db.execute('SELECT id,request,digest,status,result FROM jobs'):
    request=json.loads(request_json);validate(request);assert request['id']==job and digest(request)==request_digest
    assert status in ('done','failed')
    if status=='done':assert isinstance(json.loads(result),dict)
  assert restored_plans.tick() is False
 policy=PreviewIsolation(json.loads((private/'project-registry.json').read_bytes()))
 backend_count=0
 with closing(sqlite3.connect(restored/'builds.sqlite')) as builds:
  for entry in json.loads(config['project-registry.json'])['projects']:
   for job in entry.get('backend_jobs',[]):
    row=builds.execute('SELECT status,data FROM builds WHERE id=?',(job,)).fetchone()
    assert row and row[0]=='done' and json.loads(row[1])['request']['contract']['projectKey']==entry['project']
    backend_count+=1
 for name,raw in config.items():assert (worker/name).read_bytes()==raw and (private/name).read_bytes()==raw,'Configuration changed during backup'
 for name,path in sources.items():assert fingerprint(path,tables[name])==expected[name],'Journal changed during backup'
 for project,proof in records.items():
  with Records(record_root,project).db() as db:assert record_fingerprint(db)=={k:v for k,v in proof.items() if k!='file'},'Records changed during backup'
 result={'verified':True,'backup':str(dest),'journals':expected,'projectRecords':records,'planningRestoredWithoutReplay':'planning.sqlite' in sources,'recordsRestoredWithReceipts':True,'crossJournalReceiptsVerified':True,'sourceHashes':hashes,'privateWorkerConfigBackedUp':True,'gatewayConfigBackedUp':True,'registryVersion':json.loads(config['project-registry.json'])['version'],'backendAssignmentsVerified':backend_count,'servicesRestarted':False,'jobsReplayed':False,'independentDisasterRecovery':False}
 (dest/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':main()

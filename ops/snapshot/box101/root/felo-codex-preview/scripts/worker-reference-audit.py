"""Read-only join of restored controller references and existing worker archives.

Never imports worker queues, runs generated code, writes databases or replays jobs.
"""
from pathlib import Path
import hashlib,importlib.util,json,re,sqlite3,sys
ROOT=Path('/root/felo-codex-preview')
ID=re.compile(r'^[a-f0-9]{32}$')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(root,name,limit=16*1024*1024):
 target=root/name
 if root.is_symlink() or not target.resolve().is_relative_to(root.resolve()):raise ValueError('Unsafe recovery path')
 p=target
 while p!=root:
  if p.is_symlink():raise ValueError('Recovery links are not allowed')
  p=p.parent
 if not target.is_file() or target.stat().st_size>limit:raise ValueError('Invalid bounded recovery file')
 return target.read_bytes()
def load(root,name,limit=16*1024*1024):return json.loads(read(root,name,limit))

def check(snapshot,manifests,states,builds,plans,registry,artifact,record_apps):
 """Pure matching rules; artifact is a bounded saved-file reader, never a runner."""
 assignments={};origins=set();projects=set()
 for p in registry['projects']:
  if p['project'] in projects or p['origin'] in origins:raise ValueError('Duplicate project/origin assignment')
  projects.add(p['project']);origins.add(p['origin'])
  for job in p['jobs']:
   if job in assignments:raise ValueError('Job assigned more than once')
   assignments[job]=p
 used=set();archived=set();code=set();current_jobs=0;failed_jobs=0;planning_jobs=set();data_projects=set()
 def job_state(key,job,backend=False):
  if not isinstance(job,str) or not ID.fullmatch(job):raise ValueError('Invalid referenced job')
  state=(builds if backend else states).get(job)
  if not state or state.get('id')!=job or state.get('status') not in ('done','failed'):raise ValueError('Missing or nonterminal saved worker job')
  claimed=state.get('request',{}).get('contract',{}).get('projectKey') if backend else state.get('projectKey')
  if claimed is not None and claimed!=key:raise ValueError('Worker job belongs to another project')
  if backend and claimed is None:raise ValueError('Backend project identity missing')
  if not backend:
   assigned=assignments.get(job)
   if not assigned or assigned['project']!=key or job in assigned.get('backend_jobs',[]):raise ValueError('Frontend route belongs to another project or is missing')
  used.add(job);return state
 for row in snapshot['projects']:
  key=row['key'];p=row['data'];job=p.get('job');backend=p.get('runtimeProfile') in ('node-http-v1','node-http-records-v1')
  if job:
   state=job_state(key,job['id'],backend);current_jobs+=1
   if backend:
    if state['request']!=job:raise ValueError('Backend request differs from restored controller')
   else:
    for field in ('brief','parent','runtime','provider','routing','useFallback','templateSeed'):
     if field in job and job[field]!=state.get(field):raise ValueError('Frontend request differs from restored controller')
    assigned=assignments[job['id']]
    if p.get('previewOrigin') and p['previewOrigin']!=assigned['origin']:raise ValueError('Restored project preview origin differs')
    expected_app=key if p.get('storageMode')=='server' else None
    if assigned['data_app']!=expected_app:raise ValueError('Project data namespace differs')
    if expected_app:data_projects.add(expected_app)
   if p.get('state')=='failed':
    if state['status']!='failed':raise ValueError('Controller failure differs from saved worker status')
    failed_jobs+=1
   elif p.get('state') in ('complete','phase_review') and state['status']!='done':raise ValueError('Reviewed project has no completed worker job')
  rescue=p.get('planRescue')
  if rescue:
   request=rescue['request'];saved=plans.get(request['id'])
   if not saved or saved['request']!=request or saved['digest']!=rescue['requestDigest'] or request['project']!=key or request['revision']!=p['planJob']:raise ValueError('Planning recovery reference differs')
   if saved['status'] not in ('done','failed'):raise ValueError('Planning recovery has active work')
   planning_jobs.add(request['id'])
 # Historical template-source snapshots may contain earlier active status; only
 # their archived successful phases are linked, never replayed or re-approved.
 for row in snapshot['projects']+snapshot['sources']:
  key=row.get('key',row.get('project_key'));p=row.get('data',row.get('source'))
  for phase in p.get('phases',[]):
   if not phase.get('archive'):continue
   backend=p.get('runtimeProfile') in ('node-http-v1','node-http-records-v1')
   state=job_state(key,phase.get('job'),backend)
   if state['status']!='done':raise ValueError('Archived phase points to a failed job')
   if backend:raise ValueError('Archived backend phases need an execution-receipt join before this audit can verify them')
   archive=phase['archive'];files=manifests.get(archive)
   if not isinstance(files,list) or not files:raise ValueError('Missing saved phase manifest')
   archived.add(archive)
   for f in files:
    name=f['path']
    if not isinstance(name,str) or name.startswith('/') or '\\' in name or any(x in ('','.','..') for x in name.split('/')):raise ValueError('Unsafe archived code path')
    raw=artifact(phase['job'],name)
    if len(raw)!=f['bytes'] or sha(raw)!=f['sha256']:raise ValueError('Worker source differs from the archived phase')
    code.add((archive,name))
 return {'verified':True,'projects':len(snapshot['projects']),'templateSources':len(snapshot['sources']),'currentJobsMatched':current_jobs,'failedCurrentJobsPreserved':failed_jobs,'archivedPhasesMatched':len(archived),'codeFilesMatched':len(code),'planningJobsMatched':len(planning_jobs),'referencedWorkerJobs':len(used),'frontendDataNamespacesMatched':len(data_projects),'savedFrontendRecordNamespaces':len(record_apps),'unreferencedFrontendRecordNamespaces':len(set(record_apps)-data_projects),'unreferencedFrontendJobs':len(set(states)-used),'unreferencedBackendBuilds':len(set(builds)-used),'cutoverReady':False}

def main(bundle_path):
 spec=importlib.util.spec_from_file_location('release_inventory',ROOT/'scripts/inspect-release-components.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
 bundle=load(bundle_path.parent,bundle_path.name)
 # The transfer receipt binds the JSON bytes. Canonical equality with Node was
 # established in the prior offline database/Nextcloud rehearsal.
 backend=inv.latest(ROOT/'gemma-worker/recovery',r'backend-build-\d{8}T\d{6}Z');bp=inv.receipt(backend)
 frontend=inv.latest(ROOT/'gemma-worker/recovery',inv.STAMP);fp=inv.receipt(frontend)
 if bp.get('jobsReplayed') is not False or fp.get('jobs_executed') is not False:raise ValueError('No-replay evidence missing')
 inv.file_check(frontend,'worker-artifacts.tar.gz',fp['archive_sha256']);inv.file_check(frontend,'preview-data.sqlite',fp['sqlite_sha256'])
 manifest=load(frontend,'artifact-manifest.json',4*1024*1024)
 states={}
 for name,expected in manifest.items():
  if name.endswith('/state.json') and len(name.split('/'))==2:
   job=name.split('/')[0]
   if not ID.fullmatch(job):raise ValueError('Invalid saved state path')
   raw=read(frontend,'restored/'+name,2*1024*1024)
   if sha(raw)!=expected:raise ValueError('Restored frontend state changed')
   states[job]=json.loads(raw)
 def artifact(job,name):
  rel=job+'/workspace/'+name;raw=read(frontend,'restored/'+rel,4*1024*1024)
  if sha(raw)!=manifest.get(rel):raise ValueError('Restored frontend source changed')
  return raw
 builds={};plans={}
 for name,table in [('builds.sqlite','builds'),('planning.sqlite','jobs')]:
  if inv.journal(backend/name,table)!=bp['journals'][name]:raise ValueError('Saved worker journal changed')
  with sqlite3.connect((backend/name).as_uri()+'?mode=ro',uri=True) as db:
   if name=='builds.sqlite':
    for ident,status,data in db.execute('SELECT id,status,data FROM builds'):
     state=json.loads(data)
     if state.get('id')!=ident or state.get('status')!=status:raise ValueError('Inconsistent build identity/status')
     builds[ident]=state
   else:
    for ident,status,request,digest in db.execute('SELECT id,status,request,digest FROM jobs'):plans[ident]={'status':status,'request':json.loads(request),'digest':digest}
 registry=load(backend,'private/project-registry.json',1024*1024)
 policy_name='gemma-worker/preview_isolation.py'
 inv.file_check(backend/'source',policy_name,bp['sourceHashes'][policy_name])
 policy=inv.module(backend/'source'/policy_name,'saved_preview_policy')
 policy.PreviewIsolation(registry)
 with sqlite3.connect((frontend/'preview-data.sqlite').as_uri()+'?mode=ro',uri=True) as db:record_apps=[r[0] for r in db.execute('SELECT DISTINCT app FROM records')]
 report=check(bundle['snapshot'],bundle['manifests'],states,builds,plans,registry,artifact,record_apps)
 report.update(frontendBackup=str(frontend),backendBackup=str(backend),controllerReferenceRehearsal=bundle['rehearsal'],referenceTransferSha256=sha(read(bundle_path.parent,bundle_path.name)),jobsReplayed=False,liveDataChanged=False,scope='Saved archived frontend phase files, current controller job requests/status, planning requests, project preview origins and frontend data namespaces. Archived backend success/execution joins, unreferenced jobs, all attempt history and live services are not verified.')
 print(json.dumps(report))

if __name__=='__main__':main(Path(sys.argv[1]).resolve())

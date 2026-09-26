"""Bounded, ephemeral Node backend checks. Not a deployment or public server.

Only a trusted caller supplies expected HTTP checks. No model-supplied commands,
dependencies, images, host mounts or environment variables are accepted.
"""
import hashlib,json,os,re,selectors,subprocess,tempfile,time,uuid
from pathlib import Path
from contextlib import ExitStack

MAX_SOURCE=262144
MAX_RESPONSE=32768
IMAGE=re.compile(r'^sha256:[a-f0-9]{64}$')
JOB=re.compile(r'^[a-f0-9]{32}$')
BOOTSTRAP="""import http from 'node:http';
const {default:handler}=await import('/app/server.mjs');
if(typeof handler!=='function')throw Error('server.mjs must export a request handler');
const server=http.createServer((req,res)=>{Promise.resolve().then(()=>handler(req,res)).catch(()=>{if(!res.headersSent)res.writeHead(500,{'Content-Type':'text/plain'});res.end('Backend request failed');});});
server.requestTimeout=4000;server.headersTimeout=4000;server.maxHeadersCount=32;
server.listen(3000,'127.0.0.1');
"""
CLIENT="""const http=require('node:http');let input='';
process.stdin.on('data',x=>{input+=x;if(input.length>65536)process.exit(2)});
process.stdin.on('end',()=>{const q=JSON.parse(input);let done=false;
const finish=x=>{if(!done){done=true;process.stdout.write(JSON.stringify(x));}};
const req=http.request({hostname:'127.0.0.1',port:3000,path:q.path,method:q.method,headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(q.body)}},res=>{
let bytes=0,chunks=[];res.on('data',x=>{bytes+=x.length;if(bytes>32768){finish({error:'Response exceeds limit'});res.destroy();}else chunks.push(x)});
res.on('end',()=>finish({status:res.statusCode,body:Buffer.concat(chunks).toString('base64')}));res.on('error',()=>finish({error:'Response interrupted'}));});
req.setTimeout(4000,()=>{finish({error:'Request timed out'});req.destroy()});
req.on('error',()=>finish({error:'Backend is unavailable'}));req.end(q.body);});
"""

class BackendCheckError(ValueError):pass

def source_files(files):
    if not isinstance(files,dict) or not 1<=len(files)<=32:raise BackendCheckError('Provide one to 32 backend source files')
    result={};total=0
    for name,content in files.items():
        if (not isinstance(name,str) or len(name)>160 or not re.fullmatch(r'[A-Za-z0-9_/-]+\.(mjs|js|json|html|css|txt|md)',name)
            or any(part in ('','node_modules') or part.startswith('.') for part in name.split('/'))):raise BackendCheckError('Invalid backend source path')
        if not isinstance(content,str) or '\0' in content:raise BackendCheckError('Backend source must be UTF-8 text')
        data=content.encode('utf-8');total+=len(data)
        if total>MAX_SOURCE:raise BackendCheckError('Backend source exceeds its limit')
        result[name]=data
    if 'server.mjs' not in result:raise BackendCheckError('Backend entry point server.mjs is required')
    if 'package.json' in result or 'package-lock.json' in result:raise BackendCheckError('Dependency installation is not supported by this executor')
    if any(b.startswith(a+'/') for a in result for b in result):raise BackendCheckError('Conflicting backend source paths')
    return result

def http_checks(checks):
    if not isinstance(checks,list) or not 1<=len(checks)<=8:raise BackendCheckError('Provide one to eight independent HTTP checks')
    result=[]
    for c in checks:
        if not isinstance(c,dict) or set(c)!={'name','method','path','body','status','response'}:raise BackendCheckError('Invalid HTTP check fields')
        if not isinstance(c['name'],str) or not 1<=len(c['name'])<=120:raise BackendCheckError('Invalid check name')
        if c['method'] not in ('GET','POST','PUT','PATCH','DELETE'):raise BackendCheckError('Unsupported HTTP method')
        if not isinstance(c['path'],str) or not re.fullmatch(r'/[A-Za-z0-9/_?=&.%-]{0,300}',c['path']) or c['path'].startswith('//'):raise BackendCheckError('Use a relative backend request path')
        if type(c['status']) is not int or not 100<=c['status']<=599:raise BackendCheckError('Invalid expected status')
        if any(not isinstance(c[k],str) or len(c[k].encode('utf-8'))>MAX_RESPONSE for k in ['body','response']):raise BackendCheckError('HTTP content exceeds its limit')
        if c['method']=='GET' and c['body']:raise BackendCheckError('GET checks cannot send a body')
        result.append(dict(c))
    return result

def bounded_command(args,body='',timeout=10,limit=65536):
    """Linux pipe reads cap combined stdout/stderr; child output is untrusted."""
    if os.name!='posix':raise BackendCheckError('Backend execution requires the Linux worker')
    with tempfile.TemporaryFile() as request:
        request.write(body.encode('utf-8'));request.seek(0)
        p=subprocess.Popen(args,stdin=request,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        buffers={p.stdout:bytearray(),p.stderr:bytearray()};size=0;deadline=time.monotonic()+timeout
        selector=selectors.DefaultSelector()
        for stream in buffers:selector.register(stream,selectors.EVENT_READ)
        try:
            while selector.get_map():
                remaining=deadline-time.monotonic()
                if remaining<=0:raise BackendCheckError('Backend command timed out')
                for key,_ in selector.select(min(remaining,.2)):
                    data=os.read(key.fileobj.fileno(),8192)
                    if not data:selector.unregister(key.fileobj);continue
                    size+=len(data)
                    if size>limit:raise BackendCheckError('Backend command output exceeded its limit')
                    buffers[key.fileobj].extend(data)
            code=p.wait(timeout=max(.01,deadline-time.monotonic()))
            return code,bytes(buffers[p.stdout]).decode('utf-8','replace'),bytes(buffers[p.stderr]).decode('utf-8','replace')
        except subprocess.TimeoutExpired as error:raise BackendCheckError('Backend command timed out') from error
        finally:
            selector.close()
            if p.poll() is None:p.kill()
            p.wait(timeout=5)
            p.stdout.close();p.stderr.close()

def container_command(name,marker,workspace,image):
    return ['docker','run','-d','--name',name,'--label','felo-backend-check='+marker,'--pull','never',
        '--network','none','--read-only','--user','65534:65534','--cap-drop','ALL','--security-opt','no-new-privileges:true',
        '--pids-limit','64','--memory','256m','--memory-swap','256m','--cpus','0.5','--init','--cgroupns','private',
        '--log-driver','none','--shm-size','8m','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777',
        '--workdir','/app','--mount','type=bind,src='+str(workspace)+',dst=/app,readonly',
        '--entrypoint','/usr/bin/env',image,'-i','PATH=/usr/local/bin:/usr/bin:/bin','HOME=/tmp','NODE_ENV=test',
        'node','--input-type=module','-e',BOOTSTRAP]

class BackendChecker:
    def __init__(self,image,staging,command=bounded_command):
        if not isinstance(image,str) or not IMAGE.fullmatch(image):raise BackendCheckError('Use a locally verified immutable image ID')
        self.image=image;self.staging=Path(staging);self.command=command
        if not self.staging.is_absolute() or self.staging.is_symlink():raise BackendCheckError('Use an absolute private staging directory')

    def execute(self,job,files,checks,run_id=None,profile='node-http-v1'):
        from backend_contract import report_profile
        report_type=report_profile(profile);records=profile=='node-http-records-v1'
        if not isinstance(job,str) or not JOB.fullmatch(job):raise BackendCheckError('Invalid backend job ID')
        sources=source_files(files);checks=http_checks(checks)
        self.staging.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.staging.resolve()!=self.staging:raise BackendCheckError('Staging path cannot traverse a symlink')
        if run_id is not None and (not isinstance(run_id,str) or not JOB.fullmatch(run_id)):raise BackendCheckError('Invalid backend run ID')
        marker=run_id or uuid.uuid4().hex;name='felo-backend-'+job[:12]+'-'+marker[:12]
        digest=hashlib.sha256(''.join(n+'\0'+hashlib.sha256(b).hexdigest()+'\n' for n,b in sorted(sources.items())).encode()).hexdigest()
        report={'profile':report_type,'job':job,'image':self.image,'sourceDigest':digest,'passed':False,'checks':[],
            'deployment':False,'persistentData':False,'network':'none','cleanupVerified':False}
        if records:report['storageScope']='disposable-check'
        deadline=time.monotonic()+90;cleaning=False
        def command(args,body='',timeout=10):
            if not cleaning:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise BackendCheckError('Backend run exceeded its deadline')
                timeout=min(timeout,remaining)
            code,out,_=self.command(args,body=body,timeout=timeout)
            if code:raise BackendCheckError('Backend container operation failed')
            return out
        with ExitStack() as resources:
            folder=resources.enter_context(tempfile.TemporaryDirectory(prefix='backend-check-',dir=self.staging))
            workspace=Path(folder)/'source';workspace.mkdir(mode=0o755);workspace.chmod(0o755)
            for n,data in sources.items():
                p=workspace/n;p.parent.mkdir(parents=True,exist_ok=True,mode=0o755);p.write_bytes(data);p.chmod(0o444)
            for directory in workspace.rglob('*'):
                if directory.is_dir():directory.chmod(0o755)
            attempted=False
            try:
                attempted=True
                args=container_command(name,marker,workspace,self.image)
                if records:
                    from backend_records import Records,Broker
                    from backend_records_sdk import records_command,records_mounts_match
                    # Use the already-owned staging directory. A systemd
                    # PrivateTmp service and Docker do not share /tmp paths.
                    isolated=Path(folder)
                    broker=Broker(Records(isolated/'data','check-'+marker),isolated/'r.sock');resources.callback(broker.close)
                    args=records_command(name,marker,workspace,self.image,broker.path)
                command(args,timeout=20)
                info=json.loads(command(['docker','inspect',name]))[0]
                host=info['HostConfig'];config=info['Config']
                if not (info['Image']==self.image and config['User']=='65534:65534' and host['NetworkMode']=='none' and host['ReadonlyRootfs']
                    and host['Privileged'] is False and host['CapDrop']==['ALL'] and host['Memory']==268435456 and host['MemorySwap']==268435456
                    and host['PidsLimit']==64 and host['NanoCpus']==500000000 and 'no-new-privileges:true' in host['SecurityOpt']
                    and (records_mounts_match(info,workspace,broker.path) if records else len(info['Mounts'])==1 and info['Mounts'][0]['Destination']=='/app' and not info['Mounts'][0]['RW'])):
                    raise BackendCheckError('Backend runtime did not enforce its isolation profile')
                report['runtimeVerified']=True
                exec_args=['docker','exec','-i','--user','65534:65534',name,'/usr/bin/env','-i','PATH=/usr/local/bin:/usr/bin:/bin','node','-e',CLIENT]
                # Startup accepts an HTTP response of any status; only the supplied
                # independent checks decide whether behavior passes.
                ready=False;readiness_deadline=time.monotonic()+12
                while time.monotonic()<readiness_deadline:
                    response=json.loads(command(exec_args,json.dumps({'method':'GET','path':'/','body':''}),timeout=6))
                    if 'status' in response:ready=True;break
                    state=json.loads(command(['docker','inspect',name]))[0]['State']
                    if not state.get('Running'):break
                    time.sleep(.2)
                if not ready:raise BackendCheckError('Backend did not become ready')
                import base64
                for c in checks:
                    response=json.loads(command(exec_args,json.dumps({k:c[k] for k in ['method','path','body']}),timeout=6))
                    actual=base64.b64decode(response.get('body',''),validate=True)
                    passed='error' not in response and response.get('status')==c['status'] and actual==c['response'].encode('utf-8')
                    report['checks'].append({'name':c['name'],'passed':passed,'status':response.get('status'),
                        'responseSha256':hashlib.sha256(actual).hexdigest(),'responseBytes':len(actual),
                        'error':response.get('error') if 'error' in response else None})
                report['passed']=all(c['passed'] for c in report['checks'])
            except (BackendCheckError,ValueError,KeyError,TypeError,IndexError) as error:
                report['error']=str(error) if isinstance(error,BackendCheckError) else 'Invalid response from backend runtime'
            finally:
                cleaning=True
                if attempted:
                    try:
                        code,out,_=self.command(['docker','inspect',name],body='',timeout=10)
                        if code:
                            # A failing inspect can mean an unavailable daemon; it
                            # is not evidence that the temporary container is gone.
                            command(['docker','info','--format','{{.ServerVersion}}'])
                            listed=command(['docker','ps','-aq','--filter','name=^/'+name+'$'])
                            if listed:raise BackendCheckError('Backend cleanup could not be confirmed')
                        else:
                            info=json.loads(out)[0]
                            if info['Config']['Labels'].get('felo-backend-check')!=marker:raise BackendCheckError('Backend ownership check failed')
                            command(['docker','rm','-f',name])
                            if command(['docker','ps','-aq','--filter','name=^/'+name+'$']):raise BackendCheckError('Backend container remains after cleanup')
                        report['cleanupVerified']=True
                    except Exception:
                        report['passed']=False;report['error']='Backend cleanup could not be confirmed; inspect the worker before retrying'
                else:report['cleanupVerified']=True
        return report

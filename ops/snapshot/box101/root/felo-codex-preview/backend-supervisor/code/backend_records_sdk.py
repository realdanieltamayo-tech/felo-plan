"""Trusted Node records client and opt-in container wiring.

This capability is not enabled by adding a file to generated source. A trusted
runtime must explicitly create a project-scoped broker and mount its socket.
"""
from pathlib import Path
from backend_checks import BOOTSTRAP,BackendCheckError,container_command

SDK="""import net from 'node:net';
import {randomUUID} from 'node:crypto';
const recordsError=(code,message)=>Object.assign(new Error(message),{code});
function recordsCall(q){return new Promise((resolve,reject)=>{
 let body;try{body=Buffer.from(JSON.stringify(q));}catch{reject(recordsError('invalid','Use JSON record data'));return;}
 if(body.length>65536){reject(recordsError('invalid','Records request exceeds its limit'));return;}
 let settled=false,parts=[],bytes=0,wanted=null;
 const socket=net.createConnection({path:'/felo-data.sock'});
 const finish=(err,data)=>{if(settled)return;settled=true;clearTimeout(timer);socket.destroy();err?reject(err):resolve(data);};
 const uncertain=()=>finish(recordsError('uncertain','The operation could not be confirmed. Retain its request ID and check before retrying.'));
 const timer=setTimeout(uncertain,5500);
 socket.on('connect',()=>{const h=Buffer.alloc(4);h.writeUInt32BE(body.length);socket.end(Buffer.concat([h,body]));});
 socket.on('error',uncertain);socket.on('end',()=>{if(!settled)uncertain();});
 socket.on('data',chunk=>{
  bytes+=chunk.length;if(bytes>65540){uncertain();return;}parts.push(chunk);
  const data=Buffer.concat(parts);
  if(wanted===null&&data.length>=4){wanted=data.readUInt32BE(0);if(wanted<1||wanted>65536){uncertain();return;}}
  if(wanted!==null&&data.length>=wanted+4){
   if(data.length!==wanted+4){uncertain();return;}
   let r;try{r=JSON.parse(data.subarray(4).toString('utf8'));}catch{uncertain();return;}
   if(r?.ok===true&&r.data&&typeof r.data==='object')finish(null,r.data);
   else if(r?.ok===false&&['invalid','conflict','capacity','denied','uncertain','unavailable'].includes(r.code)&&typeof r.error==='string')finish(recordsError(r.code,r.error));
   else uncertain();
  }
 });
});}
const FeloRecords=Object.freeze({
 newRequestId:()=>randomUUID().replaceAll('-',''),
 get:key=>recordsCall({op:'get',key}),
 list:({after=null,limit=25}={})=>recordsCall({op:'list',after,limit}),
 put:({key,value,expectedVersion,requestId})=>recordsCall({op:'put',key,value,expectedVersion,requestId})
});
const FeloContext=Object.freeze({records:FeloRecords});
"""
RECORDS_BOOTSTRAP=SDK+BOOTSTRAP.replace('handler(req,res)','handler(req,res,FeloContext)')

def records_command(name,marker,workspace,image,socket_path):
 path=Path(socket_path)
 if not path.is_absolute() or path.resolve()!=path or not path.is_socket():raise BackendCheckError('Use a verified project records socket')
 args=container_command(name,marker,workspace,image)
 index=args.index('--entrypoint');args[index:index]=['--mount','type=bind,src='+str(path)+',dst=/felo-data.sock,readonly']
 args[-1]=RECORDS_BOOTSTRAP
 return args

def records_mounts_match(info,workspace,socket_path):
 mounts=info.get('Mounts') or []
 expected={'/app':str(workspace),'/felo-data.sock':str(socket_path)}
 return len(mounts)==2 and {m.get('Destination') for m in mounts}==set(expected) and all(m.get('Type')=='bind' and m.get('RW') is False and m.get('Source')==expected.get(m.get('Destination')) for m in mounts)

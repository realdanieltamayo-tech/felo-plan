const {Pool}=require('pg');const {memoryContext}=require('/w/app/lib/memory-context.js');
const pool=new Pool({connectionString:process.env.DB,options:'-c default_transaction_read_only=on'});const query=async(s,p)=>(await pool.query(s,p)).rows;
const sys='You are Felo, the assistant of Daniel Tamayo, owner of Felo Global Concepts Corp. Answer in two short sentences. Never invent a number, name or date you were not given; say you do not know instead.';
async function ask(user){const r=await fetch(process.env.OLLAMA_URL+'/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'gemma4:e4b',stream:false,think:false,options:{temperature:0},messages:[{role:'system',content:sys},{role:'user',content:user}]})});return ((await r.json()).message.content||'').replace(/\s+/g,' ').trim().slice(0,260);}
(async()=>{for(const q of ['Where am I based and what time zone do I work in?','How much is the Solo tier of Felo Studio Cloud?','What did we quote Odalyake?']){
 const mem=await memoryContext(query,q);
 console.log('\nQ: '+q+'\n  memory sent: '+mem.split('\n').length+' lines, '+mem.length+' chars');
 console.log('  BEFORE: '+await ask(q));console.log('  AFTER:  '+await ask(mem+'\n\nDANIEL ASKS: '+q));}
 await pool.end();})().catch(e=>{console.log('ERROR',e.message);process.exit(1);});

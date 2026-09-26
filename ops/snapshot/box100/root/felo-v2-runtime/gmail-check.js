const secret=require('fs').readFileSync(0,'utf8').trim();
const {createEmailService}=require('/repair/lib/email-connection');const {query}=require('/repair/lib/core');
const which=process.argv[1]==='old'?process.env.GMAIL_CLIENT_SECRET:secret;
createEmailService({env:{...process.env,GMAIL_CLIENT_SECRET:which},query}).gmail.status()
 .then(s=>{console.log(process.argv[1]+' secret -> connected:',s.connected,s.connected?'('+String(s.account).replace(/^(.).*@/,'$1…@')+')':'| '+s.error);process.exit(0);})
 .catch(e=>{console.log(process.argv[1]+' secret -> error:',e.message);process.exit(0);});

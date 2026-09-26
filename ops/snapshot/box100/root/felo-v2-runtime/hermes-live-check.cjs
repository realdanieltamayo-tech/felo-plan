const {createHermesChat,hermesTurn}=require('/w/app/lib/hermes-chat.js');
const h=createHermesChat({url:process.env.HERMES_API_URL,key:process.env.HERMES_API_KEY,conversation:'felo-hq-livecheck'});
const saved=[];
(async()=>{console.log('health:',await h.health());
 const t0=Date.now();const out=await hermesTurn(h,async(r,b,br)=>saved.push(r+':'+br),'Quick check from the Felo screen: reply in one sentence confirming you are the assistant behind the Felo screen now.');
 console.log('reply ('+((Date.now()-t0)/1000).toFixed(1)+'s):',out.reply.slice(0,200));console.log('brain:',out.brain,'| saved turns:',saved.join(', '));})();

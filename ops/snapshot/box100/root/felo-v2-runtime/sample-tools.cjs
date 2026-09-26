// Sample-data copy of the Felo tool server, only for testing Hermes' MCP client. No real Felo data.
const {startToolsServer}=require('/w/app/lib/felo-tools.js');
const rows=async q=>/crm_leads l/.test(q)?[{id:1,title:'Sample lead',name:'Sample Person'}]:[];
startToolsServer({key:process.env.K,port:8090,deps:{query:rows,crm:{list:async()=>({rows:[]}),get:async()=>({})},memory:{list:async()=>({rows:[]})},
 gmail:{list:async()=>({rows:[]}),body:async()=>({})},calendar:{overview:async()=>({upcoming:[]})},
 status:{waiting:async()=>({count:0,items:[]}),servers:async()=>({summary:'sample'})}}});

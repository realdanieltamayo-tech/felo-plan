const vm=require('vm'),fs=require('fs');
for(const f of ['app/memory.html','app/calendar.html']){let n=0;for(const m of fs.readFileSync(f,'utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)){new vm.Script(m[1]);n++;}console.log(f+' scripts ok ('+n+')');}

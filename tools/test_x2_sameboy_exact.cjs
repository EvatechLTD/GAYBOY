const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
 const core=await require(path.resolve('build/sync_link_core.cjs'))();
 const rom=fs.readFileSync('build/GAYBOY-meter-stretch-fix.gb'),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);core._link_init(ptr,rom.length);core._free(ptr);core._link_set_connected(0);
 const S=Object.fromEntries(fs.readFileSync('build/GAYBOY-meter-stretch-fix.noi','utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{let a=l.split(/\s+/);return[a[1],parseInt(a[2],16)];}));
 const v=(n,o=0)=>core._link_state_read(0,S['_'+n]+o),put=(n,x,o=0)=>core._link_state_write(0,S['_'+n]+o,x&255),word=(n,x,o=0)=>{put(n,x,o);put(n,x>>8,o+1);};
 const run=n=>core._link_run(n),until=f=>{for(let i=0;i<3000;i++){if(f())return;run(1);}throw Error('timeout');},keys={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function down(k){core._link_key(0,keys[k],1);until(()=>v('lastpad')&(1<<keys[k]));}
 function up(k){core._link_key(0,keys[k],0);until(()=>!(v('lastpad')&(1<<keys[k])));run(8);}
 function tap(k){down(k);up(k);}
 function tracks(){let count=v('seqeventcounts',4)|(v('seqeventcounts',5)<<8),off=v('seqeventoffsets',4)|(v('seqeventoffsets',5)<<8),slot=v('mx',1),out=[];core._link_write(0,0x4000,1+(slot>>2));for(let i=0;i<count;i++)out.push(Array.from({length:4},(_,j)=>core._link_read(0,0xa300+(slot&3)*2048+(off+i)*4+j)));core._link_write(0,0x4000,0);return out;}
 until(()=>v('introready'));down('start');until(()=>!v('introactive')&&v('page')==8);up('start');run(60);
 for(let c=0;c<7;c++){word('seqeventcounts',0,c*2);word('seqeventoffsets',0,c*2);word('seqlength',12,c*2);}put('seqbeats',3);put('seqdenom',4);put('seqtrack',2);put('selected',2);put('seqzoom',1);put('seqgrouptrack',255);put('seqhead',0);put('seqfocus',0);put('sticky_start',1);word('seqdefaultdur',1,4);
 for(let i=0;i<4;i++){put('seqcursor',i*3,2);put('seqpitch',[36,39,42,43][i],2);put('seqtop',48,2);put('seqdrawvalid',0);put('dirty',1);run(80);down('b');if(i==0){tap('right');tap('right');}up('b');run(80);}
 const before=tracks();assert.deepEqual(before.map(e=>e[3]),[3,3,3,3]);
 const save=Buffer.alloc(32768);core._link_write(0,0,10);for(let bank=0;bank<4;bank++){core._link_write(0,0x4000,bank);for(let j=0;j<8192;j++)save[bank*8192+j]=core._link_read(0,0xa000+j);}core._link_write(0,0x4000,0);fs.writeFileSync('build/x2-exact-before.sav',save);
 tap('start');assert(v('navopen'));tap('right');until(()=>v('navcategory')==1);for(let i=0;i<20&&v('navchoice')!=51;i++)tap('down');assert.equal(v('navchoice'),51);tap('a');run(120);
 const after=tracks();console.log(JSON.stringify({before,after,loop:v('seqlength',4)|(v('seqlength',5)<<8),cols:v('seqcols')}));assert.deepEqual(after.map(e=>e[3]),[6,6,6,6]);assert.deepEqual(after.map(e=>e[0]),[0,6,12,18]);
 fs.writeFileSync('build/x2-sameboy-exact.json',JSON.stringify({before,after}));
 const pixels=core._link_pixels(0);fs.writeFileSync('build/x2-sameboy-exact.rgba',Buffer.from(core.HEAPU8.subarray(pixels,pixels+160*144*4)));
 console.log('PASS actual SameBoy core:four dragged3-step notes all become6 via real menu');
})();

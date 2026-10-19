/* Real SameBoy cable: no writes to SB, SC, IF or the ROM's receive queue. */
const fs=require('fs'),assert=require('assert');
(async()=>{
 const core=await require('../build/sync_link_core.cjs')();
 const arg=process.argv.indexOf('--rom'),romPath=arg<0?'build/GAYBOY.gb':process.argv[arg+1];
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return [a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);core._link_init(ptr,rom.length);core._free(ptr);
 core._link_watch_rx(S['_rx']);
 let frames=0;const run=n=>{core._link_run(n);frames+=n;};
 const v=(i,n)=>core._link_read(i,S['_'+n]);
 const word=(i,n)=>v(i,n)|(core._link_read(i,S['_'+n]+1)<<8);
 const put=(i,n,x)=>core._link_write(i,S['_'+n],x);
 const until=(fn,max=3000)=>{for(let n=0;n<max;n++){if(fn())return n;run(1);}throw Error('Timed out at frame '+frames+' '+JSON.stringify([0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_read(i,0xff90),servicing:v(i,'seqservicing'),armed:v(i,'syncarmed'),sub:v(i,'syncsub'),drops:word(i,'mixunderruns'),ticks:word(i,'seqticks'),pad:v(i,'lastpad')}))));};
 const key={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function press(i,k){const mask=1<<key[k];core._link_key(i,key[k],1);until(()=>v(i,'lastpad')&mask,180);core._link_key(i,key[k],0);until(()=>!(v(i,'lastpad')&mask),180);run(4);}
 function choose(i,page){press(i,'start');until(()=>v(i,'navopen'),180);const category=[19,20,24,25].includes(page)?4:page===0?3:0;for(let n=0;n<5&&v(i,'navcategory')!==category;n++)press(i,'right');for(let n=0;n<40&&v(i,'navchoice')!==page;n++)press(i,'down');assert.equal(v(i,'navchoice'),page);press(i,'a');until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);


 const m=(i,n)=>core._link_state_read(i,S['_mx']+n),setm=(i,n,x)=>core._link_state_write(i,S['_mx']+n,x);
 const heading=()=>Array.from({length:6},(_,j)=>String.fromCharCode(core._link_state_read(0,S['_canvas']+260+j)+32)).join('').trim();
 choose(0,18);setm(0,4,37);press(0,'right');assert.equal(m(0,4),30);assert.equal(v(0,'mixer_device'),0);assert.equal(heading(),'LOCAL');
 setm(0,4,30);press(0,'a');until(()=>v(0,'linkstate')===2&&v(1,'linkstate')===2,1800);
 setm(0,4,37);press(0,'right');run(20);assert.equal(v(0,'mixer_device'),1);assert.equal(m(0,4),30);assert.equal(heading(),'LINKED');
 for(let n=0;n<8;n++)press(0,'right');assert.equal(v(0,'mixer_device'),0);assert.equal(m(0,4),30);assert.equal(heading(),'LOCAL');
 press(0,'left');assert.equal(v(0,'mixer_device'),1);assert.equal(m(0,4),37);assert.equal(heading(),'LINKED');
 core._link_set_connected(0);run(240);put(0,'dirty',1);run(20);assert.equal(heading(),'LOCAL');
 setm(0,4,37);press(0,'right');assert.equal(m(0,4),30);assert.equal(heading(),'LOCAL');
 console.log('PASS: local-only paging without peer, connected LOCAL/LINKED banks, cross-bank wrap and disconnect fallback');
})().catch(e=>{console.error(e);process.exitCode=1;});

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
 function choose(i,page){core._link_key(i,7,1);until(()=>v(i,'navopen'));put(i,'navchoice',page);press(i,'a');core._link_key(i,7,0);until(()=>!(v(i,'lastpad')&128));run(35);assert.equal(v(i,'page'),page===45?28:page);}

 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);

 // OFF is the real boot policy. Opt each endpoint into native sync through UI,
 // including interrupt-handler replacement, rather than poking syncmode.
 for(const i of [0,1]){
  assert.equal(v(i,'syncmode'),0,'Boot must default to OFF');
  put(i,'sticky_start',1);choose(i,27);
  core._link_key(i,5,1);until(()=>v(i,'lastpad')&32);press(i,'up');core._link_key(i,5,0);until(()=>!(v(i,'lastpad')&32));
  assert.equal(v(i,'syncmode'),1);choose(i,8);
 }
 choose(0,27);press(0,'down');
 core._link_key(0,5,1);until(()=>v(0,'lastpad')&32);press(0,'up');core._link_key(0,5,0);until(()=>!(v(0,'lastpad')&32));
 assert(!v(0,'syncslave')&&v(1,'syncslave'));
 core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));
 until(()=>v(0,'linkstate')===2&&v(1,'linkstate')===2,1200);
 assert(v(0,'seqplaying')&&v(1,'seqplaying'));run(180);assert(!v(0,'overflow')&&!v(1,'overflow'));
 core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));until(()=>!v(1,'seqplaying'),300);
 console.log('PASS default OFF, explicit native opt-in, real-cable discovery, play and stop');
})().catch(e=>{console.error(e);process.exitCode=1;});

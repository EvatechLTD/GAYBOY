/* Real SameBoy cable: no writes to SB, SC, IF or the ROM's receive queue. */
const fs=require('fs'),assert=require('assert');
(async()=>{
 const core=await require('../build/sync_link_core.cjs')();
 const arg=process.argv.indexOf('--rom'),romPath=arg<0?'build/GAYBOY.gb':process.argv[arg+1];
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return [a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);core._link_init(ptr,rom.length);core._free(ptr);
 const referenceArg=process.argv.indexOf('--reference-rom'),oldPath=referenceArg<0?'build/main-baseline/GAYBOY.gb':process.argv[referenceArg+1];assert(fs.existsSync(oldPath),'Build a reference main ROM and pass --reference-rom path');const oldSymbols=Object.fromEntries(fs.readFileSync(oldPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return[a[1],parseInt(a[2],16)];}));
 const oldROM=fs.readFileSync(oldPath),oldPtr=core._malloc(oldROM.length);core.HEAPU8.set(oldROM,oldPtr);core._link_load_rom(1,oldPtr,oldROM.length);core._free(oldPtr);const Ss=[S,oldSymbols];
 let frames=0;const run=n=>{core._link_run(n);frames+=n;};
 const v=(i,n)=>core._link_read(i,Ss[i]['_'+n]);
 const word=(i,n)=>v(i,n)|(core._link_read(i,Ss[i]['_'+n]+1)<<8);
 const put=(i,n,x)=>core._link_write(i,Ss[i]['_'+n],x);
 const until=(fn,max=3000)=>{for(let n=0;n<max;n++){if(fn())return n;run(1);}throw Error('Timed out at frame '+frames+' '+JSON.stringify([0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_read(i,0xff90),servicing:v(i,'seqservicing'),armed:v(i,'syncarmed'),sub:v(i,'syncsub'),drops:word(i,'mixunderruns'),ticks:word(i,'seqticks'),pad:v(i,'lastpad')}))));};
 const key={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function press(i,k){const mask=1<<key[k];core._link_key(i,key[k],1);until(()=>v(i,'lastpad')&mask,180);core._link_key(i,key[k],0);until(()=>!(v(i,'lastpad')&mask),180);run(4);}
 function choose(i,page){core._link_key(i,7,1);until(()=>v(i,'navopen'),180);for(let n=0;n<40&&v(i,'navchoice')!==page;n++)press(i,'down');assert.equal(v(i,'navchoice'),page);core._link_key(i,7,0);until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);

 choose(1,27);press(1,'right');press(1,'down');press(1,'right');
 assert.equal(v(1,'syncmode'),1);assert(v(1,'syncslave'));
 choose(0,27);press(0,'down');press(0,'right');
 const begin=core._link_trace_count();press(0,'a');run(240);
 assert(v(0,'seqplaying')&&v(1,'seqplaying'));
 assert(!v(0,'link_peer_capable'),'Legacy peer accidentally negotiated metadata');
 for(let n=begin;n<core._link_trace_count();n++){const b=core._link_trace_value(n);assert(!(b>=0xC0&&b<0xF0),'Encoded optional bits sent to legacy peer');}
 press(0,'a');run(60);assert(!v(0,'seqplaying')&&!v(1,'seqplaying'));
 // Reverse compatibility: the reference ROM now owns the clock.
 press(0,'right');assert(v(0,'syncslave'));
 press(1,'right');assert(!v(1,'syncslave'));press(1,'a');run(240);
 assert(v(0,'seqplaying')&&v(1,'seqplaying'));
 assert(v(0,'syncslave'));assert.equal(v(0,'linkstate'),0);
 press(1,'a');run(60);assert(!v(0,'seqplaying')&&!v(1,'seqplaying'));
 console.log('PASS pinned-main legacy master/slave compatibility; no metadata encoding without capability');
})().catch(e=>{console.error(e);process.exitCode=1;});

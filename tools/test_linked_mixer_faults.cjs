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
 function choose(i,page){core._link_key(i,7,1);until(()=>v(i,'navopen'),180);for(let n=0;n<40&&v(i,'navchoice')!==page;n++)press(i,'down');assert.equal(v(i,'navchoice'),page);core._link_key(i,7,0);until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);

 const state=(i,a)=>core._link_state_read(i,a);
 const mirror=(n)=>state(0,S['_linkmirror']+n);
 choose(0,27);press(0,'down');press(0,'right');
 assert(!v(0,'syncslave')&&v(1,'syncslave'));
 choose(0,18);press(0,'left');press(0,'a');
 assert.equal(v(0,'mixer_device'),1);
 until(()=>v(0,'linkstate')===2&&v(1,'linkstate')===2,600);
 until(()=>mirror(150)===255,1800);
 const baselineDrops=[word(0,'mixunderruns'),word(1,'mixunderruns')];
 press(0,'down');assert.equal(state(0,S['_mx']+4),2);
 press(0,'a');
 const tx=S['_linktx'];
 until(()=>state(0,tx+2)===5&&v(0,'linktxread')<v(0,'linktxsize')-1,180);
 const count=v(0,'linktxsize'),original=Array.from({length:count},(_,j)=>state(0,tx+j));
 // Corrupt the pending producer frame, never the hardware or receive queue.
 core._link_state_write(0,tx+count-1,original[count-1]^1);
 run(180);assert.equal(v(1,'seqmuted')&1,0,'Bad CRC changed the slave');
 until(()=>v(1,'seqmuted')&1,1800);until(()=>mirror(142)&1,600);
 run(60);const generation=word(1,'pattern_generation');
 until(()=>v(0,'linktxread')===v(0,'linktxsize'),180);
 for(let j=0;j<count;j++)core._link_state_write(0,tx+j,original[j]);
 put(0,'linktxread',0);put(0,'linktxsize',count);run(180);
 assert.equal(word(1,'pattern_generation'),generation,'Duplicate request replayed an edit');
 assert.equal(v(1,'seqmuted')&1,1);
 until(()=>v(0,'linktxread')===v(0,'linktxsize'),180);
 const malformed=[0xF3,127,1,2,3,4];for(let j=0;j<malformed.length;j++)core._link_state_write(0,tx+j,malformed[j]);
 put(0,'linktxread',0);put(0,'linktxsize',malformed.length);run(60);
 press(0,'a');until(()=>!(v(1,'seqmuted')&1),1800);until(()=>!(mirror(142)&1),600);
 assert.equal(core._link_wire_aborts(),0);
 assert(!v(0,'overflow')&&!v(1,'overflow'));
 assert.deepEqual([word(0,'mixunderruns'),word(1,'mixunderruns')],baselineDrops);
 console.log('PASS real-cable CRC rejection/retry, duplicate suppression and malformed-frame recovery');
})().catch(e=>{console.error(e);process.exitCode=1;});

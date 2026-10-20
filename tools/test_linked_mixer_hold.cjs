/* Real SameBoy cable: no writes to SB, SC, IF or the ROM's receive queue. */
const fs=require('fs'),assert=require('assert');
(async()=>{
 const core=await require('../build/sync_link_core.cjs')();
 const arg=process.argv.indexOf('--rom'),romPath=arg<0?'build/GAYBOY.gb':process.argv[arg+1];
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return [a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);core._link_init(ptr,rom.length);core._free(ptr);
 core._link_watch_rx(S['_rx']);
 let frames=0;const run=n=>{for(let j=0;j<n;j++){core._link_run(1);frames++;if(frames>500)assert([0,1].every(i=>core._link_min_sp(i)>=0xDE00),'Stack at frame '+frames+' '+JSON.stringify([0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_state_read(i,0xff90),sp:core._link_min_sp(i).toString(16)}))));}};
 const v=(i,n)=>core._link_read(i,S['_'+n]);
 const word=(i,n)=>v(i,n)|(core._link_read(i,S['_'+n]+1)<<8);
 const put=(i,n,x)=>core._link_write(i,S['_'+n],x);
 const until=(fn,max=3000)=>{for(let n=0;n<max;n++){if(fn())return n;run(1);}throw Error('Timed out at frame '+frames+' '+JSON.stringify([0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_read(i,0xff90),servicing:v(i,'seqservicing'),armed:v(i,'syncarmed'),sub:v(i,'syncsub'),drops:word(i,'mixunderruns'),ticks:word(i,'seqticks'),pad:v(i,'lastpad')}))));};
 const key={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function press(i,k){const mask=1<<key[k];core._link_key(i,key[k],1);until(()=>v(i,'lastpad')&mask,180);core._link_key(i,key[k],0);until(()=>!(v(i,'lastpad')&mask),180);run(4);}
 function choose(i,page){press(i,'start');until(()=>v(i,'navopen'),180);const category=[19,20,24,25].includes(page)?4:page===0?3:0;for(let n=0;n<5&&v(i,'navcategory')!==category;n++)press(i,'right');for(let n=0;n<40&&v(i,'navchoice')!==page;n++)press(i,'down');assert.equal(v(i,'navchoice'),page);press(i,'a');until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);


 const m=(i,n)=>core._link_state_read(i,S['_mx']+n);
 const setm=(i,n,x)=>core._link_state_write(i,S['_mx']+n,x);

 for(const side of [0,1]){for(const name of ['seqbpm','seqglobalbpm']){put(side,name,300&255);core._link_write(side,S['_'+name]+1,300>>8);}}
 choose(0,18);put(0,'mixer_device',0);setm(0,4,30);press(0,'a');
 until(()=>v(0,'seqplaying')&&v(1,'seqplaying')&&v(0,'linkstate')===2&&v(1,'linkstate')===2,2400);
 choose(1,18);put(1,'mixer_device',0);
 core._link_watch_both_launch(1);
 const events=()=>Array.from({length:core._link_event_count()},(_,n)=>{const d=new DataView(core.HEAPU8.buffer,core._link_events()+n*28,28);return {cycle:d.getUint32(0,true),side:d.getUint32(4,true),tag:d.getUint32(8,true),grid:d.getUint32(12,true)};});
 const beforeDrops=[word(0,'mixunderruns'),word(1,'mixunderruns')],results=[];
 for(const path of ['local','slave','linked','pair']){
  console.log('testing',path,'frame',frames);
  const operator=path==='slave'?1:0,receiver=path==='linked'||path==='slave'?1:0;
  put(0,'mixer_device',path==='linked'?1:0);put(0,'linkpair',path==='pair'?1:0);
  for(const side of [0,1])setm(side,3,1);
  setm(operator,4,30+m(receiver,1));
  run(30);core._link_watch_events(S['_mixer_boundary'],S['_seq_pattern_handoff'],S['_seqposition'],S['_seqticks'],S['_seqclock']);
  const launches=()=>events().filter(e=>e.side===receiver&&e.tag===0x301);
  core._link_key(operator,4,1);until(()=>launches().length>=5,3000);
  core._link_key(operator,4,0);until(()=>!(v(operator,'lastpad')&16),180);
  until(()=>m(0,2)===255&&m(1,2)===255&&!v(0,'link_pair_phase')&&!v(1,'link_pair_phase'),1800);
  run(path==='linked'?600:180);const count=launches().length;run(180);
  assert.equal(launches().length,count,'Release kept rearming '+path);
  const e=events(),launch=launches();
  assert(launch.every(x=>x.grid%2===0),'Held launch off quantize '+path);
  if(path==='local'||path==='slave'){
   const indices=launch.map(l=>e.filter(x=>x.side===receiver&&x.tag===0x300&&x.cycle<=l.cycle).length);
   assert(indices.slice(1).every((n,j)=>n-indices[j]===2),'Missed local hold interval '+path+' '+indices);
  }
  assert(!v(0,'overflow')&&!v(1,'overflow'),'Overflow during '+path);
  assert.equal(core._link_wire_aborts(),0,'Serial transfer restarted');
  results.push({path,launches:count});
 }
 assert.deepEqual([word(0,'mixunderruns'),word(1,'mixunderruns')],beforeDrops);
 console.log('PASS held local/slave/linked/paired pads, quantized boundaries, release and unchanged underruns',JSON.stringify(results));
})().catch(e=>{console.error(e);process.exitCode=1;});

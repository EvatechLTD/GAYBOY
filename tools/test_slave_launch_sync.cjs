/* Real SameBoy cable: no writes to SB, SC, IF or the ROM's receive queue. */
const fs=require('fs'),assert=require('assert');
(async()=>{
 const core=await require('../build/sync_link_core.cjs')();
 const arg=process.argv.indexOf('--rom'),romPath=arg<0?'build/GAYBOY.gb':process.argv[arg+1];
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return [a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);core._link_init(ptr,rom.length);core._free(ptr);
 core._link_watch_rx(S['_rx']);
 let frames=0,tempoJitter=false;const run=n=>{
  if(!tempoJitter){core._link_run(n);frames+=n;return;}
  for(let f=0;f<n;f++){core._link_run(1);frames++;if(frames%12===0){
   const estimate=bpm-(Math.floor(frames/12)%2?6:0);
   for(const name of ['seqbpm','seqglobalbpm']){core._link_state_write(1,S['_'+name],estimate&255);core._link_state_write(1,S['_'+name]+1,estimate>>8);}
   core._link_state_write(1,S['_seqcachedbpm'],0);core._link_state_write(1,S['_seqcachedbpm']+1,0);
  }}
 };
 const v=(i,n)=>core._link_state_read(i,S['_'+n]);
 const word=(i,n)=>v(i,n)|(core._link_state_read(i,S['_'+n]+1)<<8);
 const put=(i,n,x)=>core._link_state_write(i,S['_'+n],x);
 const until=(fn,max=3000)=>{for(let n=0;n<max;n++){if(fn())return n;run(1);}throw Error('Timed out at frame '+frames+' '+JSON.stringify([0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_state_read(i,0xff90),servicing:v(i,'seqservicing'),armed:v(i,'syncarmed'),sub:v(i,'syncsub'),drops:word(i,'mixunderruns'),ticks:word(i,'seqticks'),pad:v(i,'lastpad'),wave:v(i,'waveengine'),native:v(i,'seqnativepending'),slot:core._link_state_read(i,S['_mx']+1),pending:core._link_state_read(i,S['_mx']+2),quant:core._link_state_read(i,S['_mx']+3),rx:v(i,'wr')-v(i,'rd'),syncbusy:v(i,'syncbusy'),playing:v(i,'seqplaying'),phase:core._link_state_read(i,0xa600),lastpulse:core._link_state_read(i,0xffe8)|(core._link_state_read(i,0xffe9)<<8),time:word(i,'sys_time'),overflow:v(i,'overflow')}))));};
 const key={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function press(i,k){const mask=1<<key[k];core._link_key(i,key[k],1);until(()=>v(i,'lastpad')&mask,180);core._link_key(i,key[k],0);until(()=>!(v(i,'lastpad')&mask),180);run(4);}
 function choose(i,page){core._link_key(i,7,1);until(()=>v(i,'navopen'),180);for(let n=0;n<40&&v(i,'navchoice')!==page;n++)press(i,'down');assert.equal(v(i,'navchoice'),page);core._link_key(i,7,0);until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);
 const bpmArg=process.argv.indexOf('--bpm'),bpm=bpmArg<0?120:Number(process.argv[bpmArg+1]);
 const writeWord=(i,at,x)=>{core._link_state_write(i,at,x&255);core._link_state_write(i,at+1,x>>8);};
 writeWord(0,S['_seqbpm'],bpm);writeWord(0,S['_seqglobalbpm'],bpm);
 if(process.argv.includes('--stress')){
  const tracks=Array.from({length:7},()=>[]);
  for(let s=0;s<16;s++){tracks[0].push([s,61+s%4,100,1]);tracks[1].push([s,68+s%4,100,1]);if(s%4===0)for(const sample of [4,10])tracks[6].push([s,sample,127,4]);}
  for(const i of [0,1]){let offset=0;for(let c=0;c<7;c++){
   writeWord(i,S['_seqeventoffsets']+c*2,offset);writeWord(i,S['_seqeventcounts']+c*2,tracks[c].length);writeWord(i,S['_seqlength']+c*2,16);
   for(const e of tracks[c]){for(let j=0;j<4;j++)core._link_state_write(i,S['_seqevents_lo']+offset*4+j,e[j]);offset++;}
  }
  put(i,'seqeventcache',0);put(i,'seqcachedbpm',0);put(i,'pattern_dirty',1);writeWord(i,S['_pattern_generation'],word(i,'pattern_generation')+1);core._link_state_write(i,0xACCF,0x43);
  }
 }

 const modeArg=process.argv.indexOf('--mode'),mode=modeArg<0?1:Number(process.argv[modeArg+1]);
 const mx=S['_mx'];
 assert.equal(core._link_state_read(1,mx+3),4,'Fresh demo must default to 1/1');
 // Populate pad 1 on the slave through Save/Load UI, leaving pad 0 active.
 choose(1,20);core._link_state_write(1,mx+6,1);press(1,'b');run(40);
 choose(1,18);core._link_state_write(1,mx+4,31);press(1,'a');run(60);
 choose(1,19);core._link_state_write(1,mx+6,1);press(1,'a');run(60);
 core._link_state_write(1,mx+4,30);press(1,'a');run(60);
 for(const i of [0,1]){writeWord(i,S['_seqbpm'],bpm);writeWord(i,S['_seqglobalbpm'],bpm);choose(i,27);for(let n=1;n<mode;n++)press(i,'right');}
 core._link_state_write(1,mx+3,0); // Simulate a saved NOW preference.
 if(mode===1){press(1,'down');press(1,'right');press(1,'right');}
 else {press(0,'down');press(0,'right');press(1,'down');press(1,'right');press(1,'right');}
 assert.equal(core._link_state_read(1,mx+3),4,'Entering slave mode must enable quantization');press(0,'a');
 until(()=>v(1,'seqplaying'));run(90);assert.equal(v(1,'syncmode'),mode);
 choose(1,18);
 // Raw clock starts on its first byte, up to one pulse behind the sending
 // transport (two sixteenths for PO), plus a foreground service boundary.
 // Exact pulse/grid conservation is checked separately by the CPU test.
 // Fault injection changes BPM even with converted ticks in flight. Its
 // purpose is preparation progress; master phase comparisons use normal runs.
 tempoJitter=process.argv.includes('--tempo-jitter');
 const maxGridLag=mode===4?3:mode===1?1:2;
 const report={mode,bpm,stress:process.argv.includes('--stress'),tempoJitter,launches:[]};
 core._link_watch_events(S['_mixer_boundary'],S['_seq_pattern_handoff'],S['_seqposition'],S['_seqticks'],S['_seqclock']);
 function events(){const count=core._link_event_count(),at=core._link_events();let out=[];for(let n=0;n<count;n++){const a=at+n*28,d=new DataView(core.HEAPU8.buffer,a,28);out.push({cycle:d.getUint32(0,true),tag:d.getUint32(8,true),grid:d.getUint32(12,true),clock:d.getUint32(20,true),ticks:d.getUint32(24,true)});}return out;}
 function gridDelta(){const a=core._link_state_read(0,mx+10),b=core._link_state_read(1,mx+10);return (a-b+16)%16;}
 // All slave quantizations, switching and retriggering. A stale saved NOW is
 // promoted to bar quantization; smaller choices remain exactly as selected.
 for(const quant of [4,2,1,3,0,4,1,4]){
  // Bound the trace even when dense PCM emits thousands of APU writes.
  core._link_watch_events(S['_mixer_boundary'],S['_seq_pattern_handoff'],S['_seqposition'],S['_seqticks'],S['_seqclock']);
  const target=1-core._link_state_read(1,mx+1),before=core._link_event_count();
  core._link_state_write(1,mx+3,quant);core._link_state_write(1,mx+4,30+target);press(1,'a');
  until(()=>core._link_state_read(1,mx+1)===target&&core._link_state_read(1,mx+2)===255,1800);run(12);
  const launches=events().slice(before).filter(e=>e.tag===0x301),effective=quant||4;
  assert.equal(core._link_state_read(1,mx+3),effective,'Requested quantization changed');
  assert.equal(launches.length,1,'Expected one local handoff');
  assert.equal(launches[0].grid% (1<<effective),0,'Launch missed transport quantization grid');
  assert(v(1,'seqplaying'),'Slave stopped');
  const delta=gridDelta();assert((tempoJitter||delta<=maxGridLag||delta===15),'Slave bar grid drifted: '+JSON.stringify({quant,delta,launches}));
  report.launches.push({quant,effective,target,delta,launch:launches[0]});
  // Retrigger current pad on the same continuing transport grid.
  const retriggerStart=core._link_event_count();press(1,'a');
  until(()=>events().slice(retriggerStart).some(e=>e.tag===0x301),1800);run(8);
  const retrigger=events().slice(retriggerStart).filter(e=>e.tag===0x301);
  assert.equal(retrigger.length,1);assert.equal(retrigger[0].grid%(1<<effective),0);
  assert((tempoJitter||gridDelta()<=maxGridLag||gridDelta()===15),'Retrigger shifted slave grid '+JSON.stringify({mode,quant,delta:gridDelta()}));
 }
 // Quantization selector must still expose all four rhythmic choices.
 core._link_state_write(1,mx+4,1);const choices=[];for(let n=0;n<4;n++){press(1,'a');choices.push(core._link_state_read(1,mx+3));}
 assert.deepEqual(choices,[1,2,3,4]);report.choices=choices;
 assert(!v(0,'overflow')&&!v(1,'overflow'),'Serial queue overflow');
 assert.equal(core._link_wire_aborts(),0,'Serial transfer restarted');
 fs.writeFileSync(`build/slave-launch-mode${mode}-${bpm}${process.argv.includes('--stress')?'-stress':''}${tempoJitter?'-jitter':''}.json`,JSON.stringify(report,null,2));
 console.log('PASS slave launch grid '+JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1;});

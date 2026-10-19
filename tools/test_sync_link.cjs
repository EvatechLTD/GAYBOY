/* Real SameBoy cable: no writes to SB, SC, IF or the ROM's receive queue. */
const fs=require('fs'),assert=require('assert');
(async()=>{
 const core=await require('../build/sync_link_core.cjs')();
 const arg=process.argv.indexOf('--rom'),romPath=arg<0?'build/GAYBOY.gb':process.argv[arg+1];
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return [a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);core._link_init(ptr,rom.length);core._free(ptr);
 core._link_watch_rx(S['_rx']);
 let frames=0;const run=n=>{core._link_run(n);frames+=n;};
 const v=(i,n)=>core._link_state_read(i,S['_'+n]);
 const word=(i,n)=>v(i,n)|(core._link_state_read(i,S['_'+n]+1)<<8);
 const put=(i,n,x)=>core._link_state_write(i,S['_'+n],x);
 const until=(fn,max=3000)=>{for(let n=0;n<max;n++){if(fn())return n;run(1);}throw Error('Timed out at frame '+frames+' '+JSON.stringify([0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_state_read(i,0xff90),servicing:v(i,'seqservicing'),armed:v(i,'syncarmed'),sub:v(i,'syncsub'),drops:word(i,'mixunderruns'),ticks:word(i,'seqticks'),pad:v(i,'lastpad')}))));};
 const key={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function press(i,k){const mask=1<<key[k];core._link_key(i,key[k],1);until(()=>v(i,'lastpad')&mask,180);core._link_key(i,key[k],0);until(()=>!(v(i,'lastpad')&mask),180);run(4);}
 function choose(i,page){press(i,'start');until(()=>v(i,'navopen'),180);const category=[19,20,24,25].includes(page)?4:page===0?3:0;for(let n=0;n<5&&v(i,'navcategory')!==category;n++)press(i,'right');for(let n=0;n<40&&v(i,'navchoice')!==page;n++)press(i,'down');assert.equal(v(i,'navchoice'),page);press(i,'a');until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
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
 // Store an equivalent destination fixture through the real Save Pattern UI.
 // This keeps the launch comparison at the same musical/CPU load.
 choose(0,20);core._link_state_write(0,S['_mx']+6,0);press(0,'b');run(40);
 if(v(0,'sparse_enabled')===1){
  choose(0,18);core._link_state_write(0,S['_mx']+4,31);press(0,'a');run(60);
  choose(0,19);core._link_state_write(0,S['_mx']+6,0);press(0,'a');run(60);
  choose(0,18);
  core._link_state_write(0,S['_mx']+4,30);press(0,'a');run(60);
 }
 choose(0,27);press(0,'a');
 const offMenuFrames=[];
 core._link_key(0,7,1);until(()=>v(0,'navopen'));
 for(let n=0;n<8;n++){let before=frames;press(0,'down');offMenuFrames.push(frames-before);}
 core._link_key(0,7,0);until(()=>!v(0,'navopen'));run(40);
 choose(0,27);if(v(0,'seqplaying'))press(0,'a');
 choose(1,27);
 assert(v(0,'syncslave')&&v(1,'syncslave'),'Stopped native peers must both listen');
 press(0,'a');run(90);assert(v(1,'seqplaying'),'Cable did not start slave');assert.equal(word(1,'seqglobalbpm'),word(0,'seqglobalbpm'));
 const settle=()=>until(()=>[0,1].every(i=>!v(i,'seqservicing')&&!v(i,'syncbusy')&&v(i,'rd')===v(i,'wr')&&!v(i,'syncpending')&&word(i,'seqticks')<word(i,'seqdeadline')),180);
 const report={edges:core._link_edges(),offMenuFrames,steady:[],menuFrames:[],slaveMenuFrames:[],resync:[]};
 const traceStart=core._link_trace_count(),wireStart=core._link_wire_clocks();
 for(let n=0;n<4;n++){run(30);report.steady.push([v(0,'seqposition'),v(1,'seqposition')]);}
 core._link_key(0,7,1);until(()=>v(0,'navopen'));
 core._link_profile_start();
 for(let n=0;n<8;n++){let before=frames;press(0,'down');report.menuFrames.push(frames-before);}
 const profile=[];for(let n=0;n<65536;n++){const cycles=core._link_profile(n);if(cycles)profile.push({bank:n>>10,pc:((n&1023)<<4)+((n>>10)?0x4000:0),cycles});}fs.writeFileSync('build/sync-menu-profile.json',JSON.stringify(profile));
 core._link_key(0,7,0);until(()=>!v(0,'navopen'));run(40);
 core._link_key(1,7,1);until(()=>v(1,'navopen'));
 for(let n=0;n<3;n++){let before=frames;press(1,'down');report.slaveMenuFrames.push(frames-before);}
 core._link_key(1,7,0);until(()=>!v(1,'navopen'));run(40);
 choose(0,18);
 // Offset slave deliberately; a master pattern launch must restore beat one.
 for(let t=0;t<7;t++)core._link_state_write(1,S['_seqposition']+t,(core._link_state_read(1,S['_seqposition']+t)+4)%core._link_state_read(1,S['_seqlength']+2*t));
 const mx=S['_mx'];core._link_state_write(0,mx+3,0);core._link_state_write(0,mx+4,30);press(0,'a');run(30);
 settle();report.resync.push({master:v(0,'seqposition'),slave:v(1,'seqposition'),masterClock:word(0,'seqclock'),slaveClock:word(1,'seqclock')});
 // Also switch to another pattern using the normal mixer launch path.
 core._link_state_write(0,mx+3,2);core._link_state_write(0,mx+4,31);press(0,'a');until(()=>core._link_state_read(0,mx+1)===1,1200);run(30);
 settle();report.slot=core._link_state_read(0,mx+1);report.resync.push({master:v(0,'seqposition'),slave:v(1,'seqposition'),masterClock:word(0,'seqclock'),slaveClock:word(1,'seqclock')});
 report.state=[0,1].map(i=>({playing:v(i,'seqplaying'),slave:v(i,'syncslave'),linked:v(i,'linkstate'),collision:v(i,'linkcollision'),tick:core._link_state_read(i,0xFFC7),received:core._link_state_read(i,0xFFE1),marker:core._link_state_read(i,0xFFC5),parser:core._link_state_read(i,0xFFDF),pending:word(i,'seqticks'),overflow:v(i,'overflow'),length:word(i,'seqlength'),events:word(i,'seqeventcounts'),sparse:v(i,'sparse_enabled')}));
 const trace=[];for(let n=traceStart;n<core._link_trace_count();n++)trace.push({cycle:core._link_trace_cycle(n),value:core._link_trace_value(n)});
 const pulses=trace.filter(e=>(e.value>=0x80&&e.value<0xf0)||e.value===0xf8),period=8388608*60/(word(0,'seqglobalbpm')*24),intervals=pulses.slice(1).map((p,n)=>(p.cycle-pulses[n].cycle)/8388.608);
 const sorted=intervals.slice().sort((a,b)=>a-b);report.clock={count:pulses.length,idealMs:period/8388.608,meanMs:intervals.reduce((a,b)=>a+b,0)/intervals.length,minMs:sorted[0],medianMs:sorted[Math.floor(sorted.length/2)],maxMs:sorted.at(-1),peakErrorMs:Math.max(...intervals.map(x=>Math.abs(x-period/8388.608)))};
 report.wire={completedClocks:core._link_wire_clocks(),receivedClocks:Array.from({length:64},(_,n)=>core._link_rx_count(0x80+n)).reduce((a,b)=>a+b,core._link_rx_count(0xF8)),receivedMarkers:core._link_rx_count(0xF2),completedDuringTrace:core._link_wire_clocks()-wireStart,abortedTransfers:core._link_wire_aborts()};
 report.frames=frames;fs.writeFileSync('build/sync-link-results.json',JSON.stringify(report,null,2));fs.writeFileSync('build/sync-link-trace.json',JSON.stringify(trace));console.log(JSON.stringify(report));
 if(!process.argv.includes('--baseline')){
  assert(Math.max(...report.menuFrames)<=Math.max(24,Math.max(...offMenuFrames)+16),'Start menu navigation stalled');
  assert(Math.max(...report.slaveMenuFrames)<=Math.max(24,Math.max(...offMenuFrames)+16),'Slave Start menu navigation stalled');
  assert.equal(report.slot,1,'Second pattern did not launch');
  assert(report.clock.peakErrorMs<4,'Clock pulse spacing exceeded 4 ms error');
  assert(Math.abs(report.clock.meanMs-report.clock.idealMs)<0.015,'Master clock drifted under load');
  assert(Math.abs(report.wire.completedDuringTrace-report.clock.count)<=1,'Clock bytes started but did not complete');
  assert.equal(report.wire.abortedTransfers,0,'An active hardware serial transfer was restarted');
  assert(!v(0,'overflow')&&!v(1,'overflow'),'Serial queue overflow');
  const length=word(1,'seqlength');for(const r of report.resync){const d=(r.master-r.slave+length)%length;assert([0,1,length-1].includes(d),'Pattern launch did not resync '+JSON.stringify(r));}
  choose(0,27);press(0,'a');run(30);
  assert(!v(0,'seqplaying')&&!v(1,'seqplaying'),'Master stop did not stop both peers');
  assert(v(0,'syncslave')&&v(1,'syncslave'),'Stopped peers did not return to listening');
  choose(1,27);press(1,'a');run(90);
  assert(v(0,'seqplaying')&&v(1,'seqplaying'),'Reverse start did not start both peers');
  assert(v(0,'syncslave')&&!v(1,'syncslave'),'First local start did not become master');
  press(0,'a');run(20);
  assert(!v(0,'seqplaying')&&v(1,'seqplaying'),'Local slave stop changed master transport');
  press(0,'a');run(30);
  assert(v(0,'seqplaying')&&v(0,'syncslave')&&!v(1,'syncslave'),'Slave restart stole an active master role');
  assert.equal(core._link_wire_aborts(),0,'Slave stop/restart aborted an active transfer');
  press(1,'a');run(30);
  assert(!v(0,'seqplaying')&&!v(1,'seqplaying'),'Reverse master stop failed');
  assert(v(0,'syncslave')&&v(1,'syncslave'),'Reverse stop did not restore listening');
  choose(0,27);press(0,'down');press(0,'right');
  choose(1,27);press(1,'down');press(1,'right');press(1,'right');
  assert(!v(0,'syncslave')&&v(1,'syncslave'),'Forced roles were not selected');
  press(0,'a');run(90);
  assert(v(0,'seqplaying')&&v(1,'seqplaying'),'Forced roles did not start');
  press(0,'a');run(30);
  assert(!v(0,'seqplaying')&&!v(1,'seqplaying'),'Forced roles did not stop');
  assert(!v(0,'syncslave')&&v(1,'syncslave'),'Forced roles changed on stop');
 }
})().catch(e=>{console.error(e);process.exitCode=1;});

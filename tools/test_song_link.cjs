/* Real bit-level cable, actual APU writes; no serial/receive-queue injection. */
const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
 const option=(n,d)=>{const a=process.argv.indexOf(n);return a<0?d:process.argv[a+1];};
 const linked=process.argv.includes('--linked'),graphics=process.argv.includes('--graphics'),master=Number(option('--master','0')),romPath=option('--rom','build/GAYBOY.gb');
 const core=await require(path.resolve('build/sync_link_core.cjs'))();
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return[a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);core._link_init(ptr,rom.length);core._free(ptr);
 const save=fs.readFileSync(option('--save','assets/demo/KILLING.srm'));
 for(const side of [0,1]){const battery=side?fs.readFileSync(option('--slave-save',option('--save','assets/demo/KILLING.srm'))):save;const p=core._malloc(battery.length);core.HEAPU8.set(battery,p);core._link_battery_load(side,p,battery.length);core._free(p);}
 const v=(i,n,o=0)=>core._link_state_read(i,(S['_'+n]??0)+o),put=(i,n,x,o=0)=>core._link_state_write(i,S['_'+n]+o,x);
 const word=(i,n,o=0)=>v(i,n,o)|(v(i,n,o+1)<<8),ww=(i,n,x,o=0)=>{put(i,n,x&255,o);put(i,n,x>>8,o+1);};
 const status=()=>[0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_state_read(i,S['__current_bank']),page:v(i,'page'),playing:v(i,'song_playing'),native:v(i,'seqplaying'),active:v(i,'song_link_active'),wire:Array.from({length:29},(_,n)=>core._link_state_read(i,0xa3e2+n)),error:v(i,'song_view',15),hw:word(i,'song_hwclock'),q:[v(i,'song_qread'),v(i,'song_qwrite')],planner:{clock:word(i,'song_runtime'),wait:word(i,'song_runtime',2),position:word(i,'song_runtime',28),done:v(i,'song_runtime',156),error:v(i,'song_runtime',161)}}));
 let frames=0,lastDebug='';const run=n=>{core._link_run(n);frames+=n;},until=(f,n=3000)=>{for(let j=0;j<n;j++){if(f())return;run(1);if(process.argv.includes('--debug')){const snap=status(),stamp=snap.map(x=>x.active+':'+x.wire.slice(0,6)).join('|');if(stamp!==lastDebug){lastDebug=stamp;console.log(frames,JSON.stringify(snap));}}}const ntrace=core._link_trace_count();console.log('Last wire bytes',Array.from({length:Math.min(48,ntrace)},(_,j)=>core._link_trace_value(ntrace-Math.min(48,ntrace)+j)));throw Error('timeout '+JSON.stringify(status()));};
 const keys={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function key(i,k,down){core._link_key(i,keys[k],+down);until(()=>!!(v(i,'lastpad')&(1<<keys[k]))===down,1800);}
 function tap(i,k){key(i,k,true);key(i,k,false);run(4);}
 function choose(i,n){tap(i,'start');put(i,'navchoice',n);tap(i,'a');run(30);assert.equal(v(i,'page'),n===54?29:n);}
 function chord(i,a,b){key(i,a,true);key(i,b,true);key(i,b,false);key(i,a,false);run(4);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 for(const i of [0,1])core._link_key(i,7,1);
 until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));
 for(const i of [0,1])core._link_key(i,7,0);run(60);
 for(const i of [0,1]){
  put(i,'sticky_start',1);
  if(linked){choose(i,27);key(i,'b',true);tap(i,'up');key(i,'b',false);assert.equal(v(i,'syncmode'),1);}
  choose(i,54);
  for(let n=0;n<4;n++)put(i,'song_view',0,n);put(i,'song_view',0,12);put(i,'dirty',1);run(20);
  const bpm=Number(option('--bpm','120'));ww(i,'seqbpm',bpm);ww(i,'seqglobalbpm',bpm);
 }
 core._link_watch_events(0,0,S['_song_actual_position'],S['_seqticks'],S['_song_hwclock']);
 core._link_watch_ui(S['_song_playing'],S['_page']);
 chord(master,'select',graphics?'a':'start');
 if(!linked)chord(1-master,'select',graphics?'a':'start');
 until(()=>v(0,'song_playing')&&v(1,'song_playing'),1800);
 assert(!linked||[0,1].every(i=>v(i,'song_link_active')));
 core._link_set_drift(Number(option('--drift','0')));
 if(process.argv.includes('--profile'))core._link_profile_start();
 run(Number(option('--frames','3600')));
 if(process.argv.includes('--profile')){const profile={};for(let index=0;index<65536;index++){const cycles=core._link_profile(index);if(!cycles)continue;const bank=index>>10,pc=((index&1023)<<4)+(bank?0x4000:0),near=Object.entries(S).filter(([n,v])=>n.startsWith('_')&&v>>16===bank&&(v&65535)<=pc).sort((a,b)=>b[1]-a[1])[0];const name=near?near[0]:'unknown';profile[name]=(profile[name]||0)+cycles;}console.log('PROFILE',JSON.stringify(Object.entries(profile).sort((a,b)=>b[1]-a[1]).slice(0,25)));}
 assert([0,1].every(i=>v(i,'song_playing')),'Premature stop '+JSON.stringify(status()));
 const lostTimerRequests=[0,0],groups=Array.from({length:2},()=>[[],[],[],[]]),eventPtr=core._link_events(),count=core._link_event_count();
 const words=new Uint32Array(core.HEAPU8.buffer,eventPtr,count*7);
 for(let i=0;i<count;i++){const at=i*7,tag=words[at+2];if(tag===0x780)lostTimerRequests[words[at+1]]++;if(tag>=0x740&&tag<=0x743)groups[words[at+1]][tag-0x740].push({ms:words[at]/8388.608,pos:words[at+4]&65535});}
 const report={linked,graphics,master,drift:Number(option('--drift','0')),frames,status:status(),channels:[],lostTimerRequests,minSP:[0,1].map(i=>core._link_min_sp(i)),graphicsWrites:[0,1].map(i=>core._link_ui_vram_writes(i)),underruns:[0,1].map(i=>word(i,'song_underruns')),aborts:core._link_wire_aborts(),unarmed:core._link_unarmed_edges()};
 for(let c=0;c<4;c++){
  const a=groups[master][c],b=groups[1-master][c],grid=7500/Number(option('--bpm','120'))/(master?1+Number(option('--drift','0'))/1e6:1);
  const errors=a.slice(1).map((h,i)=>{const d=h.ms-a[i].ms;return Math.abs(d-Math.round(d/grid)*grid);});
  const slaveErrors=b.slice(1).map((h,i)=>{const d=h.ms-b[i].ms;return Math.abs(d-Math.round(d/grid)*grid);});
  const skew=a.slice(0,Math.min(a.length,b.length)).map((h,i)=>b[i].ms-h.ms);
  report.channels.push({channel:c,hits:[a.length,b.length],masterMaxGridMs:Math.max(0,...errors),slaveMaxGridMs:Math.max(0,...slaveErrors),skewMinMs:Math.min(...skew),skewMaxMs:Math.max(...skew),firstSkewMs:skew[0],lastSkewMs:skew.at(-1)});
 }
 fs.writeFileSync(option('--report','build/song-link-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 assert(report.underruns.every(n=>!n),'Register queue underrun');assert.equal(report.aborts,0,'Active serial transfer aborted');assert.equal(report.unarmed,0,'Unarmed cable edge');
 assert(report.minSP.every(n=>n>=0xde00),'Stack reserve exceeded');if(!graphics)assert(report.graphicsWrites.every(n=>!n),'Smooth wrote graphics during audio');
 assert(lostTimerRequests.every(n=>!n),'ROM cleared a pending sound timer request');
 assert(report.channels[3].hits.every(n=>n>100),'Not enough drum attacks');
 if(linked){for(const c of report.channels.filter(c=>c.hits[0]>3)){if(!process.argv.includes('--slave-save')||c.channel===3)assert(Math.abs(c.skewMinMs)<1.5&&Math.abs(c.skewMaxMs)<1.5,'Inter-device onset skew');assert(c.masterMaxGridMs<1.3,'Master timing regression');assert(c.slaveMaxGridMs<1.3,'Slave timing regression');}}
 chord(master,'select',graphics?'a':'start');until(()=>!v(master,'song_playing'));
 if(linked)until(()=>!v(1-master,'song_playing'));else chord(1-master,'select',graphics?'a':'start');
 if(linked)assert(!v(0,'song_link_active')&&!v(1,'song_link_active'),'Link ownership stuck after stop');
 console.log('PASS prepared real-cable song start, actual attacks, queues, bounded skew and shared stop');
})().catch(e=>{console.error(e);process.exitCode=1;});

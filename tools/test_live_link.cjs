/* Real bit-level cable, actual APU writes; no serial/receive-queue injection. */
const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
 const option=(n,d)=>{const a=process.argv.indexOf(n);return a<0?d:process.argv[a+1];};
 const linked=process.argv.includes('--linked'),graphics=true,master=Number(option('--master','0')),romPath=option('--rom','build/reference/GAYBOY.gb');
 const core=await require(path.resolve('build/sync_link_core.cjs'))();
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return[a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);core._link_init(ptr,rom.length);core._free(ptr);
 const save=fs.readFileSync(option('--save','assets/demo/KILLING.srm'));
 for(const side of [0,1]){const battery=Buffer.from(side?fs.readFileSync(option('--slave-save',option('--save','assets/demo/KILLING.srm'))):save);battery[32647]=Number(option('--pad','5'))-1;const p=core._malloc(battery.length);core.HEAPU8.set(battery,p);core._link_battery_load(side,p,battery.length);core._free(p);}
 const v=(i,n,o=0)=>core._link_state_read(i,(S['_'+n]??0)+o),put=(i,n,x,o=0)=>core._link_state_write(i,S['_'+n]+o,x);
 const word=(i,n,o=0)=>v(i,n,o)|(v(i,n,o+1)<<8),ww=(i,n,x,o=0)=>{put(i,n,x&255,o);put(i,n,x>>8,o+1);};
 const status=()=>[0,1].map(i=>({pc:core._link_pc(i).toString(16),page:v(i,'page'),playing:v(i,'seqplaying'),slave:v(i,'syncslave'),link:v(i,'linkstate'),pending:v(i,'syncpending'),ticks:word(i,'seqticks'),position:Array.from({length:7},(_,j)=>v(i,'seqposition',j)),drums:v(i,'drum_irq_active'),notes:v(i,'editirq_running'),arp:v(i,'arpirq_enabled'),lfo:v(i,'lfo_irq_mask'),overflow:v(i,'overflow'),raw:S._sync_raw_ready?v(i,'sync_raw_ready'):0,pulsequot:core._link_state_read(i,0xffec)|(core._link_state_read(i,0xffed)<<8),divider:v(i,'syncdivider'),counter:v(i,'synctick'),expected:word(i,'syncincrement'),local:word(i,'synclimit'),debt:v(i,'syncdue'),TMA:core._link_read(i,0xff06),TAC:core._link_read(i,0xff07),SC:core._link_read(i,0xff02),SB:core._link_read(i,0xff01)}));
 let frames=0,lastDebug='';const firstOverflow=[false,false];const run=n=>{for(let j=0;j<n;j++){core._link_run(1);frames++;if(process.argv.includes('--clock-debug')&&frames%60===0&&[0,1].every(i=>v(i,'seqplaying')))console.log('CLOCK',frames,JSON.stringify(status().map(x=>({playing:x.playing,slave:x.slave,fine:x.fine,fraction:x.fraction,anchor:x.anchor,expected:x.expected,local:x.local,debt:x.debt,pulsequot:x.pulsequot}))));if(process.argv.includes('--overflow-debug'))for(let i=0;i<2;i++)if(frames>100&&v(i,'overflow')===1&&!firstOverflow[i]){firstOverflow[i]=true;console.log('FIRST OVERFLOW',frames,i,JSON.stringify({state:status()[i],prepare:v(i,'native_prepare'),busy:v(i,'syncbusy'),servicing:v(i,'seqservicing'),rd:v(i,'rd'),wr:v(i,'wr'),head:Array.from({length:8},(_,j)=>v(i,'rx',(v(i,'rd')+j)&255))}));}}},until=(f,n=3000)=>{for(let j=0;j<n;j++){if(f())return;run(1);if(process.argv.includes('--debug')){const snap=status(),stamp=JSON.stringify(snap);if(stamp!==lastDebug){lastDebug=stamp;console.log(frames,JSON.stringify(snap));}}}const ntrace=core._link_trace_count();console.log('Last wire bytes',Array.from({length:Math.min(48,ntrace)},(_,j)=>core._link_trace_value(ntrace-Math.min(48,ntrace)+j)));throw Error('timeout '+JSON.stringify(status()));};
 const inputAcks=[[],[]];
 const keys={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function key(i,k,down){const began=frames,eventBegan=core._link_event_count(),stallPC={};if(process.argv.includes('--key-profile'))core._link_profile_start();core._link_key(i,keys[k],+down);until(()=>{if(process.argv.includes('--stall-pc')){const pc=core._link_pc(i),bank=pc<0x4000?0:core._link_read(i,0xff90),address=(bank<<16)|(pc&0xfff0);stallPC[address]=(stallPC[address]||0)+1;}return !!(v(i,'lastpad')&(1<<keys[k]))===down;},1800);if(process.argv.includes('--stall-pc')&&frames-began>30){const entries=Object.entries(stallPC).sort((a,b)=>b[1]-a[1]).slice(0,12).map(([a,n])=>{const address=Number(a),near=Object.entries(S).filter(([name,x])=>name.startsWith('_')&&x>>16===address>>16&&x<=address).sort((a,b)=>b[1]-a[1])[0];return[address.toString(16),n,near?.[0]];});console.log('STALLPC',i,k,down,frames-began,JSON.stringify(entries));}inputAcks[i].push(frames-began);if(process.argv.includes('--key-profile')&&frames-began>60){const sums={};for(let q=0;q<65536;q++){const cycles=core._link_profile(q);if(!cycles)continue;const bank=q>>10,pc=((q&1023)<<4)+(bank?0x4000:0),near=Object.entries(S).filter(([n,x])=>n.startsWith('_')&&x>>16===bank&&(x&65535)<=pc).sort((a,b)=>b[1]-a[1])[0],name=near?.[0]??'unknown';sums[name]=(sums[name]||0)+cycles;}console.log('KEYPROFILE',i,k,down,frames-began,JSON.stringify(Object.entries(sums).sort((a,b)=>b[1]-a[1]).slice(0,50)));}if(process.argv.includes('--trace-ui')&&frames-began>6){const count=core._link_event_count(),raw=new Uint32Array(core.HEAPU8.buffer,core._link_events(),count*7),tags={};for(let n=eventBegan;n<count;n++){const a=n*7,tag=raw[a+2];if(raw[a+1]!==i||tag<0x310||tag>0x316&&tag!==0x720)continue;const id=tag.toString(16);if(!tags[id])tags[id]={n:0,first:raw[a]/8388.608,last:0};tags[id].n++;tags[id].last=raw[a]/8388.608;}console.log('SLOWKEY',i,k,down,frames-began,JSON.stringify(tags));}}
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
  choose(i,8);
  if(process.argv.includes('--fixture')){
   const arp=process.argv.includes('--arp');
   const tracks=[[],arp?[[0,61,127,16],[0,65,127,16],[0,68,127,16]]:[0,4,8,12].map((s,j)=>[s,[61,65,68,65][j],127,4]),[[0,37,127,16]],[],[],[],[...Array.from({length:16},(_,s)=>[s,11,127,1]),...[0,4,8,12].map(s=>[s,13,127,1])]];
   let offset=0;const slot=v(i,'mx',1),bank=1+(slot>>2),base=0xa000+(slot&3)*2048+768;
   for(let c=0;c<7;c++){ww(i,'seqeventoffsets',offset,c*2);ww(i,'seqeventcounts',tracks[c].length,c*2);ww(i,'seqlength',16,c*2);for(const e of tracks[c]){core._link_write(i,0x4000,bank);e.forEach((x,j)=>core._link_write(i,base+offset*4+j,x));offset++;}}core._link_write(i,0x4000,0);
   for(let j=0;j<48;j++)put(i,'evalpatch',0,j);for(let j=0;j<9;j++)put(i,'coarsepitch',0,j);for(let j=0;j<6;j++)put(i,'finepitch',0,j);
   if(arp)for(const [j,x] of [[0,1],[2,4],[4,1],[13,1]])put(i,'evalpatch',x,16+j);
   put(i,'seqmuted',0);put(i,'seqsolo',0);ww(i,'drummutemask',0);ww(i,'drumsolomask',0);put(i,'seqeventcache',0);put(i,'pattern_dirty',1);put(i,'seqirqdirty',1);put(i,'eval_moddirty',1);ww(i,'pattern_generation',word(i,'pattern_generation')+1);put(i,'seqtrack',arp?1:6);put(i,'seqcursor',0,arp?1:6);put(i,'seqhead',0);put(i,'seqfocus',0);
  }
  const bpm=Number(option('--bpm','120'));ww(i,'seqbpm',bpm);ww(i,'seqglobalbpm',bpm);
  if(process.argv.includes('--settle-fixture')&&process.argv.includes('--fixture')){put(i,'dirty',1);put(i,'seqdrawvalid',0);until(()=>v(i,'seqdrawvalid')===1&&v(i,'seqviewtrack')===v(i,'seqtrack')&&!core._link_state_read(i,S._rollbuilding),600);run(4);}
 }
 if(linked&&process.argv.includes('--arm-slave')){
  const i=1-master;choose(i,27);tap(i,'down');key(i,'b',true);tap(i,'up');tap(i,'up');key(i,'b',false);
  assert.equal(v(i,'syncrole'),2,'Forced slave role not selected');choose(i,8);
  chord(i,'select','a');run(90);assert(!v(i,'seqplaying')&&v(i,'native_prepare')===2,'Slave must prepare and wait without free-running');
  chord(i,'select','a');run(30);assert(!v(i,'seqplaying')&&!v(i,'native_prepare'),'Second Play must cancel prepared wait');
  console.log('PASS forced slave prepares silently, waits for master and cancels');
 }
 core._link_watch_events(0,0,S['_seqposition'],S['_seqticks'],S['_seqclock']);
 core._link_watch_ui(S['_seqplaying'],S['_page']);
 if(process.argv.includes('--trace-ui')){core._link_watch_both_launch(1);core._link_watch_launch_detail(S._ui_input,S._seq_frame,S._ui_render,S._ui_action);core._link_watch_launch_transport(S._mixfill,S._service,S._roll_commit);core._link_watch_servicing(S._seqservicing);}
 chord(master,'select','a');
 if(!linked)chord(1-master,'select','a');
 until(()=>v(0,'seqplaying')&&v(1,'seqplaying'),1800);
 run(240); // Exclude startup from steady-state attack timing; startup needs its own readiness test.
 assert(!linked||v(master,'syncslave')===0&&v(1-master,'syncslave')===1);
 core._link_set_drift(Number(option('--drift','0')));
 const measurementStart=core._link_event_count();
 if(process.argv.includes('--profile'))core._link_profile_start();
 inputAcks.forEach(a=>a.length=0);
 if(process.argv.includes('--ui-test'))for(let j=0;j<24;j++){tap(0,j%12<6?'right':'left');tap(1,j%12<6?'right':'left');if(!j)for(const i of [0,1])assert.equal(v(i,'seqcursor',v(i,'seqtrack')),1,'Grid navigation must apply, not merely acknowledge input');}

 run(Number(option('--frames','3600')));
 if(process.argv.includes('--profile')){const profile={};for(let index=0;index<65536;index++){const cycles=core._link_profile(index);if(!cycles)continue;const bank=index>>10,pc=((index&1023)<<4)+(bank?0x4000:0),near=Object.entries(S).filter(([n,v])=>n.startsWith('_')&&v>>16===bank&&(v&65535)<=pc).sort((a,b)=>b[1]-a[1])[0];const name=near?near[0]:'unknown';profile[name]=(profile[name]||0)+cycles;}console.log('PROFILE',JSON.stringify(Object.entries(profile).sort((a,b)=>b[1]-a[1]).slice(0,25)));}
 assert([0,1].every(i=>v(i,'seqplaying')),'Premature stop '+JSON.stringify(status()));
 const lostTimerRequests=[0,0],groups=Array.from({length:2},()=>[[],[],[],[]]),eventPtr=core._link_events(),count=core._link_event_count();
 const words=new Uint32Array(core.HEAPU8.buffer,eventPtr,count*7);
 for(let i=measurementStart;i<count;i++){const at=i*7,tag=words[at+2];if(tag===0x780)lostTimerRequests[words[at+1]]++;if(tag>=0x740&&tag<=0x743)groups[words[at+1]][tag-0x740].push({ms:words[at]/8388.608,pos:words[at+4]&65535});}
 const report={measurementOnly:process.argv.includes('--measure-only'),startupExcluded:true,fixture:process.argv.includes('--fixture'),arp:process.argv.includes('--arp'),indexSkewRequiresMatchingAttackSequence:true,linked,graphics,master,drift:Number(option('--drift','0')),frames,status:status(),channels:[],lostTimerRequests,minSP:[0,1].map(i=>core._link_min_sp(i)),graphicsWrites:[0,1].map(i=>core._link_ui_vram_writes(i)),inputFrames:inputAcks.map(a=>({count:a.length,max:Math.max(0,...a),median:[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)]})),underruns:[0,1].map(i=>word(i,'editirq_underruns')),aborts:core._link_wire_aborts(),unarmed:core._link_unarmed_edges()};
 for(let c=0;c<4;c++){
  const a=groups[master][c],b=groups[1-master][c],grid=7500/Number(option('--bpm','120'))/(master?1+Number(option('--drift','0'))/1e6:1);
  const errors=a.slice(1).map((h,i)=>{const d=h.ms-a[i].ms;return Math.abs(d-Math.round(d/grid)*grid);});
  const slaveErrors=b.slice(1).map((h,i)=>{const d=h.ms-b[i].ms;return Math.abs(d-Math.round(d/grid)*grid);});
  const skew=a.slice(0,Math.min(a.length,b.length)).map((h,i)=>b[i].ms-h.ms);
  report.channels.push({channel:c,hits:[a.length,b.length],masterMaxGridMs:Math.max(0,...errors),slaveMaxGridMs:Math.max(0,...slaveErrors),skewMinMs:Math.min(...skew),skewMaxMs:Math.max(...skew),firstSkewMs:skew[0],lastSkewMs:skew.at(-1)});
 }
 if(process.argv.includes('--onsets'))report.onsets=groups;
 fs.writeFileSync(option('--report','build/song-link-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 assert(report.underruns.every(n=>!n),'Register queue underrun');
 assert(report.minSP.every(n=>n>=0xde00),'Stack reserve exceeded');
 assert(report.lostTimerRequests.every(n=>!n),'Discarded timer request');
 assert(report.aborts===0&&report.unarmed===0,'Unsafe cable transfer/rearm');
 assert(report.status.every(s=>!s.overflow),'Receive or clock overflow');

 assert(report.channels[3].hits.every(n=>n>100),'Not enough drum attacks');
 if(linked&&!process.argv.includes('--measure-only')){for(const c of report.channels.filter(c=>c.hits[0]>3)){if(!process.argv.includes('--slave-save')||c.channel===3)assert(Math.abs(c.skewMinMs)<1.5&&Math.abs(c.skewMaxMs)<1.5,'Inter-device onset skew');assert(c.masterMaxGridMs<1.3,'Master timing regression');assert(c.slaveMaxGridMs<1.3,'Slave timing regression');}}
 chord(master,'select',process.argv.includes('--panic-stop')?'start':'a');until(()=>!v(master,'seqplaying'));
 if(linked)until(()=>!v(1-master,'seqplaying'));else chord(1-master,'select','a');
 if(process.argv.includes('--panic-stop')){
  run(120);assert([0,1].every(i=>!v(i,'seqplaying')&&!v(i,'syncarmed')),'Panic must stop and disarm both peers');
  assert([0,1].every(i=>!v(i,'drum_irq_active')&&!v(i,'arpirq_enabled')),'Panic must retire both audio schedulers');
  console.log('PASS master Start+Select panic stops and disarms slave');
 }

 console.log('PASS real-cable live-pattern start, actual attack measurement and shared stop');
})().catch(e=>{console.error(e);process.exitCode=1;});

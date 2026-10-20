/* Diagnostic launch-path comparison. Fixture state uses direct writes;
   launches use button input and the real cable, never injected serial bytes.
   This reports timing distributions without declaring timing parity. */
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
 const until=(fn,max=3000)=>{for(let n=0;n<max;n++){if(fn())return n;run(1);}throw Error('Timed out at frame '+frames+' '+JSON.stringify([0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_read(i,0xff90),servicing:v(i,'seqservicing'),armed:v(i,'syncarmed'),sub:v(i,'syncsub'),drops:word(i,'mixunderruns'),ticks:word(i,'seqticks'),pad:v(i,'lastpad'),slot:core._link_state_read(i,S['_mx']+1),pending:core._link_state_read(i,S['_mx']+2),error:core._link_state_read(i,S['_mx']+52),pair:v(i,'link_pair_phase'),hold:v(i,'link_pair_hold'),linked:v(i,'linkstate'),txread:v(i,'linktxread'),txsize:v(i,'linktxsize'),txtype:core._link_state_read(i,S['_linktx']+2),names:core._link_state_read(i,S['_linkmirror']+150),rxready:v(i,'link_rx_ready'),namesDirty:v(i,'link_names_dirty')}))));};
 const key={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function press(i,k,limit=180){const mask=1<<key[k];core._link_key(i,key[k],1);until(()=>v(i,'lastpad')&mask,limit);core._link_key(i,key[k],0);until(()=>!(v(i,'lastpad')&mask),limit);run(4);}
 function choose(i,page){press(i,'start');until(()=>v(i,'navopen'),180);const target=page===1?11:page===28?45:page;const category=[19,20,24,25].includes(page)?4:page===1?3:0;for(let n=0;n<5&&v(i,'navcategory')!==category;n++)press(i,'right');for(let n=0;n<40&&v(i,'navchoice')!==target;n++)press(i,'down');assert.equal(v(i,'navchoice'),target);press(i,'a',1800);until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);

 const st=(i,a)=>core._link_state_read(i,a),sw=(i,a,x)=>core._link_state_write(i,a,x);
 const mx=S['_mx'];const m=(i,n)=>st(i,mx+n);const setm=(i,n,x)=>sw(i,mx+n,x);
 const bpmArg=process.argv.indexOf('--bpm'),bpm=bpmArg<0?300:Number(process.argv[bpmArg+1]);
 const writeWord=(i,a,x)=>{sw(i,a,x&255);sw(i,a+1,x>>8);};

 const wave=process.argv.includes('--wave'),long=process.argv.includes('--long');
 for(const i of [0,1]){
  const tracks=Array.from({length:7},()=>[]);
  for(let step=0;step<16;step++){
   if(wave&&i===1){if(step%4===0)tracks[2].push([step,49+(step%8),110,3]);}
   else {tracks[0].push([step,61+step%4,100,1]);tracks[1].push([step,68+step%4,100,1]);if(step%4===0)for(const sample of [4,10])tracks[6].push([step,sample,127,4]);}
  }
  let offset=0;for(let c=0;c<7;c++){writeWord(i,S['_seqeventoffsets']+c*2,offset);writeWord(i,S['_seqeventcounts']+c*2,tracks[c].length);writeWord(i,S['_seqlength']+c*2,long?(c===1?24:c===0?7:c===2?256:16):16);for(const e of tracks[c]){for(let j=0;j<4;j++)sw(i,S['_seqevents_lo']+offset*4+j,e[j]);offset++;}}
  if(wave&&i===1)sw(i,S['_param']+2*26+15,1);
  sw(i,S['_seqeventcache'],0);sw(i,S['_pattern_dirty'],1);writeWord(i,S['_seqbpm'],bpm);writeWord(i,S['_seqglobalbpm'],bpm);writeWord(i,S['_seqcachedbpm'],0);
  const library=v(i,'sparse_patterns');choose(i,20);setm(i,6,library);press(i,'b',1800);
  for(let slot=1;slot<3;slot++){choose(i,18);setm(i,4,30+slot);press(i,'b');run(80);choose(i,19);setm(i,6,library);press(i,'a');if(v(i,'page')===26){press(i,'up');press(i,'a',1800);}}
  choose(i,18);setm(i,3,4);
 }
 if(process.argv.includes('--forced')){choose(0,27);press(0,'down');press(0,'right');choose(1,27);press(1,'down');press(1,'right');press(1,'right');assert.equal(v(0,'syncrole'),1);assert.equal(v(1,'syncrole'),2);}
 choose(0,27);press(0,'a');until(()=>v(0,'linkstate')===2&&v(1,'linkstate')===2,1800);
 choose(0,18);put(0,'mixer_device',1);

 core._link_watch_both_launch(1);core._link_watch_event_cache(S['_seqeventcache']);if(process.argv.includes('--cpu'))core._link_watch_servicing(S['_seqservicing']);core._link_watch_launch_transport(S['_sync_transport'],S['_link_begin'],S['_link_reset']);core._link_watch_launch_detail(S['_seq_native_launch'],S['_sync_pattern'],S['_seq_native_fire'],S['_seq_pattern_start']);
 const results=[],round=x=>Math.round(x*1000)/1000;
 const readEvents=()=>Array.from({length:core._link_event_count()},(_,n)=>{const d=new DataView(core.HEAPU8.buffer,core._link_events()+n*28,28);return {cycle:d.getUint32(0,true),side:d.getUint32(4,true),tag:d.getUint32(8,true),value:d.getUint32(12,true),positions:d.getUint32(16,true)};});
 const gaps=(events,side,tag)=>{const a=events.filter(e=>e.side===side&&e.tag===tag);const d=a.slice(1).map((e,n)=>((e.cycle-a[n].cycle)>>>0)/8388.608);return {count:a.length,min:round(Math.min(...d)),max:round(Math.max(...d)),mean:round(d.reduce((a,b)=>a+b,0)/d.length)};};
 choose(1,18);put(0,'linkpair',0);put(1,'linkpair',0);setm(0,3,long?5:4);setm(1,3,long?5:4);
 for(let trial=0;trial<(process.argv.includes('--quick')?1:4);trial++)for(const path of (process.argv.includes('--slave-only')?['slave-local']:['host-local','host-remote','slave-local'])){
  const side=path==='host-local'?0:1,target=(m(side,1)+1)%3,operator=path==='slave-local'?1:0;
  put(0,'mixer_device',path==='host-remote'?1:0);setm(operator,4,30+target);run(30+trial*3);
  core._link_watch_events(S['_mixer_boundary'],S['_seq_pattern_handoff'],S['_seqposition'],S['_seqticks'],S['_seqclock']);
  const before=[word(0,'mixunderruns'),word(1,'mixunderruns')];run(55);
  if(process.argv.includes('--cpu'))core._link_profile_launch_window(side,0,Math.round(150*8388.608));
  press(operator,'a');until(()=>m(side,1)===target&&m(side,2)===255,2400);run(55);
  const e=readEvents(),markers=e.filter(e=>e.tag===0xff01&&e.value===0xf2).length;
  const clocks=e.filter(e=>e.side===0&&e.tag===0xff01&&e.value>=0x80&&e.value<0xf0);
  const clockGaps=clocks.slice(1).map((v,n)=>((v.cycle-clocks[n].cycle)>>>0)/8388.608);
  const result={path,trial,target,markers,stagedInstallSides:e.filter(e=>e.tag===0x721&&e.value===3).map(e=>e.side),transportCalls:e.filter(e=>e.tag===0x314).map(e=>e.side),linkBegins:e.filter(e=>e.tag===0x315).map(e=>e.side),linkResets:e.filter(e=>e.tag===0x316).map(e=>e.side),slaveRestarts:e.filter(e=>e.side===1&&e.tag===0x313).length,hostPulse:gaps(e,0,0xff14),slavePulse:gaps(e,1,0xff14),hostP2:gaps(e,0,0xff19),slaveP2:gaps(e,1,0xff19),maxClockGapMs:round(Math.max(...clockGaps)),extraUnderruns:[word(0,'mixunderruns')-before[0],word(1,'mixunderruns')-before[1]],handoffs:e.filter(e=>e.tag===0x301).map(h=>{const onset=e.find(e=>e.side===h.side&&e.tag===0xff14&&e.cycle>h.cycle);return {side:h.side,cycle:h.cycle,firstPulseMs:onset?round((onset.cycle-h.cycle)/8388.608):null,phases:e.filter(e=>e.side===h.side&&e.cycle>=h.cycle&&onset&&e.cycle<onset.cycle&&e.tag>=0x310&&e.tag<=0x313).map(e=>({tag:e.tag,ms:round((e.cycle-h.cycle)/8388.608)}))};})};
  const handoff=e.find(e=>e.tag===0x301&&e.side===side);result.largestGaps=[0,1].map(i=>{const a=e.filter(e=>e.tag===0xff14&&e.side===i);return a.slice(1).map((x,n)=>({gap:round((x.cycle-a[n].cycle)/8388.608),from:handoff?round((a[n].cycle-handoff.cycle)/8388.608):null,to:handoff?round((x.cycle-handoff.cycle)/8388.608):null})).sort((a,b)=>b.gap-a.gap).slice(0,3);});
  if(long)for(const h of e.filter(e=>e.tag===0x301)){const b=e.filter(e=>e.side===h.side&&e.tag===0x300&&e.cycle<=h.cycle).at(-1);assert(b,'Missing LONG boundary trace');assert.equal((b.positions>>8)&255,23,'LONG launched before the longest populated sequence completed');}
  if(process.argv.includes('--cpu')){let entered=null;result.longServicing=[];for(const x of e.filter(x=>x.side===side&&x.tag===0x720)){if(x.value&0x80000000)entered=x;else if(entered){const ms=(x.cycle-entered.cycle)/8388.608;if(ms>20)result.longServicing.push({ms:round(ms),entry:(entered.value&0x7fffffff).toString(16),exit:x.value.toString(16),relative:handoff?round((entered.cycle-handoff.cycle)/8388.608):null});entered=null;}}result.cpu=[];for(let n=0;n<65536;n++){const cycles=core._link_profile(n);if(cycles)result.cpu.push({address:((n>>10)<<16)|((n&1023)<<4)|((n>>10)?0x4000:0),cycles});}result.cpu.sort((a,b)=>b.cycles-a.cycles);result.cpu=result.cpu.slice(0,20).map(p=>{const sym=Object.entries(S).filter(([n,a])=>n.startsWith('_')&&(a>>16)===(p.address>>16)&&a<=p.address).sort((a,b)=>b[1]-a[1])[0];return {...p,symbol:sym?.[0],offset:p.address-(sym?.[1]||0)};});}
  results.push(result);console.log(JSON.stringify(result));
  assert.equal(markers,process.argv.includes('--baseline-markers')&&path==='host-local'?1:0,'Independent quantized launch emitted a transport restart marker');
  assert.equal(result.slaveRestarts,process.argv.includes('--baseline-markers')&&path==='host-local'?1:0,'Independent launch restarted the slave');
  assert(!result.stagedInstallSides.includes(1),'Slave launch entered the host staging path');
  assert(v(0,'seqplaying')&&v(1,'seqplaying'));assert(!v(0,'overflow')&&!v(1,'overflow'));
 }
 const report={bpm,rom_sha256:require('crypto').createHash('sha256').update(rom).digest('hex'),results};fs.writeFileSync('build/launch-path-profile'+(long?'-long':'')+(process.argv.includes('--forced')?'-forced':'')+(process.argv.includes('--baseline-markers')?'-baseline':'')+(process.argv.includes('--slave-only')?'-slave-only':'')+'.json',JSON.stringify(report,null,2));console.log('Launch path profile saved; measurements are diagnostic, not a hardware timing guarantee');
})().catch(e=>{console.error(e);process.exitCode=1;});

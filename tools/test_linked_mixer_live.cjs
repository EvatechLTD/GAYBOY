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
 const until=(fn,max=3000)=>{for(let n=0;n<max;n++){if(fn())return n;run(1);}throw Error('Timed out at frame '+frames+' '+JSON.stringify([0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_read(i,0xff90),servicing:v(i,'seqservicing'),armed:v(i,'syncarmed'),sub:v(i,'syncsub'),drops:word(i,'mixunderruns'),ticks:word(i,'seqticks'),pad:v(i,'lastpad'),slot:core._link_state_read(i,S['_mx']+1),pending:core._link_state_read(i,S['_mx']+2),error:core._link_state_read(i,S['_mx']+52),pair:v(i,'link_pair_phase'),hold:v(i,'link_pair_hold'),linked:v(i,'linkstate'),txread:v(i,'linktxread'),txsize:v(i,'linktxsize'),txtype:core._link_state_read(i,S['_linktx']+2),names:core._link_state_read(i,S['_linkmirror']+150),rxready:v(i,'link_rx_ready'),namesDirty:v(i,'link_names_dirty')}))));};
 const key={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function press(i,k,limit=180){const mask=1<<key[k];core._link_key(i,key[k],1);until(()=>v(i,'lastpad')&mask,limit);core._link_key(i,key[k],0);until(()=>!(v(i,'lastpad')&mask),limit);run(4);}
 function choose(i,page){press(i,'start');until(()=>v(i,'navopen'),180);const category=[19,20,24,25].includes(page)?4:page===0?3:0;for(let n=0;n<5&&v(i,'navcategory')!==category;n++)press(i,'right');for(let n=0;n<40&&v(i,'navchoice')!==page;n++)press(i,'down');assert.equal(v(i,'navchoice'),page);press(i,'a');until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);

 const st=(i,a)=>core._link_state_read(i,a),sw=(i,a,x)=>core._link_state_write(i,a,x);
 const mx=S['_mx'];const m=(i,n)=>st(i,mx+n);const setm=(i,n,x)=>sw(i,mx+n,x);
 const bpmArg=process.argv.indexOf('--bpm'),bpm=bpmArg<0?300:Number(process.argv[bpmArg+1]);
 const writeWord=(i,a,x)=>{sw(i,a,x&255);sw(i,a+1,x>>8);};
 for(const i of [0,1]){
  const tracks=Array.from({length:7},()=>[]);for(let s=0;s<16;s++){tracks[0].push([s,61+s%4,100,1]);tracks[1].push([s,68+s%4,100,1]);if(s%4===0)for(const sample of [4,10])tracks[6].push([s,sample,127,4]);}
  let offset=0;for(let c=0;c<7;c++){writeWord(i,S['_seqeventoffsets']+c*2,offset);writeWord(i,S['_seqeventcounts']+c*2,tracks[c].length);writeWord(i,S['_seqlength']+c*2,16);for(const e of tracks[c]){for(let j=0;j<4;j++)sw(i,S['_seqevents_lo']+offset*4+j,e[j]);offset++;}}
  sw(i,S['_seqeventcache'],0);sw(i,S['_pattern_dirty'],1);writeWord(i,S['_seqbpm'],bpm);writeWord(i,S['_seqglobalbpm'],bpm);writeWord(i,S['_seqcachedbpm'],0);sw(i,0xACCF,0x43);
  const name=Buffer.from('PAIRED LIVE TEST\0');for(let j=0;j<17;j++)setm(i,26+j,name[j]||0);
  choose(i,20);setm(i,6,0);press(i,'b');if(v(i,'page')===26){press(i,'up');press(i,'a');}
  for(let slot=1;slot<8;slot++){choose(i,18);setm(i,4,30+slot);press(i,'b');run(80);choose(i,19);setm(i,6,0);press(i,'a');if(v(i,'page')===26){press(i,'up');press(i,'a');}}
  choose(i,18);assert.equal(m(i,1),7);
 }
 if(process.argv.includes('--storage')){choose(1,25);setm(1,6,0);press(1,'b',1800);choose(1,18);}
 choose(0,27);press(0,'a');until(()=>v(1,'seqplaying'),600);
 until(()=>v(0,'linkstate')===2&&v(1,'linkstate')===2,1800);
 until(()=>st(0,S['_linkmirror']+150)===255,Math.max(1800,Math.ceil(240000/bpm)));
 choose(0,18);put(0,'linkpair',!v(0,'linkpair'));assert(v(0,'linkpair'));
 const beforeDrops=[word(0,'mixunderruns'),word(1,'mixunderruns')],report={bpm,rom_sha256:require('crypto').createHash('sha256').update(rom).digest('hex'),pairs:[],admission:{}};
 core._link_watch_events(S['_mixer_boundary'],S['_seq_pattern_handoff'],S['_seqposition'],S['_seqticks'],S['_seqclock']);
 for(let slot=0;slot<8;slot++){
  choose(0,18);setm(0,4,30+slot);press(0,'a');
  until(()=>m(0,1)===slot&&m(1,1)===slot&&m(0,2)===255&&m(1,2)===255&&!v(0,'link_pair_phase')&&!v(1,'link_pair_phase')&&!v(0,'seqservicing')&&!v(1,'seqservicing'),2400);
  run(8);assert(v(0,'seqplaying')&&v(1,'seqplaying'));
  // Slot publication happens inside the handoff. Sample complete scheduler
  // states, rather than one CPU halfway through its elapsed-time catch-up.
  const settling=until(()=>[0,1].every(i=>!v(i,'seqservicing')&&!v(i,'syncbusy')&&v(i,'rd')===v(i,'wr')&&!v(i,'syncpending')&&word(i,'seqticks')<word(i,'seqdeadline')),180);
  const a=st(0,S['_seqposition']),b=st(1,S['_seqposition']),delta=(a-b+16)%16;if(![0,1,15].includes(delta)){const before=[0,1].map(i=>({position:st(i,S['_seqposition']),ticks:word(i,'seqticks'),clock:word(i,'seqclock'),deadline:word(i,'seqdeadline'),phase:v(i,'link_pair_phase'),received:st(i,0xFFE1),marker:st(i,0xFFC5),BPM:word(i,'seqbpm')}));run(120);console.log('DIVERGENCE',slot,before,[0,1].map(i=>({position:st(i,S['_seqposition']),ticks:word(i,'seqticks'),clock:word(i,'seqclock')})));const history=[];for(let n=0;n<core._link_event_count();n++){const d=new DataView(core.HEAPU8.buffer,core._link_events()+n*28,28);history.push(Array.from({length:7},(_,j)=>d.getUint32(j*4,true)));}fs.writeFileSync('build/pair-divergence.json',JSON.stringify(history));}assert([0,1,15].includes(delta),'Paired grids diverged '+JSON.stringify({slot,a,b,delta}));const tracks=[0,1,6].map(track=>{const a=st(0,S['_seqposition']+track),b=st(1,S['_seqposition']+track);return{track,a,b,delta:(a-b+16)%16};});assert(tracks.every(t=>[0,1,15].includes(t.delta)),'Individual instrument grids diverged '+JSON.stringify(tracks));report.pairs.push({slot,delta,tracks,settlingFrames:settling,overflow:[v(0,'overflow'),v(1,'overflow')]});
 }
 choose(0,18);put(0,'linkpair',!v(0,'linkpair'));assert(!v(0,'linkpair'));
 // PAIR off must retain independent pad selection.
 setm(0,4,30);press(0,'a');until(()=>m(0,1)===0&&m(0,2)===255,1200);run(20);assert.equal(m(1,1),7);
 // Live linked controls and independent remote pad selection use the same wire.
 put(0,'mixer_device',!v(0,'mixer_device'));assert.equal(v(0,'mixer_device'),1);
 setm(0,4,2);press(0,'a');until(()=>v(1,'seqmuted')&1,2400);
 until(()=>st(0,S['_linkmirror']+142)&1,1200);
 setm(0,4,3);press(0,'a');until(()=>v(1,'seqsolo')&1,2400);
 setm(0,4,4);core._link_key(0,4,1);until(()=>v(0,'lastpad')&16);press(0,'down');core._link_key(0,4,0);until(()=>!(v(0,'lastpad')&16));
 until(()=>m(1,12)===126,2400);
 setm(0,4,5);core._link_key(0,4,1);until(()=>v(0,'lastpad')&16);press(0,'down');core._link_key(0,4,0);until(()=>!(v(0,'lastpad')&16));
 until(()=>m(1,19)===2,2400);
 // Restore audible fixture before checking save/underrun behavior.
 setm(0,4,2);press(0,'a');until(()=>!(v(1,'seqmuted')&1),2400);
 setm(0,4,3);press(0,'a');until(()=>!(v(1,'seqsolo')&1),2400);until(()=>!(st(0,S['_linkmirror']+143)&1),1200);run(10);
 setm(0,4,31);press(0,'a');until(()=>m(1,1)===1&&m(1,2)===255,2400);until(()=>st(0,S['_linkmirror']+148)===m(1,1),1200);run(10);assert.equal(m(0,1),0);
 setm(0,4,37);press(0,'a');until(()=>m(1,1)===7&&m(1,2)===255,2400);until(()=>st(0,S['_linkmirror']+148)===m(1,1),1200);run(10);assert.equal(m(0,1),0);
 report.liveRemoteControls=true;report.independentRemoteLaunch=true;
 // A real slave save publishes the renamed current pad without a name request.
 choose(1,20);const renamed=Buffer.from('SLAVE NEW NAME\0');for(let j=0;j<17;j++)sw(1,0xae98+j,renamed[j]||0);setm(1,6,process.argv.includes('--storage')?1:0);const saveStarted=frames;press(1,'b',1800);if(v(1,'page')===26){press(1,'up');press(1,'a',1800);}report.liveSaveFrames=frames-saveStarted;
 const remoteName=slot=>Buffer.from(Array.from({length:16},(_,j)=>st(0,S['_linkmirror']+slot*16+j))).toString().split('\0')[0];
 until(()=>remoteName(7)==='SLAVE NEW NAME',1800);
 if(process.argv.includes('--storage')){
  choose(1,19);setm(1,6,0);press(1,'a',1800);if(v(1,'page')===26){press(1,'up');press(1,'a',1800);}until(()=>remoteName(7)==='PAIRED LIVE TEST',3600);
  choose(1,19);setm(1,6,1);press(1,'a',1800);if(v(1,'page')===26){press(1,'up');press(1,'a',1800);}until(()=>remoteName(7)==='SLAVE NEW NAME',1800);
  choose(1,24);setm(1,6,0);press(1,'a',1800);if(v(1,'page')===26){press(1,'up');press(1,'a',1800);}until(()=>remoteName(7)==='PAIRED LIVE TEST',3600);
  assert(v(0,'seqplaying')&&v(1,'seqplaying'));report.patternAndSongLoadNames=true;
 }

 assert([0,1].every(i=>core._link_min_sp(i)>=0xDE00),'Reserved stack exhausted');
 const faults=[];for(let n=0;n<core._link_event_count();n++){const d=new DataView(core.HEAPU8.buffer,core._link_events()+n*28,28);if(d.getUint32(8,true)===0x600)faults.push(Array.from({length:7},(_,j)=>d.getUint32(j*4,true)));}console.log('pairs',JSON.stringify(report.pairs));console.log('save',report.liveSaveFrames,'overflow',[v(0,'overflow'),v(1,'overflow')],'minSP',[0,1].map(i=>core._link_min_sp(i).toString(16)),faults.slice(0,5));
 assert(!v(0,'overflow')&&!v(1,'overflow'));assert.equal(core._link_wire_aborts(),0);
 assert.deepEqual([word(0,'mixunderruns'),word(1,'mixunderruns')],beforeDrops);
 assert(core._link_event_count()<262144,'Event trace filled; timing proof incomplete');
 const events=[];for(let n=0;n<core._link_event_count();n++){const d=new DataView(core.HEAPU8.buffer,core._link_events()+n*28,28);if(d.getUint32(4,true)===0)events.push({cycle:d.getUint32(0,true),tag:d.getUint32(8,true),value:d.getUint32(12,true)});}
 const starts=events.filter(e=>e.tag===0xff01);let payload=0,carriers=0,clocks=0;const extra=[];
 for(const e of starts){const b=e.value;if((b>=0x80&&b<0xF0)||b===0xF8){clocks++;if(b>=0xC0&&b<0xF0)carriers++;continue;}if(b===0xF1){payload=2;continue;}if(b===0xF2){payload=3;continue;}if([0xFA,0xFB,0xFC].includes(b)){payload=0;continue;}if(b<128&&payload){payload--;continue;}extra.push(e);}
 assert.equal(extra.length,0,'Metadata created an extra serial transfer '+JSON.stringify(extra.slice(0,5)));
 assert(carriers>0,'No negotiated clock-carried control bits were measured');
 let due=null;const launchDelays=[];for(const e of events){if(e.tag===0x500)due=e;if(e.tag===0xff01&&e.value>=0x80&&e.value<0xF0&&due&&(e.value&63)===due.value){launchDelays.push(((e.cycle-due.cycle)>>>0)/8388.608);due=null;}}
 const pulseCycles=starts.filter(e=>e.value>=0x80&&e.value<0xF0).map(e=>e.cycle),intervals=pulseCycles.slice(1).map((c,n)=>((c-pulseCycles[n])>>>0)/8388.608),ideal=60000/(bpm*24);
 report.clock={meanMs:intervals.reduce((a,b)=>a+b,0)/intervals.length,idealMs:ideal,peakSpacingErrorMs:Math.max(...intervals.map(x=>Math.abs(x-ideal))),maxDueToLaunchMs:Math.max(...launchDelays)};
 assert(Math.abs(report.clock.meanMs-ideal)<0.015,'Clock rate drifted');assert(report.clock.peakSpacingErrorMs<4,'Clock spacing regression');
 report.unarmedSerialEdges=core._link_unarmed_edges();assert.equal(report.unarmedSerialEdges,0,'Slave missed incoming wire edges before serial rearm');
 report.admission={clockTransfers:clocks,clockCarriers:carriers,extraMetadataTransfers:extra.length};
 require('fs').writeFileSync('build/linked-mixer-live-'+bpm+'.json',JSON.stringify(report,null,2));console.log('PASS paired pads, independent launch, automatic saved names and clock admission',JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1;});

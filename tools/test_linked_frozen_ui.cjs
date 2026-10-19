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
 function choose(i,page){press(i,'start');until(()=>v(i,'navopen'),180);const target=page===1?11:page===28?45:page;const category=[19,20,24,25].includes(page)?4:page===1?3:0;for(let n=0;n<5&&v(i,'navcategory')!==category;n++)press(i,'right');for(let n=0;n<40&&v(i,'navchoice')!==target;n++)press(i,'down');assert.equal(v(i,'navchoice'),target);press(i,'a',1800);until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);

 const st=(i,a)=>core._link_state_read(i,a),sw=(i,a,x)=>core._link_state_write(i,a,x);
 const mx=S['_mx'];const m=(i,n)=>st(i,mx+n);const setm=(i,n,x)=>sw(i,mx+n,x);
 const bpmArg=process.argv.indexOf('--bpm'),bpm=bpmArg<0?300:Number(process.argv[bpmArg+1]);
 const writeWord=(i,a,x)=>{sw(i,a,x&255);sw(i,a+1,x>>8);};

 const wave=process.argv.includes('--wave');
 for(const i of [0,1]){
  const tracks=Array.from({length:7},()=>[]);
  for(let step=0;step<16;step++){
   if(wave&&i===1){if(step%4===0)tracks[2].push([step,49+(step%8),110,3]);}
   else {tracks[0].push([step,61+step%4,100,1]);tracks[1].push([step,68+step%4,100,1]);if(step%4===0)for(const sample of [4,10])tracks[6].push([step,sample,127,4]);}
  }
  let offset=0;for(let c=0;c<7;c++){writeWord(i,S['_seqeventoffsets']+c*2,offset);writeWord(i,S['_seqeventcounts']+c*2,tracks[c].length);writeWord(i,S['_seqlength']+c*2,16);for(const e of tracks[c]){for(let j=0;j<4;j++)sw(i,S['_seqevents_lo']+offset*4+j,e[j]);offset++;}}
  if(wave&&i===1)sw(i,S['_param']+2*26+15,1);
  sw(i,S['_seqeventcache'],0);sw(i,S['_pattern_dirty'],1);writeWord(i,S['_seqbpm'],bpm);writeWord(i,S['_seqglobalbpm'],bpm);writeWord(i,S['_seqcachedbpm'],0);
  const library=v(i,'sparse_patterns');choose(i,20);setm(i,6,library);press(i,'b',1800);
  for(let slot=1;slot<3;slot++){choose(i,18);setm(i,4,30+slot);press(i,'b');run(80);choose(i,19);setm(i,6,library);press(i,'a');if(v(i,'page')===26){press(i,'up');press(i,'a',1800);}}
  choose(i,18);setm(i,3,4);
 }
 choose(0,27);press(0,'a');until(()=>v(0,'linkstate')===2&&v(1,'linkstate')===2,1800);
 choose(0,18);put(0,'mixer_device',1);
 const cases=[8,1,16,27,18,19,20,28,'menu'],results=[];
 core._link_watch_events(S['_mixer_boundary'],S['_seq_pattern_handoff'],S['_seqposition'],S['_seqticks'],S['_seqclock']);
 const drops=[word(0,'mixunderruns'),word(1,'mixunderruns')];
 for(let n=0;n<cases.length;n++){
  const expected=cases[n]==='menu'?8:cases[n];console.log('opening',expected,'case',n);choose(1,expected);
  if(cases[n]==='menu')press(1,'start');
  const nav=v(1,'navopen'),target=(n+1)%3;
  core._link_watch_ui(S['_link_ui_hold'],S['_page']);
  setm(0,4,30+target);press(0,'a');
  until(()=>core._link_ui_holds(1)>0,2400);
  until(()=>{assert.equal(v(1,'page'),expected,'Remote launch changed receiver page');assert.equal(v(1,'navopen'),nav,'Remote launch closed receiver menu');return !v(1,'link_ui_hold');},2400);
  assert.equal(m(1,1),target);assert.equal(v(1,'page'),expected);assert.equal(core._link_ui_vram_writes(1),0,'VRAM drawn before playback stabilized');assert.equal(core._link_ui_page_changes(1),0,'Page changed while held');
  run(20);assert(v(0,'seqplaying')&&v(1,'seqplaying'));assert.equal(v(1,'page'),expected);
  results.push({page:cases[n],slot:target,heldVramWrites:core._link_ui_vram_writes(1),heldPageChanges:core._link_ui_page_changes(1)});
  if(nav)press(1,'select',1800);
 }
 assert.deepEqual([word(0,'mixunderruns'),word(1,'mixunderruns')],drops);assert(!v(0,'overflow')&&!v(1,'overflow'));assert.equal(core._link_wire_aborts(),0);assert.equal(core._link_unarmed_edges(),0);
 if(process.argv.includes('--disconnect')){
  choose(1,8);const original=m(1,1),target=(original+1)%3;
  setm(0,4,30+target);press(0,'a');until(()=>v(1,'link_ui_hold'),2400);
  core._link_set_connected(0);run(240);
  assert.equal(v(1,'link_ui_hold'),0,'Cable pull left receiver UI frozen');
  assert.equal(v(1,'page'),8);assert.equal(m(1,2),255,'Disconnected launch remained pending');
  assert.equal(m(1,1),original,'Disconnected preparation committed without a clock');
  core._link_set_connected(1);until(()=>v(0,'linkstate')===2&&v(1,'linkstate')===2,2400);
  assert(v(0,'seqplaying')&&v(1,'seqplaying'));
  console.log('PASS cable pull during pending launch releases receiver UI and reconnects');
 }
 const report={bpm,wave,results,extraUnderruns:0,wireAborts:0,unarmedSerialEdges:0,rom_sha256:require('crypto').createHash('sha256').update(rom).digest('hex')};fs.writeFileSync('build/linked-frozen-ui-'+(wave?'wave':'pcm')+'.json',JSON.stringify(report,null,2));console.log('PASS: remote launches preserve receiver screen/menu and perform zero VRAM writes until stable',JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1;});

/* Whole-step APU timing with SameBoy's C write callbacks, real UI controls,
 * and isolated RAM. No Python opcode hooks or injected clock ticks. */
const fs=require('fs'),assert=require('assert'),crypto=require('crypto');
(async()=>{
 const option=(name,fallback)=>{const i=process.argv.indexOf(name);return i<0?fallback:process.argv[i+1];};
 const romPath=option('--rom','build/GAYBOY.gb'),fixture=option('--fixture','demo'),bpm=Number(option('--bpm','300')),output=option('--output','build/native-sameboy.json');
 assert(['demo','native-four','pcm'].includes(fixture));
 const c=await require('../build/sync_link_core.cjs')();
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return [a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),ptr=c._malloc(rom.length);c.HEAPU8.set(rom,ptr);c._link_init(ptr,rom.length);c._free(ptr);
 let frames=0,phase='boot',completed=false;const phases=[];
 const run=n=>{c._link_run(n);frames+=n;};
 const read=a=>c._link_read(1,a),write=(a,x)=>c._link_write(1,a,x&255);
 const v=(name,i=0)=>read(S['_'+name]+i),put=(name,x,i=0)=>write(S['_'+name]+i,x);
 const word=name=>v(name)|(v(name,1)<<8),wordAt=(a,x)=>{write(a,x);write(a+1,x>>8);};
 const state=()=>Object.fromEntries(['page','navopen','lastpad','padsampled','seqplaying','seqservicing','rollbuilding','rollcancelled','seqnativepending','pool_error'].filter(n=>S['_'+n]!==undefined).map(n=>[n,v(n)]));
 const until=(fn,max=180)=>{for(let n=0;n<max;n++){if(fn())return;run(1);}throw Error('Timeout '+phase+' '+JSON.stringify(state()));};
 const keys={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 const inputTimes=[];
 function press(key){const mask=1<<keys[key],at=frames;c._link_key(1,keys[key],1);until(()=>v('lastpad')&mask);c._link_key(1,keys[key],0);until(()=>!(v('lastpad')&mask));inputTimes.push({phase,key,frames:frames-at});run(4);}
 function choose(page){const at=frames;c._link_key(1,7,1);until(()=>v('navopen'));inputTimes.push({phase,key:'open-menu',frames:frames-at});for(let n=0;n<40&&v('navchoice')!==page;n++)press('down');assert.equal(v('navchoice'),page);c._link_key(1,7,0);until(()=>!v('navopen'));run(40);assert.equal(v('page'),page>=11&&page<=15?1:page);}
 function mark(name){phase=name;phases.push({phase,frame:frames,event:c._link_event_count()});}
 function writePattern(variant){let offset=0;
  for(let track=0;track<7;track++){
   const notes=track<4?Array.from({length:16},(_,step)=>[step,49+track*7+variant+step%3,100,1]):track===6&&fixture==='pcm'?Array.from({length:4},(_,i)=>[i*4,4,100,4]):[];
   wordAt(S['_seqeventoffsets']+track*2,offset);wordAt(S['_seqeventcounts']+track*2,notes.length);
   for(const event of notes){const at=offset<256?S['_seqevents_lo']+offset*4:0xa800+(offset-256)*4;event.forEach((x,i)=>write(at+i,x));offset++;}
   wordAt(S['_seqlength']+track*2,16);put('seqgate',100,track);
  }
  put('seqeventfull',0);put('pattern_dirty',1);wordAt(S['_pattern_generation'],(word('pattern_generation')+1)&65535);put('seqirqready',0);put('seqirqdirty',1);wordAt(S['_seqcachedbpm'],0);
  put('param',1,2*26+15);put('param',12,3*26+1);
 }
 let error;
 try{
  until(()=>v('introready'),3000);c._link_key(0,7,1);c._link_key(1,7,1);until(()=>!v('introactive')&&v('page')===8,3000);c._link_key(0,7,0);c._link_key(1,7,0);run(60);
  choose(18);
  if(fixture!=='demo'){
   for(let slot=0;slot<2;slot++){
    if(slot){put('mx',31,4);press('a');run(60);choose(18);}
    writePattern(slot);choose(20);put('mx',slot,6);press('b');choose(18);
   }
   put('mx',30,4);press('a');run(60);
  }
  for(const name of ['seqbpm','seqglobalbpm'])wordAt(S['_'+name],bpm);
  c._link_watch_events(S['_mixer_boundary'],S['_seq_pattern_start'],S['_seqposition'],S['_seqticks'],S['_seqclock']);
  c._link_watch_pcm(S['_drumon'],S['_mixread'],S['_mixwrite'],S['_drum_mix']);
  mark('start');put('mx',0,4);press('a');assert(v('seqplaying'));
  mark('idle');run(240);
  mark('navigate');for(const page of [11,12,13,15,8,10,17,18])choose(page);
  for(const quant of [4,2,1])for(const slot of fixture==='demo'?[1,2,3,0]:[1,0]){
   mark('launch-q'+quant+'-pad'+slot);put('mx',quant,3);put('mx',30+slot,4);press('a');run(240);assert.equal(v('mx',1),slot,'Requested pattern never launched');assert.equal(v('pool_error'),0);
  }
  mark('recovery');run(240);completed=true;
 }catch(e){error=String(e);}
 const count=c._link_event_count(),at=c._link_events(),raw=new Uint32Array(c.HEAPU8.buffer,at,count*7),events=[];
 for(let n=0;n<count;n++)events.push(Array.from(raw.slice(n*7,n*7+7)));
 const summaries=[];
 for(let n=0;n<phases.length;n++){
  const part=events.slice(phases[n].event,phases[n+1]?.event??count).filter(e=>e[1]===1),groups=new Map();let epoch=0;
  for(const event of part){if(event[2]===0x300||event[2]===0x301){epoch++;continue;}
   const channel=event[2]===0xff14?0:event[2]===0xff19?1:event[2]===0xff23?3:event[2]===(fixture==='pcm'?0x400:0xff1e)?2:-1;
   if(channel<0)continue;if(!groups.has(epoch))groups.set(epoch,[[],[],[],[]]);groups.get(epoch)[channel].push(event[0]);
  }
  const clean=[...groups.values()].filter(g=>g.every(a=>a.length===1)),spreads=clean.map(g=>(Math.max(...g.flat())-Math.min(...g.flat()))/8388.608).sort((a,b)=>a-b);
  summaries.push({phase:phases[n].phase,steps:epoch,unambiguousFourVoiceGroups:clean.length,medianSpreadMs:spreads[Math.floor(spreads.length/2)]??null,maxSpreadMs:spreads.at(-1)??null});
 }
 const result={rom:romPath,rom_sha256:crypto.createHash('sha256').update(rom).digest('hex'),fixture,bpm,completed,error,state:state(),pc:c._link_pc(1),frames,phases,inputTimes,summaries,events,limitations:'DMG emulation; actual trigger writes and the first uploaded block rendered after source assignment. Epoch groups with duplicate/missing channels are excluded, not silently counted as coherent.'};
 fs.writeFileSync(output,JSON.stringify(result));const pixels=c._link_pixels(1);fs.writeFileSync(output.replace(/\.json$/,'.rgba'),Buffer.from(c.HEAPU8.slice(pixels,pixels+160*144*4)));
 console.log(JSON.stringify({completed,error,state:result.state,summaries}));assert(completed,error);assert(count<65536,'Event buffer filled');
 if(fixture!=='demo'){
  assert(summaries.reduce((n,s)=>n+s.unambiguousFourVoiceGroups,0)>=100,'Too few complete groups measured');
  for(const s of summaries){assert(s.unambiguousFourVoiceGroups>0,'No complete group in '+s.phase);assert(s.maxSpreadMs<=(fixture==='pcm'?0.3:0.1),'Whole-step attack spread exceeded budget in '+s.phase);}
 }
})().catch(e=>{console.error(e);process.exitCode=1;});

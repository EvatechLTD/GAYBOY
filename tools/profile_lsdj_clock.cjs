/* Built-in demo against the supplied LSDj ROM over SameBoy's bit-level cable.
 * --slave selects LSDj clock; default retains internal clock. */
const fs=require('fs'),assert=require('assert'),crypto=require('crypto');
(async()=>{
 const c=await require('../build/sync_link_core.cjs')();
 const romPath='build/GAYBOY.gb',slave=process.argv.includes('--slave');
 const S=Object.fromEntries(fs.readFileSync('build/GAYBOY.noi','utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return [a[1],parseInt(a[2],16)];}));
 function load(file,side){const b=fs.readFileSync(file),p=c._malloc(b.length);c.HEAPU8.set(b,p);if(side===undefined)c._link_init(p,b.length);else c._link_load_rom(side,p,b.length);c._free(p);}
 load(romPath);load('reference/01_LSDJ.gb',0);
 let frames=0,phase='boot',phases=[];
 const run=n=>{c._link_run(n);frames+=n;};
 const v=(name,i=0)=>c._link_read(1,S['_'+name]+i);
 const put=(name,i,x)=>c._link_write(1,S['_'+name]+i,x);
 const word=name=>v(name)|(v(name,1)<<8);
 const until=(fn,max=1800)=>{for(let n=0;n<max;n++){if(fn())return;run(1);}throw Error('timeout '+phase);};
 const keys={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function tap(side,key){c._link_key(side,keys[key],1);run(5);c._link_key(side,keys[key],0);run(5);}
 function press(key){const mask=1<<keys[key];c._link_key(1,keys[key],1);until(()=>v('lastpad')&mask,180);c._link_key(1,keys[key],0);until(()=>!(v('lastpad')&mask),180);run(4);}
 function choose(page){c._link_key(1,7,1);until(()=>v('navopen'),180);for(let n=0;n<40&&v('navchoice')!==page;n++)press('down');assert.equal(v('navchoice'),page);c._link_key(1,7,0);until(()=>!v('navopen'),180);run(40);assert.equal(v('page'),page>=11&&page<=15?1:page);}
 function lsdjChord(key){c._link_key(0,6,1);run(5);tap(0,key);c._link_key(0,6,0);run(15);}
 function lsdjEdit(key){c._link_key(0,4,1);run(5);tap(0,key);c._link_key(0,4,0);run(5);}
 function mark(name){phase=name;phases.push({phase,frame:frames,event:c._link_event_count()});}
 run(1800);
 c._link_key(1,7,1);until(()=>!v('introactive')&&v('page')===8);c._link_key(1,7,0);run(60);
 // LSDj: SONG -> LIVE -> PROJECT. Set SYNC to LSDJ using actual buttons.
 lsdjChord('left');lsdjChord('up');tap(0,'down');tap(0,'down');lsdjEdit('right');
 // Return to SONG, create chain 00 / phrase 00 so transport keeps running.
 lsdjChord('down');lsdjChord('right');tap(0,'a');lsdjChord('right');tap(0,'a');
 const ptr=c._link_pixels(0);fs.writeFileSync('build/lsdj-fixture.rgba',Buffer.from(c.HEAPU8.slice(ptr,ptr+160*144*4)));
 choose(18);
 for(const name of ['seqbpm','seqglobalbpm']){put(name,0,128);put(name,1,0);}
 if(slave){choose(27);press('right');press('right');press('down');press('right');assert.equal(v('syncmode'),2);assert(v('syncslave'));choose(18);}
 c._link_watch_events(S['_mixer_boundary'],S['_seq_pattern_start'],S['_seqposition'],S['_seqticks'],S['_seqclock']);
 mark('start');
 if(slave)tap(0,'start');else{put('mx',4,0);press('a');}
 run(120);console.log('Started', {slave,playing:v('seqplaying'),bpm:word('seqbpm'),lsdjPC:c._link_pc(0).toString(16),sc:c._link_read(0,0xff02),sb:c._link_read(0,0xff01),edges:c._link_edges(),events:c._link_event_count(),pos:v('seqposition')});
 assert(v('seqplaying'),'LSDj clock did not start the sequencer');
 mark('idle');run(240);
 mark('navigate');for(const page of [11,12,13,15,8,10,17,18])choose(page);
 for(const q of [4,2,1])for(const slot of [1,2,3,0]){
  mark('launch-q'+q+'-pad'+slot);put('mx',3,q);put('mx',4,30+slot);press('a');run(240);
 }
 mark('recovery');run(240);
 const count=c._link_event_count(),at=c._link_events();
 const raw=new Uint32Array(c.HEAPU8.buffer,at,count*7),events=[];
 for(let n=0;n<count;n++)events.push(Array.from(raw.slice(n*7,n*7+7)));
 const result={rom_sha256:crypto.createHash('sha256').update(fs.readFileSync(romPath)).digest('hex'),reference_sha256:crypto.createHash('sha256').update(fs.readFileSync('reference/01_LSDJ.gb')).digest('hex'),slave,clock:slave?'Actual LSDj 9.4.0 ROM via virtual bit cable':'Internal clock',phases,events,
  limitations:'DMG emulation; NRx4 trigger writes include silence and PCM block uploads, not detected audible onsets.'};
 const out='build/lsdj-comparison-'+(slave?'slave':'internal')+'.json';fs.writeFileSync(out,JSON.stringify(result));
 for(let n=0;n<phases.length;n++){
  const a=phases[n].event,b=phases[n+1]?.event??count,es=events.slice(a,b).filter(e=>e[1]===1&&e[2]===0x300);
  const gaps=es.slice(1).map((e,i)=>(e[0]-es[i][0])/8388.608);
  console.log(phases[n].phase,{steps:es.length,min:Math.min(...gaps),max:Math.max(...gaps)});
 }
})().catch(e=>{console.error(e);process.exitCode=1;});

/* Built-in demo against the supplied LSDj ROM over SameBoy's bit-level cable.
 * --slave selects LSDj clock; default retains internal clock. */
const fs=require('fs'),assert=require('assert'),crypto=require('crypto');
(async()=>{
 const c=await require('../build/sync_link_core.cjs')();
 const opt=(n,d)=>process.argv.includes(n)?process.argv[process.argv.indexOf(n)+1]:d;const romPath=opt('--rom','build/GAYBOY-LINKED-SMOOTH-TEST.gb'),slave=true;
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return [a[1],parseInt(a[2],16)];}));
 function load(file,side){const b=fs.readFileSync(file),p=c._malloc(b.length);c.HEAPU8.set(b,p);if(side===undefined)c._link_init(p,b.length);else c._link_load_rom(side,p,b.length);c._free(p);}
 load(romPath);load('../../reference/01_LSDJ.gb',0);
 const battery=Buffer.from(fs.readFileSync('assets/demo/KILLING.srm'));battery[32647]=4;{const p=c._malloc(battery.length);c.HEAPU8.set(battery,p);c._link_battery_load(1,p,battery.length);c._free(p);}
 let frames=0,phase='boot',phases=[];
 const run=n=>{c._link_run(n);frames+=n;};
 const v=(name,i=0)=>c._link_state_read(1,S['_'+name]+i);
 const put=(name,i,x)=>c._link_state_write(1,S['_'+name]+i,x);
 const word=name=>v(name)|(v(name,1)<<8);
 const until=(fn,max=1800)=>{for(let n=0;n<max;n++){if(fn())return;run(1);}throw Error('timeout '+phase);};
 const keys={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function tap(side,key){c._link_key(side,keys[key],1);run(5);c._link_key(side,keys[key],0);run(5);}
 function press(key){const mask=1<<keys[key];c._link_key(1,keys[key],1);until(()=>v('lastpad')&mask,180);c._link_key(1,keys[key],0);until(()=>!(v('lastpad')&mask),180);run(4);}
 function choose(page){if(page===27){choose(16);press('down');press('down');press('a');run(30);assert.equal(v('page'),27);return;}press('start');for(let n=0;n<5&&v('navcategory')!==0;n++)press('right');for(let n=0;n<40&&v('navchoice')!==page;n++)press('down');assert.equal(v('navchoice'),page);press('a');run(30);assert.equal(v('page'),page);}
 function lsdjChord(key){c._link_key(0,6,1);run(5);tap(0,key);c._link_key(0,6,0);run(15);}
 function lsdjEdit(key){c._link_key(0,4,1);run(5);tap(0,key);c._link_key(0,4,0);run(5);}
 function mark(name){phase=name;phases.push({phase,frame:frames,event:c._link_event_count()});}
 run(1800);
 c._link_key(1,7,1);until(()=>!v('introactive')&&v('page')===8);c._link_key(1,7,0);run(60);put('sticky_start',0,1);
 // LSDj: SONG -> LIVE -> PROJECT. Set SYNC to LSDJ using actual buttons.
 lsdjChord('left');lsdjChord('up');tap(0,'down');tap(0,'down');lsdjEdit('right');
 // Return to SONG, create chain 00 / phrase 00 so transport keeps running.
 lsdjChord('down');lsdjChord('right');tap(0,'a');lsdjChord('right');tap(0,'a');
 const ptr=c._link_pixels(0);fs.writeFileSync('build/lsdj-fixture.rgba',Buffer.from(c.HEAPU8.slice(ptr,ptr+160*144*4)));
 choose(18);
 for(const name of ['seqbpm','seqglobalbpm']){put(name,0,128);put(name,1,0);}
 if(slave){choose(27);c._link_key(1,5,1);until(()=>v('lastpad')&32);for(let n=0;n<8&&v('syncmode')!==2;n++)press('up');c._link_key(1,5,0);until(()=>!(v('lastpad')&32));assert.equal(v('syncmode'),2);assert(v('syncslave'));choose(18);}
 c._link_watch_events(S['_mixer_boundary'],S['_seq_pattern_start'],S['_seqposition'],S['_seqticks'],S['_seqclock']);
 mark('start');
 if(slave)tap(0,'start');else{put('mx',4,0);press('a');}
 run(120);console.log('Started', {slave,playing:v('seqplaying'),bpm:word('seqbpm'),lsdjPC:c._link_pc(0).toString(16),sc:c._link_read(0,0xff02),sb:c._link_read(0,0xff01),edges:c._link_edges(),events:c._link_event_count(),pos:v('seqposition')});
 assert(v('seqplaying'),'LSDj clock did not start the sequencer');
 mark('idle');run(240);
 mark('steady');run(Number(opt('--frames','1800')));
 const count=c._link_event_count(),at=c._link_events();
 const raw=new Uint32Array(c.HEAPU8.buffer,at,count*7),events=[];
 for(let n=0;n<count;n++)events.push(Array.from(raw.slice(n*7,n*7+7)));
 const groups=[[],[],[],[]];for(const e of events)if(e[1]===1&&e[2]>=0x740&&e[2]<=0x743)groups[e[2]-0x740].push(e[0]/8388.608);console.log('Actual audible attacks',groups.map(g=>g.length));
 const result={bpm:word('seqbpm'),rawReady:S._sync_raw_ready?v('sync_raw_ready'):0,drumIRQ:v('drum_irq_active'),noteIRQ:v('editirq_enabled'),arpIRQ:v('arpirq_enabled'),lfoIRQ:v('lfo_irq_mask'),underruns:word('editirq_underruns'),overflow:v('overflow'),actualAttacks:groups,rom_sha256:crypto.createHash('sha256').update(fs.readFileSync(romPath)).digest('hex'),reference_sha256:crypto.createHash('sha256').update(fs.readFileSync('../../reference/01_LSDJ.gb')).digest('hex'),slave,clock:slave?'Actual LSDj 9.4.0 ROM via virtual bit cable':'Internal clock',phases,events,
  limitations:'DMG emulation. Positive routed APU attack markers measure register commits; hardware listening is still required.'};
 const steady=events.slice(phases.find(p=>p.phase==='steady').event).filter(e=>e[1]===1&&e[2]===0x743).map(e=>e[0]/8388.608);
 const gaps=steady.slice(1).map((t,i)=>t-steady[i]),grid=15000/128;
 result.steadyNoise={attacks:steady.length,minGapMs:Math.min(...gaps),maxGapMs:Math.max(...gaps),maxGridErrorMs:Math.max(0,...gaps.map(g=>Math.abs(g-Math.round(g/grid)*grid)))};
 console.log('Steady positive noise attacks',result.steadyNoise);
 const out=opt('--report','build/lsdj-current.json');fs.writeFileSync(out,JSON.stringify(result));
 if(process.argv.includes('--verify')){assert(result.rawReady&&result.drumIRQ,'Prepared external-clock path not active');assert(!result.overflow&&!result.underruns,'Clock overflow or audio underrun');assert(result.steadyNoise.attacks>100,'Insufficient audible drum attacks');assert(result.steadyNoise.maxGridErrorMs<1.3,'LSDj clock drum jitter');}
 for(let n=0;n<phases.length;n++){
  const a=phases[n].event,b=phases[n+1]?.event??count,es=events.slice(a,b).filter(e=>e[1]===1&&e[2]===0x300);
  const gaps=es.slice(1).map((e,i)=>(e[0]-es[i][0])/8388.608);
  console.log(phases[n].phase,{steps:es.length,min:Math.min(...gaps),max:Math.max(...gaps)});
 }
 if(process.argv.includes('--verify')){
  c._link_set_connected(0);run(150);assert(!v('seqplaying')&&!v('sync_raw_ready'),'External clock loss failed to stop');
  c._link_set_connected(1);until(()=>v('seqplaying'),300);run(120);assert(v('sync_raw_ready')&&!v('overflow'),'Clock reconnect failed');
  console.log('PASS LSDj audible drum timing, no underruns, clock-loss stop and reconnect');
 }
})().catch(e=>{console.error(e);process.exitCode=1;});

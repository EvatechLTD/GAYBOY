/* Two distinct DMG ROMs on the real emulated cable; no receive-ring injection. */
const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
 const core=await require(path.resolve(process.argv[2]||'build/sync_link_core.cjs'))();
 const companion=process.argv[3]||['../../../MONOSIMP/build/MONOSIMP.gb','../../MONOSIMP/build/MONOSIMP.gb'].map(p=>path.resolve(__dirname,p)).find(p=>fs.existsSync(p));
 assert(companion,'MONOSIMP companion ROM not found; pass its path as the second argument');
 const roms=[process.argv[4]||'build/GAYBOY.gb',companion];
 const symbols=roms.map(p=>Object.fromEntries(fs.readFileSync(p.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{let a=l.split(/\s+/);return[a[1],parseInt(a[2],16)];})));
 roms.forEach((p,i)=>{const rom=fs.readFileSync(p),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);if(!i)core._link_init(ptr,rom.length);else core._link_load_rom(i,ptr,rom.length);core._free(ptr);});
 const at=(i,n,o=0)=>symbols[i]['_'+n]+o;
 const v=(i,n,o=0)=>core._link_state_read(i,at(i,n,o));
 const put=(i,n,x,o=0)=>core._link_state_write(i,at(i,n,o),x);
 const word=(i,n,o=0)=>v(i,n,o)|(v(i,n,o+1)<<8);
 const writeword=(i,n,x,o=0)=>{put(i,n,x&255,o);put(i,n,x>>8,o+1);};
 const run=n=>core._link_run(n);
 function until(fn,max=2000){for(let n=0;n<max;n++){if(fn())return;run(1);}throw Error('timeout '+JSON.stringify({page:v(0,'page'),sync:v(0,'syncmode'),ready:v(0,'twink_ready'),remote:v(1,'twink_link'),input:v(1,'twink_input'),playing:v(0,'seqplaying'),armed:v(0,'syncarmed'),pc:[0,1].map(i=>core._link_pc(i).toString(16))}));}
 const keys={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function press(i,k){let bit=1<<keys[k];core._link_key(i,keys[k],1);until(()=>v(i,'lastpad')&bit,300);core._link_key(i,keys[k],0);until(()=>!(v(i,'lastpad')&bit),300);run(8);}
 function choose(n){core._link_key(0,7,1);until(()=>v(0,'navopen'));run(35);put(0,'navchoice',n);press(0,'a');core._link_key(0,7,0);until(()=>!(v(0,'lastpad')&128));run(35);assert.equal(v(0,'page'),n,'Finder opens requested page');}

 const receiverMenu=('_navigation_input' in symbols[1]);
 function chooseReceiver(item){
  core._link_key(1,7,1);until(()=>v(1,'navopen'),120);
  for(let n=0;n<13&&v(1,'navchoice')!==item;n++)press(1,'down');
  assert.equal(v(1,'navchoice'),item,'Receiver page menu reaches requested item');
  core._link_key(1,7,0);until(()=>!v(1,'navopen'),120);run(16);
 }

 until(()=>v(0,'introready'));core._link_key(0,7,1);until(()=>!v(0,'introactive')&&v(0,'page')===8);core._link_key(0,7,0);run(60);
 // Choose MONOSIMP's sixth page and use its real INPUT toggle.
 if(receiverMenu)chooseReceiver(12);else for(let n=0;n<5;n++)press(1,'select');
 assert.equal(v(1,'synthview'),5);press(1,'a');assert.equal(v(1,'twink_input'),1);
 // Select TWINK through GAYBOY's real sync settings.
 choose(27);core._link_key(0,5,1);until(()=>v(0,'lastpad')&32);for(let n=0;n<5;n++)press(0,'up');core._link_key(0,5,0);until(()=>!(v(0,'lastpad')&32));assert.equal(v(0,'syncmode'),6);assert.equal(v(0,'syncslave'),0);
 until(()=>v(0,'twink_ready')&&v(1,'twink_link'));assert.equal(word(1,'twink_bpm'),120);
 const stopped=word(1,'twink_pulses');run(180);assert(v(1,'twink_link'));assert.equal(word(1,'twink_pulses'),stopped,'Stopped heartbeat must not advance phase');
 // MS title navigation is reachable from the DRUM sequencer.
 choose(8);core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'left');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));run(20);assert.equal(v(0,'seqtrack'),5);
 // Plot/erase through real buttons: playback fixtures alone cannot test admission.
 assert.equal(word(0,'seqeventcounts',10),0);
 core._link_set_connected(0);run(150);assert.equal(v(0,'twink_ready'),0);
 const plottedPitch=v(0,'seqpitch',5),plottedVelocity=v(0,'eval_plotvel',5);
 press(0,'b');assert.equal(word(0,'seqeventcounts',10),1,'MS must admit a plotted note');
 press(0,'b');assert.equal(word(0,'seqeventcounts',10),0,'MS must erase a plotted note');
 press(0,'b');assert.equal(word(0,'seqeventcounts',10),1,'MS must reinsert a plotted note');
 core._link_set_connected(1);until(()=>v(0,'twink_ready')&&v(1,'twink_link'));
 core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));
 until(()=>v(1,'monocount')>0,200);assert.equal(v(1,'held'),plottedPitch,'Plotted MS note reaches MONOSIMP');assert.equal(v(1,'monovel'),plottedVelocity);
 core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));run(20);
 // Seed a sustained MS event into the real resident pattern storage.
 const slot=v(0,'mx',1),bank=1+(slot>>2),base=0xa000+(slot&3)*2048;
 const tracks=[[[0,49,100,16]],[],[],[],[],[[0,61,111,16]],[[0,1,100,4]]];let offset=0;
 for(let c=0;c<7;c++){writeword(0,'seqeventcounts',tracks[c].length,c*2);writeword(0,'seqeventoffsets',offset,c*2);writeword(0,'seqlength',16,c*2);for(const event of tracks[c]){event.forEach((x,j)=>{core._link_write(0,0x4000,bank);core._link_write(0,base+768+offset*4+j,x);});offset++;}}core._link_write(0,0x4000,0);
 put(0,'seqeventcache',0);put(0,'pattern_dirty',1);writeword(0,'pattern_generation',word(0,'pattern_generation')+1);
 choose(27);core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));until(()=>v(1,'monocount')>0,200);assert.equal(v(1,'held'),60);assert.equal(v(1,'monovel'),111);assert(v(1,'twink_running'));
 assert(v(0,'seqowned')>0,'Local P1 remains independently sequenced');const pulses=word(1,'twink_pulses');run(60);assert.notEqual(word(1,'twink_pulses'),pulses);assert.equal(v(1,'twink_link'),1);
 core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));run(20);assert.equal(v(1,'monocount'),0);assert.equal(v(1,'twink_running'),0);
 // Round-trip MS through the normal pattern archive UI. Slot assignment
 // precedes metadata restore; wait for the complete handoff before reading.
 choose(20);put(0,'mx',0,6);press(0,'b');run(60);if(v(0,'page')===26){press(0,'up');press(0,'a');run(40);}
 choose(18);put(0,'mx',31,4);press(0,'a');until(()=>v(0,'mx',1)===1&&!v(0,'seqservicing'));assert.equal(word(0,'seqeventcounts',10),0,'Other pattern has independent MS notes');
 put(0,'mx',30,4);press(0,'a');until(()=>v(0,'mx',1)===0&&!v(0,'seqservicing'));assert.equal(word(0,'seqeventcounts',10),1,'MS pattern save/restore');
 choose(27);if(v(0,'seqplaying')){core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));}
 // Tempo changes while stopped and reconnect need no transport restart.
 writeword(0,'seqbpm',30);writeword(0,'seqglobalbpm',30);until(()=>word(1,'twink_bpm')===30);
 for(const bpm of [30,300]){writeword(0,'seqbpm',bpm);writeword(0,'seqglobalbpm',bpm);until(()=>word(1,'twink_bpm')===bpm);core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));run(180);assert.equal(v(1,'twink_link'),1,'Link remains live at '+bpm);assert.equal(v(1,'twink_running'),1);assert.equal(v(0,'overflow'),0,'TX overflow at '+bpm);core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));assert.equal(v(0,'seqplaying'),0,'Master stops at '+bpm);until(()=>v(1,'monocount')===0&&!v(1,'twink_running'),120);}
 core._link_set_connected(0);run(150);assert.equal(v(1,'twink_link'),0);assert.equal(v(1,'monocount'),0);assert.equal(v(0,'twink_ready'),0);
 core._link_set_connected(1);until(()=>v(0,'twink_ready')&&v(1,'twink_link'));
 // Toggle back to MIDI: parser/session clear and MIDI mode survives clocks.
 press(1,'a');assert.equal(v(1,'twink_input'),0);assert.equal(v(1,'twink_link'),0);assert.equal(v(1,'monocount'),0);
 console.log('PASS: TWINK mode UI, independent MS lane, real cable notes/velocity, clock, stopped heartbeat, tempo, stop, disconnect/reconnect and MIDI toggle');
})().catch(e=>{console.error(e);process.exit(1);});

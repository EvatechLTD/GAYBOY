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
 let totalframes=0;const run=n=>{core._link_run(n);totalframes+=n;};
 function until(fn,max=2000){for(let n=0;n<max;n++){if(fn())return;run(1);}throw Error('timeout '+JSON.stringify({page:v(0,'page'),sync:v(0,'syncmode'),ready:v(0,'twink_ready'),remote:v(1,'twink_link'),input:v(1,'twink_input'),playing:v(0,'seqplaying'),view:v(1,'synthview'),inputread:v(1,'inputread'),inputwrite:v(1,'inputwrite'),inputsample:v(1,'inputsample'),lastpad:v(1,'lastpad'),armed:v(0,'syncarmed'),pc:[0,1].map(i=>core._link_pc(i).toString(16))}));}
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
 choose(27);core._link_key(0,5,1);until(()=>v(0,'lastpad')&32);for(let n=0;n<8&&v(0,'syncmode')!==6;n++)press(0,'up');core._link_key(0,5,0);until(()=>!(v(0,'lastpad')&32));assert.equal(v(0,'syncmode'),6);assert.equal(v(0,'syncslave'),0);
 until(()=>v(0,'twink_ready')&&v(1,'twink_link'));assert.equal(word(1,'twink_bpm'),120);
 const stopped=word(1,'twink_pulses');run(180);assert(v(1,'twink_link'));assert.equal(word(1,'twink_pulses'),stopped,'Stopped heartbeat must not advance phase');

 // Keep the receiver on its normal gate/status screen.
 if(receiverMenu)chooseReceiver(0);else press(1,'start');
 const preset=Number(process.env.TWINK_PRESET||3);for(let n=0;n<preset;n++)press(1,'right');
 const tracks=[[],[],[],[],[],[[0,61,111,8],[8,65,111,8],[16,68,111,8],[24,73,111,8]],[[0,13,110,1],[4,13,110,1],[8,13,110,1],[12,13,110,1]]];
 const localArp=process.env.TWINK_LOCAL_ARP==='1',localAudio=localArp||process.env.TWINK_LOCAL_AUDIO==='1';
 if(localAudio){choose(8);tracks[0]=localArp?[49,53,56,61].map(n=>[0,n,110,16]):[0,4,8,12].map(s=>[s,49,110,1]);tracks[6]=[0,4,8,12].map(s=>[s,4,100,1]);if(localArp){put(0,'evalpatch',1);put(0,'evalpatch',2,2);put(0,'evalpatch',1,13);}}
 const slot=v(0,'mx',1),bank=1+(slot>>2),base=0xa000+(slot&3)*2048;let offset=0;
 for(let c=0;c<7;c++){writeword(0,'seqeventcounts',tracks[c].length,c*2);writeword(0,'seqeventoffsets',offset,c*2);writeword(0,'seqlength',c===5?32:16,c*2);for(const event of tracks[c]){event.forEach((x,j)=>{core._link_write(0,0x4000,bank);core._link_write(0,base+768+offset*4+j,x);});offset++;}}core._link_write(0,0x4000,0);
 put(0,'seqeventcache',0);put(0,'pattern_dirty',1);writeword(0,'pattern_generation',word(0,'pattern_generation')+1);
 core._link_watch_rx(at(1,'rx'));core._link_watch_both_launch(1);
 core._link_watch_events(0,0,at(0,'seqposition'),at(0,'seqticks'),at(0,'seqclock'));
 core._link_key(0,6,1);until(()=>v(0,'lastpad')&64);press(0,'a');core._link_key(0,6,0);until(()=>!(v(0,'lastpad')&64));
 let navframes=[];
 let failures=[],badframes=0,loops=0,lastpos=v(0,'seqposition',5),samples=0;
 const frames=Number(process.env.TWINK_FRAMES||8000);
 for(let f=0;f<frames;f++){
  if(f%240===120){const view=v(1,'synthview'),before=totalframes;if(receiverMenu){chooseReceiver(view===0?4:0);assert.equal(v(1,'synthview'),view===0?3:0,'Receiver menu navigates during sustained notes');}else{core._link_key(1,6,1);run(3);core._link_key(1,6,0);run(3);until(()=>v(1,'synthview')===(view+1)%6,30);assert.equal(v(1,'synthview'),(view+1)%6,'Receiver navigation captures short taps during notes');}navframes.push(totalframes-before);}

  run(1);const rawpos=v(0,'seqposition',5);assert(rawpos<=32,'MS position corrupted: '+rawpos);const pos=rawpos&31,expected=tracks[5][pos>>3][1]-1;
  if(pos<lastpos)loops++;lastpos=pos;
  if(pos%8>=2&&pos%8<=5){samples++;if(!v(1,'monodown')||v(1,'held')!==expected||!v(1,'twink_link')||!v(1,'twink_running')){badframes++;if(failures.length<24)failures.push({f,loops,pos,expected,held:v(1,'held'),gate:v(1,'monodown'),count:v(1,'monocount'),link:v(1,'twink_link'),running:v(1,'twink_running'),master:v(0,'seqplaying'),overflow:v(0,'overflow'),rxoverflow:v(1,'overflow'),tick:v(0,'synctick'),rxpulses:word(1,'twink_pulses'),ready:v(0,'twink_ready')});}}
 }
 const events=[];const evptr=core._link_events(),view=new DataView(core.HEAPU8.buffer);
 for(let n=0;n<core._link_event_count();n++){const a=evptr+n*28,side=view.getUint32(a+4,true),tag=view.getUint32(a+8,true);if((side===0&&tag===0xff01)||(side===1&&tag===0x705))events.push({cycle:view.getUint32(a,true),side,byte:view.getUint32(a+12,true)});}
 function crc(body){let c=0;for(let b of body)for(let i=0;i<7;i++){let top=(c^b)&64;c=(c<<1)&127;if(top)c^=9;b<<=1;}return c;}
 const packetErrors=[0,0],packetCounts=[0,0],bodies=[null,null];
 for(const e of events){const side=e.side,b=e.byte;if(b===0xf3)bodies[side]=[];else if(b>=0x80&&b<=0xbf||b===0xf9)continue;else if(b&128)bodies[side]=null;else if(bodies[side]){bodies[side].push(b);if(bodies[side].length===4){const body=bodies[side];packetCounts[side]++;if(body[3]!==crc(body.slice(0,3)))packetErrors[side]++;bodies[side]=null;}}}
 if(localAudio){assert(v(0,'editbuffer_valid'),'Playback snapshot remains active with TWINK');assert(v(0,localArp?'arpirq_enabled':'editirq_enabled')&1,'Local pulse timer dispatch remains active with TWINK');}
 const report={preset,localAudio,localArp,frames,loops,samples,badframes,navTaps:navframes.length,maxNavFrames:Math.max(...navframes),packetCounts,packetErrors,unarmed:core._link_unarmed_edges(),aborts:core._link_wire_aborts(),failures};
 console.log(JSON.stringify({...report,failures:failures.slice(0,2)},null,2));fs.writeFileSync('build/twink-sustain-'+preset+'-wire.json',JSON.stringify(events));fs.writeFileSync('build/twink-sustain-'+preset+'-report.json',JSON.stringify(report,null,2));
 assert.equal(badframes,0,'Sustained ascending MS notes must not disappear between boundaries');assert.deepEqual(packetErrors,[0,0],'Both transmitted and received packets remain intact');assert.deepEqual(packetCounts.slice(0,1),packetCounts.slice(1),'No lost serial packets');assert.equal(report.unarmed,0,'No bits arrive before the receiver rearms');assert.equal(report.aborts,0,'No serial transfer is overwritten');
})().catch(e=>{console.error(e);process.exit(1);});

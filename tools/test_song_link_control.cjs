/* Use the same real-cable boot/settings/save fixture as the timing gate. */
const fs=require('fs');
const prefix=fs.readFileSync('tools/test_song_link.cjs','utf8').split(' core._link_watch_events')[0];
const controls=String.raw`
 const scenario=option('--scenario','restart');
 const protectedBytes=()=>[0,1].map(side=>Array.from({length:5},(_,slot)=>{const base=(1+(slot>>2))*8192+(slot&3)*2048;return Array.from({length:1312},(_,n)=>core._link_cart_read(side,base+480+n));}));
 let before=protectedBytes();
 if(scenario==='missing')core._link_set_connected(0);
 if(scenario==='wrong-page')choose(1,8);
 if(scenario==='once'){put(0,'song_view',2,12);tap(0,'a');put(0,'song_view',0,12);before=protectedBytes();}
 chord(0,'select','start');
 if(scenario==='missing'||scenario==='wrong-page'){
  until(()=>!v(0,'song_link_active'),1800);assert(!v(0,'song_playing')&&!v(1,'song_playing'));assert.equal(v(0,'song_view',15),11);
 }else if(scenario==='cancel-header'||scenario==='cancel-prep'){
  until(()=>core._link_state_read(1,0xa3e2)===(scenario==='cancel-header'?5:6),1200);
  chord(0,'select','start');until(()=>!v(0,'song_link_active')&&!v(1,'song_link_active'),1800);
  assert(!v(0,'song_playing')&&!v(1,'song_playing'));
 }else{
  until(()=>v(0,'song_playing')&&v(1,'song_playing'),1800);run(180);
  if(scenario==='slave-stop'){
   const was=word(0,'song_hwclock');chord(1,'select','start');until(()=>!v(1,'song_playing'));run(180);
   assert(v(0,'song_playing')&&word(0,'song_hwclock')!==was,'Slave local stop changed master');
  }else if(scenario==='drop'){
   core._link_set_connected(0);const was=word(0,'song_hwclock');run(600);
   assert(v(0,'song_playing')&&word(0,'song_hwclock')!==was,'Cable pull blocked master');
  }else if(scenario==='once'){
   until(()=>!v(0,'song_playing')&&!v(1,'song_playing'),12000);
  }
  if(v(0,'song_playing'))chord(0,'select','start');
  if(scenario==='drop'&&v(1,'song_playing'))chord(1,'select','start');
  until(()=>!v(0,'song_playing')&&!v(1,'song_playing'),1800);
  if(scenario==='restart'){
   chord(0,'select','start');until(()=>v(0,'song_playing')&&v(1,'song_playing'),1800);run(180);
   chord(0,'select','start');until(()=>!v(0,'song_playing')&&!v(1,'song_playing'),1800);
  }
 }
 assert(!v(0,'song_link_active')&&!v(1,'song_link_active'),'Link ownership stuck');
 assert.deepEqual(protectedBytes(),before,'Resident notes or arrangement changed');
 assert(!word(0,'song_underruns')&&!word(1,'song_underruns'),'Queue underrun');
 console.log('PASS song link control',scenario,'and protected arrangement/notes');
})().catch(e=>{console.error(e);process.exitCode=1;});
`;
eval(prefix+controls);

/* Small, isolated transport shared by MIDI, SID and tracker backends. */
const $=s=>document.querySelector(s),params=new URLSearchParams(location.search);
const format=params.get('format'),source=params.get('src');
let transport=null,track=null,blob=null,loading=false,playing=false,ended=false,timer=null;
const status=s=>$('#status').textContent=s;
const stamp=t=>Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');
const scripts=new Map();
function script(src){if(!scripts.has(src))scripts.set(src,new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.onload=resolve;s.onerror=()=>reject(Error('Could not load the music engine. Reload and try again.'));document.head.append(s);}));return scripts.get(src);}
function volume(){if(transport)transport.volume=$('#volume').value/100;}
function finish(){playing=false;ended=true;$('#play').textContent='PLAY';status('Finished.');if($('#loop').checked)setTimeout(()=>{if(ended&&$('#loop').checked)start();},0);}
function fail(e){playing=false;loading=false;transport?.pause();$('#play').textContent='PLAY';$('#play').disabled=false;status(e.message||'This music file could not be played.');}
async function bytes(){
 const u=new URL(source,location.href);if(u.protocol!=='https:'&&!(u.origin===location.origin&&u.protocol==='http:'))throw Error('Use an HTTPS music link.');
 const r=await fetch(u,{signal:AbortSignal.timeout(20000),credentials:u.origin===location.origin?'same-origin':'omit'});
 if(!r.ok)throw Error('Music file unavailable ('+r.status+').');
 if(+r.headers.get('Content-Length')>2400000)throw Error('Choose a file under 2.4 MB.');
 const reader=r.body.getReader(),chunks=[];let size=0;
 while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>2400000){await reader.cancel();throw Error('Choose a file under 2.4 MB.');}chunks.push(value);}
 const b=new Uint8Array(size);let pos=0;for(const c of chunks){b.set(c,pos);pos+=c.length;}return b;
}
async function load(){
 const b=await bytes(),magic=String.fromCharCode(...b.subarray(0,4));
 if(['mid','midi'].includes(format)){
  if(magic!=='MThd')throw Error('This is not a Standard MIDI file.');
  await script('JZZ.js');await script('JZZ.midi.SMF.js');await script('JZZ.synth.Tiny.js');
  const player=new JZZ.MIDI.SMF(b).player(),synth=JZZ.synth.Tiny(),ctx=JZZ.lib.getAudioContext(),gain=ctx.createGain();
  gain.connect(ctx.destination);synth.plug(gain);player.connect(synth);player.onEnd=finish;
  transport={play(){ctx.resume();if(ended){player.play();ended=false;}else player.resume();},pause(){player.pause();},stop(){player.stop();},get currentTime(){return player.positionMS()/1000;},get duration(){return player.durationMS()/1000;},set volume(v){gain.gain.value=v;}};
 }else{
  if(format==='sid'&&(!['PSID','RSID'].includes(magic)||b.length<126))throw Error('This is not a SID file.');
  await script('cowbell.min.js');await script('cowbell-audio.js');await script(format==='sid'?'jssid.js':'openmpt.min.js');
  blob=URL.createObjectURL(new Blob([b]));let selected=0;
  if(format==='sid'){
   const count=(b[14]<<8)|b[15],first=(b[16]<<8)|b[17];selected=Math.max(0,Math.min(count-1,(+params.get('subsong')||first)-1));
   if(count<1||count>256)throw Error('Unsupported SID tune count.');
   $('#subsong').replaceChildren(...Array.from({length:count},(_,i)=>new Option(String(i+1),i+1,false,i===selected)));$('#subsong-label').hidden=count<2;
  }
  const backend=format==='sid'?new Cowbell.Player.JSSID({backgroundNoise:0}):new Cowbell.Player.OpenMPT({pathToLibOpenMPT:'libopenmpt.js'});
  track=new backend.Track(blob+(format==='sid'?'#'+(selected+1):''));
  transport=await openTrack(track);
  transport.onended=finish;
 }
 volume();$('#stop').disabled=false;
 timer=setInterval(()=>{if(transport)$('#time').textContent=stamp(transport.currentTime||0)+(format==='sid'?'':' / '+stamp(transport.duration||0));},250);
}
function openTrack(t){return new Promise((resolve,reject)=>{const output=t.open(),timeout=setTimeout(()=>{output.pause();reject(Error('This file could not be decoded. Try a different file.'));},15000);output.onloadedmetadata=()=>{clearTimeout(timeout);resolve(output);};});}
async function start(){
 if(loading)return;
 try{
  if(playing){transport.pause();playing=false;$('#play').textContent='PLAY';status('Paused.');return;}
  if(!transport){loading=true;$('#play').disabled=true;status('Loading music…');await load();loading=false;$('#play').disabled=false;}
  transport.play();playing=true;ended=false;$('#play').textContent='PAUSE';status('Playing.');
 }catch(e){fail(e instanceof TypeError?Error('Could not fetch this link. Upload the file in Music, or use a host that permits cross-site playback.'):e);}
}
function stop(){transport?.pause();if(transport?.stop)transport.stop();else if(transport)transport.currentTime=0;playing=false;ended=true;$('#play').textContent='PLAY';status('Stopped.');}
$('#play').onclick=start;$('#stop').onclick=stop;$('#volume').oninput=volume;
$('#subsong').onchange=async()=>{if(loading)return;stop();track?.close();transport=null;loading=true;$('#play').disabled=true;status('Loading SID tune…');try{const backend=new Cowbell.Player.JSSID({backgroundNoise:0});track=new backend.Track(blob+'#'+$('#subsong').value);transport=await openTrack(track);volume();loading=false;$('#play').disabled=false;await start();}catch(e){fail(e);}};
window.addEventListener('pagehide',()=>{stop();track?.close();clearInterval(timer);if(blob)URL.revokeObjectURL(blob);});
window.addEventListener('error',()=>fail(Error('This music file could not be decoded. Try a different file.')));
if(!source||!['mid','midi','sid','mod','xm','s3m','it','mptm','mtm','stm','669','med'].includes(format)){$('#play').disabled=true;status('Choose a MIDI, SID or tracker file in Music.');}
else $('#title').textContent=(format==='sid'?'SID':format==='mid'||format==='midi'?'MIDI':format.toUpperCase()+' TRACKER')+' / PAGE SOUNDTRACK';
if(format==='sid'){$('#loop').closest('label').hidden=true;}

if(parent!==window)new ResizeObserver(()=>parent.postMessage({type:'y2k-retro-height',height:Math.ceil(document.body.getBoundingClientRect().height)},location.origin)).observe(document.body);

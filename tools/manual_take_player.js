// Run the exact website SameBoy core against the audio clock. Encoding is
// performed by MediaRecorder, never by Python frame-by-frame polling.
window.startManualTake = async function(seconds) {
  const canvas = document.querySelector('#screen'), display = canvas.getContext('2d');
  const small = document.createElement('canvas'); small.width=160; small.height=144;
  const ctx=small.getContext('2d'), image=ctx.createImageData(160,144);
  display.imageSmoothingEnabled=false;
  const status=document.querySelector('#status');
  const audio=new AudioContext({sampleRate:48000}); await audio.resume();
  const destination=audio.createMediaStreamDestination();
  const gain=audio.createGain(); gain.gain.value=1;
  gain.connect(audio.destination); gain.connect(destination);
  const keys={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right',
    KeyX:'A',KeyZ:'B',Space:'start',ShiftLeft:'select',ShiftRight:'select'};
  function key(event,down) {
    const name=keys[event.code]; if(!name)return;
    event.preventDefault(); if(event.repeat)return;
    m['_set_joyp_'+name](e,down);
    manualStats.inputs.push({at:audio.currentTime,button:name,down});
  }
  document.addEventListener('keydown', ev=>key(ev,1));
  document.addEventListener('keyup', ev=>key(ev,0));
  window.addEventListener('blur',()=>Object.values(keys).forEach(k=>m['_set_joyp_'+k](e,0)));
  window.manualStats={seconds,inputs:[],audioBuffers:0,audioUnderruns:0,frames:0};
  // Discard the partial preparation buffer; start live scheduling on a clean block.
  while(!(m._emulator_run_until_f64(e,m._emulator_get_ticks_f64(e)+70224)&2)){}
  const epoch=m._emulator_get_ticks_f64(e), audioEpoch=audio.currentTime;
  let nextAudio=audioEpoch+.06, live=true, recording=false;
  function tick(){
    if(!live)return;
    const target=epoch+(audio.currentTime-audioEpoch+.09)*4194304;
    let event;
    do{
      event=m._emulator_run_until_f64(e,target);
      if(event&16)throw Error('Invalid ROM instruction');
      if(event&1){
        image.data.set(m.HEAPU8.subarray(m._get_frame_buffer_ptr(e),m._get_frame_buffer_ptr(e)+160*144*4));
        ctx.putImageData(image,0,0);display.drawImage(small,0,0,640,576);manualStats.frames++;
      }
      if(event&2){
        const data=new Int16Array(m.HEAPU8.buffer,m._get_audio_buffer_ptr(e),2048);
        const buffer=audio.createBuffer(2,1024,48000);
        for(let c=0;c<2;c++){const out=buffer.getChannelData(c);for(let i=0;i<1024;i++)out[i]=data[i*2+c]/32768;}
        if(nextAudio<audio.currentTime){nextAudio=audio.currentTime+.04;if(recording)manualStats.audioUnderruns++;}
        const source=audio.createBufferSource();source.buffer=buffer;source.connect(gain);source.start(nextAudio);
        nextAudio+=1024/48000;manualStats.audioBuffers++;
      }
    }while(!(event&4));
  }
  const pump=setInterval(tick,5);tick();
  for(let n=(window.manualCountdown ?? 3);n>0;n--){status.textContent=`Demo playing — recording starts in ${n}…`;await new Promise(r=>setTimeout(r,1000));}
  const stream=canvas.captureStream(30);destination.stream.getAudioTracks().forEach(t=>stream.addTrack(t));
  const mime=['video/webm;codecs=vp8,opus','video/webm'].find(t=>MediaRecorder.isTypeSupported(t));
  const recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:8000000,audioBitsPerSecond:192000});
  const chunks=[];recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
  recorder.onstop=()=>{
    const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(chunks,{type:mime}));
    a.download='take.webm';a.click();status.textContent='Take complete. Saving recording…';
  };
  recording=true;recorder.start(1000);const start=performance.now();
  const countdown=setInterval(()=>status.textContent=`RECORDING — ${Math.max(0,Math.ceil(seconds-(performance.now()-start)/1000))} seconds left`,100);
  setTimeout(()=>{recording=false;recorder.stop();clearInterval(countdown);clearInterval(pump);live=false;
    gain.gain.setValueAtTime(0,audio.currentTime);},seconds*1000);
};

/* GAYBOY browser player. SameBoy 1.0.4; see SAMEBOY-LICENSE.txt.
 * The core adapter is built from tools/browser_sameboy.c. */
(() => {
  'use strict';
  const root = document.querySelector('#live-demo');
  const canvas = root.querySelector('canvas');
  const screen = canvas.getContext('2d', {alpha: false});
  const status = root.querySelector('[role="status"]');
  const play = root.querySelector('#demo-play');
  const pause = root.querySelector('#demo-pause');
  const restart = root.querySelector('#demo-restart');
  const mute = root.querySelector('#demo-mute');
  const exportSave = root.querySelector('#demo-save');
  const resumeOverlay = document.createElement('button');
  resumeOverlay.type = 'button';
  resumeOverlay.className = 'demo-resume-overlay';
  resumeOverlay.textContent = '▶ TAP TO RESUME';
  resumeOverlay.hidden = true;
  root.querySelector('.demo-screen').append(resumeOverlay);
  resumeOverlay.addEventListener('click', () => setPaused(false));
  const expand = root.querySelector('#demo-fullscreen');
  function expanded(value) {
    root.classList.toggle('demo-expanded', value);
    document.body.classList.toggle('demo-open', value);
    expand.textContent = value ? '⛶ back to page' : '⛶ big screen';
    expand.setAttribute('aria-expanded', String(value));
  }
  expand.setAttribute('aria-expanded', 'false');
  expand.addEventListener('click', () => expanded(!root.classList.contains('demo-expanded')));
  const SAVE_KEY = 'gayboy-browser-sram-0.3-10cc021b';
  const LEGACY_SAVE_KEYS = ['gayboy-browser-sram-0.3-622c7024','gayboy-browser-sram-0.3-4a7e3e79','gayboy-browser-sram-0.3-73d49395'];
  const CLOCK = 4194304;
  const AUDIO_FRAMES = 2048;
  const AUDIO_LEAD = 0.09;
  let core, instance = 0, romPtr = 0, joypad = 0, audio, gain, highpass;
  let rom, raf = 0, lastTime = 0, nextAudio = 0, running = false;
  let loading = false, muted = false, ramDirty = false, storageAvailable = true;
  let audioEpoch = 0, emulationEpoch = 0;
  let resumeGeneration = 0, resuming = false, rebuildAudio = false;
  let lastAudioClock = 0, lastAudioAdvance = 0;
  const held = new Map();
  const pressedAt = new Map();
  const releaseTimers = new Map();
  const sources = new Set();
  const buttons = ['up', 'down', 'left', 'right', 'A', 'B', 'start', 'select'];
  const keys = {ArrowUp:'up', ArrowDown:'down', ArrowLeft:'left', ArrowRight:'right',
    KeyX:'A', KeyZ:'B', Space:'select', ShiftLeft:'start', ShiftRight:'start'};
  const image = screen.createImageData(160, 144);

  const tutorialStart = root.querySelector('#demo-tutorial');
  const tutorialReopen = root.querySelector('#demo-tutorial-reopen');
  let tutorialActive = false, tutorialLoading = false, parked = null;
  let beatParked = null, beatBusy = false;
  function tutorialKeydown(event) {
    if (event.code === 'Escape' && !event.repeat) { setPaused(true); return; }
    if (!keys[event.code] || !running) return;
    event.preventDefault(); input(keys[event.code], event.code, true);
  }
  function rebaseAudio() {
    release(); silence();
    core._emulator_set_sample_rate(instance, audio.sampleRate);
    audioEpoch = audio.currentTime;
    emulationEpoch = core._emulator_get_ticks_f64(instance);
    lastAudioClock = audio.currentTime; lastAudioAdvance = performance.now();
    render();
  }
  async function exitTutorial() {
    if (!parked) return;
    ++resumeGeneration; resuming = false; running = false;
    cancelAnimationFrame(raf); release(); silence();
    core._emulator_delete(instance); core._joypad_delete(joypad); core._free(romPtr);
    const saved = parked; parked = null;
    ({instance,romPtr,joypad,rom,ramDirty} = saved);
    tutorialActive = false;
    root.querySelectorAll('[data-runtime]').forEach(el => el.disabled = false);
    tutorialReopen.disabled = false;
    expanded(saved.expanded);
    rebaseAudio();
    if (saved.running) await resumePlayback();
    else setPaused(true);
    message('Back to your music. Your original session and saved patterns are preserved.');
  }
  const tour = window.createGayboyTutorial({root, handheld:root.querySelector('.handheld'),
    ticks:() => core._emulator_get_ticks_f64(instance),
    read:address => core._emulator_observe_mem(instance,address),
    running:() => running,
    held:() => pressedAt.size > 0 || Array.from(held.values()).some(set => set.size),
    snapshot:() => core._emulator_checkpoint_new(instance),
    restore:ptr => {
      if (core._emulator_checkpoint_restore(instance,ptr)) throw new Error('Could not restore the practice screen.');
      rebaseAudio();
    },
    deleteSnapshot:ptr => core._emulator_checkpoint_delete(ptr),
    release,
    press:(button,down) => {
      core['_set_joyp_'+button](instance,down?1:0);
      root.querySelector(`[data-pad="${button}"]`).classList.toggle('held',down);
    },
    highlight:pads => root.querySelectorAll('[data-pad]').forEach(el => el.classList.toggle('tutorial-target',pads.includes(el.dataset.pad))),
    keydown:tutorialKeydown, expand:expanded, exit:exitTutorial
  });
  async function startTutorial() {
    if (loading || tutorialLoading || tutorialActive || beatParked || beatBusy) return;
    tutorialLoading = true;
    tutorialStart.disabled = true; tutorialReopen.disabled = true;
    try {
      if (!instance) await powerOn();
      if (!instance) return;
      const response = await fetch('emulator/practice-rom.json?v=stable-1.0-f3ff8d7fee18');
      if (!response.ok) throw new Error('Tutorial information could not be loaded.');
      const metadata = await response.json();
      const download = await fetch(metadata.rom+'?v='+metadata.sha256);
      if (!download.ok) throw new Error('Practice cartridge could not be loaded.');
      const practiceRom = await download.arrayBuffer();
      const digest = new Uint8Array(await crypto.subtle.digest('SHA-256',practiceRom));
      const hash = Array.from(digest,b=>b.toString(16).padStart(2,'0')).join('');
      if (hash !== metadata.sha256) throw new Error('Practice cartridge does not match its lesson map.');
      const wasRunning = running || resuming;
      setPaused(true, true); persist();
      parked = {instance,romPtr,joypad,rom,ramDirty,running:wasRunning,expanded:root.classList.contains('demo-expanded')};
      tutorialActive = true; instance = romPtr = joypad = 0; rom = practiceRom;
      await boot(); exportSave.disabled = true; restart.disabled = true;
      if (!running) throw new Error('Practice audio could not start.');
      await tour.start(metadata);
    } catch (error) {
      if (tutorialActive) await tour.close();
      message('Could not start the tutorial. Please try again. Your music is preserved.');
      console.error('GAYBOY tutorial:',error);
    } finally {
      tutorialLoading = false; tutorialStart.disabled = false;
      tutorialReopen.disabled = tutorialActive;
    }
  }
  tutorialStart.addEventListener('click',startTutorial);
  tutorialReopen.addEventListener('click',startTutorial);
  function message(text) { status.textContent = text; }
  function ramBytes() {
    const file = core._ext_ram_file_data_new(instance);
    try {
      core._emulator_write_ext_ram(instance, file);
      return new Uint8Array(core.HEAPU8.buffer, core._get_file_data_ptr(file),
        core._get_file_data_size(file)).slice();
    } finally { core._file_data_delete(file); }
  }
  function persist() {
    if (!instance || !ramDirty || tutorialActive || beatParked) return;
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(Array.from(ramBytes())));
      ramDirty = false;
    } catch {
      storageAvailable = false;
      message('Browser storage unavailable. Use “download save” to keep saved patterns.');
    }
  }
  function restore() {
    try {
      const data = JSON.parse(localStorage.getItem(SAVE_KEY) || 'null');
      if (!Array.isArray(data) || data.length !== 32768 ||
          !data.every(n => Number.isInteger(n) && n >= 0 && n <= 255)) return;
      const file = core._ext_ram_file_data_new(instance);
      try {
        if (core._get_file_data_size(file) === data.length) {
          core.HEAPU8.set(data, core._get_file_data_ptr(file));
          core._emulator_read_ext_ram(instance, file);
        }
      } finally { core._file_data_delete(file); }
    } catch { storageAvailable = false; }
  }
  function input(button, source, down) {
    if (!instance) return;
    if (tutorialActive && !tour.acceptsInput()) return;
    if (tutorialActive && down && running && !pressedAt.has(button + ':' + source)) tour.learnerInput();
    const token = button + ':' + source;
    clearTimeout(releaseTimers.get(token));
    releaseTimers.delete(token);
    if (down && !pressedAt.has(token)) pressedAt.set(token, performance.now());
    // A quick phone tap must survive long enough for the ROM's input poll.
    if (!down && pressedAt.has(token)) {
      const remaining = 100 - (performance.now() - pressedAt.get(token));
      if (remaining > 0) {
        releaseTimers.set(token, setTimeout(() => input(button, source, false), remaining));
        return;
      }
    }
    if (!down) pressedAt.delete(token);
    const set = held.get(button) || new Set();
    down ? set.add(source) : set.delete(source);
    held.set(button, set);
    core['_set_joyp_' + button](instance, running && set.size > 0 ? 1 : 0);
    root.querySelector(`[data-pad="${button}"]`).classList.toggle('held', running && set.size > 0);
  }
  function release() {
    releaseTimers.forEach(clearTimeout); releaseTimers.clear(); pressedAt.clear();
    held.clear();
    if (instance) buttons.forEach(button => core['_set_joyp_' + button](instance, 0));
    root.querySelectorAll('[data-pad]').forEach(el => el.classList.remove('held'));
  }
  function queueAudio() {
    if (audio.state !== 'running') return;
    const now = audio.currentTime;
    if (nextAudio < now + 0.005) nextAudio = now + 0.045;
    const data = new Int16Array(core.HEAPU8.buffer, core._get_audio_buffer_ptr(instance),
      core._get_audio_buffer_capacity(instance) / 2);
    const buffer = audio.createBuffer(2, AUDIO_FRAMES, audio.sampleRate);
    for (let channel = 0; channel < 2; channel++) {
      const output = buffer.getChannelData(channel);
      for (let i = 0; i < AUDIO_FRAMES; i++) output[i] = data[i * 2 + channel] / 32768;
    }
    const source = audio.createBufferSource();
    source.buffer = buffer; source.connect(highpass);
    source.onended = () => sources.delete(source);
    sources.add(source); source.start(nextAudio);
    nextAudio += AUDIO_FRAMES / audio.sampleRate;
  }
  function render() {
    image.data.set(new Uint8Array(core.HEAPU8.buffer,
      core._get_frame_buffer_ptr(instance), 160 * 144 * 4));
    screen.putImageData(image, 0, 0);
  }
  function tick(time) {
    if (!running) return;
    if (audio.state !== 'running') {
      rebuildAudio = true; setPaused(true); return;
    }
    if (audio.currentTime > lastAudioClock) {
      lastAudioClock = audio.currentTime; lastAudioAdvance = time;
    } else if (time - lastAudioAdvance > 1500) {
      rebuildAudio = true; setPaused(true); return;
    }
    lastTime = time;
    // Run ahead of the sound device, rather than allowing animation-frame
    // jitter to break the audio into gaps. Keep a short cushion for phones.
    const target = emulationEpoch + (audio.currentTime - audioEpoch + AUDIO_LEAD) * CLOCK;
    try {
      let event;
      do {
        event = core._emulator_run_until_f64(instance, target);
        if (event & 16) throw new Error('ROM encountered an invalid instruction');
        if (event & 1) render();
        if (event & 2) queueAudio();
      } while (!(event & 4));
      if (core._emulator_was_ext_ram_updated(instance)) ramDirty = true;
      if (tutorialActive) tour.poll();
      raf = requestAnimationFrame(tick);
    } catch (error) {
      setPaused(true);
      message('The demo stopped. Try restart, or download the ROM to use your own emulator.');
      console.error('GAYBOY emulator:', error);
    }
  }
  function silence() {
    sources.forEach(source => { try { source.stop(); } catch {} });
    sources.clear(); nextAudio = 0;
  }
  function createAudioContext() {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const old = audio;
    audio = new AudioContext();
    gain = audio.createGain(); gain.gain.value = muted ? 0 : 0.65;
    highpass = gain; gain.connect(audio.destination);
    audio.addEventListener('statechange', () => {
      if (audio.state === 'interrupted' || audio.state === 'closed') rebuildAudio = true;
      if (running && audio.state !== 'running') setPaused(true);
    });
    if (instance) core._emulator_set_sample_rate(instance, audio.sampleRate);
    if (old && old.state !== 'closed') old.close().catch(() => {});
    rebuildAudio = false;
  }
  async function resumePlayback() {
    if (!instance || resuming || document.hidden) return;
    const generation = ++resumeGeneration;
    resuming = true;
    let timeout;
    try {
      // A new sound device on this user gesture also recovers iOS contexts
      // that stay interrupted after screen lock. The emulated GB stays intact.
      if (rebuildAudio || audio.state === 'interrupted' || audio.state === 'closed') createAudioContext();
      await Promise.race([audio.resume(), new Promise((_, reject) => {
        timeout = setTimeout(() => reject(new Error('Audio resume timed out')), 2000);
      })]);
      if (generation !== resumeGeneration || document.hidden) return;
      if (audio.state !== 'running') throw new Error('Audio is still interrupted');
      running = true; resuming = false; resumeOverlay.hidden = true;
      pause.textContent = 'Ⅱ pause'; pause.setAttribute('aria-pressed', 'false');
      audioEpoch = audio.currentTime;
      emulationEpoch = core._emulator_get_ticks_f64(instance);
      lastAudioClock = audio.currentTime; lastAudioAdvance = performance.now();
      raf = requestAnimationFrame(tick);
      if (tutorialActive) message('Tutorial practice. Follow the task above; exit returns to your original music.');
      else message(storageAvailable ? 'Playing! Press Shift / START for the menu. Save patterns in-game to keep them in this browser.' :
        'Playing! Browser storage unavailable; use “download save” to keep saved patterns.');
      if (tutorialActive) { tour.focus(); tour.resume(); }
      else canvas.focus({preventScroll:true});
    } catch {
      if (generation === resumeGeneration) {
        rebuildAudio = true;
        message('Sound needs another tap after the interruption. Tap the screen’s RESUME button. Your sequencer is preserved.');
      }
    } finally {
      clearTimeout(timeout);
      if (generation === resumeGeneration) resuming = false;
    }
  }
  function setPaused(value, keepAudio = false) {
    if (!instance) return;
    if (!value) {
      // Keep an obvious recovery button until the sound device has resumed.
      resumeOverlay.hidden = false;
      return resumePlayback();
    }
    ++resumeGeneration; resuming = false; running = false;
    release(); silence(); cancelAnimationFrame(raf); lastTime = 0;
    if (tutorialActive) tour.suspend();
    pause.textContent = '▶ resume'; pause.setAttribute('aria-pressed', 'true');
    resumeOverlay.hidden = false;
    if (!keepAudio && audio.state === 'running') audio.suspend().catch(() => { rebuildAudio = true; });
    persist();
    message('Paused. Tap RESUME on the screen to continue. Your sequencer is preserved.');
  }
  function boot() {
    if (instance) { core._emulator_delete(instance); core._joypad_delete(joypad); core._free(romPtr); }
    romPtr = core._malloc(rom.byteLength);
    core.HEAPU8.set(new Uint8Array(rom), romPtr);
    instance = core._emulator_new_simple(romPtr, rom.byteLength, audio.sampleRate, AUDIO_FRAMES, 2);
    if (!instance) throw new Error('Unable to load ROM');
    joypad = core._joypad_new();
    core._emulator_set_default_joypad_callback(instance, joypad);
    // Neutral white palette, lightest to darkest, for every DMG layer.
    for (let type = 0; type < 3; type++) {
      core._emulator_set_bw_palette_simple(instance, type,
        0xffffffff, 0xffaaaaaa, 0xff555555, 0xff000000);
    }
    if (!tutorialActive && !beatParked) restore();
    ramDirty = false;
    root.querySelectorAll('[data-runtime]').forEach(el => el.disabled = false);
    root.classList.add('demo-started');
    if (tutorialReopen) tutorialReopen.hidden = false;
    return setPaused(false);
  }
  async function powerOn() {
    if (loading || instance) return;
    loading = true; play.disabled = true;
    if (tutorialStart) tutorialStart.disabled = true;
    message('Loading your tiny music machine…');
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!window.WebAssembly || !AudioContext) throw new Error('Unsupported browser');
      if (!audio || audio.state === 'closed') createAudioContext();
      await audio.resume();
      if (!window.SameBoyCore) await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'emulator/sameboy.js?v=beats-1'; script.onload = resolve;
        script.onerror = () => { script.remove(); reject(new Error('Emulator download failed')); };
        document.head.append(script);
      });
      const metadataResponse=await fetch('emulator/tutorial-rom.json?v=stable-1.0-adf25cd8612d');
      if(!metadataResponse.ok)throw new Error('Cartridge information could not be loaded.');
      const metadata=await metadataResponse.json();
      const response = await fetch(metadata.rom+'?v='+metadata.sha256);
      if (!response.ok) throw new Error('ROM download failed');
      rom = await response.arrayBuffer();
      const romHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',rom)),b=>b.toString(16).padStart(2,'0')).join('');
      if (rom.byteLength !== 1048576||romHash!==metadata.sha256) throw new Error('Incomplete or outdated ROM');
      core = await window.SameBoyCore({locateFile: name => 'emulator/' + name + '?v=beats-1'});
      await boot();
      if (window.matchMedia('(max-width: 590px)').matches) expanded(true);
    } catch (error) {
      message('Couldn’t start the demo. Try again in a current browser, or download the ROM below.');
      play.disabled = false;
      if (audio) await audio.close();
      console.error('GAYBOY emulator:', error);
    } finally { loading = false; if (tutorialStart) tutorialStart.disabled = false; }
  }
  play.addEventListener('click', powerOn);
  async function returnToMyBeat() {
    if (!beatParked) return;
    setPaused(true,true);
    core._emulator_delete(instance);core._joypad_delete(joypad);core._free(romPtr);
    const saved=beatParked;beatParked=null;
    ({instance,romPtr,joypad,rom,ramDirty}=saved);
    expanded(saved.expanded);rebaseAudio();
    tutorialStart.disabled=false;tutorialReopen.disabled=false;
    if(saved.running)await resumePlayback();else setPaused(true);
    message('Back to your own beat. Your music was preserved.');
  }
  window.gayboyBeats = {
    minimize() { expanded(false); },
    unlock() {
      if(!audio||audio.state==='closed')createAudioContext();
      audio.resume().catch(()=>{});
    },
    async capture() {
      if(!instance||loading||tutorialActive||beatBusy||beatParked)throw new Error('Start your own beat in the emulator before sharing.');
      const metadata=await(await fetch('emulator/tutorial-rom.json?v=stable-1.0-adf25cd8612d')).json();
      if(!core._emulator_observe_mem(instance,metadata.symbols.seqplaying))
        throw new Error('Start your sequencer with SELECT + A, then share your beat.');
      release();
      const file=core._emulator_beat_file_new(instance);
      if(!file)throw new Error('Could not capture that beat. Try again.');
      try {
        const size=core._get_file_data_size(file),bytes=new Uint8Array(size+40);
        bytes.set(new TextEncoder().encode('GBBT0001'));
        bytes.set(metadata.sha256.match(/../g).map(n=>parseInt(n,16)),8);
        bytes.set(core.HEAPU8.slice(core._get_file_data_ptr(file),core._get_file_data_ptr(file)+size),40);
        return bytes;
      } finally {core._file_data_delete(file);}
    },
    async listen(bytes) {
      if(beatBusy||tutorialLoading||loading)throw new Error('Please wait for the emulator to finish loading.');
      if(bytes.length<40||new TextDecoder().decode(bytes.slice(0,8))!=='GBBT0001')throw new Error('That beat could not be read.');
      beatBusy=true;
      try {
        if(tutorialActive)await tour.close();
        if(beatParked)await returnToMyBeat();
        if(!instance)await powerOn();
        if(!instance)throw new Error('Tap POWER ON, then try playing that beat again.');
        const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',rom)),b=>b.toString(16).padStart(2,'0')).join('');
        const targetHash=Array.from(bytes.slice(8,40),b=>b.toString(16).padStart(2,'0')).join('');
        const versions=await(await fetch('emulator/rom-versions.json?v=stable-1.0-adf25cd8612d')).json();
        const metadata=versions.versions[targetHash];
        if(!metadata)throw new Error('That beat uses an unavailable version of GAYBOY.');
        let beatRom=rom;
        if(hash!==targetHash){
          const response=await fetch(metadata.rom+'?v='+targetHash);
          if(!response.ok)throw new Error('The archived beat cartridge could not be loaded.');
          beatRom=await response.arrayBuffer();
          const archivedHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',beatRom)),b=>b.toString(16).padStart(2,'0')).join('');
          if(archivedHash!==targetHash)throw new Error('The beat cartridge download was incomplete.');
        }
        const wasRunning=running||resuming;
        setPaused(true,true);persist();
        beatParked={instance,romPtr,joypad,rom,ramDirty,running:wasRunning,expanded:root.classList.contains('demo-expanded')};
        instance=romPtr=joypad=0;rom=beatRom;
        await boot();setPaused(true,true);
        const ptr=core._malloc(bytes.length-40);
        try {
          core.HEAPU8.set(bytes.subarray(40),ptr);
          if(core._emulator_beat_load(instance,ptr,bytes.length-40))throw new Error('That beat could not be loaded. Your music is safe.');
        } finally {core._free(ptr);}
        if(core._emulator_observe_mem(instance,metadata.symbols.seqplaying)!==1)
          throw new Error('That shared beat does not contain a running sequence.');
        release();rebaseAudio();
        root.querySelectorAll('[data-runtime]').forEach(el=>el.disabled=false);
        tutorialStart.disabled=true;tutorialReopen.disabled=true;
        expanded(true);await resumePlayback();
        if(!running)message('Beat loaded! Tap RESUME to hear it.');
      } catch(error){if(beatParked)await returnToMyBeat();throw error;}
      finally{beatBusy=false;}
    },
    returnToMyBeat
  };
  pause.addEventListener('click', () => setPaused(running));
  restart.addEventListener('click', () => {
    if (tutorialActive) return;
    setPaused(true); persist(); boot();
  });
  mute.addEventListener('click', () => {
    muted = !muted;
    gain.gain.setValueAtTime(muted ? 0 : 0.65, audio.currentTime);
    mute.textContent = muted ? '♫ unmute' : '♫ mute';
    mute.setAttribute('aria-pressed', String(muted));
  });
  // Fixed-record saves suppress the new cartridge's song library. Keep them
  // recoverable without automatically installing them into the new ROM.
  try{
    const previous=LEGACY_SAVE_KEYS.map(key=>localStorage.getItem(key)).find(Boolean);
    if(previous){const data=JSON.parse(previous);if(Array.isArray(data)&&data.length===32768&&data.every(n=>Number.isInteger(n)&&n>=0&&n<=255)){
      const backup=document.createElement('button');backup.type='button';backup.textContent='download previous save';backup.title='Your older cartridge save is preserved separately.';
      backup.onclick=()=>{const href=URL.createObjectURL(new Blob([new Uint8Array(data)],{type:'application/octet-stream'})),a=document.createElement('a');a.href=href;a.download='GAYBOY-previous.sav';a.click();setTimeout(()=>URL.revokeObjectURL(href),1000);};
      root.querySelector('.demo-toolbar').append(backup);
    }}
  }catch{}
  exportSave.addEventListener('click', () => {
    if (tutorialActive) return;
    persist();
    const url = URL.createObjectURL(new Blob([ramBytes()], {type:'application/octet-stream'}));
    const link = document.createElement('a');
    link.href = url; link.download = 'GAYBOY-1.0.sav'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  canvas.addEventListener('keydown', event => {
    if (event.code === 'Escape' && !event.repeat) { setPaused(true); pause.focus(); return; }
    if (!keys[event.code] || !running) return;
    event.preventDefault(); input(keys[event.code], event.code, true);
  });
  window.addEventListener('keyup', event => {
    if (keys[event.code]) input(keys[event.code], event.code, false);
  });
  canvas.addEventListener('blur', release);
  root.querySelectorAll('[data-pad]').forEach(button => {
    const end = event => input(button.dataset.pad, 'pointer-' + event.pointerId, false);
    button.addEventListener('pointerdown', event => {
      if (!running) return;
      event.preventDefault(); button.setPointerCapture(event.pointerId);
      canvas.focus({preventScroll: true});
      input(button.dataset.pad, 'pointer-' + event.pointerId, true);
    });
    button.addEventListener('pointerup', end);
    button.addEventListener('pointercancel', end);
    button.addEventListener('lostpointercapture', end);
    button.addEventListener('keydown', event => {
      if (event.code === 'Space' || event.code === 'Enter') {
        event.preventDefault(); input(button.dataset.pad, 'button-key', true);
      }
    });
    button.addEventListener('keyup', event => {
      if (event.code === 'Space' || event.code === 'Enter') {
        event.preventDefault(); input(button.dataset.pad, 'button-key', false);
      }
    });
    button.addEventListener('blur', release);
  });
  window.addEventListener('blur', () => { if (running || resuming) setPaused(true); });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && instance) { rebuildAudio = true; setPaused(true); }
  });
  window.addEventListener('pagehide', () => {
    if (instance) { rebuildAudio = true; setPaused(true); }
    persist();
  });
  setInterval(persist, 1000);
})();

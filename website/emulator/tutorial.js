/* Guided practice against a checksum-pinned, unmodified GAYBOY ROM.
 * Demonstrations use joypad input. Only full emulator checkpoints reset tasks;
 * success is read from the ROM's live variables and note event pool. */
window.createGayboyTutorial = function(api) {
  'use strict';
  const panel = document.createElement('section');
  panel.className = 'demo-tutorial';
  panel.hidden = true;
  panel.tabIndex = 0;
  panel.setAttribute('aria-label', 'Interactive sequencer and mixer lessons');
  panel.innerHTML = `<div class="tutorial-heading"><strong>LEARN BY MAKING NOISE</strong><span class="tutorial-score"></span><button type="button" data-tour="close">exit</button></div>
    <progress aria-label="Completed lessons"></progress>
    <div class="tutorial-copy" aria-live="polite" aria-atomic="true"><div class="tutorial-meta"></div><h3></h3><p class="tutorial-description"></p><p class="tutorial-feedback"></p></div>
    <div class="tutorial-navigation"><button type="button" data-tour="replay">watch again</button><button type="button" data-tour="retry">reset</button><button type="button" data-tour="next" disabled>next lesson</button></div>`;
  api.handheld.before(panel);
  const sizeObserver = new ResizeObserver(() => {
    if (!panel.hidden) api.root.style.setProperty('--tutorial-height',panel.getBoundingClientRect().height+'px');
  });
  sizeObserver.observe(panel);
  let active = false, stage = 'idle', index = 0, score = 0, penalty = 0;
  let generation = 0, map, checkpoint = 0, clean = 0, carry = 0;
  let baseline, stableSince = 0, inputCount = 0, suspended = false, best = 0, lastProgress = '';
  let advanceAt = 0;
  const checkpoints = new Set();
  const el = selector => panel.querySelector(selector);
  const touchInstructions = window.matchMedia('(max-width: 590px), (pointer: coarse)');
  const instruction = text => touchInstructions.matches ? text
    .replace(/\s+\((?:Z|X|Shift|Space)\)/g, '')
    .replace(/ Keyboard:.*$/, '') : text;
  touchInstructions.addEventListener('change', () => {
    if (active && stage !== 'finished') draw();
  });
  const cancelled = () => new Error('Tutorial operation cancelled');
  const clock = () => api.ticks() / 4194.304;
  function read() {
    const byte = address => api.read(address);
    const word = address => byte(address) | byte(address + 1) << 8;
    const v = name => byte(map.symbols[name]);
    const events = track => {
      const count = word(map.symbols.seqeventcounts + track * 2);
      const offset = word(map.symbols.seqeventoffsets + track * 2);
      if (count > 512 || offset + count > 512) return [];
      return Array.from({length: count}, (_, i) => {
        const n = offset + i;
        const p = n < 256 ? map.symbols.seqevents_lo + n * 4 : map.symbols.seqevents_hi + (n - 256) * 4;
        return {step: byte(p), pitch: byte(p + 1) - 1, velocity: byte(p + 2), length: byte(p + 3) || 256};
      });
    };
    const tracks = Array.from({length:7}, (_, track) => events(track));
    return {page: v('page'), menu: v('navopen'), choice: v('navchoice'), playing: v('seqplaying'),
      pad: v('lastpad'), track: v('seqtrack'), pending: v('seqapending'), muted: v('seqmuted'), solo: v('seqsolo'),
      cursors: Array.from({length:7}, (_, i) => byte(map.symbols.seqcursor+i)),
      pitches: Array.from({length:7}, (_, i) => byte(map.symbols.seqpitch+i)),
      lengths: Array.from({length:7}, (_, i) => word(map.symbols.seqlength+i*2)),
      head: v('seqhead'), position: byte(map.symbols.seqposition), tracks,
      total: tracks.reduce((sum,notes)=>sum+notes.length,0),
      focus: byte(map.mixer + 4), edit: byte(map.mixer + 5),
      levels: Array.from({length:7}, (_, i) => byte(map.mixer+12+i)),
      pans: Array.from({length:7}, (_, i) => byte(map.mixer+19+i))};
  }
  async function wait(ms, token = generation) {
    const until = clock() + ms;
    while (clock() < until) {
      if (!active || token !== generation) throw cancelled();
      await new Promise(resolve => setTimeout(resolve, 20));
    }
    if (!active || token !== generation) throw cancelled();
  }
  async function until(test, timeout = 6000) {
    const start = clock();
    while (!test(read())) {
      if (clock() - start > timeout) throw new Error('The ROM did not reach the expected screen.');
      await wait(50);
    }
  }
  function highlight(pads = []) { api.highlight(pads); }
  const masks={right:1,left:2,up:4,down:8,A:16,B:32,select:64,start:128};
  async function press(button, down) {
    api.press(button,down);
    await until(s => !!(s.pad&masks[button])===down);
  }
  async function tap(button, times = 1, hold = null) {
    for (let i = 0; i < times; i++) {
      highlight(hold?[hold,button]:[button]);
      // Wait for the ROM to acknowledge each edge, instead of relying on
      // wall-clock taps that can disappear during a long banked render.
      await press(button,true); await press(button,false); await wait(180);
    }
  }
  async function chord(hold, button, times = 1) {
    highlight([hold]); await press(hold,true);
    await tap(button,times,hold);
    await press(hold,false); await wait(180);
  }
  async function menu(page) {
    highlight(['start']); await press('start',true);
    for (let n = 0; read().choice !== page && n < 24; n++) await tap('down',1,'start');
    if (read().choice !== page) throw new Error('Could not find the requested ROM menu page.');
    await press('start',false); await wait(250);
    await until(s => s.page === page && !s.menu);
  }
  function save() {
    const ptr = api.snapshot();
    if (!ptr) throw new Error('Could not create a practice checkpoint.');
    checkpoints.add(ptr); return ptr;
  }
  function restore(ptr) { api.release(); api.restore(ptr); stableSince = 0; }
  function discard(ptr) { if (checkpoints.delete(ptr)) api.deleteSnapshot(ptr); }
  async function gridSetup() { await menu(8); }
  async function melodicSetup() { await gridSetup(); if(read().track===6) await chord('select','right'); }
  async function cell(step, pitch) {
    const c = read().track;
    for (let n=0;read().cursors[c]!==step && n<256;n++) await tap('right');
    for (let n=0;read().pitches[c]!==pitch && n<160;n++) await tap(read().pitches[c]<pitch?'up':'down');
    if (read().head) await tap(read().head===6?'right':read().head===5?'up':'down');
    if (read().pitches[c]!==pitch || read().head) throw new Error('Could not position the demonstration cursor.');
  }
  async function addNotes(count) {
    if(read().track===6) await chord('select','right');
    const c=read().track;
    for (let i=0;i<count;i++) {
      const s=read(), notes=s.tracks[c], used=new Set(notes.map(n=>n.step));
      let target=null;
      for(const pitch of [s.pitches[c],s.pitches[c]+1,s.pitches[c]-1,s.pitches[c]+2]){
        if(pitch<0||pitch>127)continue;
        const free=Array.from({length:s.lengths[c]},(_,n)=>n).filter(step=>!used.has(step)&&!notes.some(n=>n.pitch===pitch&&step>=n.step&&step<n.step+n.length));
        if(free.length){target={step:free[Math.min(i,free.length-1)],pitch};break;}
      }
      if (!target) throw new Error('No empty steps available for the demonstration.');
      await cell(target.step,target.pitch); await tap('B');
    }
  }
  async function selectNote() {
    const s=read(),track=s.tracks.findIndex((notes,c)=>c<6&&notes.length>0);
    if(track<0)throw new Error('This lesson needs a note from the earlier lessons.');
    for(let n=0;read().track!==track&&n<7;n++)await chord('select','right');
    const chosen=read().tracks[track][0];
    await cell(chosen.step,chosen.pitch); return chosen;
  }
  async function mixerSetup() { await menu(18); }
  const grid = s => s.page === 8 && !s.menu && !s.pending;
  const changed = (before,after) => after.some((v,i)=>v!==before[i]);
  const lessons = [
    {title:'Start the groove',pads:['select','A'],setup:gridSetup,
      demo:async()=>{await chord('select','A');await wait(900);},
      watch:'A C2 note is ready. Watch: hold SELECT and tap A, then release both. Hear it loop.',
      task:'Start the C2 groove: hold the highlighted SELECT button and tap A, then release both. Keyboard: hold Space and tap X.',
      goal:s=>grid(s)&&!!s.playing,praise:'Your C2 groove is playing! Playback carries on as you learn.'},
    {title:'Plot your own notes',pads:['up','down','left','right','B'],setup:gridSetup,
      demo:async()=>addNotes(1),watch:'Keep the groove going. Watch: choose an empty cell with the D-pad and tap B to add a note while it plays.',
      task:'Add a note while the groove plays: D-pad to any empty cell, B (Z) to place it. Choose your own pitch and rhythm. Keep adding notes even after you pass.',
      goal:s=>grid(s)&&!!s.playing&&s.tracks.slice(0,6).some((notes,c)=>notes.length>baseline.tracks[c].length),praise:'Your note joined the groove! Keep making it yours.'},
    {title:'Add four more notes',pads:['up','down','left','right','B'],setup:gridSetup,
      demo:async()=>addNotes(4),watch:'Watch: I am adding four notes in empty places while your loop plays. Your melody can be completely different.',
      task:'Your turn: add four more notes anywhere. Choose your own pitches and rhythm. Keep your existing notes.',
      goal:s=>grid(s)&&s.total>=baseline.total+4,praise:'Four more notes, your own melody. Keep that creativity going.'},
    {title:'Try another instrument',pads:['select','right','B','up','down','left'],setup:gridSetup,
      demo:async()=>{await chord('select','right');await addNotes(4);},
      watch:'Watch: hold SELECT and tap Right to change instrument, release, then place four notes with B.',
      task:'Goal: switch to a different instrument with SELECT + Left/Right, then plot four new notes on it with B. Choose any pitches and steps.',
      goal:s=>grid(s)&&s.track!==baseline.track&&s.tracks[s.track].length>=baseline.tracks[s.track].length+4,
      praise:'Another instrument, another layer. This is becoming your track.'},
    {title:'Make a note longer',pads:['B','right','up','down','left'],setup:melodicSetup,
      demo:async()=>{await selectNote();await chord('B','right',2);},
      watch:'Watch: move onto a note, hold B and tap Right to stretch it. Release B when it is long enough.',
      task:'Your turn: find any note. Hold B (Z) and tap Right to make it longer, then release. Any longer length counts.',
      goal:s=>grid(s)&&s.total===baseline.total&&s.tracks.some((notes,c)=>notes.some(n=>baseline.tracks[c].some(b=>b.step===n.step&&b.pitch===n.pitch&&n.length>b.length))),
      praise:'Nice sustain. You shaped the rhythm your way.'},
    {title:'Move a note',pads:['A','up','down','left','right'],setup:melodicSetup,
      demo:async()=>{await selectNote();await chord('A','up');},
      watch:'Watch: hold A on an existing note and use the D-pad to move it. Up/Down changes pitch; Left/Right changes time.',
      task:'Your turn: hold A (X) on any note and move it with the D-pad, then release. Choose the new pitch or time yourself.',
      goal:s=>grid(s)&&s.total===baseline.total&&s.tracks.some((notes,c)=>notes.some(n=>!baseline.tracks[c].some(b=>b.step===n.step&&b.pitch===n.pitch))),
      praise:'Clean move. You can reshape a melody without starting over.'},
    {title:'Erase one note',pads:['B','up','down','left','right'],setup:gridSetup,
      demo:async()=>{await selectNote();await tap('B');},watch:'Watch: a quick B tap on an existing note erases it. Holding B is for stretching.',
      task:'Your turn: choose any existing note and tap B (Z) to erase it. Your choice which one goes.',
      goal:s=>grid(s)&&s.total===baseline.total-1,praise:'Edited with intention. Sometimes a little space is what a loop needs.'},
    {title:'Take it to the mixer',pads:['start','down'],setup:gridSetup,
      demo:async()=>menu(18),watch:'Watch: hold START, tap Down until MIXER is highlighted, then release START.',
      task:'Your turn: hold START (Shift), find MIXER with Up/Down, then release START. Your pattern comes with you.',
      goal:s=>s.page===18&&!s.menu,praise:'Welcome to the control room. Let us mix your pattern.'},
    {title:'Mute a track',pads:['down','right','left','A'],setup:mixerSetup,
      demo:async()=>{await tap('down');await tap('A');},watch:'Watch: Down selects M on the first channel. A toggles mute. Left/Right chooses another channel.',
      task:'Your turn: Down to M, choose any channel with Left/Right, then A (X) to toggle its mute.',
      goal:s=>s.page===18&&!s.menu&&s.muted!==baseline.muted,praise:'Muted. You can drop parts in and out of your performance.'},
    {title:'Solo a track',pads:['down','right','left','A'],setup:mixerSetup,
      demo:async()=>{await tap('down',2);await tap('A');},watch:'Watch: Down twice selects S. A solos the channel. Left/Right chooses which channel.',
      task:'Your turn: Down twice to S, choose any channel, then A (X) to toggle solo.',
      goal:s=>s.page===18&&!s.menu&&s.solo!==baseline.solo,praise:'Solo found. Now you can focus on an individual part.'},
    {title:'Change a channel volume',pads:['down','up','right','left','A'],setup:mixerSetup,
      demo:async()=>{await tap('down',3);await tap('A');await tap('down',4);await tap('A');},
      watch:'Watch: Down three times to VOL, A to edit, Up/Down changes the level, A finishes editing.',
      task:'Your turn: Down x3 to VOL. Choose any channel with Left/Right. A, Up/Down to change its volume, then A to finish. Any different level counts.',
      goal:s=>s.page===18&&!s.menu&&!s.edit&&changed(baseline.levels,s.levels),praise:'Your mix, your balance. That volume change counts!'},
    {title:'Move a sound in stereo',pads:['down','up','left','right','A'],setup:mixerSetup,
      demo:async()=>{await tap('down',4);await tap('A');await tap('down');await tap('A');},
      watch:'Watch: Down four times to PAN, A to edit, Up/Down changes routing, A finishes. LR is both ears, L is left, R is right.',
      task:'Your turn: Down x4 to PAN, choose any channel, A to edit. Change its stereo setting with Up/Down, then A to finish.',
      goal:s=>s.page===18&&!s.menu&&!s.edit&&changed(baseline.pans,s.pans),praise:'You did it. Sequencer, instruments and mixer - all with your own music!'}
  ];
  function draw() {
    const lesson = lessons[index];
    el('progress').max = lessons.length;
    el('progress').value = index + (stage === 'passed' ? 1 : 0);
    el('.tutorial-score').textContent = `${score} / ${lessons.length * 100} pts`;
    el('.tutorial-meta').textContent = `LESSON ${index + 1}/${lessons.length} · ${stage === 'demo' ? 'WATCH ME' : stage === 'practice' ? 'YOUR TURN' : stage === 'passed' ? 'NAILED IT' : stage === 'setup' ? 'GETTING READY' : stage === 'error' ? 'TRY AGAIN' : 'PAUSED'}`;
    el('h3').textContent = lesson.title;
    el('.tutorial-description').textContent = instruction(stage === 'demo' ? lesson.watch : stage === 'setup' ? 'Setting up a fresh practice screen in the ROM…' : lesson.task);
    el('[data-tour="next"]').disabled = stage !== 'passed';
    el('[data-tour="next"]').textContent = stage === 'passed' ? index === lessons.length - 1 ? 'see my score' : 'next lesson' : 'next lesson';
    for (const action of ['replay','retry']) el(`[data-tour="${action}"]`).disabled = stage !== 'practice';
    panel.dataset.stage = stage; panel.dataset.lesson = String(index + 1);
    api.root.classList.toggle('tutorial-demonstrating', ['demo','setup'].includes(stage));
  }
  function feedback(text) { el('.tutorial-feedback').textContent = instruction(text); }
  function failure(error) {
    if (!active || error.message === 'Tutorial operation cancelled') return;
    ++generation; api.release(); stage = 'error'; draw();
    feedback('The practice session stopped. Exit and start the tutorial again to retry.');
    console.error('GAYBOY tutorial:', error);
  }
  async function teach() {
    ++generation; api.release(); stage = 'setup'; draw(); api.root.scrollTop=0;
    feedback('A demonstration first. Your practice screen resets immediately afterwards.');
    if (checkpoint) { discard(checkpoint); checkpoint = 0; }
    restore(carry);
    await lessons[index].setup(); await wait(250);
    checkpoint = save(); baseline = read();
    stage = 'demo'; draw(); await wait(450);
    await lessons[index].demo(); await wait(250);
    if (!lessons[index].goal(read())) throw new Error(`Demonstration failed its ROM check: ${lessons[index].title}`);
    feedback('That is the result. Now I am clearing the demonstration so you can do it.');
    await wait(1000);
    restore(checkpoint); await wait(100);
    stage = 'practice'; inputCount = 0; stableSince = 0; lastProgress=''; api.root.scrollTop=0;
    highlight(lessons[index].pads); draw();
    feedback(`Up to ${Math.max(40,100-penalty)} pts. Replay -15, reset -10. No timer.`);
    panel.focus({preventScroll:true});
  }
  async function start(metadata) {
    map = metadata; suspended = false; active = true; stage = 'setup'; index = score = penalty = 0;
    panel.hidden = false; api.root.classList.add('tutorial-active');
    api.expand(true); api.root.scrollTop = 0;
    try { best = Number(localStorage.getItem('gayboy-tutorial-best-v2')) || 0; } catch {}
    draw(); feedback('Booting a separate practice cartridge. Your music is waiting safely outside this lesson.');
    try {
      // The real intro is skipped with START, never by changing ROM variables.
      await wait(3000); await tap('start'); await wait(450);
      await until(s => api.read(map.mixer) === 0xD3 && !s.menu, 10000);
      await menu(8);
      for (let n=0;read().track!==0 && n<7;n++) await chord('select','right');
      if (read().track!==0) throw new Error('Could not open the first instrument.');
      // Seed a real C2 note through the same controls the learner uses.
      // seq_name labels MIDI pitch 36 as C2; event storage encodes pitch + 1.
      await cell(0,36); await tap('B');
      clean = save(); carry = clean; await teach();
    } catch (error) { failure(error); }
  }
  function poll() {
    if (active && stage === 'passed' && api.running() && clock() >= advanceAt) {
      advanceLesson(); return;
    }
    if (!active || stage !== 'practice' || !api.running()) return;
    const state = read();
    if(state.track>=state.tracks.length)return;
    if (index === 2) {
      const added=Math.max(0,state.total-baseline.total), progress=`notes:${added}`;
      el('.tutorial-meta').textContent = `LESSON 3/${lessons.length} · ${Math.min(4,added)}/4 NOTES`;
      if(progress!==lastProgress){lastProgress=progress;feedback(`${Math.min(4,added)}/4 more notes added. Choose pitches and steps you like.`);}
    }
    if(index === 3 && state.track!==baseline.track){
      const added=Math.max(0,state.tracks[state.track].length-baseline.tracks[state.track].length), progress=`track:${state.track}:${added}`;
      el('.tutorial-meta').textContent = `LESSON 4/${lessons.length} · ${Math.min(4,added)}/4 NOTES`;
      if(progress!==lastProgress){lastProgress=progress;feedback(`New instrument selected. ${Math.min(4,added)}/4 notes added on this track.`);}
    } else if (index === 3) {
      el('.tutorial-meta').textContent = `LESSON 4/${lessons.length} · SWITCH INSTRUMENT`;
    }
    // Require a stable ROM result after the learner releases every control.
    if (!api.held() && inputCount && lessons[index].goal(state)) {
      if (!stableSince) stableSince = clock();
      if (clock() - stableSince < 180) return;
      const earned = Math.max(40,100-penalty); score += earned; stage = 'passed';
      advanceAt = clock() + 3500;
      api.release(); highlight([]); draw();
      feedback(`Lesson complete! +${earned} points. ${lessons[index].praise} ${index === lessons.length - 1 ? 'Your score is coming up…' : 'Next lesson coming up…'}`);
    } else stableSince = 0;
  }
  function learnerInput() {
    if (stage === 'practice') {
      inputCount++;
      if (inputCount === 18 || inputCount % 35 === 0) feedback('Keep going. Try the action above, or use “show me again” for another demonstration.');
    }
  }
  function finish() {
    stage = 'finished'; ++generation; api.release(); highlight([]);
    best = Math.max(best,score);
    try { localStorage.setItem('gayboy-tutorial-best-v2',String(best)); } catch {}
    el('progress').value = lessons.length;
    el('.tutorial-meta').textContent = 'COURSE COMPLETE · 12/12';
    el('h3').textContent = score >= 1100 ? 'Tiny studio superstar.' : 'You made it. Keep making noise.';
    el('.tutorial-description').textContent = `You earned ${score}/${lessons.length*100} points. Personal best: ${best}. Every lesson was completed in the running ROM.`;
    feedback('100 points per lesson. Each practice reset costs 10; another demonstration costs 15. Minimum 40 per lesson. No speed penalties.');
    el('[data-tour="next"]').disabled = false;
    el('[data-tour="next"]').textContent = 'return to my music';
    for (const action of ['retry','replay']) el(`[data-tour="${action}"]`).disabled = true;
    api.root.classList.remove('tutorial-demonstrating'); panel.dataset.stage = stage;
  }
  async function close() {
    active = false; suspended = false; ++generation; api.release(); highlight([]);
    checkpoints.forEach(ptr => api.deleteSnapshot(ptr)); checkpoints.clear();
    clean = carry = checkpoint = 0; panel.hidden = true;
    api.root.classList.remove('tutorial-active','tutorial-demonstrating');
    await api.exit();
  }
  function advanceLesson() {
    if (stage !== 'passed') return;
    if (index === lessons.length - 1) { finish(); return; }
    if (carry && carry !== clean) discard(carry);
    carry = save(); index++; penalty = 0; teach().catch(failure);
  }
  panel.addEventListener('click', event => {
    const action = event.target.closest('[data-tour]')?.dataset.tour;
    if (!action) return;
    if (action === 'close' || (action === 'next' && stage === 'finished')) { close().catch(failure); return; }
    if (action === 'next' && stage === 'passed') {
      advanceLesson();
    } else if (action === 'replay' && stage === 'practice') {
      penalty += 15; teach().catch(failure);
    } else if (action === 'retry' && stage === 'practice') {
      penalty += 10; restore(checkpoint); inputCount = 0; lastProgress=''; highlight(lessons[index].pads);
      feedback(`Clean slate. You have got this. Up to ${Math.max(40,100-penalty)} points this try.`);
      panel.focus({preventScroll:true});
    }
  });
  panel.addEventListener('keydown', event => {
    if (event.target === panel) api.keydown(event);
  });
  panel.addEventListener('blur', () => api.release());
  return {start, close, poll, panel, learnerInput,
    acceptsInput: () => active && ['practice','passed'].includes(stage),
    focus: () => { api.root.scrollTop=0; panel.focus({preventScroll:true}); },
    suspend() {
      if (!active || !['setup','demo'].includes(stage)) return;
      suspended = true; ++generation; api.release(); stage = 'paused'; draw();
      feedback('Paused. Resume the emulator to watch this demonstration from the beginning.');
    },
    resume() {
      if (!suspended || !active) return;
      suspended = false;
      if (!clean) { start(map); return; }
      teach().catch(failure);
    }
  };
};

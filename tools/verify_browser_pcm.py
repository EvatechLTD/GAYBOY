"""Play overlapping samples through the real site's UI and check audio delivery."""
from pathlib import Path
import json
import sys
import wave
import numpy as np
from playwright.sync_api import sync_playwright, expect
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:18975/'
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True)
 page=b.new_page(viewport={'width':1440,'height':1200})
 errors=[]
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.add_init_script('''
 window.qaCapture=false;window.qaBuffers=[];window.qaTimes=[];
 const original=AudioContext.prototype.createBufferSource;
 AudioContext.prototype.createBufferSource=function(...args){
  const source=original.apply(this,args),start=source.start;
  source.start=function(...args){
   if(window.qaCapture&&source.buffer){
    window.qaBuffers.push(Array.from(source.buffer.getChannelData(0)));
    window.qaTimes.push({at:args[0],duration:source.buffer.duration,rate:source.buffer.sampleRate});
   }return start.apply(this,args);
  };return source;
 };
 ''')
 page.goto(URL,wait_until='networkidle')
 page.add_script_tag(url=URL+'emulator/sameboy.js')
 page.evaluate('''()=>{const factory=SameBoyCore;window.SameBoyCore=async(...args)=>{
   const module=await factory(...args);window.qaCore=module;
   const create=module._emulator_new_simple;
   module._emulator_new_simple=(...args)=>{window.qaInstance=create(...args);return qaInstance;};
   return module;
 };}''')
 page.locator('#demo-play').click()
 expect(page.locator('#live-demo')).to_have_class('panel demo-panel demo-started',timeout=20000)
 page.wait_for_timeout(4500)
 page.keyboard.down('Shift');page.wait_for_timeout(1800)
 page.keyboard.up('Shift');page.wait_for_timeout(1300)
 metadata=page.evaluate("async()=>await(await fetch('emulator/tutorial-rom.json')).json()")
 page.evaluate('(m)=>window.qaMap=m',metadata)
 # Navigate from the actual current instrument, rather than assuming Pulse 1.
 for _ in range(7):
  if page.evaluate('qaCore._emulator_observe_mem(qaInstance,qaMap.symbols.seqtrack)')==6:break
  page.keyboard.down('Space');page.wait_for_timeout(160)
  page.keyboard.press('ArrowRight',delay=180);page.keyboard.up('Space');page.wait_for_timeout(800)
 assert page.evaluate('qaCore._emulator_observe_mem(qaInstance,qaMap.symbols.seqtrack)')==6
 page.keyboard.press('z',delay=180);page.wait_for_timeout(400)
 # A second sample on the same step exercises two simultaneous PCM voices.
 for _ in range(3):page.keyboard.press('ArrowDown',delay=180);page.wait_for_timeout(200)
 page.keyboard.press('z',delay=180);page.wait_for_timeout(400)
 page.keyboard.down('Space');page.wait_for_timeout(160)
 page.keyboard.press('x',delay=180);page.keyboard.up('Space');page.wait_for_timeout(700)
 page.evaluate('()=>{qaCapture=true;qaStartTicks=qaCore._emulator_get_ticks_f64(qaInstance);qaStartTime=performance.now();}')
 page.wait_for_timeout(5000)
 state=page.evaluate('''()=>({buffers:qaBuffers,times:qaTimes,
   rate:qaTimes[0].rate,emulated:(qaCore._emulator_get_ticks_f64(qaInstance)-qaStartTicks)/4194304,
   elapsed:(performance.now()-qaStartTime)/1000,
   waveFrequency:qaCore._emulator_get_wave_frequency(qaInstance)})''')
 page.locator('#live-demo canvas').screenshot(path=str(ROOT/'build/sameboy-actual-drums.png'))
 audio=np.concatenate(state.pop('buffers'))
 times=state.pop('times')
 gaps=[times[i]['at']-(times[i-1]['at']+times[i-1]['duration']) for i in range(1,len(times))]
 assert np.ptp(audio)>.05,'Sample output is silent or too quiet'
 assert np.max(np.abs(audio))<1,'Sample output clipped'
 assert max(map(abs,gaps),default=0)<0.0001,('Discontinuous audio schedule',max(gaps))
 assert .95<state['emulated']/state['elapsed']<1.05,('Emulation did not keep real time',state)
 assert state['waveFrequency'] in (0x749,0x750),'PCM wave-channel mode did not start'
 page.locator('#live-demo canvas').focus()
 assert page.locator('#live-demo canvas').evaluate('e=>getComputedStyle(e).outlineStyle')=='none'
 assert page.locator('.demo-screen').evaluate('e=>parseFloat(getComputedStyle(e).outlineOffset)')>=5
 assert not errors,errors
 out=ROOT/'build/web-audio/actual-drums.wav'
 with wave.open(str(out),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(state['rate'])
  w.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
 state.update({'url':URL,'audio_peak':float(np.max(np.abs(audio))),
  'max_scheduled_gap_ms':max(map(abs,gaps),default=0)*1000,'focus_outline':'outside bezel',
  'browser_errors':errors})
 (ROOT/'build/web-audio/actual-drums.json').write_text(json.dumps(state,indent=2))
 print(json.dumps(state,indent=2));b.close()

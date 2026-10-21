"""Render all four hardware shades and simulate phone sleep/audio interruption."""
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright, expect
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:18976/'
OUT=Path(__file__).resolve().parents[1]/'build'
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
 page=context.new_page()
 errors=[]
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.add_init_script('''
 window.qaContexts=[];window.qaHidden=false;window.qaRejectNextResume=false;
 Object.defineProperty(document,'hidden',{get:()=>qaHidden});
 const NativeAudioContext=window.AudioContext;
 window.AudioContext=class extends NativeAudioContext {
  constructor(...args){super(...args);qaContexts.push(this);}
  get state(){return this.qaInterrupted?'interrupted':super.state;}
  resume(){
   if(this.qaInterrupted)return Promise.reject(new Error('Simulated iOS interruption'));
   if(qaRejectNextResume){qaRejectNextResume=false;return Promise.reject(new Error('Simulated resume failure'));}
   return super.resume();
  }
 };
 ''')
 page.goto(URL,wait_until='networkidle')
 page.add_script_tag(url=URL+'emulator/sameboy.js')
 shades=page.evaluate('''async(base)=>{
  const m=await SameBoyCore({locateFile:name=>base+'emulator/'+name});
  const rom=new Uint8Array(await(await fetch(base+'downloads/GAYBOY-0.3.gb')).arrayBuffer());
  rom.set([0xc3,0x50,0x01],0x100);rom.set([0xf3,0x18,0xfd],0x150);
  const ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);
  const e=m._emulator_new_simple(ptr,rom.length,48000,2048,2);
  m._emulator_set_bw_palette_simple(e,0,0xffffffff,0xffaaaaaa,0xff555555,0xff000000);
  function run(t){let event;do{event=m._emulator_run_until_f64(e,t)}while(!(event&4));}
  run(4194304*3);
  const write=(a,v)=>m._emulator_write_mem(e,a,v);
  write(0xff40,0);
  for(let y=0;y<8;y++){write(0x8000+y*2,0x33);write(0x8001+y*2,0x0f);}
  for(let i=0;i<1024;i++)write(0x9800+i,0);
  write(0xff42,0);write(0xff43,0);write(0xff47,0xe4);write(0xff40,0x91);
  run(4194304*3+70224*4);
  const bytes=Array.from(m.HEAPU8.slice(m._get_frame_buffer_ptr(e),m._get_frame_buffer_ptr(e)+32));
  m._emulator_delete(e);m._free(ptr);
  return [0,2,4,6].map(x=>bytes.slice(x*4,x*4+4));
 }''',URL)
 assert shades==[[255,255,255,255],[170,170,170,255],[85,85,85,255],[0,0,0,255]],shades
 page.evaluate('''()=>{const factory=SameBoyCore;window.SameBoyCore=async(...args)=>{
  const m=await factory(...args);window.qaCore=m;const create=m._emulator_new_simple;
  m._emulator_new_simple=(...args)=>{window.qaInstance=create(...args);return qaInstance;};return m;
 };}''')
 page.locator('#demo-play').tap()
 expect(page.locator('#live-demo')).to_have_class('panel demo-panel demo-started demo-expanded',timeout=20000)
 page.wait_for_timeout(3500)
 original=page.evaluate('qaInstance')
 for interruption in ['hidden','interrupted','resume-rejection']:
  if interruption=='hidden':
   page.evaluate("()=>{qaHidden=true;document.dispatchEvent(new Event('visibilitychange'));}")
  else:
   page.evaluate("()=>{const c=qaContexts.at(-1);c.qaInterrupted=true;c.dispatchEvent(new Event('statechange'));}")
  expect(page.locator('.demo-resume-overlay')).to_be_visible()
  expect(page.locator('#demo-pause')).to_have_attribute('aria-pressed','true')
  ticks=page.evaluate('qaCore._emulator_get_ticks_f64(qaInstance)')
  page.wait_for_timeout(200)
  assert page.evaluate('qaCore._emulator_get_ticks_f64(qaInstance)')==ticks
  page.evaluate("()=>{qaHidden=false;document.dispatchEvent(new Event('visibilitychange'));}")
  contexts=page.evaluate('qaContexts.length')
  if interruption=='resume-rejection':page.evaluate('qaRejectNextResume=true')
  page.locator('.demo-resume-overlay').tap()
  if interruption=='resume-rejection':
   expect(page.locator('.demo-status')).to_contain_text('another tap')
   expect(page.locator('.demo-resume-overlay')).to_be_visible()
   page.locator('.demo-resume-overlay').tap()
  expect(page.locator('.demo-resume-overlay')).to_be_hidden()
  expect(page.locator('#demo-pause')).to_have_attribute('aria-pressed','false')
  page.wait_for_timeout(250)
  assert page.evaluate('qaInstance')==original,'Emulator was reset on resume'
  assert page.evaluate('qaCore._emulator_get_ticks_f64(qaInstance)')>ticks
  assert page.evaluate('qaContexts.length')>contexts
  assert page.evaluate('qaContexts.at(-1).state')=='running'
 page.screenshot(path=str(OUT/'palette-recovery-mobile.png'))
 assert not errors,errors
 print(json.dumps({'url':URL,'shades':'all four exact RGBA values in correct order',
   'phone_sleep':'pause then user-tap recovery preserves GB instance',
   'iOS_interruption':'fresh audio context, GB instance preserved',
   'rejected_resume':'retry works without reload','browser_errors':[]}))
 browser.close()

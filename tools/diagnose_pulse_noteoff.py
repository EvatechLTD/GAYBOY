"""Isolate a DMG pulse note-off DAC click in the production SameBoy core."""
from functools import partial
from http.server import ThreadingHTTPServer
import threading,json,wave
import numpy as np
from playwright.sync_api import sync_playwright
from record_sameboy import ROOT,QuietHandler
rom=bytearray((ROOT/'build/GAYBOY.gb').read_bytes())
rom[0x100:0x103]=bytes.fromhex('c3 50 01');rom[0x150:0x153]=bytes.fromhex('f3 18 fd')
server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'website')))
threading.Thread(target=server.serve_forever,daemon=True).start()
out=ROOT/'build/pulse-diagnostics';out.mkdir(exist_ok=True)
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='chrome',headless=True);page=browser.new_page()
  page.goto(f'http://127.0.0.1:{server.server_port}/__capture_blank__.html');page.add_script_tag(url=f'http://127.0.0.1:{server.server_port}/emulator/sameboy.js')
  results=[]
  for tag,cutoff in [('dac-left-on',-1),('gate90-dac-off',.426),('gate100-dac-off',.474),('gate90-length-off',.426),('gate100-length-off',.474),('gate90-zero-trigger',.426),('gate100-zero-trigger',.474)]:
   data=page.evaluate('''async({rom,cutoff,tag})=>{
    const m=await SameBoyCore(),ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);
    const e=m._emulator_new_simple(ptr,rom.length,48000,1024,2);let captured=[];
    function run(t){let event;do{event=m._emulator_run_until_f64(e,t);if(event&2){
      const d=new Int16Array(m.HEAPU8.buffer,m._get_audio_buffer_ptr(e),2048);
      for(let i=0;i<2048;i++)captured.push(d[i]);}}while(!(event&4));}
    const write=(a,v)=>m._emulator_write_mem(e,a,v);
    run(4194304*3);write(0xff26,0);write(0xff26,128);write(0xff24,0x77);write(0xff25,0x22);
    write(0xff16,0x80);write(0xff17,0x51);write(0xff18,0x16);write(0xff19,0x84);
    const begin=m._emulator_get_ticks_f64(e);captured=[];
    if(cutoff>0){run(begin+cutoff*4194304);if(tag.includes('length')){write(0xff16,0xbf);write(0xff19,0x44);}else if(tag.includes('zero-trigger')){write(0xff17,8);write(0xff19,0x80);}else write(0xff17,0);}
    run(begin+4194304);m._emulator_delete(e);m._free(ptr);return captured;
   }''',{'rom':list(rom),'cutoff':cutoff,'tag':tag})
   x=np.asarray(data,dtype='<i2').reshape(-1,2)
   with wave.open(str(out/(tag+'.wav')),'wb') as w:w.setparams((2,2,48000,0,'NONE','not compressed'));w.writeframes(x.tobytes())
   # The shared partial buffer at the start changes the origin by <=21 ms.
   late=x[int(.30*48000):int(.60*48000)].astype(float)
   results.append({'fixture':tag,'late_peak':int(np.abs(late).max()),'late_rms':round(float(np.sqrt(np.mean(late*late))),2)})
  browser.close()
 (out/'report.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
finally:server.shutdown();server.server_close()

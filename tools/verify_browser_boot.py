"""Verify the browser core hands off before any boot logo can be displayed."""
import json
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:18980/'
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page()
    page.goto(URL,wait_until='networkidle')
    page.add_script_tag(url=URL+'emulator/sameboy.js')
    result=page.evaluate('''async base=>{
      const m=await SameBoyCore({locateFile:n=>base+'emulator/'+n});
      const rom=new Uint8Array(await(await fetch(base+'downloads/GAYBOY-tutorial.gb')).arrayBuffer());
      const ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);
      const e=m._emulator_new_simple(ptr,rom.length,48000,2048,2);
      if(!e)throw new Error('Cartridge failed to initialize');
      const pixels=new Uint32Array(m.HEAPU8.buffer,m._get_frame_buffer_ptr(e),160*144);
      const result={bootUnmapped:!!m._emulator_observe_mem(e,0xff50),
        cartridgeHasLCD:!(m._emulator_observe_mem(e,0xff40)&128),
        noLogoFrame:Array.from(pixels).every(p=>p===0xffa1e8d5),
        noBootAudio:m._get_audio_buffer_capacity(e)===0,
        startsAtZero:m._emulator_get_ticks_f64(e)===0};
      m._emulator_delete(e);m._free(ptr);return result;
    }''',URL)
    assert all(result.values()),result
    print(json.dumps(result))
    browser.close()

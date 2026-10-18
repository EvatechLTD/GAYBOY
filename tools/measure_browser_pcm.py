"""Compare real sample packets and constant-DC PCM refresh in browser cores.

The disposable ROM only idles; the same timed register writes feed each APU.
This isolates emulation from the website's scheduling and GUI.
"""
from pathlib import Path
import json
import math
import wave
import numpy as np
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/web-audio/measurements'
OUT.mkdir(parents=True,exist_ok=True)
rom=bytearray((ROOT/'website/downloads/GAYBOY-0.3.gb').read_bytes())
rom[0x100:0x103]=bytes([0xc3,0x50,0x01]);rom[0x150:0x153]=bytes([0xf3,0x18,0xfd])
sample=list(rom[16*16384:16*16384+816])
SCRIPT=r"""async ({rom,packets,factory})=>{
 const m=await window[factory]();
 const ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);
 const e=m._emulator_new_simple(ptr,rom.length,48000,1024,2);
 m._emulator_set_default_joypad_callback(e,m._joypad_new());
 let captured=[];
 function run(t){let event;do{
  event=m._emulator_run_until_f64(e,t);
  if(event&2){
   const values=factory==='SameBoyCore' ? new Int16Array(m.HEAPU8.buffer,m._get_audio_buffer_ptr(e),2048) :
     new Uint8Array(m.HEAPU8.buffer,m._get_audio_buffer_ptr(e),2048);
   for(let i=0;i<2048;i+=2)captured.push(values[i]);
  }
 }while(!(event&4));}
 const write=(addr,value)=>m._emulator_write_mem(e,addr,value);
 run(4194304*3);captured=[];
 write(0xff26,0x80);write(0xff24,0x77);write(0xff25,0x44);
 write(0xff12,0);write(0xff17,0);write(0xff21,0);
 const begin=m._emulator_get_ticks_f64(e);
 for(let block=0;block<300;block++){
  const start=begin+block*11712;
  run(start);write(0xff25,0);
  run(start+12);write(0xff1a,0);
  for(let j=0;j<16;j++){run(start+24+j*20);write(0xff30+j,packets[(block*16+j)%packets.length]);}
  run(start+344);write(0xff1a,0x80);
  run(start+364);write(0xff1b,0);write(0xff1c,0x20);write(0xff1d,0x49);
  run(start+400);write(0xff1e,0x87);
  run(start+412);write(0xff25,0x44);
 }
 run(begin+300*11712);
 m._emulator_delete(e);m._free(ptr);
 return captured;
} """
results=[]
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True)
 page=b.new_page();page.goto('http://127.0.0.1:18975/')
 for filename in ['binjgb.js','sameboy.js']:page.add_script_tag(url='http://127.0.0.1:18975/emulator/'+filename)
 for fixture,packets in [('flat8',[0x88]*16),('sample',sample)]:
  for factory in ['Binjgb','SameBoyCore']:
   values=page.evaluate(SCRIPT,{'rom':list(rom),'packets':packets,'factory':factory})
   x=np.array(values,dtype=float)
   if factory=='Binjgb':x=x/255
   else:x=x/32768
   x=x[4800:];x-=x.mean()
   spectrum=np.abs(np.fft.rfft(x*np.hanning(len(x))))
   frequencies=np.fft.rfftfreq(len(x),1/48000)
   peak=int(np.argmax(spectrum[1:])+1)
   item={'fixture':fixture,'core':factory,'RMS':float(np.sqrt(np.mean(x*x))),'peak_hz':float(frequencies[peak])}
   results.append(item)
   with wave.open(str(OUT/(factory+'-'+fixture+'.wav')),'wb') as wav:
    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(48000)
    wav.writeframes((np.clip(x*2,-1,1)*32767).astype('<i2').tobytes())
 b.close()
(OUT/'report.json').write_text(json.dumps(results,indent=2))
baseline=next(r['RMS'] for r in results if r['fixture']=='flat8' and r['core']=='Binjgb')
improved=next(r['RMS'] for r in results if r['fixture']=='flat8' and r['core']=='SameBoyCore')
assert improved<baseline*.15, 'PCM refresh noise did not improve sufficiently'
print('Constant-value PCM noise reduction (dB):',round(20*math.log10(baseline/improved),2))
print(json.dumps(results,indent=2))

"""Capture the unchanged hardware demo with one/both pulses in SameBoy.

Uses a minimal page, native stereo and the production core's accurate HPF.
The split capture puts P1 on the left and P2 on the right for attribution.
"""
from functools import partial
from http.server import ThreadingHTTPServer
import argparse, hashlib, json, threading, wave
from pathlib import Path
import numpy as np
from playwright.sync_api import sync_playwright
from record_sameboy import ROOT, QuietHandler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path,default=ROOT/'gayboydemo.gb')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'build/pulse-overlap')
    args=parser.parse_args()
    rom = args.rom
    symbols = {l.split()[1]: int(l.split()[2], 16)
               for l in rom.with_suffix('.noi').read_text().splitlines()
               if l.startswith('DEF ')}
    out = args.output_dir
    out.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT/'website')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    report = {'rom_sha256': hashlib.sha256(rom.read_bytes()).hexdigest(),
              'rate': 48000, 'highpass': 'accurate', 'captures': []}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome', headless=True)
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/__capture_blank__.html')
            page.add_script_tag(url=f'http://127.0.0.1:{server.server_port}/emulator/sameboy.js')
            page.evaluate('''async rom => {
              window.m=await SameBoyCore();const p=m._malloc(rom.length);m.HEAPU8.set(rom,p);
              window.e=m._emulator_new_simple(p,rom.length,48000,1024,2);
              let event;do{event=m._emulator_run_until_f64(e,4194304*3);}while(!(event&4));
              window.checkpoint=m._emulator_checkpoint_new(e);m._free(p);
            }''', list(rom.read_bytes()))
            for name, muted, split, direction, period, gate in [
                    ('p1',126,False,0,1,88), ('p2',125,False,0,1,88),
                    ('both',124,False,0,1,88), ('split',124,True,0,1,88),
                    ('both-p1-rise',124,False,1,1,88),
                    ('both-p1-fall-period7-gate68',124,False,0,7,68),
                    ('full',0,False,0,1,88), ('full-p2-muted',2,False,0,1,88)]:
                print('Capturing '+name, flush=True)
                result = page.evaluate('''({s,muted,split,direction,period,gate}) => {
                  m._emulator_checkpoint_restore(e,checkpoint);
                  const write=(a,v)=>m._emulator_write_mem(e,a,v);
                  write(s._seqmuted,muted);
                  write(s._param+2,direction);write(s._param+3,period);write(s._seqgate,gate);
                  if(split){write(s._mx+19,2);write(s._mx+20,1);}
                  const start=m._emulator_get_ticks_f64(e), audio=[],trace=[];
                  let event,read=0;
                  for(let t=1;t<=600;t++){
                    const until=start+t*4194304/100;
                    do{
                      if(read===1024)read=0;
                      event=m._emulator_run_until_f64(e,until);
                      const n=m._get_audio_buffer_capacity(e)/4;
                      const a=new Int16Array(m.HEAPU8.buffer,m._get_audio_buffer_ptr(e),n*2);
                      for(let i=read*2;i<n*2;i++)audio.push(a[i]);read=n;
                    }while(!(event&4));
                    trace.push([t/100,...[s._seqowned,s._seqowned+1,0xff12,0xff17,0xff25,0xff26].map(a=>m._emulator_observe_mem(e,a))]);
                  }
                  return {audio,trace};
                }''', {'s':symbols,'muted':muted,'split':split,'direction':direction,'period':period,'gate':gate})
                pcm=np.asarray(result.pop('audio'),dtype='<i2').reshape(-1,2)
                with wave.open(str(out/(name+'.wav')),'wb') as wav:
                    wav.setparams((2,2,48000,0,'NONE','not compressed'));wav.writeframes(pcm.tobytes())
                (out/(name+'-trace.json')).write_text(json.dumps(result['trace']))
                report['captures'].append({'name':name,'frames':len(pcm),'peak':int(np.abs(pcm.astype(np.int32)).max())})
            browser.close()
        (out/'report.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    finally:
        server.shutdown();server.server_close()


if __name__ == '__main__':
    main()

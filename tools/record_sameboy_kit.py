"""Capture the live kit workflow entirely in the project's SameBoy WASM core.

Memory edits prepare disposable patterns off camera. Recorded edits use buttons.
The frame observer checks the outgoing loop and active PCM sample slots.
"""
import argparse
import base64
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
from kit_demo import KitDemo
from record_sameboy import QuietHandler, ROOT, RATE


class Memory:
    def __init__(self):
        self.data = bytearray(65536)
        self.writes = []

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            values = list(value)
            assert key.stop-key.start == len(values)
            self.data[key] = bytes(values)
            self.writes.extend([key.start+i, v] for i, v in enumerate(values))
        else:
            self.data[key] = value
            self.writes.append([key, value])


class SameBoy:
    def __init__(self, page, symbols):
        self.page, self.s = page, symbols
        self.memory = Memory()
        self.keys, self.observers = [], {}

    def button_press(self, key):
        self.keys.append([key, 1])

    def button_release(self, key):
        self.keys.append([key, 0])

    def hook_register(self, bank, address, callback, context):
        # SameBoy browser exposes frame observations, not instruction hooks.
        # Only the workflow's two observation sites are supported here.
        name = next(n for n in ('_seq_pattern_release', '_drum_pack')
                    if self.s[n] == (bank << 16 | address))
        self.observers[name] = (callback, context)

    def tick(self, count=1):
        for _ in range(count):
            previous = self.memory.data[:]
            result = self.page.evaluate('''({keys,writes}) => {
                for(const [address,value] of writes)m._emulator_write_mem(e,address,value);
                for(const [key,down] of keys)
                    m['_set_joyp_'+(key==='a'?'A':key==='b'?'B':key)](e,down);
                const audio=[];let event,attempts=0;
                do {
                    if(++attempts>100)throw Error('No SameBoy video frame');
                    if(readAudio===1024)readAudio=0;
                    event=m._emulator_run_until_f64(e,m._emulator_get_ticks_f64(e)+70224);
                    const n=m._get_audio_buffer_capacity(e)/4;
                    const data=new Int16Array(m.HEAPU8.buffer,m._get_audio_buffer_ptr(e),n*2);
                    for(let i=readAudio*2;i<n*2;i++)audio.push(data[i]);
                    readAudio=n;
                }while(!(event&1));
                function b64(bytes){return btoa(String.fromCharCode(...bytes));}
                const ptr=m._get_frame_buffer_ptr(e),mem=new Uint8Array(0x4000);
                for(let a=0xa000;a<0xe000;a++)mem[a-0xa000]=m._emulator_read_mem(e,a);
                return {noiseEnvelope:m._emulator_read_mem(e,0xff21),noiseTimbre:m._emulator_read_mem(e,0xff22),audio:b64(new Uint8Array(new Int16Array(audio).buffer)),
                        pixels:b64(m.HEAPU8.subarray(ptr,ptr+160*144*4)),memory:b64(mem)};
            }''', {'keys':self.keys, 'writes':self.memory.writes})
            self.keys.clear()
            self.memory.writes.clear()
            self.memory.data[0xa000:0xe000] = base64.b64decode(result['memory'])
            mx = self.s['_mx']
            if previous[mx+1] != self.memory.data[mx+1] and '_seq_pattern_release' in self.observers:
                # Inspect the last outgoing frame, before the observed pad change.
                current = self.memory.data
                self.memory.data = previous
                cb, ctx = self.observers['_seq_pattern_release']
                cb(ctx)
                self.memory.data = current
            if '_drum_pack' in self.observers:
                cb, ctx = self.observers['_drum_pack']
                cb(ctx)
            self.audio = base64.b64decode(result['audio'])
            self.pixels = base64.b64decode(result['pixels'])
            self.noise_envelope = result['noiseEnvelope']
            self.noise_timbre = result['noiseTimbre']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT/'recordings/GAYBOY-30sec-909-live-drums-SameBoy.mp4')
    args = parser.parse_args()
    rom = ROOT/'build/GAYBOY.gb'
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    symbols = {line.split()[1]:int(line.split()[2],16)
               for line in rom.with_suffix('.noi').read_text().splitlines() if line.startswith('DEF ')}
    server = ThreadingHTTPServer(('127.0.0.1',0), partial(QuietHandler,directory=str(ROOT/'website')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('FFmpeg must be on PATH')
    palette = [0xffffffff, 0xffaaaaaa, 0xff555555, 0xff000000]
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf',23)
    small = ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
    try:
        with tempfile.TemporaryDirectory(prefix='sameboy-kit-') as tmp, sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome',headless=True)
            page = browser.new_page()
            # Keep capture independent of the site's animation/rendering workload.
            page.route('**/capture.html', lambda route: route.fulfill(
                status=200, content_type='text/html', body='<!doctype html><title>Capture</title>'))
            page.goto(f'http://127.0.0.1:{server.server_port}/capture.html')
            page.add_script_tag(url=f'http://127.0.0.1:{server.server_port}/emulator/sameboy.js')
            page.evaluate('''async ({rom,palette})=>{
                window.m=await SameBoyCore();const ptr=m._malloc(rom.length);
                m.HEAPU8.set(rom,ptr);window.e=m._emulator_new_simple(ptr,rom.length,48000,1024,2);
                if(!e)throw Error('SameBoy initialization failed');window.readAudio=0;
                for(let type=0;type<3;type++)m._emulator_set_bw_palette_simple(e,type,...palette);
            }''',{'rom':list(rom.read_bytes()),'palette':palette})
            p = SameBoy(page,symbols)
            print('Preparing disposable TR-909 patterns in SameBoy...',flush=True)
            for _ in range(2800):
                p.tick()
                if p.memory[symbols['_introready']]:break
            assert p.memory[symbols['_introready']]
            p.button_press('start')
            for _ in range(1800):
                p.tick()
                if not p.memory[symbols['_introactive']] and p.memory[symbols['_page']]==8:break
            assert p.memory[symbols['_page']]==8, 'Application startup did not finish'
            p.button_release('start');p.tick(50)
            workflow = KitDemo(p,symbols)
            try:
                for _ in workflow.prepare():
                    p.tick()
            except Exception:
                Image.frombytes('RGBA',(160,144),p.pixels).resize((640,576)).save(ROOT/'build/sameboy-kit-failure.png')
                print({n:p.memory[symbols['_'+n]] for n in ('page','navchoice','navopen','lastpad')},flush=True)
                raise
            workflow.frames=0;workflow.log=[];workflow.stage_times=[];workflow.sequence=workflow.run()
            # Drop any pre-roll samples still pending in the core's audio buffer.
            page.evaluate('readAudio=m._get_audio_buffer_capacity(e)/4')
            samples=frames=peak=0
            audio=Path(tmp)/'audio.wav';video=Path(tmp)/'video.mp4'
            encoder=subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-y',
                '-f','rawvideo','-pix_fmt','rgb24','-s','540x960','-r','60','-i','-',
                '-an','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p',str(video)],stdin=subprocess.PIPE)
            print('Recording SameBoy framebuffer and unmodified stereo PCM...',flush=True)
            try:
                with wave.open(str(audio),'wb') as wav:
                    wav.setparams((2,2,RATE,0,'NONE','not compressed'))
                    while not workflow.done:
                        workflow.step();p.tick()
                        sound=np.frombuffer(p.audio,dtype='<i2')
                        peak=max(peak,int(np.abs(sound.astype(np.int32)).max(initial=0)))
                        wav.writeframes(p.audio);samples+=len(sound)//2
                        canvas=Image.new('RGB',(540,960),'#141414');draw=ImageDraw.Draw(canvas)
                        draw.line((247,124,293,124),fill='#aaaaaa',width=3)
                        draw.multiline_text((270,193),workflow.story,font=font,fill='#eeeeee',anchor='mm',align='center',spacing=12)
                        draw.text((270,760),'SAMEBOY / LIVE CONTROLS / STEREO PCM',font=small,fill='#aaaaaa',anchor='mm')
                        screen=Image.frombytes('RGBA',(160,144),p.pixels).convert('RGB')
                        canvas.paste(screen.resize((480,432),Image.Resampling.NEAREST),(30,280))
                        while frames/60<samples/RATE:
                            encoder.stdin.write(canvas.tobytes());frames+=1
                        if workflow.frames%300==0:print(f'Captured {samples/RATE:.1f}s',flush=True)
                        if workflow.frames>2400:raise RuntimeError('Workflow exceeded capture limit')
            finally:
                encoder.stdin.close();code=encoder.wait();browser.close()
            if code:raise RuntimeError('Video encoding failed')
            subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(video),'-i',str(audio),
                '-vf','scale=1080:1920:flags=neighbor','-c:v','libx264','-preset','fast','-crf','18',
                '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(output)],check=True)
            shutil.copyfile(audio,output.with_suffix('.wav'))
        metadata={'core':'SameBoy 1.0.4 website WASM','model':'DMG-B','highpass':'accurate',
                  'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),
                  'wasm_sha256':hashlib.sha256((ROOT/'website/emulator/sameboy.wasm').read_bytes()).hexdigest(),
                  'duration_seconds':samples/RATE,'size':[1080,1920],'fps':60,'audio_sample_rate':RATE,
                  'audio_peak':peak,'audio_gain':1,'palette':['#ffffff','#aaaaaa','#555555','#000000'],
                  'workflow_complete':workflow.done,'button_events':workflow.log,'stages':workflow.stage_times,
                  'composition':workflow.composition,'observation':'Frame-level boundary and active PCM slot checks'}
        output.with_suffix('.json').write_text(json.dumps(metadata,indent=2))
        print(json.dumps({'output':str(output),'seconds':samples/RATE,'peak':peak}),flush=True)
    finally:
        server.shutdown();server.server_close()


if __name__=='__main__':
    main()

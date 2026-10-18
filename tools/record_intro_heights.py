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
from heights_demo import HeightsDemo, DMXHeightsDemo, EightOhEightDemo, LinnHeightsDemo, NativeIntroDemo
from seq_storage_helpers import read_word
from record_sameboy import QuietHandler, ROOT, RATE


from record_sameboy_kit import SameBoy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT/'recordings/GAYBOY-60sec-intro-heights-SameBoy.mp4')
    parser.add_argument('--kit', choices=('909','dmx','808','linn','native'), default='909')
    parser.add_argument('--palette', choices=('classic','teal'), default='classic')
    args = parser.parse_args()
    KitDemo = {'909':HeightsDemo,'dmx':DMXHeightsDemo,'808':EightOhEightDemo,'linn':LinnHeightsDemo,'native':NativeIntroDemo}[args.kit]
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
    palette_rgb = ['#bfffe0','#65dcb1','#208b79','#073f3a'] if args.palette=='teal' else ['#b1d12d','#8bac0f','#306230','#0f380f']
    palette = [0xff000000|int(c[1:3],16)|int(c[3:5],16)<<8|int(c[5:7],16)<<16 for c in palette_rgb]
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
            print('Capturing complete intro and first prompt loop...',flush=True)
            for _ in range(500):
                p.tick()
                if p.memory[symbols['_introactive']]==1 and p.memory[symbols['_intro_audio_running']]==1:break
            intro_frames=[]
            prompt_seen=False
            for _ in range(2800):
                p.tick()
                audio=p.audio
                if p.memory[symbols['_introready']]:prompt_seen=True
                if prompt_seen and p.memory[symbols['_introfade']]>=1:
                    ticks=read_word(p,symbols['_intro_scene_ticks'])
                    # First two-bar loop on the prompt lasts 960 timer ticks.
                    # Trim the end-frame overshoot; residual timer phase <4ms.
                    excess=max(0,round((ticks-960)*RATE/256))
                    if excess:audio=audio[:max(0,len(audio)-excess*4)]
                    intro_frames.append((p.pixels,audio))
                    break
                intro_frames.append((p.pixels,audio))
                if len(intro_frames)%300==0:print('Intro frames',len(intro_frames),flush=True)
            else:raise RuntimeError('Intro prompt loop boundary not reached')
            intro_seconds=sum(len(a)//4 for _,a in intro_frames)/RATE
            print(f'Intro cut at {intro_seconds:.3f}s, scene ticks {ticks}; preparing live scene off camera...',flush=True)
            p.button_press('start')
            for _ in range(1800):
                p.tick()
                if not p.memory[symbols['_introactive']] and p.memory[symbols['_page']]==8:break
            assert p.memory[symbols['_page']]==8, 'Application startup did not finish'
            p.button_release('start');p.tick(50)
            workflow = KitDemo(p,symbols)
            live_preroll=[]
            try:
                for _ in workflow.prepare():
                    p.tick()
                    if p.memory[symbols['_seqplaying']]:
                        live_preroll.append((p.pixels,p.audio))
            except Exception:
                Image.frombytes('RGBA',(160,144),p.pixels).resize((640,576)).save(ROOT/'build/sameboy-kit-failure.png')
                print({n:p.memory[symbols['_'+n]] for n in ('page','navchoice','navopen','lastpad')},flush=True)
                raise
            assert live_preroll
            pixels,attack=live_preroll[0]
            values=np.frombuffer(attack,dtype='<i2').reshape(-1,2)
            nonzero=np.flatnonzero(np.max(np.abs(values.astype(np.int32)),axis=1)>8)
            trim=max(0,int(nonzero[0])-1) if len(nonzero) else 0
            live_preroll[0]=(pixels,attack[trim*4:])
            preroll_seconds=sum(len(a)//4 for _,a in live_preroll)/RATE
            print(f'Live first-attack preroll {preroll_seconds:.4f}s, leading silence trimmed {trim/RATE:.4f}s',flush=True)
            workflow.frames=0;workflow.log=[];workflow.stage_times=[];workflow.sequence=workflow.run()
            # Drop any pre-roll samples still pending in the core's audio buffer.
            page.evaluate('readAudio=m._get_audio_buffer_capacity(e)/4')
            samples=frames=peak=0
            intro_index=0
            preroll_index=0
            workflow.duration_limit=60-intro_seconds-preroll_seconds
            workflow.outro_start_live=54-intro_seconds-preroll_seconds
            audio=Path(tmp)/'audio.wav';video=Path(tmp)/'video.mp4'
            encoder=subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-y',
                '-f','rawvideo','-pix_fmt','rgb24','-s','540x960','-r','60','-i','-',
                '-an','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p',str(video)],stdin=subprocess.PIPE)
            print('Recording SameBoy framebuffer and unmodified stereo PCM...',flush=True)
            try:
                with wave.open(str(audio),'wb') as wav:
                    wav.setparams((2,2,RATE,0,'NONE','not compressed'))
                    while samples<60*RATE:
                        is_intro=intro_index<len(intro_frames)
                        if is_intro:
                            pixels,audio_bytes=intro_frames[intro_index];intro_index+=1
                            story=''
                        elif preroll_index<len(live_preroll):
                            pixels,audio_bytes=live_preroll[preroll_index];preroll_index+=1
                            story=getattr(workflow,'opening_caption',
                                          'Same melody. Same 128 BPM.\nComplete the bass as the loop plays.')
                        else:
                            workflow.step();p.tick()
                            if hasattr(workflow,'observe_audio'):workflow.observe_audio()
                            pixels,audio_bytes=p.pixels,p.audio
                            story=workflow.story
                        audio_bytes=audio_bytes[:max(0,(60*RATE-samples))*4]
                        sound=np.frombuffer(audio_bytes,dtype='<i2')
                        peak=max(peak,int(np.abs(sound.astype(np.int32)).max(initial=0)))
                        wav.writeframes(audio_bytes);samples+=len(sound)//2
                        canvas=Image.new('RGB',(540,960),'#0f380f');draw=ImageDraw.Draw(canvas)
                        if story:draw.line((247,124,293,124),fill='#8bac0f',width=3)
                        draw.multiline_text((270,193),story,font=font,fill='#b1d12d',anchor='mm',align='center',spacing=12)
                        if not is_intro:draw.text((270,760),'SAMEBOY / LIVE CONTROLS / 128 BPM',font=small,fill='#8bac0f',anchor='mm')
                        screen=Image.frombytes('RGBA',(160,144),pixels).convert('RGB')
                        canvas.paste(screen.resize((480,432),Image.Resampling.NEAREST),(30,280))
                        while frames/60<samples/RATE:
                            encoder.stdin.write(canvas.tobytes());frames+=1
                        if not is_intro and workflow.frames%300==0:print(f'Captured {samples/RATE:.1f}s',flush=True)
                        if workflow.frames>3000:raise RuntimeError('Workflow exceeded capture limit')
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
                  'audio_peak':peak,'audio_gain':1,'palette':palette_rgb,
                  'workflow_complete':workflow.done,'intro_duration_seconds':intro_seconds,
                  'edit':'Intro first prompt loop boundary to prepared live sequence; setup omitted; no tempo/pitch change',
                  'transition_timing_tolerance_ms':4,'live_bpm':128,'live_preroll_seconds':preroll_seconds,'button_events':workflow.log,'stages':workflow.stage_times,
                  'composition':workflow.composition,'observation':'Frame-level boundary and active PCM slot checks'}
        if getattr(workflow,'expected_native_drums',False):
            assert workflow.observed_noise=={(0x61,0x64),(0x72,0x37),(0x31,0x15)},workflow.observed_noise
            metadata['observed_intro_drum_registers']=sorted(workflow.observed_noise)
            assert any(s.get('event')=='whole arrangement restored during website outro' for s in workflow.stage_times)
        else:
            assert any(stage.get('sample_slots')==list(range(8)) for stage in workflow.stage_times)
        assert len([stage for stage in workflow.stage_times if stage.get('event')=='raised pulse mixer fader live'])==2
        output.with_suffix('.json').write_text(json.dumps(metadata,indent=2))
        print(json.dumps({'output':str(output),'seconds':samples/RATE,'peak':peak}),flush=True)
    finally:
        server.shutdown();server.server_close()


if __name__=='__main__':
    main()

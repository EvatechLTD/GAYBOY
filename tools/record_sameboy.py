"""Record the website's exact SameBoy WASM core, using the current development ROM.

python tools/record_sameboy.py --seconds 30 --output recordings/sameboy-demo.mp4
Optional --timeline uses record_demo.py's at/button/hold/release input format.
Captures native stereo PCM without gain changes and a 640x576 nearest-neighbor video.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import wave

import numpy as np
from playwright.sync_api import sync_playwright
from sameboy_palette import website_palette

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom', type=Path, default=ROOT/'build/GAYBOY.gb')
    ap.add_argument('--seconds', type=float, default=30)
    ap.add_argument('--output', type=Path, default=ROOT/'recordings/sameboy-demo.mp4')
    ap.add_argument('--timeline', type=Path)
    args = ap.parse_args()
    if args.seconds <= 0:
        ap.error('--seconds must be positive')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        ap.error('FFmpeg must be on PATH')
    events = json.loads(args.timeline.read_text()) if args.timeline else []
    for event in list(events):
        if 'button' in event:
            events.append({'at': event['at']+event.get('hold', .15), 'release': event['button']})
    events.sort(key=lambda e: e['at'])
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT/'website')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    samples = frames = index = peak = 0
    try:
        with tempfile.TemporaryDirectory(prefix='sameboy-capture-') as tmp, sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome', headless=True)
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            page.add_script_tag(url=f'http://127.0.0.1:{server.server_port}/emulator/sameboy.js')
            print('Initializing website SameBoy core...', flush=True)
            palette = website_palette()
            page.evaluate('''async ({rom,palette}) => {
                window.m = await SameBoyCore();
                const ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);
                window.e=m._emulator_new_simple(ptr,rom.length,48000,1024,2);
                if(!e)throw Error('SameBoy initialization failed');
                for(let type=0;type<3;type++)m._emulator_set_bw_palette_simple(e,type,...palette);
                window.readAudio=0;
            }''', {'rom': list(args.rom.read_bytes()), 'palette': palette})
            print('Capturing SameBoy video and stereo PCM...', flush=True)
            audio_path = Path(tmp)/'audio.wav'
            video_path = Path(tmp)/'video.mp4'
            encoder = subprocess.Popen([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '160x144', '-r', '60',
                '-i', '-', '-vf', 'scale=640:576:flags=neighbor', '-an',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(video_path)], stdin=subprocess.PIPE)
            try:
                with wave.open(str(audio_path), 'wb') as wav:
                    wav.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
                    while samples < args.seconds*RATE:
                        keys = []
                        while index < len(events) and events[index]['at'] <= samples/RATE:
                            event = events[index]
                            if 'button' in event: keys.append([event['button'], 1])
                            if 'release' in event: keys.append([event['release'], 0])
                            index += 1
                        result = page.evaluate('''keys => {
                            for(const [key,down] of keys){
                                const name=key==='a'?'A':key==='b'?'B':key;
                                m['_set_joyp_'+name](e,down);
                            }
                            const audio=[];let event,attempts=0;
                            do {
                                if(++attempts>100)throw Error('SameBoy did not produce a video frame');
                                // A full buffer resets at the next run call.
                                if(readAudio===1024)readAudio=0;
                                event=m._emulator_run_until_f64(e,m._emulator_get_ticks_f64(e)+70224);
                                const n=m._get_audio_buffer_capacity(e)/4;
                                const data=new Int16Array(m.HEAPU8.buffer,m._get_audio_buffer_ptr(e),n*2);
                                for(let i=readAudio*2;i<n*2;i++)audio.push(data[i]);
                                readAudio=n;
                            }while(!(event&1));
                            const ptr=m._get_frame_buffer_ptr(e);
                            return {audio,pixels:Array.from(m.HEAPU8.subarray(ptr,ptr+160*144*4))};
                        }''', keys)
                        sound = np.asarray(result['audio'], dtype='<i2')
                        peak = max(peak, int(np.abs(sound.astype(np.int32)).max(initial=0)))
                        wav.writeframes(sound.tobytes())
                        samples += len(sound)//2
                        # Audio is the clock, including LCD-off/boot vblanks.
                        pixels = bytes(result['pixels'])
                        while frames/60 < samples/RATE:
                            encoder.stdin.write(pixels)
                            frames += 1
            finally:
                encoder.stdin.close()
                code = encoder.wait()
                browser.close()
            if code:
                raise RuntimeError('SameBoy video encoding failed')
            subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                '-i', str(video_path), '-i', str(audio_path), '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', str(args.output)], check=True)
            shutil.copyfile(audio_path, args.output.with_suffix('.wav'))
        import hashlib
        metadata = {'core': 'SameBoy 1.0.4 website WASM', 'model': 'DMG-B',
                    'highpass': 'accurate', 'rom': str(args.rom.resolve()),
                    'rom_sha256': hashlib.sha256(args.rom.read_bytes()).hexdigest(),
                    'wasm_sha256': hashlib.sha256((ROOT/'website/emulator/sameboy.wasm').read_bytes()).hexdigest(),
                    'seconds': samples/RATE, 'frames': frames, 'video_fps': 60, 'audio_sample_rate': RATE,
                    'audio_peak': peak, 'timeline': events}
        metadata['palette_rgb'] = [f'#{c & 255:02X}{(c >> 8) & 255:02X}{(c >> 16) & 255:02X}' for c in palette]
        args.output.with_suffix('.json').write_text(json.dumps(metadata, indent=2))
        print(json.dumps({'output': str(args.output), **metadata}, indent=2))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()

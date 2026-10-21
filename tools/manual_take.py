"""Interactive SameBoy demo with a timed, direct screen + stereo sound recording."""
import argparse
from datetime import datetime
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import threading

from playwright.sync_api import sync_playwright
from record_sameboy import ROOT, QuietHandler
from record_sameboy_kit import SameBoy
from heights_demo import NativeIntroDemo


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seconds', type=float, default=30)
    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--immediate', action='store_true', help='Record the current ROM from launch, without fixture preparation or countdown')
    args = ap.parse_args()
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('FFmpeg is missing from PATH')
    folder = ROOT/('recordings' if args.immediate else 'recordings/manual')
    folder.mkdir(parents=True, exist_ok=True)
    output = folder/('take-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    rom = ROOT/'build/GAYBOY.gb'
    symbols = {line.split()[1]: int(line.split()[2], 16)
               for line in rom.with_suffix('.noi').read_text().splitlines() if line.startswith('DEF ')}
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT/'website')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print('Preparing demo. Recording starts automatically after the countdown.', flush=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome', headless=args.headless,
                args=['--autoplay-policy=no-user-gesture-required', '--disable-background-timer-throttling'])
            page = browser.new_page(viewport={'width':900, 'height':780}, accept_downloads=True)
            page.route('**/manual.html', lambda r: r.fulfill(content_type='text/html', body='''<!doctype html>
<title>GAYBOY manual take</title><style>
body{margin:0;background:#080c0c;color:#bfffe0;font:16px Consolas,monospace;text-align:center}
canvas{width:min(90vw,640px);image-rendering:pixelated;display:block;margin:14px auto}
p{margin:10px}#status{color:#ffe66a}</style>
<p id="status">Preparing your demo…</p><canvas id="screen" width="640" height="576"></canvas>
<p>Arrows: move · X: A · Z: B / add note · Space: Start / menu · Shift: Select</p>
<p>Shift + X: play/stop · Shift + Z: mute track · Shift + ←/→: track</p>
<p>30-second capture: emulator display + stereo audio. No captions or overlays.</p>'''))
            page.goto(f'http://127.0.0.1:{server.server_port}/manual.html')
            page.add_script_tag(url=f'http://127.0.0.1:{server.server_port}/emulator/sameboy.js')
            page.evaluate('''async rom=>{
                window.m=await SameBoyCore();const ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);
                window.e=m._emulator_new_simple(ptr,rom.length,48000,1024,2);window.readAudio=0;
                for(let type=0;type<3;type++)m._emulator_set_bw_palette_simple(e,type,
                    0xffe0ffbf,0xffb1dc65,0xff798b20,0xff3a3f07);
            }''', list(rom.read_bytes()))
            if not args.immediate:
                p = SameBoy(page, symbols)
                for _ in range(2800):
                    p.tick()
                    if p.memory[symbols['_introready']]:
                        break
                p.button_press('start')
                for _ in range(1800):
                    p.tick()
                    if not p.memory[symbols['_introactive']] and p.memory[symbols['_page']]==8:
                        break
                assert p.memory[symbols['_page']]==8
                p.button_release('start')
                p.tick(50)
                workflow = NativeIntroDemo(p, symbols)
                for _ in workflow.prepare():
                    p.tick()
                p.tick()
                assert workflow.v('seqplaying') and workflow.v('seqtrack')==1
            page.add_script_tag(path=str(ROOT/'tools/manual_take_player.js'))
            page.bring_to_front()
            page.evaluate('(immediate)=>{window.manualCountdown=immediate?0:3;}', args.immediate)
            page.locator('p').last.inner_text()
            page.locator('p').last.evaluate('(el,seconds)=>el.textContent=seconds+"-second capture: emulator display + stereo audio."', args.seconds)
            print('RECORDING NOW: '+str(args.seconds)+' seconds. Arrows, X=A, Z=B, Space=Start, Shift=Select.' if args.immediate else 'Demo ready. Take starts in 3 seconds.', flush=True)
            with page.expect_download(timeout=(args.seconds+30)*1000) as download:
                page.evaluate('(seconds)=>startManualTake(seconds)', args.seconds)
            download.value.save_as(str(output.with_suffix('.webm')))
            stats = page.evaluate('manualStats')
            output.with_suffix('.json').write_text(json.dumps(stats, indent=2))
            browser.close()
        print('Recording complete. Saving MP4...', flush=True)
        encoded = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
            '-i', str(output.with_suffix('.webm')), '-t', str(args.seconds),
            '-vf', 'fps=30,tpad=stop_mode=clone:stop_duration=1', '-af', 'apad',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
            str(output.with_suffix('.mp4'))], capture_output=True, text=True)
        if encoded.returncode:
            raise RuntimeError(encoded.stderr)
        print(f'Saved: {output.with_suffix(".mp4")}', flush=True)
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()

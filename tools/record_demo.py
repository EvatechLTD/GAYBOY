"""Capture actual PyBoy video/audio as a vertical MP4, optionally with scripted input.

python tools/record_demo.py
python tools/record_demo.py --seconds 30 --timeline demo.json
Timeline: [{"at": 5, "button": "start", "hold": 0.15},
           {"at": 6, "caption": "Choose an instrument"}]
Times are seconds from power-on. Captions remain until replaced (empty clears).
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyboy import PyBoy
from demo_style import DMG_PALETTE

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000
FPS = 60


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom', type=Path, default=ROOT / 'build/GAYBOY.gb')
    ap.add_argument('--output', type=Path, default=ROOT / 'recordings/GAYBOY-intro-reel.mp4')
    ap.add_argument('--seconds', type=float, help='Fixed duration; default stops after intro fades to silence')
    ap.add_argument('--timeline', type=Path)
    ap.add_argument('--story', type=Path, help='Timed story JSON; defaults to intro-story.json for automatic intro capture')
    ap.add_argument('--song-demo', action='store_true', help='Capture the button-driven song workflow, compressed to 30 seconds')
    ap.add_argument('--realtime', action='store_true', help='Keep song workflow audio and video at their original speed')
    ap.add_argument('--intro-song', action='store_true', help='Use the prepared intro-derived 32/64-step score and live layer arrangement')
    ap.add_argument('--quick-demo', action='store_true', help='30-second grayscale performance with a pattern-triggered drum entrance')
    ap.add_argument('--kit-demo', action='store_true', help='TR-909 groove with live drum plotting after quantized launch')
    args = ap.parse_args()
    if args.kit_demo: args.quick_demo = True
    if args.quick_demo:
        args.intro_song = True
    if args.intro_song:
        args.song_demo = args.realtime = True
    palette = (0xFFFFFF,0xAAAAAA,0x555555,0x000000) if args.quick_demo else DMG_PALETTE
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise SystemExit('FFmpeg must be on PATH')
    events = json.loads(args.timeline.read_text()) if args.timeline else []
    story_path = args.story or (ROOT / 'tools/intro-story.json' if not args.seconds and not args.song_demo else None)
    if story_path:
        events.extend(json.loads(story_path.read_text()))
    for event in list(events):
        if 'button' in event:
            events.append({'at': event['at'] + event.get('hold', .15), 'release': event['button']})
    events.sort(key=lambda event: event['at'])
    symbols = {}
    noi = args.rom.with_suffix('.noi')
    if noi.exists():
        symbols = {line.split()[1]: int(line.split()[2], 16) for line in noi.read_text().splitlines() if line.startswith('DEF ')}
    if not args.seconds and '_introfade' not in symbols:
        ap.error('Automatic intro capture requires matching .noi symbols; otherwise provide --seconds')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    font_path = Path('C:/Windows/Fonts/consola.ttf')
    title_font = ImageFont.truetype(str(font_path), 23)
    caption_font = ImageFont.truetype(str(font_path), 19)
    small_font = ImageFont.truetype(str(font_path), 15)
    p = PyBoy(str(args.rom), window='null', sound_emulated=True, sound_sample_rate=RATE, cgb=False, color_palette=palette,
              **({'ram_file': BytesIO(bytes(32768))} if args.song_demo else {}))
    p.set_emulation_speed(0)
    workflow = None
    if args.song_demo:
        if args.kit_demo:
            from kit_demo import KitDemo as SongDemo
        elif args.quick_demo:
            from quick_demo import QuickDemo as SongDemo
        elif args.intro_song:
            from intro_song import IntroSongDemo as SongDemo
        else:
            from song_demo import SongDemo
        p.tick(150)
        p.button_press('start'); p.tick(15)
        p.button_release('start'); p.tick(30)
        workflow = SongDemo(p, symbols)
        if args.quick_demo:
            for _ in workflow.prepare():
                p.tick(1)
            workflow.frames = 0
            workflow.log = []
            workflow.stage_times = []
            workflow.sequence = workflow.run()
    samples = frames = index = 0
    caption = ''
    story = ''
    intro_changes = []
    last_intro_state = None
    silent_since = None
    peaks = 0
    with tempfile.TemporaryDirectory(prefix='gayboy-record-') as tmp:
        tmp = Path(tmp)
        video = tmp / 'screen.mp4'
        audio = tmp / 'audio.wav'
        encoder = subprocess.Popen([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '540x960', '-r', str(FPS), '-i', '-',
            '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', str(video)], stdin=subprocess.PIPE)
        try:
            with wave.open(str(audio), 'wb') as wav:
                wav.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
                while samples / RATE < (args.seconds or (180 if workflow else 75)):
                    elapsed = samples / RATE
                    while index < len(events) and events[index]['at'] <= elapsed:
                        event = events[index]
                        if 'button' in event: p.button_press(event['button'])
                        if 'release' in event: p.button_release(event['release'])
                        if 'caption' in event: caption = event['caption']
                        if 'story' in event: story = event['story']
                        index += 1
                    if workflow:
                        workflow.step()
                        story = workflow.story
                    p.tick(1)
                    sound = p.sound.ndarray.copy().astype(np.int16) * 256
                    peaks = max(peaks, int(np.abs(sound.astype(np.int32)).max(initial=0)))
                    wav.writeframes(sound.astype('<i2').tobytes())
                    samples += len(sound)
                    if '_intro_audio_scene' in symbols:
                        scene = p.memory[symbols['_intro_audio_scene']]
                        state = (scene, bytes(p.memory[0x9a20:0x9a34]) if scene < 4 else b'')
                        if state != last_intro_state:
                            intro_changes.append(samples / RATE)
                            last_intro_state = state
                    canvas = Image.new('RGB', (540, 960), '#141414' if args.quick_demo else '#0c142c')
                    draw = ImageDraw.Draw(canvas)
                    if story:
                        draw.line((247, 124, 293, 124), fill='#aaaaaa' if args.quick_demo else '#ec95bd', width=3)
                        draw.multiline_text((270, 193), story, font=title_font, fill='#eeeeee' if args.quick_demo else '#dceeff', anchor='mm', align='center', spacing=12)
                    if workflow:
                        footer = ('PREPARED SCORE / LIVE ARRANGEMENT' if args.intro_song else
                                  'REAL CONTROLS / LIVE LOOP' if args.realtime else 'REAL CONTROLS / ACCELERATED BUILD')
                        draw.text((270, 760), footer, font=small_font, fill='#aaaaaa' if args.quick_demo else '#ec95bd', anchor='mm')
                    canvas.paste(p.screen.image.convert('RGB').resize((480, 432), Image.Resampling.NEAREST), (30, 280))
                    if caption:
                        draw.multiline_text((270, 770), caption, font=caption_font, fill='#dceeff', anchor='mm', align='center', spacing=8)
                    while frames / FPS < samples / RATE:
                        encoder.stdin.write(canvas.tobytes())
                        frames += 1
                    if workflow and workflow.done: break
                    if not workflow and not args.seconds and p.memory[symbols['_introfade']] == 4:
                        if silent_since is None: silent_since = samples / RATE
                        if samples / RATE - silent_since >= 1: break
        finally:
            p.stop(save=False)
            encoder.stdin.close()
            code = encoder.wait()
        if code: raise RuntimeError('Video encoding failed')
        speed = samples / RATE / 30 if workflow and not args.realtime else 1
        if workflow and not workflow.done: raise RuntimeError('Song workflow did not finish')
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(video), '-i', str(audio),
            '-vf', f'scale=1080:1920:flags=neighbor,setpts=PTS/{speed}',
            *(['-af', f'atempo={speed}'] if workflow else []),
            '-r', '60', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', str(args.output)], check=True)
    metadata = {'rom': str(args.rom.resolve()), 'duration_seconds': samples / RATE, 'frames': frames,
                'size': [1080, 1920], 'fps': FPS, 'audio_sample_rate': RATE, 'audio_peak': peaks,
                'palette': [f'#{color:06x}' for color in palette],
                'intro_caption_or_scene_changes': intro_changes,
                'timeline': events, 'capture': 'PyBoy framebuffer and emulated stereo audio; DMG'}
    if workflow:
        metadata.update(playback_speed=speed, output_duration_seconds=samples / RATE / speed, button_events=workflow.log,
                        workflow_complete=workflow.done)
        if args.intro_song:
            metadata.update(composition=workflow.composition, stages=workflow.stage_times)
    args.output.with_suffix('.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps({'output': str(args.output.resolve()), **metadata}, indent=2))


if __name__ == '__main__':
    main()

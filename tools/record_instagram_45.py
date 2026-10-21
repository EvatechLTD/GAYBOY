"""Capture a fresh 45-second Reel from the current ROM and embedded song."""
from io import BytesIO
from pathlib import Path
import hashlib
import json
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyboy import PyBoy
from boot_helpers import enter_app
from demo_style import DMG_PALETTE

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / 'build/GAYBOY.gb'
OUT = ROOT / 'recordings/GAYBOY-45sec-instagram-2026-10-18.mp4'
WORK = ROOT / 'build/instagram-45-2026-10-18'
RATE, FPS = 48000, 30


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    symbols = {l.split()[1]: int(l.split()[2], 16) for l in ROM.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
    p = PyBoy(str(ROM), window='null', sound_emulated=True, sound_sample_rate=RATE,
              cgb=False, ram_file=BytesIO(bytes(32768)), color_palette=DMG_PALETTE)
    p.set_emulation_speed(0)
    recording = False
    samples = frames = 0
    events = []
    stage = 'THE WHOLE BEAT. IN YOUR POCKET.'
    detail = 'GAYBOY / DEMO SONG'
    font = lambda size, bold=False: ImageFont.truetype('C:/Windows/Fonts/' + ('consolab.ttf' if bold else 'consola.ttf'), size)
    title, heading, body, small = font(61, True), font(21, True), font(17), font(13)
    encoder = None
    wav = None

    def v(name):
        return p.memory[symbols['_' + name]]

    def tick(n=1):
        nonlocal samples, frames
        for _ in range(n):
            p.tick(1)
            if not recording or samples >= 45 * RATE:
                continue
            sound = p.sound.ndarray.copy().astype(np.int16) * 256
            sound = sound[:45 * RATE - samples]
            wav.writeframes(sound.astype('<i2').tobytes())
            samples += len(sound)
            while frames / FPS < samples / RATE and frames < 45 * FPS:
                t = frames / FPS
                im = Image.new('RGB', (540, 960), '#101010')
                d = ImageDraw.Draw(im)
                d.text((40, 100), 'GAYBOY', font=title, fill='#f3f3ed')
                d.text((42, 174), 'A GAME BOY MUSIC WORKSTATION', font=small, fill='#aaaaa5')
                d.rectangle((40, 224, 500, 227), fill='#ef94bc')
                d.text((40, 251), '45 SECONDS / SOUND ON', font=small, fill='#ef94bc')
                d.rectangle((26, 300, 513, 739), fill='#555555')
                im.paste(p.screen.image.convert('RGB').resize((480, 432), Image.Resampling.NEAREST), (30, 304))
                d.text((40, 776), stage, font=heading, fill='#f3f3ed')
                d.text((40, 811), detail, font=body, fill='#aaaaa5')
                d.rectangle((40, 860, 500, 862), fill='#333333')
                d.rectangle((40, 860, 40 + round(460 * t / 45), 862), fill='#ef94bc')
                d.text((40, 883), 'ACTUAL ROM VIDEO + AUDIO', font=small, fill='#777777')
                if frames in (60, 450, 810, 1140, 1290):
                    im.save(WORK / f'preview-{frames:04d}.png')
                encoder.stdin.write(im.tobytes())
                frames += 1

    def press(key):
        mask = {'right': 1, 'left': 2, 'up': 4, 'down': 8, 'a': 16, 'b': 32, 'select': 64, 'start': 128}[key]
        for down in (True, False):
            (p.button_press if down else p.button_release)(key)
            if recording:
                events.append({'at': samples / RATE, 'button': key, 'down': down})
            for _ in range(600):
                tick()
                if bool(v('lastpad') & mask) == down:
                    break
            else:
                raise RuntimeError('Input timeout: ' + key)
        tick(8)

    def choose(target):
        p.button_press('start')
        for _ in range(600):
            tick()
            if v('navopen'): break
        assert v('navopen')
        for _ in range(32):
            if v('navchoice') == target: break
            press('down')
        assert v('navchoice') == target
        p.button_release('start')
        for _ in range(600):
            tick()
            if v('page') == target and not v('navopen') and not (v('lastpad') & 128): break
        assert v('page') == target
        tick(30)

    cues = []
    def cue(text, sub):
        nonlocal stage, detail
        stage, detail = text, sub
        cues.append({'at': samples / RATE, 'title': text, 'detail': sub})
        print(f'{samples / RATE:.2f}s: {text}', flush=True)

    def until(seconds):
        while samples < seconds * RATE: tick()

    try:
        enter_app(p, symbols)
        choose(24)
        press('a')
        for _ in range(1800):
            tick()
            if v('page') == 18 and v('sparse_song') == 0: break
        name = bytes(p.memory[symbols['_sparse_song_name']:symbols['_sparse_song_name'] + 17]).split(b'\0')[0].decode()
        assert name == 'DEMO SONG', name
        press('a')
        assert v('seqplaying')
        choose(8)
        wav = wave.open(str(WORK / 'audio.wav'), 'wb')
        wav.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        encoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '540x960', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-pix_fmt', 'yuv420p', str(WORK / 'video.mp4')], stdin=subprocess.PIPE)
        recording = True
        cue('THE WHOLE BEAT. IN YOUR POCKET.', 'GAYBOY / DEMO SONG')
        until(7)
        cue('DRUMS. MELODY. ONE SMALL SCREEN.', 'The sequencer, playing in real time.')
        until(13)
        cue('BUILT FOR SMALL SCREENS.', 'Native-speed playback. Original sound.')
        until(22)
        cue('MEET THE MIXER.', 'Your patterns. All together.')
        choose(18)
        until(32)
        cue('BACK TO THE GROOVE.', 'No added soundtrack. This is GAYBOY.')
        choose(8)
        until(41)
        cue('MAKE SOMETHING WITH GAYBOY.', 'A music workstation for Game Boy.')
        until(45)
    finally:
        recording = False
        p.stop(save=False)
        if wav: wav.close()
        if encoder:
            encoder.stdin.close()
            assert encoder.wait() == 0
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(WORK / 'video.mp4'), '-i', str(WORK / 'audio.wav'), '-vf', 'scale=1080:1920:flags=neighbor', '-af', 'volume=7dB,afade=t=in:d=0.03,afade=t=out:st=44.7:d=0.3', '-t', '45', '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(OUT)], check=True)
    OUT.with_suffix('.json').write_text(json.dumps({'output': str(OUT), 'duration_seconds': 45, 'resolution': [1080, 1920], 'fps': FPS, 'rom_sha256': hashlib.sha256(ROM.read_bytes()).hexdigest(), 'song': name, 'capture': 'Unmodified current ROM; real joypad navigation; native-speed live audio', 'captions': cues, 'button_events': events}, indent=2) + '\n')
    print(OUT, flush=True)


if __name__ == '__main__':
    main()

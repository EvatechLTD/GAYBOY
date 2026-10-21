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
from seq_storage_helpers import read_tracks

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / 'build/GAYBOY.gb'
OUT = ROOT / 'recordings/GAYBOY-45sec-CURRENT-ROM-DEMO-BEAT.mp4'
WORK = ROOT / 'build/current-rom-demo-beat-reel'
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
                d.multiline_text((40, 765), stage, font=heading, fill='#f3f3ed', spacing=3)
                d.text((40, 826), detail, font=body, fill='#aaaaa5')
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

    def state(key, down):
        mask = {'select':64, 'b':32, 'a':16}[key]
        (p.button_press if down else p.button_release)(key)
        for _ in range(600):
            tick()
            if bool(v('lastpad') & mask) == down: return
        raise RuntimeError('Held input timeout: ' + key)

    def chord(mod, key):
        state(mod, True); press(key); state(mod, False); tick(4)

    def track(target):
        for _ in range(8):
            if v('seqtrack') == target: return
            chord('select', 'right')
        raise RuntimeError('Track navigation failed')

    def mark(action, **values):
        events.append({'at':samples/RATE, 'action':action, **values})
        print(action, values, flush=True)

    def focus(target):
        assert p.memory[symbols['_mx']+4] == target, (target, p.memory[symbols['_mx']+4])

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
        initial_tracks = read_tracks(p, symbols)
        print('Loaded embedded demo:', initial_tracks, flush=True)
        press('a')
        assert v('seqplaying')
        choose(8)
        track(1)
        # Locate the existing P2 melody through normal piano navigation.
        press('left')
        assert v('seqhead') == 6
        for _ in range(128):
            pitch = p.memory[symbols['_seqpitch']+1]
            if pitch == 64: break
            press('up' if pitch < 64 else 'down')
        press('right')
        p.screen.image.save(WORK/'prepared-melody.png')
        wav = wave.open(str(WORK / 'audio.wav'), 'wb')
        wav.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        encoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '540x960', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-pix_fmt', 'yuv420p', str(WORK / 'video.mp4')], stdin=subprocess.PIPE)
        recording = True
        cue('YOUR BEAT. A WHOLE\nPOCKET STUDIO.', 'Embedded DEMO SONG / current ROM')
        until(2)
        cue('WRITE IT LIVE.\nHEAR IT IN THE GROOVE.', 'New notes. Zero stop-and-start.')
        for _ in range(4): press('right')
        before = read_tracks(p, symbols)[1]
        press('b')
        after = read_tracks(p, symbols)[1]
        assert before != after
        mark('live melody note edit', before=before, after=after)
        until(6)
        cue('TINY BUTTONS.\nLONGER, BIGGER NOTES.', 'Stretch a note while the beat plays.')
        chord('b','right')
        mark('live note length change', notes=read_tracks(p,symbols)[1])
        until(10)
        cue('THE WHOLE MIX.\nRIGHT AT YOUR FINGERTIPS.', 'Real-time volume. Real control.')
        choose(18)
        focus(0)
        for _ in range(4):press('down')
        focus(4)
        level = p.memory[symbols['_mx']+12]
        chord('b','left');chord('b','left')
        mark('P1 volume lowered live', before=level, after=p.memory[symbols['_mx']+12])
        until(16)
        cue('MAKE SOME SPACE.\nOWN THE STEREO FIELD.', 'Pan channels live. Shape the mix.')
        press('down');focus(5)
        chord('b','down')
        mark('P1 pan changed live', pan=p.memory[symbols['_mx']+19])
        assert p.memory[symbols['_mx']+19] in (1,2)
        until(19)
        chord('b','up')
        until(20)
        cue('DROP A LAYER.\nBRING THE ENERGY BACK.', 'Instant channel mutes. Big dynamics.')
        for _ in range(3):press('up')
        focus(2);press('a')
        mark('P1 muted', mute=v('seqmuted'))
        until(22);press('a')
        mark('P1 unmuted', mute=v('seqmuted'))
        until(24)
        cue('FOUR DEMO PATTERNS.\nONE SERIOUS GROOVE.', 'Launch the next part of DEMO SONG.')
        press('up');focus(0)
        press('right');focus(1)
        # A quarter-note launch boundary, selected through the real control.
        for _ in range(5):
            if p.memory[symbols['_mx']+3]==2:break
            press('a')
        press('up');focus(30);press('right');focus(31);press('a')
        for _ in range(600):
            tick()
            if p.memory[symbols['_mx']+1]==1:break
        assert p.memory[symbols['_mx']+1]==1
        mark('second embedded demo pattern launched', slot=1)
        until(30)
        cue('RESHAPE THE BEAT.\nKEEP THE MOMENTUM.', 'Live drum edits on your demo beat.')
        choose(8)
        track(6)
        # Add an absent kick in the existing demo, then a second accent.
        assert v('seqhead')==0
        for _ in range(16):
            if p.memory[symbols['_seqcursor']+6]==4:break
            press('right')
        for _ in range(16):
            if v('drumrow')==0:break
            press('up')
        drum_before=read_tracks(p,symbols)[6]
        press('b')
        mark('live drum hit toggled', before=drum_before, after=read_tracks(p,symbols)[6])
        until(36)
        cue('A LITTLE MORE BITE.\nA LOT MORE ATTITUDE.', 'Add accents without stopping playback.')
        for _ in range(3):press('down')
        for _ in range(2):press('right')
        press('b')
        mark('live hat accent toggled', notes=read_tracks(p,symbols)[6])
        until(41)
        cue('GAYBOY. SMALL CONSOLE.\nMASSIVE POSSIBILITIES.', 'Your demo beat. Made to be played.')
        until(45)
    finally:
        recording = False
        p.stop(save=False)
        if wav: wav.close()
        if encoder:
            encoder.stdin.close()
            assert encoder.wait() == 0
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(WORK / 'video.mp4'), '-i', str(WORK / 'audio.wav'), '-vf', 'scale=1080:1920:flags=neighbor', '-af', 'volume=7dB,afade=t=in:d=0.03,afade=t=out:st=44.7:d=0.3', '-t', '45', '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(OUT)], check=True)
    OUT.with_suffix('.json').write_text(json.dumps({'output': str(OUT), 'duration_seconds': 45, 'resolution': [1080, 1920], 'fps': FPS, 'rom_sha256': hashlib.sha256(ROM.read_bytes()).hexdigest(), 'song': name, 'initial_tracks':initial_tracks,'capture': 'Fresh unmodified current-ROM capture; embedded DEMO SONG; all edits through joypad; continuous live audio; disposable save RAM', 'captions': cues, 'button_events': events}, indent=2) + '\n')
    print(OUT, flush=True)


if __name__ == '__main__':
    main()

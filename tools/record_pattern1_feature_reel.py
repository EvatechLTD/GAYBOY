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
OUT = ROOT / 'recordings/GAYBOY-45sec-PATTERN1-bass-pulsekick-noise.mp4'
WORK = ROOT / 'build/pattern1-feature-reel'
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

    def midi_note(note, down):
        # Feed the ROM's normal incoming MIDI queue, rather than changing
        # oscillator state. Audition notes taken from pattern 1's bassline.
        for byte in (0x94 if down else 0x84, note, 110 if down else 0):
            at=v('wr')
            p.memory[symbols['_rx']+at]=byte
            p.memory[symbols['_wr']]=(at+1)&255
            tick(8)
        mark('monosynth MIDI bass audition', note=note, down=down)

    def cut_choose(target):
        nonlocal recording
        recording=False
        choose(target)
        recording=True

    def drum_goto(step,row):
        for _ in range(260):
            current=p.memory[symbols['_seqcursor']+6]
            if current==step:break
            if v('seqhead')==5:press('up')
            elif v('seqhead'):press('down')
            else:press('right' if current<step else 'left')
        for _ in range(15):
            if v('drumrow')==row:break
            press('down' if v('drumrow')<row else 'up')
        assert p.memory[symbols['_seqcursor']+6]==step and v('drumrow')==row
        assert v('seqhead')==0

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
        track(0)
        # Locate the existing P2 melody through normal piano navigation.
        press('left')
        assert v('seqhead') == 6
        for _ in range(128):
            pitch = p.memory[symbols['_seqpitch']]
            if pitch == 37: break
            press('up' if pitch < 37 else 'down')
        press('right')
        p.screen.image.save(WORK/'prepared-melody.png')
        wav = wave.open(str(WORK / 'audio.wav'), 'wb')
        wav.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        encoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '540x960', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-pix_fmt', 'yuv420p', str(WORK / 'video.mp4')], stdin=subprocess.PIPE)
        recording = True
        cue('PATTERN 1. BIG BASS.\nZERO COMPROMISE.', 'Your demo beat. Played and edited live.')
        until(1)
        cue('RESHAPE THE BASSLINE.\nKEEP THE GROOVE.', 'Move bass notes. Hear the new attitude.')
        bass_before=read_tracks(p,symbols)[0]
        chord('a','up');chord('a','up')
        mark('bass note transposed live', before=bass_before, after=read_tracks(p,symbols)[0])
        until(4)
        cue('TIGHTER NOTES.\nPUNCHIER BASS.', 'Trim the bass note while playback rolls.')
        chord('b','left');chord('b','left')
        assert read_tracks(p,symbols)[0]!=bass_before
        mark('bass length edited live', notes=read_tracks(p,symbols)[0])
        until(8)
        cut_choose(17)
        cue('LOSE THE METAL.\nFIND THE SWEET SPOT.', 'Hi-hat METALLIC: 001 -> 000.')
        assert v('drumsynthvoice')==0
        for _ in range(3):press('down')
        assert v('drumsynthrow')==3
        metal_before=p.memory[symbols['_noisepatch']+3]
        until(10)
        press('left')
        assert p.memory[symbols['_noisepatch']+3]==0
        mark('hi-hat metallic switched off', before=metal_before, after=0)
        until(13)
        cut_choose(8)
        recording=False;track(6);recording=True
        cue('SAMPLE KICK OUT.\nPULSE KICK IN.', 'Same rhythm. A whole new punch.')
        kicks=[e[:] for e in read_tracks(p,symbols)[6] if e[1]==1]
        assert kicks,kicks
        for kick in kicks:
            drum_goto(kick[0],0)
            # Drag the original hit to PK; timing, velocity and length survive.
            state('a',True)
            for i in range(12):
                # Cut the slow scroll between rows, retaining the start and
                # final drop of the actual held-A move into the PK lane.
                if i==1:recording=False
                if i==11:recording=True
                press('down')
            state('a',False);tick(8)
        after_drums=read_tracks(p,symbols)[6]
        assert not any(e[1]==1 for e in after_drums)
        for kick in kicks:
            assert [kick[0],13,kick[2],kick[3]] in after_drums
        mark('all original kicks replaced by pulse kicks', originals=kicks, after=after_drums)
        until(20)
        cut_choose(17)
        for _ in range(3):
            if v('drumsynthvoice')==2:break
            press('select')
        cue('A REAL SYNTH KICK.\nMAKE IT YOURS.', 'Tune the pulse kick in your own beat.')
        press('down');press('left');press('left')
        mark('pulse kick tuned live', pitch=p.memory[symbols['_pulsekickpatch']+1])
        until(23)
        cut_choose(16)
        cue('FLIP THE SWITCH.\nUNLOCK THE WEIRD.', 'Experimental mode. More sonic trouble.')
        assert not v('experimental_mode')
        until(24);press('a')
        assert v('experimental_mode')
        mark('experimental mode enabled on screen')
        until(26)
        cut_choose(7)
        # Monosynth activation stops transport; restart the same edited pattern.
        cut_choose(8)
        chord('select','a')
        assert v('seqplaying')
        cut_choose(7)
        cue('THREE OSCILLATORS.\nONE SMALL MONSTER.', 'Pulse voices. Wave shapes. Modulation.')
        audition=None
        for target,end,note in [(0,28.5,37),(2,31,42),(3,34,36)]:
            for _ in range(5):
                if v('monoosc')==target:break
                chord('select','right')
            if audition is not None:midi_note(audition,False)
            midi_note(note,True);audition=note
            assert v('monodown')
            mark('monosynth screen shown', oscillator=v('monoosc'))
            until(end)
        midi_note(audition,False)
        cut_choose(9)
        cue('MASTURBATE.\nMAKE BEAUTIFUL TROUBLE.', 'Noise performance mode. Drone on.')
        chord('select','a')
        assert v('noiseon')
        mark('noise performance drone enabled')
        until(36)
        chord('b','right')
        press('down');chord('b','right')
        mark('noise pitch and wave edited live', pitch=v('noisevalues'), wave=p.memory[symbols['_noisevalues']+1])
        until(39)
        cue('CHAOS AT YOUR\nFINGERTIPS.', 'Randomize the patch. Ride the noise.')
        chord('select','b')
        mark('noise patch randomized live', patch=list(p.memory[symbols['_noisevalues']:symbols['_noisevalues']+16]))
        until(42)
        for _ in range(2):press('down')
        chord('b','right')
        cue('GAYBOY. TINY BOX.\nSERIOUSLY UNHINGED.', 'Bass. Pulse kicks. Synths. Pure chaos.')
        until(44.6)
        chord('select','a')
        until(45)
        assert p.memory[symbols['_mx']+1]==0
    finally:
        recording = False
        p.stop(save=False)
        if wav: wav.close()
        if encoder:
            encoder.stdin.close()
            assert encoder.wait() == 0
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(WORK / 'video.mp4'), '-i', str(WORK / 'audio.wav'), '-vf', 'scale=1080:1920:flags=neighbor', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.03,afade=t=out:st=44.7:d=0.3', '-t', '45', '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(OUT)], check=True)
    OUT.with_suffix('.json').write_text(json.dumps({'output': str(OUT), 'duration_seconds': 45, 'resolution': [1080, 1920], 'fps': FPS, 'rom_sha256': hashlib.sha256(ROM.read_bytes()).hexdigest(), 'song': name, 'initial_tracks':initial_tracks,'pattern':1,'capture': 'Fresh unmodified current-ROM capture; embedded DEMO SONG; all edits through joypad; native-speed live audio; menu travel cut between features; disposable save RAM', 'captions': cues, 'button_events': events}, indent=2) + '\n')
    print(OUT, flush=True)


if __name__ == '__main__':
    main()

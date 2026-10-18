"""Screen-only, button-driven bass edits, quantized 808 launch, drum edits."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import wave

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from record_sameboy import ROOT, RATE, QuietHandler
from record_sameboy_kit import SameBoy
from heights_demo import HeightsDemo
from seq_storage_helpers import read_tracks, write_tracks, write_word


class ProgramDemo(HeightsDemo):
    kit_id=1
    kit_name='TR-808'
    kit_bank=32
    bpm=128
    missing_steps=(4,12)
    navigation_pause=0
    late_mixer=False
    mixer_volume=False

    def choose(self,target):
        print('Menu target',target,'from',self.v('page'),self.v('navchoice'),flush=True)
        yield from self.key('start',True)
        while not self.v('navopen'):yield
        visited=[]
        for _ in range(64):
            visited.append(self.v('navchoice'))
            if not _%8:print('Menu progress',target,visited[-8:],flush=True)
            if self.v('navchoice')==target:break
            yield from self.tap('down')
            yield from self.wait(3)
        assert self.v('navchoice')==target,(target,visited,self.v('page'),self.v('navopen'))
        yield from self.key('start',False)
        yield from self.wait(8)
        assert self.v('page')==target,(target,self.v('page'))

    def prepare_parts(self, incomplete=False):
        super().prepare_parts(False)
        tracks=read_tracks(self.p,self.s)
        if incomplete:
            tracks[1]=[e for e in tracks[1] if e[0] not in self.missing_steps]
        elif self.late_mixer:
            for event in tracks[1]:
                if event[0] in (4,12):event[3]=4
        # A sparse backbeat, with the kick and open hats left for the live edit.
        tracks[6]=[[4,5,110,2],[12,5,110,2],[2,3,80,1],[10,3,80,1]]
        write_tracks(self.p,self.s,tracks)
        self.p.memory[self.s['_drumrow']]=0
        self.p.memory[self.s['_seqcursor']+6]=0
        self.p.memory[self.s['_seqdefaultvel']+6]=110
        write_word(self.p,self.s['_seqdefaultdur']+12,0) # natural sample lengths
        write_word(self.p,self.s['_seqbpm'],self.bpm)
        self.composition.update(bpm=self.bpm,sparse_events=tracks,missing_bass_steps=list(self.missing_steps))
        if self.mixer_volume and not incomplete:self.p.memory[self.s['_mx']+12]=50

    def mark(self,event,**details):
        self.stage_times.append(dict(frame=self.frames,event=event,**details))
        print(f'{self.frames/59.7275:.2f}s: {event} {details}',flush=True)

    def before(self,step):
        # Stay in the first pass: a late edit must fail rather than silently
        # waiting a whole four-bar phrase before the listener hears it.
        assert self.v('seqposition',1)<step,(step,self.v('seqposition',1))
        while self.v('seqposition',1)<step-(3 if self.bpm>150 else 2):
            yield

    def diagonal(self):
        # Two real directions pressed together: move to the next column and
        # lower the cursor a semitone without spending a second on redraws.
        for down in (True,False):
            for key in ('right','down'):
                (self.p.button_press if down else self.p.button_release)(key)
                self.log.append(dict(frame=self.frames,button=key,down=down))
            while True:
                yield
                if (self.v('lastpad')&9)==(9 if down else 0):break

    def heard(self,step):
        while step not in self.bass_heard and self.v('seqposition',1)<step:
            yield
        assert step in self.bass_heard,(step,self.v('seqposition',1),self.frames)
        self.mark('new bass note played on first pass',step=step,heard_frame=self.bass_heard[step],position=self.v('seqposition',1))

    def run(self):
        assert self.v('seqplaying') and self.v('seqtrack')==1
        second=self.missing_steps[1]
        assert [e[0] for e in read_tracks(self.p,self.s)[1] if e[0] in self.missing_steps]==[]
        yield from self.before(4)
        self.mark('insert bass note just before playhead',step=4,position=self.v('seqposition',1))
        yield from self.tap('b')
        yield from self.heard(4)
        if self.bpm>150 and second in (12,44):
            for _ in range(5):yield from self.diagonal()
            for _ in range(second-9):yield from self.tap('right')
        else:
            for _ in range(second-4):yield from self.tap('right')
            for _ in range(5):yield from self.tap('up' if second==20 else 'down')
        self.mark('second bass note cursor ready',position=self.v('seqposition',1))
        yield from self.before(second)
        self.mark('insert bass note just before playhead',step=second,position=self.v('seqposition',1))
        yield from self.tap('b')
        yield from self.heard(second)
        yield from self.wait(6)
        if self.late_mixer:
            # Demonstrate actual note-length editing while the pulse plays.
            yield from self.chord('b','right')
            assert next(e for e in read_tracks(self.p,self.s)[1] if e[0]==12)[3]==4
            self.mark('extended second bass note live',step=12,duration=4)
            while self.v('seqcursor',1)>4:yield from self.tap('left')
            for _ in range(5):yield from self.tap('up')
            yield from self.chord('b','right')
            assert next(e for e in read_tracks(self.p,self.s)[1] if e[0]==4)[3]==4
            self.mark('extended first bass note live',step=4,duration=4)
            # Keep the real bass edits and the resulting playback visible.
            # Enter the menu only when its readable navigation will deliver
            # us to the mixer shortly before the next full-phrase handoff.
            yield from self.until(5.1 if self.mixer_volume else 6.3)
        if self.navigation_pause:
            yield from self.key('start',True)
            while not self.v('navopen'):yield
            yield from self.wait(self.navigation_pause)
            while self.v('navchoice')!=18:
                yield from self.tap('down')
                yield from self.wait(4)
            yield from self.wait(self.navigation_pause)
            yield from self.key('start',False)
            yield from self.wait(self.navigation_pause)
            assert self.v('page')==18
        else:
            yield from self.choose(18)
        self.mark('mixer page entered',position=self.v('seqposition',1))
        if self.mixer_volume:
            for _ in range(3):yield from self.tap('down')
            assert self.p.memory[self.s['_mx']+4]==4
            yield from self.key('b',True)
            yield from self.tap('right')
            for _ in range(2):yield from self.tap('up')
            yield from self.key('b',False)
            assert self.p.memory[self.s['_mx']+12]==50
            self.mark('adjusted pulse volume in mixer',channel=0,level=50,scale=127)
            yield from self.tap('down');yield from self.tap('down');yield from self.tap('right')
            assert self.p.memory[self.s['_mx']+4]==31
        else:
            yield from self.tap('up')
            yield from self.tap('right')
        if self.late_mixer:
            assert 24<=self.v('seqposition',1)<=40,self.v('seqposition',1)
            while self.v('seqposition',1)<32:yield
        elif self.bpm>150:
            # At this tempo snapshot/prefetch occupies more musical steps.
            # Queue halfway through the phrase so it is primed before 64.
            while self.v('seqposition',1)>32:yield
            while self.v('seqposition',1)<32:yield
        else:
            while self.v('seqposition',1)<48:yield
        yield from self.tap('a')
        self.mark('queued drum pattern from mixer',position=self.v('seqposition',1))
        while self.p.memory[self.s['_mx']+1]!=1:yield
        self.mark('drums entered at loop boundary',outgoing_positions=self.transition_snapshot)
        assert self.transition_snapshot[:2]==[63,63],self.transition_snapshot
        yield from self.tap('b')
        yield from self.wait(self.navigation_pause)
        yield from self.chord('select','left')
        yield from self.wait(self.navigation_pause)
        yield from self.chord('select','left')
        yield from self.wait(self.navigation_pause)
        assert self.v('seqtrack')==6
        if self.mixer_volume:
            # Supply a clean musical edit point for the direct jump from
            # launch to DRUM: all intervening track navigation is cut later.
            previous=self.v('seqposition',6)
            while True:
                yield
                position=self.v('seqposition',6)
                if position<previous:break
                previous=position
        self.mark('drum sequencer visible')
        assert self.v('drumrow')==0 and self.v('seqcursor',6)==0
        yield from self.tap('b')
        self.mark('added kick on downbeat',step=0)
        for _ in range(8):yield from self.tap('right')
        yield from self.tap('b')
        self.mark('added kick on beat three',step=8)
        for _ in range(3):yield from self.tap('down')
        for _ in range(2):yield from self.tap('left')
        yield from self.tap('b')
        self.mark('added open hat accent',step=6)
        for _ in range(8):yield from self.tap('right')
        yield from self.tap('b')
        self.mark('added open hat accent',step=14)
        tracks=read_tracks(self.p,self.s)
        assert sorted(e[0] for e in tracks[6] if e[1]==1)==[0,8]
        assert sorted(e[0] for e in tracks[6] if e[1]==4)==[6,14]
        self.composition['final_drum_events']=tracks[6]
        # Count four complete 16-step passes after the edit, beginning at 0.
        previous=self.v('seqposition',6)
        while True:
            yield
            position=self.v('seqposition',6)
            if position<previous:break
            previous=position
        self.mark('finished beat begins four full loops')
        for loop in range(4):
            previous=self.v('seqposition',6)
            while True:
                yield
                position=self.v('seqposition',6)
                if position<previous:break
                previous=position
            self.mark('finished beat loop complete',loop=loop+1)
        assert {0,2,3,4}.issubset(self.sounds_heard),self.sounds_heard


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bpm',type=int,default=128)
    ap.add_argument('--default-kick',action='store_true')
    ap.add_argument('--readable-navigation',action='store_true')
    ap.add_argument('--late-mixer',action='store_true')
    ap.add_argument('--mixer-volume',action='store_true')
    args=ap.parse_args()
    output=ROOT/('recordings/GAYBOY-program-demo-default-kick-172.mp4' if args.default_kick else 'recordings/GAYBOY-program-demo-808.mp4')
    if args.late_mixer:output=ROOT/'recordings/GAYBOY-program-demo-172-pulse-focus.mp4'
    if args.mixer_volume:output=ROOT/'recordings/GAYBOY-program-demo-172-mixer-volume.mp4'
    rom=ROOT/'build/GAYBOY.gb'
    symbols={line.split()[1]:int(line.split()[2],16)
             for line in rom.with_suffix('.noi').read_text().splitlines() if line.startswith('DEF ')}
    rom_data=bytearray(rom.read_bytes())
    if args.default_kick:
        # Disposable capture ROM: replace only the 808 kit's kick descriptor
        # with AMEN ORIGINAL's default kick. Keep its hats and clap intact.
        for name,data in (('_kitbank',bytes([16])),('_kitoffset',bytes([0,0])),
                          ('_kitlength',(816).to_bytes(2,'little'))):
            address=symbols[name];offset=(address>>16)*0x4000+(address&0xffff)-0x4000
            rom_data[offset:offset+len(data)]=data
        checksum=sum(rom_data[:0x14e])+sum(rom_data[0x150:])
        rom_data[0x14e:0x150]=(checksum&0xffff).to_bytes(2,'big')
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'website')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as pw, tempfile.TemporaryDirectory(prefix='program-demo-') as tmp:
            browser=pw.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page()
            page.route('**/capture.html',lambda r:r.fulfill(content_type='text/html',body='<title>Capture</title>'))
            page.goto(f'http://127.0.0.1:{server.server_port}/capture.html')
            page.add_script_tag(url=f'http://127.0.0.1:{server.server_port}/emulator/sameboy.js')
            page.evaluate('''async rom=>{
                window.m=await SameBoyCore();const ptr=m._malloc(rom.length);m.HEAPU8.set(rom,ptr);
                window.e=m._emulator_new_simple(ptr,rom.length,48000,1024,2);window.readAudio=0;
                for(let t=0;t<3;t++)m._emulator_set_bw_palette_simple(e,t,0xffe0ffbf,0xffb1dc65,0xff798b20,0xff3a3f07);
            }''',list(rom_data))
            p=SameBoy(page,symbols)
            print('Preparing two bass gaps and sparse 808 scene...',flush=True)
            for _ in range(2800):
                p.tick()
                if not _%1000:print('Boot progress',_,p.memory[symbols['_introready']],flush=True)
                if p.memory[symbols['_introready']]:break
            p.button_press('start')
            for _ in range(1800):
                p.tick()
                if not p.memory[symbols['_introactive']] and p.memory[symbols['_page']]==8:break
            p.button_release('start');p.tick(50)
            print('Startup state',dict((n,p.memory[symbols['_'+n]]) for n in ('page','navchoice','navopen','lastpad','introactive')),flush=True)
            w=ProgramDemo(p,symbols)
            w.bpm=args.bpm
            w.missing_steps=(4,12)
            w.late_mixer=args.late_mixer
            w.mixer_volume=args.mixer_volume
            w.navigation_pause=18 if args.readable_navigation else 0
            for _ in w.prepare():p.tick()
            if args.default_kick:
                w.composition['kick_sample']='AMEN ORIGINAL default kick; 808 hats and clap retained'
                w.observed_kick_banks=set()
                def observe_mixed_kit(_):
                    for voice in range(2):
                        if not w.v('drumon',voice):continue
                        sample=w.v('drumsamplevoice',voice);bank=w.v('drumbankvoice',voice)
                        if sample==0:
                            w.observed_kick_banks.add(bank)
                            assert bank==16,bank
                        if bank==(16 if sample==0 else 32):w.sounds_heard.add(sample)
                p.observers['_drum_pack']=(observe_mixed_kit,None)
            # Start the capture at the beginning of a fresh bass phrase.
            while w.v('seqposition',1)!=0:p.tick()
            w.frames=0;w.log=[];w.stage_times=[];w.sequence=w.run()
            w.bass_heard={}
            page.evaluate('readAudio=m._get_audio_buffer_capacity(e)/4')
            video=Path(tmp)/'screen.mp4';audio=Path(tmp)/'audio.wav'
            encoder=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                '-s','640x576','-r','60','-i','-','-an','-c:v','libx264','-preset','fast',
                '-crf','16','-threads','2','-pix_fmt','yuv420p',str(video)],stdin=subprocess.PIPE)
            samples=frames=peak=0
            try:
                with wave.open(str(audio),'wb') as wav:
                    wav.setparams((2,2,RATE,0,'NONE','not compressed'))
                    while not w.done:
                        w.step();p.tick()
                        position=w.v('seqposition',1)
                        if position in w.missing_steps and w.v('seqsource',1)==position and w.v('seqowned',1):
                            w.bass_heard.setdefault(position,w.frames)
                        pcm=np.frombuffer(p.audio,dtype='<i2')
                        peak=max(peak,int(np.abs(pcm.astype(np.int32)).max(initial=0)))
                        wav.writeframes(p.audio);samples+=len(pcm)//2
                        screen=Image.frombytes('RGBA',(160,144),p.pixels).convert('RGB').resize((640,576),Image.Resampling.NEAREST)
                        while frames/60<samples/RATE:
                            encoder.stdin.write(screen.tobytes());frames+=1
                        if w.frames>3600:raise RuntimeError('Demo exceeded one minute')
            finally:
                encoder.stdin.close();code=encoder.wait();browser.close()
            assert code==0
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-i',str(audio),
                '-c:v','copy','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(output)],check=True)
            shutil.copyfile(audio,output.with_suffix('.wav'))
            output.with_suffix('.json').write_text(json.dumps(dict(
                core='SameBoy 1.0.4',duration_seconds=samples/RATE,size=[640,576],fps=60,
                audio_sample_rate=RATE,audio_peak=peak,overlays=False,workflow_complete=w.done,
                stages=w.stage_times,button_events=w.log,composition=w.composition,
                observed_sample_slots=sorted(w.sounds_heard),
                observed_kick_banks=sorted(getattr(w,'observed_kick_banks',set()))),indent=2))
            print(f'Saved {output} ({samples/RATE:.2f}s)',flush=True)
    finally:
        server.shutdown();server.server_close()


if __name__=='__main__':main()

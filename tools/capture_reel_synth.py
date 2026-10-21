"""Record real pulse-kick sound-design controls for the feature Reel."""
from pathlib import Path
from io import BytesIO
import json, subprocess, wave
import numpy as np
from pyboy import PyBoy
from boot_helpers import enter_app
from demo_style import DMG_PALETTE

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/feature-reel';OUT.mkdir(exist_ok=True)
S={l.split()[1]:int(l.split()[2],16) for l in (ROOT/'build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy(str(ROOT/'build/GAYBOY.gb'),window='null',cgb=False,sound_emulated=True,sound_sample_rate=48000,ram_file=BytesIO(bytes(32768)),color_palette=DMG_PALETTE)
p.set_emulation_speed(0)
active=False;samples=frames=0;events=[]
def v(n):return p.memory[S['_'+n]]
def tick(n=1):
 global samples,frames
 for _ in range(n):
  p.tick(1)
  if active and samples<432000:
   audio=(p.sound.ndarray.copy().astype(np.int16)*256)[:432000-samples]
   wav.writeframes(audio.astype('<i2').tobytes());samples+=len(audio)
   while frames/30<samples/48000:
    enc.stdin.write(p.screen.image.convert('RGB').tobytes());frames+=1
def press(k):
 mask={'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'select':64}[k]
 for down in (True,False):
  (p.button_press if down else p.button_release)(k)
  for _ in range(600):
   tick()
   if bool(v('lastpad')&mask)==down:break
  else:raise RuntimeError(k)
 tick(5)
def choose(n):
 p.button_press('start')
 for _ in range(600):
  tick()
  if v('navopen'):break
 for _ in range(32):
  if v('navchoice')==n:break
  press('down')
 assert v('navchoice')==n
 p.button_release('start');tick(40);assert v('page')==n
def until(t):
 while samples<t*48000:tick()
try:
 enter_app(p,S);choose(17);press('select');press('select')
 assert v('drumsynthvoice')==2
 press('down')
 wav=wave.open(str(OUT/'synth.wav'),'wb');wav.setparams((2,2,48000,0,'NONE','not compressed'))
 enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','160x144','-r','30','-i','-','-an','-c:v','libx264','-crf','12','-pix_fmt','yuv420p',str(OUT/'synth-video.mp4')],stdin=subprocess.PIPE)
 active=True
 for at,direction in [(0,'left'),(.8,'left'),(1.6,'left'),(2.4,'right'),(3.2,'right'),(4,'right')]:
  until(at);press(direction);press('b')
  events.append({'at':samples/48000,'action':'pitch change + audition','pitch':p.memory[S['_pulsekickpatch']+1]})
 until(4.8)
 for _ in range(5):press('down')
 for at in [5.7,6.5,7.3,8.1]:
  until(at);press('right');press('b')
  events.append({'at':samples/48000,'action':'length change + audition','length':p.memory[S['_pulsekickpatch']+6]})
 until(9)
 p.screen.image.save(OUT/'synth-preview.png')
finally:
 p.stop(save=False)
 if active:wav.close();enc.stdin.close();assert enc.wait()==0
subprocess.run(['ffmpeg','-v','error','-y','-i',str(OUT/'synth-video.mp4'),'-i',str(OUT/'synth.wav'),'-c:v','copy','-c:a','aac','-b:a','192k','-t','9',str(OUT/'synth.mp4')],check=True)
(OUT/'synth-actions.json').write_text(json.dumps(events,indent=2))
print(events)

"""Capture review-guide evidence using real controls and isolated emulator RAM."""
from pathlib import Path
from io import BytesIO
import hashlib,json,sys
from pyboy import PyBoy
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from boot_helpers import enter_app
from demo_style import DMG_PALETTE
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/user-guide'; (OUT/'screenshots').mkdir(parents=True,exist_ok=True)
S={l.split()[1]:int(l.split()[2],16) for l in (ROOT/'build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy(str(ROOT/'build/GAYBOY.gb'),window='null',ram_file=BytesIO(bytes(32768)),color_palette=DMG_PALETTE,cgb=False)
p.set_emulation_speed(0)
log=[]
def v(n):return p.memory[S['_'+n]]
def tick(n=20):p.tick(n,True)
def press(k):
 mask={'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'select':64}[k]
 p.button_press(k)
 for _ in range(120):
  tick(1)
  if v('lastpad')&mask:break
 else:raise AssertionError(('press',k))
 p.button_release(k)
 for _ in range(120):
  tick(1)
  if not v('lastpad')&mask:break
 else:raise AssertionError(('release',k))
 tick(8);log.append({'button':k,'frame':p.frame_count})
def chord(k,d):
 p.button_press(k);tick(12);press(d);p.button_release(k);tick(20)
def shot(name):
 tick(30);p.screen.image.resize((640,576),Image.Resampling.NEAREST).save(OUT/'screenshots'/f'{name}.png');print(name,flush=True)
 log.append({'screenshot':name,'frame':p.frame_count,'page':v('page')})
def choose(n,menu=False):
 p.button_press('start')
 for _ in range(120):
  tick(1)
  if v('navopen'):break
 assert v('navopen')
 for _ in range(40):
  if v('navchoice')==n:break
  press('down')
 assert v('navchoice')==n, (n,v('navchoice'))
 if menu:shot('02-page-menu')
 p.button_release('start');tick(100)
 assert not v('navopen')
try:
 enter_app(p,S);shot('01-drum-roll')
 chord('select','a');assert v('seqplaying');shot('03-playing');chord('select','a');assert not v('seqplaying')
 choose(23,True);shot('04-kits');press('down');press('a');press('b');shot('05-kit-loaded')
 choose(17);shot('06-drumsynth');press('select');shot('07-snare');press('select');shot('08-pulsekick')
 choose(11);shot('09-pulse-tone');press('b');press('up');press('a');shot('10-preset-picker');press('b')
 choose(8);shot('11-piano-roll');press('b');press('right');press('up');press('b');shot('12-note-entry')
 chord('b','right');shot('13-note-duration');chord('select','down');shot('14-zoom');chord('select','up')
 press('select');shot('15-seq-settings');press('select')
 choose(18);shot('16-mixer')
 choose(20);shot('17-save-pattern');press('a');shot('18-name-keyboard');press('select');press('b');tick(160);assert v('page')==18
 choose(19);shot('19-load-pattern');press('a');tick(160)
 if v('sparse_enabled')==1:
  choose(25);shot('20-save-song');press('b');tick(160);choose(24);shot('21-load-song')
 choose(16);shot('22-global-off');press('a');assert v('experimental_mode');shot('23-global-on')
 choose(7);shot('24-monosynth');chord('select','right');shot('25-mono-pulse2');chord('select','right');shot('26-mono-wave');chord('select','right');shot('27-mono-mod');chord('select','right');shot('28-mono-exp')
 choose(9);shot('29-masturbate')
 (OUT/'capture-manifest.json').write_text(json.dumps({'rom':'build/GAYBOY.gb','sha256':hashlib.sha256((ROOT/'build/GAYBOY.gb').read_bytes()).hexdigest(),'emulator':'PyBoy DMG; isolated blank RAM; actual joypad controls; no memory writes','captures':log},indent=2))
finally:p.stop(save=False)

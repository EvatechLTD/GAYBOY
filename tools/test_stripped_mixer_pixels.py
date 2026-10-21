"""Check actual mixer fader tile pixels after page, menu and pad transitions."""
from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
def check(label):
 p.tick(240)
 mismatches=[]
 for slot in range(6):
  knob=v('fader_image_knob',slot)
  assert knob!=255,(label,'pending fader',slot)
  for part in range(7):
   index=slot*7+part;tile=192+index if index<12 else 220+index-12
   mapped=p.memory[0x9800+(6+part)*32+3+slot*3]
   assert mapped==tile,(label,'map mismatch',slot,part,mapped,tile)
   address=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16
   expected=[]
   for y in range(8):
    row=part*8+y;bits=0x18 if 1<=row<=53 else 0
    if knob<=row<knob+3:bits=0x42 if row==knob+1 else 0x7e
    expected.extend((bits,bits))
   actual=list(p.memory[address:address+16])
   if actual!=expected:mismatches.append((slot,part,tile,knob,actual,expected))
 assert not mismatches,(label,mismatches)
try:
 enter_app(p,S);menu(18);check('first entry')
 for bpm in (99,120,200,255,256,300):
  put('seqglobalbpm',bpm&255);put('seqglobalbpm',bpm>>8,1);put('dirty',1);p.tick(60)
  assert line(1)[4:7]==f'{bpm:03}',('BPM digits',bpm,line(1))
 put('seqglobalbpm',120);put('seqglobalbpm',0,1)
 for target in (11,30,16,2,23):
  menu(target);menu(18);check('return from '+str(target))
  p.button_press('start');p.tick(20);press('select');p.button_release('start');check('cancel menu')
 put('mx',30,4);put('dirty',1);p.tick(20)
 for _ in range(3):press('right');press('a');check('pad launch')
 # Change the viewport while the initial faders are deliberately still pending.
 menu(30);menu(18)
 for slot in range(6):put('fader_image_knob',255,slot)
 p.memory[0xa43d]=63;put('mx',39,4);put('dirty',1);p.tick(2)
 p.tick(180)
 for part in range(7):assert p.memory[0x9800+(6+part)*32+18]==0,('old queued fader drawn on sample channel',part)
 for slot in range(6):
  for part in range(7):
   at=(6+part)*20+3+slot*3
   assert p.memory[0x9800+(6+part)*32+3+slot*3]==v('canvas',at),('stale deferred fader published into another viewport',slot,part)
 print('PASS: actual fader pixels survive instrument, sequencer, Settings, Kits, menu cancellation and pattern changes')
finally:p.stop(save=False)


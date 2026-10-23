"""Snapshot/IRQ playback survives every workstation page and live sound changes."""
from pathlib import Path
from io import BytesIO
import statistics
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
from arp_probe_helpers import hook_attacks
# These timing assertions exercise the queued path. Avoid patching generic
# audition stores with emulator breakpoints during PCM interrupts.
queued_symbols={k:v for k,v in symbols.items() if k not in ('_play','_arp_native_sound','_arp_irq_tick','_arp_irq_due')}
hits=[];pitches=[];hook_attacks(p,rom,queued_symbols,1,hits.append,pitches.append,include_editbuffer=True)
def k(name,down):
 mask={'a':16,'b':32,'select':64,'start':128,'up':4,'down':8,'left':2,'right':1}[name]
 (p.button_press if down else p.button_release)(name)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',name,down))
def tap(name):k(name,True);k(name,False)
def changed():word('pattern_generation',(get('pattern_generation')|(get('pattern_generation',1)<<8))+1);put('seqirqdirty',1);word('seqdeadline',1)
def note_count():return get('editirq_attacks')|(get('editirq_attacks',1)<<8)
try:
 enter_app(p,symbols);offset=0
 for c in range(7):
  events=[[i,(61,65,68)[i%3],127,1] for i in range(8)] if c==1 else [[0,37,127,16]] if c==2 else [[i,11,100,1] for i in range(0,16,2)] if c==6 else []
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',8 if c==1 else 16,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 for c in range(3):put('evalpatch',0,c*16);put('evalpatch',0,c*16+13)
 put('seqtrack',1);put('selected',1);put('seqhead',0);put('seqfocus',0);word('seqbpm',240);word('seqglobalbpm',240);changed()
 k('select',True);tap('a');k('select',False);p.tick(500)
 assert get('editbuffer_valid') and get('editirq_enabled')&2
 for page,menu in [(8,1),(1,1),(1,0),(2,0),(17,0),(18,0),(27,0),(10,0),(8,0)]:
  put('page',page);put('navopen',menu);put('navcategory',0);put('navchoice',1);put('dirty',1);p.tick(100)
  assert get('editbuffer_valid') and get('editirq_enabled')&2,(page,menu,'lost ownership')
  hits.clear();p.tick(180);intervals=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])]
  assert len(intervals)>30 and max(abs(x-62.5) for x in intervals)<1.5,(page,menu,len(intervals),min(intervals),max(intervals))
  print('PASS queued playback page',page,'menu',menu,'max error',round(max(abs(x-62.5) for x in intervals),3),flush=True)
 # Live patch/mixer changes outside the grid must affect the next attacks.
 put('page',1);put('dirty',1);put('param',5,26+1);changed();p.tick(80)
 assert p.memory[0xff17]>>4==5,('stale pulse level',p.memory[0xff17])
 put('mx',64,13);changed();p.tick(80);assert p.memory[0xff17]>>4==2
 put('mx',1,20);changed();p.tick(80);assert p.memory[0xff25]&0x22==2
 print('PASS off-grid instrument volume, mixer level and pan updates',flush=True)
 assert not get('editirq_enabled')&1,'Empty P1 must not own the APU'
 p.memory[0xff12]=0xf0;p.memory[0xff14]=0x80;p.tick(90);assert p.memory[0xff26]&1,'Empty sequence silenced an audition'
 print('PASS empty lanes leave manual audition sounding')
 put('evalpatch',1,16+9);changed();p.tick(80);assert not get('editirq_enabled')&2,'modulation kept IRQ ownership'
 put('evalpatch',0,16+9);changed();p.tick(160);assert get('editirq_enabled')&2,'simple voice did not regain IRQ ownership'
 print('PASS modulation fallback and queued recovery',flush=True)
 # Remove the drum hash collision and inspect Wave RAM with the DAC off.
 word('seqeventcounts',0,12);changed();p.tick(240);assert get('editirq_enabled')&4
 def wave_ram():
  p.memory[0xff1a]=0;out=list(p.memory[0xff30:0xff40]);p.memory[0xff1a]=128;return out
 put('custom',1);image=[i*17 for i in range(16)]
 for i,x in enumerate(image):put('customwave',x,i)
 changed();p.tick(180);assert wave_ram()==image
 put('custom',0);put('param',3,52+14);changed();p.tick(180)
 a=symbols['_monowaves']+3*16;image=list(p.memory[a:a+16]);assert wave_ram()==image
 print('PASS custom and factory Wave changes update queued playback off-grid',flush=True)
 # Stop on a sequencer page, verify no pending attacks, then restart from a menu.
 put('page',8);k('select',True);tap('a');k('select',False);assert not get('seqplaying')
 before=note_count();p.tick(120);assert note_count()==before
 put('page',27);k('select',True);tap('a');k('select',False);p.tick(500)
 assert get('seqplaying') and get('editbuffer_valid') and get('editirq_enabled')&2
 print('PASS stopped queue stays silent and menu-start prepares a fresh snapshot')
finally:p.stop(save=False)

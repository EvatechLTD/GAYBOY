"""A mid-step snapshot publication must not retrigger a sounding Wave note."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
import test_pcm_timing as probes

def key(n,down):
 mask={'a':16,'b':32,'right':1,'select':64}[n];(p.button_press if down else p.button_release)(n)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError((n,down))
def u16(n):return get(n)|(get(n,1)<<8)
hits=[]
def write(site):
 op,extra,cost=site;r=p.register_file
 at=(r.B<<8)|r.C if op==2 else (r.D<<8)|r.E if op==0x12 else r.HL if op in (0x22,0x32,0x36,0x77) else 0xff00+extra if op==0xe0 else 0xff00+r.C if op==0xe2 else extra
 value=extra if op==0x36 else r.A
 if at==0xff1e and value&128:hits.append(p._cycles()+cost)
try:
 enter_app(p,symbols);offset=0
 tracks=[[],[],[[0,37,110,8]],[],[],[],[[s,11,100,1] for s in range(16)]+[[4,12,100,1],[12,12,100,1],[0,13,100,1],[8,13,100,1]]]
 for c,events in enumerate(tracks):
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',16,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 word('seqbpm',120);word('seqglobalbpm',120);put('pattern_dirty',1)
 put('page',8);put('seqtrack',2);put('selected',2);put('seqhead',0);put('seqfocus',0);put('seqcursor',0,2);put('seqpitch',36,2);put('seqtop',48,2);put('seqdrawvalid',0);put('dirty',1)
 probes.ROM=rom
 for pc,op,extra,cost in probes.pulse_write_sites(symbols):p.hook_register(0,pc,write,(op,extra,cost))
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(360)
 assert get('editbuffer_valid') and hits,'fixture has no Wave triggers'
 for _ in range(600):
  if get('seqposition',2)==2:break
  p.tick(1)
 original=hits[-1];before=len(hits);swaps=u16('editbuffer_swaps')
 key('b',True);key('right',True);key('right',False)
 assert p.memory[1,0xa303]==9
 for _ in range(600):
  p.tick(1)
  if u16('editbuffer_swaps')!=swaps:break
 assert u16('editbuffer_swaps')!=swaps,'edit never published'
 assert len(hits)==before,'publication retriggered the sustained note'
 for _ in range(600):
  p.tick(1)
  if len(hits)>before:break
 assert len(hits)==before+1,'unexpected Wave trigger count'
 delta=(hits[-1]-original)/4194.304
 assert abs(delta-2000)<25,('Wave retrigger timing changed',delta)
 print('PASS snapshot publishes mid-pattern without retriggering Wave; next APU trigger interval',round(delta,3),'ms')
finally:p.stop(save=False)

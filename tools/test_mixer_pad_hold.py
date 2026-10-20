"""Held pad launches follow musical quantization, never button-repeat time."""
exec(open('tools/test_mixer_settings.py').read().split('try:\n')[0])
from seq_storage_helpers import write_word,write_tracks
launches=[];boundaries=[]
def hook(name,callback):
 a=S['_'+name];p.hook_register(a>>16,a&65535,callback,None)
def boundary(_):boundaries.append((v('seqposition'),v('seqposition',1)))
def launch(_):launches.append((len(boundaries),boundaries[-1] if boundaries else None))
def wait(fn,limit=2400):
 for _ in range(limit):
  if fn():return
  p.tick(1)
 assert fn(),(launches,v('mx',2),v('page'))
try:
 enter_app(p,S);choose(18)
 p.memory[S['_syncmode']]=0;p.memory[S['_syncslave']]=0
 write_word(p,S['_seqbpm'],300);write_word(p,S['_seqglobalbpm'],300)
 tracks=[[] for _ in range(7)];tracks[0]=[[0,61,100,1]];tracks[1]=[[0,68,100,1]]
 write_tracks(p,S,tracks)
 write_word(p,S['_seqlength'],7);write_word(p,S['_seqlength']+2,24)
 hook('mixer_boundary',boundary);hook('seq_pattern_handoff',launch)
 p.memory[0,S['_mx']+4]=0;tap('a');assert v('seqplaying')
 for quant in [1,2,3,4,5]:
  p.memory[0,S['_mx']+3]=quant;p.memory[0,S['_mx']+4]=30
  launches.clear();boundaries.clear();p.button_press('a')
  wait(lambda:len(launches)>=5)
  held=launches[:5]
  expected=24 if quant==5 else 1<<quant
  assert all(b[0]-a[0]==expected for a,b in zip(held,held[1:])),(quant,held)
  if quant==5:assert all(x[1][1]==23 for x in held),(quant,held)
  p.button_release('a');wait(lambda:not v('lastpad')&16)
  # Like a tap, a launch already queued before release still completes.
  wait(lambda:v('mx',2)==255);count=len(launches);p.tick(240)
  assert len(launches)==count,(quant,'repeated after release')
  print('PASS held quant',quant,'consecutive boundary interval',expected)
 # NOW has no musical repeat interval and must remain one-shot.
 p.memory[0,S['_mx']+3]=0;launches.clear();p.button_press('a');p.tick(240)
 assert len(launches)==1,launches
 p.button_release('a');p.tick(30)
 # Holding A on Play must not repeatedly toggle transport.
 p.memory[0,S['_mx']+4]=0;p.button_press('a');p.tick(90)
 assert not v('seqplaying')
 print('PASS release stops rearming; NOW and transport remain one-shot')
finally:p.stop(save=False)

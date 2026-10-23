"""Exercise P2 mode switching using a copied hardware/emulator save."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
assert args.save,'Supply --save; this test preserves the supplied file'
changes=[];redraws=[];timings=[];pending=[None]
def mode(_):
 changes.append(p._cycles());pending[0]=p._cycles()
def flush(_):
 if pending[0] is not None:
  timings.append((p._cycles()-pending[0])*1000/4194304);pending[0]=None
for name,callback in [('eval_set_mode',mode),('ui_flush',flush),('seq_pixels',lambda _:redraws.append(p._cycles()))]:
 a=symbols['_'+name];p.hook_register(a>>16,a&65535,callback,None)
def key(key,down):
 mask={'a':16,'select':64}[key]
 (p.button_press if down else p.button_release)(key)
 for _ in range(1200):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError((key,down))
try:
 enter_app(p,symbols)
 print('saved P2 count',get('seqeventcounts',2),'length',get('seqlength',2),flush=True)
 assert get('seqeventcounts',2)>0
 put('seqtrack',1);put('selected',1);put('seqhead',1);put('seqfocus',0);put('seqdrawvalid',0);put('dirty',1);p.tick(200)
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(400)
 for i in range(6):
  before=get('evalpatch',16);redraws.clear();count=len(changes)
  key('a',True);p.tick(3);key('a',False);p.tick(200)
  assert len(changes)==count+1,(i,'unexpected toggle count',len(changes)-count)
  assert get('evalpatch',16)==1-before,(i,'mode did not stay switched',before,get('evalpatch',16))
  print('toggle',i,'mode',get('evalpatch',16),'grid rebuilds',len(redraws),'render ms',round(timings[-1],2) if timings else None,flush=True)
 print('PASS P2 switches both directions and stays selected during playback',flush=True)
finally:p.stop(save=False)

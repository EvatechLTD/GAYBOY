"""Global MPC swing settings and alternating scheduler intervals."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import write_tracks

try:
 choose(10);put('seqtrack',0,0);put('seqlength',0,16)
 assert v('seqswing')==50
 press('right');assert v('seqfocus')==2
 edit(1);assert v('seqlength')==17
 # Swing is accessible in ordinary mode and spans 50..100.
 put('seqfocus',0,11)
 edit(-1);assert v('seqswing')==50
 for _ in range(16):edit(1)
 assert v('seqswing')==66
 p.screen.image.save('build/ui-seq-swing.png')
 write_tracks(p,S,[[] for _ in range(7)])
 boundaries=[]
 def boundary(_):boundaries.append((v('seqswingphase'),word('seqthreshold')))
 a=S['_mixer_boundary'];p.hook_register(a>>16,a&65535,boundary,None)
 def check(amount,long,short):
  put('seqswing',0,amount);boundaries.clear()
  p.button_press('select');p.tick(3);press('a');p.button_release('select');p.tick(100)
  assert v('seqplaying') and len(boundaries)>4,(amount,boundaries)
  assert boundaries[:4]==[(1,short),(0,long),(1,short),(0,long)],boundaries[:4]
  p.button_press('select');p.tick(3);press('a');p.button_release('select');p.tick(4)
  assert not v('seqplaying')
 check(66,20480,10240)
 check(50,15360,15360)
 check(75,23040,7680)
 check(100,30720,0)
 put('seqswing',0,100);edit(1);assert v('seqswing')==100
 put('seqtrack',0,1);assert v('seqswing')==100
 print('PASS: global swing 50..100, straight/triplet/75/max scheduler intervals and sequence length settings')
finally:p.stop(save=False)

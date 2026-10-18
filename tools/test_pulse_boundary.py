"""Adjacent native pulse notes replace once; a following rest still releases."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].replace('range(60)','range(600)').replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file='))
from seq_storage_helpers import write_tracks
mx=S['_mx'];log=[];mute_after_first=False
def hook(name,cb):
 a=S['_'+name];p.hook_register(a>>16,a&65535,cb,None)
try:
 choose(18)
 tracks=[[] for _ in range(7)];tracks[0]=[[0,61,100,1],[1,65,100,1]]
 write_tracks(p,S,tracks)
 p.memory[S['_seqbpm']]=120;p.memory[S['_seqbpm']+1]=0
 def played(_):
  if p.register_file.A==0:
   log.append(('on',p._cycles()))
   if mute_after_first:p.memory[mx+12]=0
 hook('play',played)
 hook('seq_off',lambda _:log.append(('off',p._cycles())) if p.register_file.A==0 and v('seqowned') else None)
 p.memory[mx+4]=0;press('a')
 for _ in range(60):
  p.tick(1)
  if len(log)>=3:break
 assert [kind for kind,_ in log[:3]]==['on','on','off'],log
 assert not v('active') and not v('seqowned'), 'Rest must release the replacement gate'
 assert v('keycount')==0, 'Replacing sequence keys must not leave held keys'
 press('a');assert not v('seqplaying')
 log.clear();mute_after_first=True
 press('a');assert v('seqplaying')
 for _ in range(60):
  p.tick(1)
  if v('seqposition')>=2:break
 assert not v('active') and not v('keycount'), 'A zero-level replacement must silence the old pulse'
 print('PASS: adjacent pulse notes trigger without an intervening note-off; rests and zero-level replacements release normally')
finally:p.stop(save=False)

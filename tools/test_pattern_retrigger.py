"""Active pattern pads relaunch on the first eligible quantize boundary."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import read_tracks,write_tracks,write_word
mx=S['_mx'];boundaries=[];starts=[];fires=[];stops=[];releases=[]
def setm(i,value):p.memory[mx+i]=value
def put(n,i,value):fixture_put(p,S,n,i,value)
def hook(name,callback):
 a=S['_'+name];p.hook_register(a>>16,a&65535,callback,None)
def freeze():
 for _ in range(4):put('seqservicing',0,1);p.tick(1)
def began(_):starts.append((len(boundaries),p.frame_count))
def fired(_):
 if starts:fires.append(tuple(v('seqposition',c) for c in range(7)))
hook('mixer_boundary',lambda _:boundaries.append(p.frame_count))
hook('seq_pattern_start',began);hook('seq_fire',fired)
hook('seq_transport',lambda _:stops.append(p.frame_count))
hook('seq_pattern_release',lambda _:releases.append(p.frame_count))
try:
 choose(18)
 tracks=[[] for _ in range(7)];tracks[0]=[[0,61,99,2],[7,65,88,3]];write_tracks(p,S,tracks)
 for c in range(7):put('seqlength',c,32+c)
 # Start transport, then hold service while requesting a launch with real A.
 setm(4,0);press('a');assert v('seqplaying');stops.clear()
 for quant,boundary in ((1,1),(2,13)):
  freeze();setm(3,quant);setm(4,30)
  write_word(p,mx+10,boundary)
  for c in range(7):put('seqposition',c,5+c)
  before=read_tracks(p,S);boundaries.clear();starts.clear();fires.clear()
  press('a');assert p.memory[mx+2]==0 and not starts,(quant,p.memory[mx+1],p.memory[mx+2],p.memory[mx+3],p.memory[mx+4],v('seqservicing'),starts)
  # Repeated requests leave the same upcoming boundary queued.
  press('a');assert p.memory[mx+2]==0 and not starts
  write_word(p,S['_seqclock'],0);write_word(p,S['_seqticks'],0);put('seqservicing',0,0)
  for _ in range(120):
   p.tick(1)
   if starts:break
  assert len(starts)==1 and starts[0][0]==3,(quant,starts,boundaries)
  assert fires and fires[0]==(0,)*7,fires
  assert p.memory[mx+2]==255 and read_tracks(p,S)==before
 # OFF launches during the button action without waiting for any step.
 freeze();setm(3,0);setm(4,30)
 boundaries.clear();starts.clear();fires.clear();press('a')
 assert len(starts)==1 and not boundaries and fires[0]==(0,)*7
 assert v('seqplaying') and read_tracks(p,S)==before
 put('seqservicing',0,0)
 # Reselecting the current pad also supersedes a different queued pattern.
 freeze();setm(3,2);setm(2,1);starts.clear();press('a')
 assert p.memory[mx+2]==0 and not starts
 assert not stops and not releases,('Retrigger stopped/released audio',stops,releases)
 # A rest on the relaunched downbeat must not cut an existing sustain.
 setm(2,255);put('seqservicing',0,0);setm(3,0);setm(4,30)
 tracks=[[] for _ in range(7)];tracks[0]=[[0,61,99,16]];write_tracks(p,S,tracks)
 press('a');assert v('seqowned')==61 and v('active')
 tracks[0]=[[8,65,99,1]];write_tracks(p,S,tracks)
 setm(3,1);starts.clear();press('a')
 for _ in range(120):
  p.tick(1)
  if starts:break
 assert starts and v('seqowned')==61 and v('active'),'Downbeat rest cut the sustained note'
 assert not stops and not releases
 # Stopped patterns remain stopped, with their playheads reset.
 setm(2,255);setm(4,0);press('a');assert not v('seqplaying')
 starts.clear();setm(4,30);press('a');assert not starts and not v('seqplaying')
 assert all(v('seqposition',c)==0 for c in range(7))
 print('PASS: current-pad BEAT/BAR/OFF retrigger, first eligible boundary, all-track reset, live edits, repeated queue and replacement of pending launch')
finally:p.stop(save=False)

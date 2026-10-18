"""Selection-only tile XOR is pixel-identical to rebuilding notes and grid."""
exec(open('tools/test_seq_incremental.py').read().split('choose(8); settle()')[0])
from seq_storage_helpers import write_tracks
import random
rng=random.Random(7231)
def settle():
 # A broad full reference inversion can exceed ninety DMG frames. Never
 # mutate its selection bounds while it is still painting the reference.
 for _ in range(1800):
  p.tick(1)
  if v('seqdrawvalid')==1 and not v('rollbuilding') and v('seqviewtrack')==v('seqtrack') and bytes(p.memory[S['_canvas']:S['_canvas']+360])==bytes(p.memory[S['_visible']:S['_visible']+360]):
   p.tick(2);return
 raise AssertionError('Selection renderer did not settle')
calls=[];full=[]
def hook(name,fn):
 a=S['_'+name];p.hook_register(a>>16,a&65535,fn,None)
if '_roll_selection_update' in S:hook('roll_selection_update',lambda _:calls.append(p.frame_count))
hook('seq_pixels',lambda _:full.append(p.frame_count));hook('drum_render',lambda _:full.append(p.frame_count))
try:
 choose(8)
 tracks=[[] for _ in range(7)]
 tracks[0]=[[s,54+s%24,30+s,1+s%4] for s in range(64)]
 tracks[6]=[[s,1+(s%13),50+s,1+s%3] for s in range(64)]
 write_tracks(p,S,tracks)
 checked=0;fast=0
 for channel in (0,6):
  put('seqtrack',0,channel);put('seqlength',channel,64);put('seqcursor',channel,0)
  for zoom in range(4):
   for hidden in (0,1):
    put('seqzoom',0,zoom);put('seqvelocityhidden',0,hidden);put('seqtop',channel,75);put('seqpitch',channel,66);put('drumrow',0,0);put('seqgrouptrack',0,255);invalidate(True)
    for i in range(10):
     a,b=sorted((rng.randrange(64),rng.randrange(64)))
     low,high=sorted((rng.randrange(13),rng.randrange(13))) if channel==6 else sorted((rng.randrange(48,85),rng.randrange(48,85)))
     for name,value in zip(('seqgroupx0','seqgroupx1','seqgroupy0','seqgroupy1'),(a,b,low,high)):put(name,0,value)
     if channel==6:put('drumrow',0,high)
     put('seqgrouptrack',0,255 if i%4==3 else channel);put('seqdrawvalid',0,2);put('dirty',0,1)
     before=len(full);settle();image=background();fast+=len(full)==before
     if p.memory[S['_rollcache']]==168:
      expected=[0]*120
      for tile in p.memory[S['_seqscreen']:S['_seqscreen']+360]:
       index=tile-64 if 64<=tile<96 else tile-128 if 160<=tile<244 else tile-136 if tile>=252 else None
       if index is not None:expected[index]+=1
      base=S['_rollonsets'];actual=[p.memory[base+j*2]|p.memory[base+j*2+1]<<8 for j in range(120)]
      assert actual==expected,('Selection reference counts differ from published map',channel,zoom,hidden,i)
     invalidate(True)
     assert np.array_equal(image,background()),('Selection XOR/full mismatch',channel,zoom,hidden,i,a,b,low,high,np.count_nonzero(image!=background()))
     checked+=1
 assert not calls or fast>checked//2,('Fast selection path not exercised',fast,checked)
 print('PASS:',checked,'selection/deselection pixel comparisons,',fast,'without grid rebuilding; all zooms and velocity layouts')
finally:p.stop(save=False)

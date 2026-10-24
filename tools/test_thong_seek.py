"""Select+A resumes from the navigator, reconstructing notes inside clips."""
from pathlib import Path
exec(Path('tools/test_thong_audio.py').read_text().split('\ntry:\n')[0])
def transport():key('select',True);key('a',True);key('a',False);key('select',False)
def locate(step):
 for i,v in enumerate(step.to_bytes(4,'little')):put('song_view',v,i)
 put('song_view',0,12);put('dirty',1);p.tick(60)
def position():return int.from_bytes(bytes(get('song_actual_position',i) for i in range(4)),'little')
try:
 enter_app(p,S);put('sticky_start',1);put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0;put('waveengine',0)
 for c in range(7):
  word('seqeventcounts',2 if c==1 else 1 if c==2 else 0,c*2);word('seqeventoffsets',0 if c<=1 else 2 if c==2 else 3,c*2);word('seqlength',32,c*2)
 p.memory[1,0xa300:0xa30c]=[0,61,127,16,16,65,127,16,0,37,127,32]
 for i in range(128):put('evalpatch',0,i)
 for i in range(24):put('coarsepitch',0,i)
 put('pattern_dirty',1);word('pattern_generation',1);p.tick(180)
 p.memory[1,0xa800:0xb000]=p.memory[1,0xa000:0xa800]
 choose_song();tap('b')
 for _ in range(4):tap('right')
 tap('down');tap('b');assert clips()==[(0,32,0),(64,32,1)],clips()
 locate(16);hits['p2'].clear();transport();assert get('song_playing') and not get('smooth_playback_active')
 assert hits['p2'][0]['position']==16 and hits['p2'][0]['scene']==0,hits['p2'][:1]
 assert p.memory[runtime+103]==65,'Mid-clip seek replayed the first-bar note'
 assert p.memory[runtime+132]==37 and hits['wave'][-1]['position']==16,'Mid-clip seek lost the sustained Wave note'
 transport();assert cursor()==position()&~15 and not get('song_playing')
 locate(64);hits['p2'].clear();transport();assert hits['p2'][0]['position']==64 and hits['p2'][0]['scene']==1
 transport();locate(48);hits['p2'].clear();transport()
 assert get('song_playing') and get('song_actual_scene')==255 and not hits['p2'],'Gap seek played a previous clip'
 p.tick(150);assert hits['p2'] and hits['p2'][0]['position']==64,hits['p2'][:1]
 transport();locate(96);transport();assert not get('song_playing') and get('song_view',15)==10,'Seek past song end started at the beginning'
 print('PASS mid-clip note reconstruction, later clip, silent gap, stop playhead and end guard')
finally:p.stop(save=False)

"""Gaps are silent, LOOP defaults on, ONCE stops at the exact final clip."""
from pathlib import Path
from io import BytesIO
exec(Path('tools/test_thong_mode.py').read_text().split('\ntry:\n')[0])
def transport():key('select',True);key('start',True);key('start',False);key('select',False)
try:
 enter_app(p,S);put('sticky_start',1);put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0;put('waveengine',0)
 for c in range(7):word('seqeventcounts',1 if c==1 else 0,c*2);word('seqeventoffsets',0 if c<=1 else 1,c*2);word('seqlength',16,c*2)
 p.memory[1,0xa300:0xa304]=[0,61,127,16];put('evalpatch',0,16);put('pattern_dirty',1);word('pattern_generation',1);p.tick(180)
 p.memory[1,0xa800:0xb000]=p.memory[1,0xa000:0xa800]
 choose_song();tap('b');tap('right');tap('right');tap('down');tap('b')
 assert clips()==[(0,16,0),(32,16,1)],clips()
 assert read_storage(6,1)==b'\1'
 tap('up');tap('up');tap('right');tap('a');assert read_storage(6,1)==b'\0'
 saved=BytesIO();p.save_state(saved)
 transport();assert get('song_playing');p.tick(140)
 position=int.from_bytes(bytes(get('song_actual_position',i) for i in range(4)),'little')
 assert 16<=position<32,(position,get('song_actual_scene'))
 assert get('song_actual_scene')==255 and p.memory[0xff17]&0xf0==0,'Gap did not silence pulse'
 p.tick(260)
 assert not get('song_playing') and not get('seqplaying') and not get('smooth_playback_active')
 assert get('mx',1)==0 and get('seqeventcounts',2)==1,'Stop did not restore source pattern'
 print('PASS silent internal gap and ONCE end-stop with source restoration')
 saved.seek(0);p.load_state(saved);tap('a');assert read_storage(6,1)==b'\1'
 transport();p.tick(420);assert get('song_playing') and get('seqplaying')
 assert int.from_bytes(bytes(get('song_actual_position',i) for i in range(4)),'little')<48
 transport();assert not get('song_playing')
 print('PASS LOOP repeats the arrangement and manual shortcut stops it')
finally:p.stop(save=False)

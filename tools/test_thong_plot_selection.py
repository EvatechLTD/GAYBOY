"""Plot/resize stays solid. A selection alone inverts a clip's contents."""
from pathlib import Path
import numpy as np
exec(Path('tools/test_thong_mode.py').read_text().split('\ntry:\n')[0])
def body():
 p.tick(45);image=np.asarray(p.screen.image);part=image[33:39,33:39,:3]
 return int(np.sum(np.max(part,axis=2)<100))
def selected():return get('song_view',8)|(get('song_view',9)<<8)
try:
 enter_app(p,S);put('sticky_start',1);choose_song()
 key('b',True);assert clips()==[(0,16,0)] and selected()==65535
 key('b',False);assert body()>=30,'Newly plotted clip rendered hollow'
 key('b',True);tap('right');key('b',False)
 assert clips()==[(0,32,0)],clips()
 tap('left');assert body()>=30,'B resize implicitly selected the clip'
 key('a',True);assert body()<25,'A selection did not invert the clip'
 key('a',False);assert body()>=30 and selected()==65535,'Single A gesture stayed implicitly selected'
 tap('b');assert clips()==[],'B tap did not delete the existing clip'
 assert body()<10,'Deleted clip remained visible'
 print('PASS solid plotting/B resize, inverted A selection, release and visible deletion')
finally:p.stop(save=False)

"""Four-bar and eight-bar pads occupy four and eight fixed song cells."""
from pathlib import Path
exec(Path('tools/test_thong_mode.py').read_text().split('\ntry:\n')[0])
try:
 enter_app(p,S);put('sticky_start',1)
 for c in range(7):word('seqlength',64,c*2)
 for c in range(7):p.memory[1,0xa800+46+c*2:0xa800+48+c*2]=[128,0]
 choose_song();tap('b');assert clips()==[(0,64,0)],clips()
 for _ in range(4):tap('right')
 tap('down');tap('b');assert clips()==[(0,64,0),(64,128,1)],clips()
 key('b',True);tap('right');tap('right');key('b',False)
 assert clips()==[(0,64,0),(64,160,1)],clips()
 assert cursor()==208,cursor()
 assert all(start%16==0 and length%16==0 for start,length,_ in clips())
 print('PASS four/eight bars occupy four/eight cells, resize eight to ten bars, and every edit snaps to whole bars')
finally:p.stop(save=False)

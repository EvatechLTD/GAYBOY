"""Each actual sequencer entry snaps its lowest note to the bottom row."""
from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
try:
 enter_app(p,S);lows=(48,60,36,72)
 for c,low in enumerate(lows):
  put('seqeventoffsets',c,c*2);put('seqeventoffsets',0,c*2+1);put('seqeventcounts',1,c*2);put('seqeventcounts',0,c*2+1);p.memory[1,0xa300+c*4:0xa304+c*4]=[0,low+1,100,1]
 for c in (4,5,6):put('seqeventoffsets',4,c*2);put('seqeventcounts',0,c*2);put('seqeventcounts',0,c*2+1)
 def check(c,low):assert v('seqtrack')==c and v('seqtop',c)-v('seqrows')+1==low,(c,low,v('seqtrack'),v('seqtop',c),v('seqrows'))
 for c,low in enumerate(lows):
  menu(28+c);check(c,low);put('seqtop',110,c);put('dirty',1);p.tick(40);menu(16);menu(8);check(c,low)
 menu(34);p.button_press('select');p.tick(3);press('right');p.button_release('select');p.tick(100);check(0,lows[0])
 put('seqtop',110);put('dirty',1);p.tick(40);press('select');assert v('page')==10;press('select');p.tick(80);check(0,lows[0])
 put('seqzoom',0);menu(30);check(2,lows[2]);put('seqzoom',3);menu(29);check(1,lows[1])
 put('seqeventcounts',0);menu(28);check(0,36)
finally:p.stop(save=False)
print('PASS: repeated menu entries, most recent grid, drum-to-native paging, Seq Settings return, zooms and empty C2')

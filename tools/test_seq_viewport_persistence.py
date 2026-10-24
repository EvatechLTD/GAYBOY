"""Returning from Finder, mixer and another track retains each grid viewport."""
from pathlib import Path
exec(Path('tools/test_shared_ui_tiles.py').read_text().split('\ntry:\n')[0])
try:
 enter_app(p,symbols);put('sticky_start',1)
 for track in range(3):word('seqlength',128,track*2)
 positions={0:(21,78,85),1:(39,49,55),2:(71,32,39)}
 for track,(cursor,pitch,top) in positions.items():
  choose(28+track);put('seqcursor',cursor,track);put('seqpitch',pitch,track);put('seqtop',top,track);put('seqhead',0);put('seqfocus',0);put('dirty',1);p.tick(60)
  tap('right');positions[track]=(cursor+1,pitch,top)
 for _ in range(2):
  for track,expected in positions.items():
   choose(18);choose(28+track)
   actual=(get('seqcursor',track),get('seqpitch',track),get('seqtop',track))
   assert actual==expected,(track,expected,actual)
 print('PASS independent P1/P2/Wave scroll, pitch and cursor survive real page navigation')
finally:p.stop(save=False)

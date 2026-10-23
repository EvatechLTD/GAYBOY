"""Arp rate bounds, timing-mode changes and freerun direction."""
from pathlib import Path
import statistics
exec(Path('tools/test_arp_stress.py').read_text().split('reports=[]')[0])
def edit(k):
 key('a',True);key(k,True);key(k,False);key('a',False)
def rate():return get('evalpatch',22)|(get('evalpatch',23)<<8)
def setup():
 put('page',1);put('selected',1);put('eval_tab',3);put('eval_row',1);put('dirty',1);p.tick(60)
try:
 enter_app(p,S)
 assert get('evalpatch',18)>=3,'Saved fast divisor was not clamped'
 setup();put('evalpatch',0,17);put('evalpatch',0,19);put('evalpatch',3,18)
 edit('up');assert get('evalpatch',18)==3
 # Switching straight 1/32 to triplet must move to 1/16.
 put('eval_row',2);edit('up');assert get('evalpatch',19)==1 and get('evalpatch',18)==4
 put('eval_row',1);edit('up');assert get('evalpatch',18)==4
 put('eval_row',2);edit('up');assert get('evalpatch',19)==2
 put('eval_row',1);edit('up');assert get('evalpatch',18)==3
 edit('up');assert get('evalpatch',18)==3
 print('PASS straight/dotted 1/32 and triplet 1/16 bounds, including timing switch')
 put('evalpatch',1,17);word('evalpatch',125,22)
 edit('up');assert rate()==111,rate()
 edit('down');assert rate()==125,rate()
 for _ in range(3):edit('right')
 assert rate()==63,rate()
 edit('up');assert rate()==63
 for _ in range(3):edit('left')
 assert rate()==1000,rate()
 edit('down');assert rate()==1000
 print('PASS freerun 1..16 Hz, increasing value increases speed, both bounds')
 # Actual APU intervals at all three synced ceilings and freerun max.
 put('page',8);put('seqtrack',1);put('seqhead',1);put('seqfocus',0)
 put('evalpatch',1,16);put('evalpatch',0,20)
 word('seqbpm',120);word('seqglobalbpm',120)
 key('select',True);key('a',True);key('a',False);key('select',False)
 for clock,timing,division,ms,expected in [(0,0,0,125,62.5),(0,1,0,125,83.333333),(0,2,0,125,93.75),(1,0,3,1,63)]:
  put('evalpatch',clock,17);put('evalpatch',timing,19);put('evalpatch',division,18);word('evalpatch',ms,22)
  word('pattern_generation',(get('pattern_generation')|(get('pattern_generation',1)<<8))+1);word('seqdeadline',1)
  p.tick(150);hits.clear();p.tick(240)
  intervals=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])]
  actual=statistics.median(intervals)
  assert abs(actual-expected)<1,(clock,timing,actual,expected)
  print('PASS playback ceiling',clock,timing,round(actual,3),'ms')
finally:p.stop(save=False)

"""Selected cells invert both background bitplanes, including empty cells."""
exec(open('tools/test_seq_incremental.py').read().split('choose(8); settle()')[0])
from seq_storage_helpers import write_tracks
try:
 choose(8)
 tracks=[[] for _ in range(7)];tracks[0]=[[2,61,100,1],[4,66,90,2]];tracks[6]=[[1,1,100,1],[3,2,100,1]]
 write_tracks(p,S,tracks)
 for channel in (0,6):
  put('seqtrack',0,channel);put('seqgrouptrack',0,255);put('seqtop',0,71);invalidate(True)
  baseline=background()
  bounds=(1,5,59,66) if channel==0 else (0,5,0,3)
  for name,value in zip(('seqgroupx0','seqgroupx1','seqgroupy0','seqgroupy1'),bounds):put(name,0,value)
  put('seqgrouptrack',0,channel);invalidate()
  expected=baseline.copy()
  if channel==0: expected[8+(71-66)*8:8+(71-59+1)*8,25:70]=3-expected[8+(71-66)*8:8+(71-59+1)*8,25:70]
  else: expected[8:40,24:75]=3-expected[8:40,24:75]
  assert np.array_equal(expected,background()),('inversion',channel,np.count_nonzero(expected!=background()))
  selected=background();invalidate(True);assert np.array_equal(selected,background()),('full',channel)
  put('seqgrouptrack',0,255);invalidate();assert np.array_equal(baseline,background()),('deselect',channel)
 # Selection must survive retained scrolling and all row heights.
 put('seqtrack',0,0);put('seqgrouptrack',0,0)
 for zoom in range(4):
  for hidden in (0,1):
   put('seqzoom',0,zoom);put('seqvelocityhidden',0,hidden);put('seqtop',0,71);invalidate(True)
   for delta in (1,-1,2,-2):
    put('seqtop',0,v('seqtop')+delta);invalidate();retained=background()
    invalidate(True);assert np.array_equal(retained,background()),('selected scroll',zoom,hidden,delta)
 put('seqgrouptrack',0,255);invalidate();retained=background();invalidate(True)
 assert np.array_equal(retained,background()),'selected scroll deselection'
 # Exercise broad selection/deselection while the 808 PCM track runs.
 put('seqzoom',0,1);put('seqvelocityhidden',0,1);put('seqtop',0,71);invalidate(True)
 p.button_press('select');p.tick(5);press('a');p.button_release('select');p.tick(20)
 assert v('seqplaying')
 for selected in (0,255,0,255):
  for name,value in zip(('seqgroupx0','seqgroupx1','seqgroupy0','seqgroupy1'),(0,15,55,71)):put(name,0,value)
  put('seqgrouptrack',0,selected);invalidate()
 assert not word('mixunderruns'),'audio underrun during selection inversion'
 print('PASS: piano and DRUM selected notes, empty cells, grid lines invert exactly; deselection restores pixels')
finally:p.stop(save=False)

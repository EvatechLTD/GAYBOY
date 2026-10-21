from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
try:
 enter_app(p,S)
 assert v('param',1)==8 and v('param',27)==8
 assert v('eval_hidden')&128 and v('globalmod',7)==1 and v('globalmod',6)==8
 menu(11)
 for target in (1,2,3,4,0):
  p.button_press('select');p.tick(2);press('right');p.button_release('select');p.tick(20)
  assert (4 if v('page')==17 else v('selected'))==target,(target,v('page'),v('selected'))
 # A pitch row has three columns; leaving its edge changes the page.
 row(0,5);press('right');assert v('eval_col')==1 and v('eval_tab')==0
 press('right');assert v('eval_col')==2 and v('eval_tab')==0
 press('right');assert v('eval_tab')==3
 press('left');assert v('eval_tab')==0
 # Coarse pitch uses the same value / strength / source controls as fine.
 row(0,4);adjust('up');assert v('coarsepitch')==1
 put('eval_col',1);adjust('down');assert v('coarsepitch',1)==255
 put('eval_col',2);press('a');assert v('coarsepitch',2)==1
 p.screen.image.save('build/stripped-coarse.png')
 print('PASS: pulse defaults 8, waveforms off, LFO clock 1/1, instrument/page navigation and coarse controls')
finally:p.stop(save=False)

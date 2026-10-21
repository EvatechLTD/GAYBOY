"""Return from pattern/song filename keyboards without stale alphabet graphics."""
from pathlib import Path
exec(Path('tools/test_stripped_mixer_pixels.py').read_text().split('\ntry:')[0])
try:
 enter_app(p,S);menu(18);check('initial')
 for destination in (20,25):
  menu(destination);press('a');p.tick(100);assert v('mx',7)==1,(destination,'keyboard missing',v('page'))
  press('a');put('mx',39,4);put('dirty',1);p.tick(30);press('a');p.tick(180)
  if v('page')==26:press('up');press('a');p.tick(240)
  assert v('page')==18,(destination,'save did not return',v('page'),v('mx',7))
  check('keyboard save '+str(destination))
  for row in range(18):
   actual=list(p.memory[0x9800+row*32:0x9800+row*32+20]);wanted=list(p.memory[S['_canvas']+row*20:S['_canvas']+row*20+20]);assert actual==wanted,(destination,'stale map',row,actual,wanted)
  assert line(1).startswith('BPM') and line(2).strip()=='P1 P2 WV  N DR NHH',(line(1),line(2))
  p.screen.image.save('build/stripped-after-keyboard-'+str(destination)+'.png')
 print('PASS: naming pattern/song, saving and returning to mixer, complete VRAM map and fader pixels')
finally:p.stop(save=False)

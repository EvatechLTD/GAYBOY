"""Actual button regressions for Kits, Select release and both Start menu modes."""
from pathlib import Path
import json,sys
rom=Path(sys.argv[sys.argv.index('--rom')+1]) if '--rom' in sys.argv else Path('build/GAYBOY.gb')
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
prefix=prefix.replace("Path('build/GAYBOY.noi')","rom.with_suffix('.noi')").replace("'build/GAYBOY.gb',",'str(rom),')
if '--baseline' in sys.argv:prefix=prefix.replace("v('sticky_start')",'1')
exec(prefix)
def published(row):return ''.join(chr(p.memory[S['_visible']+row*20+i]%96+32) for i in range(20))
try:
 enter_app(p,S)
 if '--baseline' in sys.argv:
  menu(23);p.tick(30);print('Baseline Kits:',v('page'),v('navopen'),repr(line(0)),repr(published(0)));assert line(0)!=published(0)
 else:
  assert v('sticky_start')==0
  menu(23);p.tick(30);assert line(0)==published(0) and 'KITS' in published(0),(line(0),published(0))
  press('down');assert v('kitchoice')==2
  press('a');assert v('drumkit')==2
  press('b');p.tick(30)
  menu(34);p.tick(180);assert v('page')==8
  press('select');assert v('page')==10,v('page')
  press('select');assert v('page')==8,v('page');p.tick(180)
  # Chord commands consume Select; release must not open settings.
  p.button_press('select');p.tick(3);press('a');p.button_release('select');p.tick(20);assert v('page')==8 and v('seqplaying')
  p.button_press('select');p.tick(3);press('a');p.button_release('select');p.tick(20);assert not v('seqplaying') and v('page')==8
  # Hold-to-browse: cancellation followed by Start release has no selection.
  original=v('page');p.button_press('start');p.tick(20);assert v('navopen');put('navchoice',23);press('select');assert not v('navopen');p.button_release('start');p.tick(20);assert v('page')==original
  menu(16);put('eval_row',5);put('dirty',1);p.tick(10);assert 'STICKY START' in text(0);press('a');assert v('sticky_start')==1 and v('pool_root',124)==1
  press('start');assert v('navopen');put('navchoice',23);press('start');p.tick(20);assert v('page')==23 and 'KITS' in published(0)
  # Sticky menu supports Select cancellation as well.
  press('start');put('navchoice',16);press('select');assert not v('navopen') and v('page')==23
  menu(16);put('eval_row',5);put('dirty',1);p.tick(10);press('b');assert v('sticky_start')==0
  menu(30);p.tick(180);assert v('seqtrack')==2
  menu(11);menu(10);assert v('seqtrack')==0
  menu(8);p.tick(180);assert v('seqtrack')==2,'Sequencer shortcut lost the last grid channel'
  menu(34);p.tick(30);p.screen.image.save('build/stripped-cellfix-menus.png')
  print('PASS: Kits publishes, auditions and loads; Select tap and combinations; sticky and held Start, cancellation, default and persistence byte')
finally:p.stop(save=False)

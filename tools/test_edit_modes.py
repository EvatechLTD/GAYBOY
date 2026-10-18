exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(7);goto(0,1)
def pos():return (v('monoosc'),v('cursor',7),v('monocol'))
start=pos();level=v('monoset',1)
p.button_press('b');press('left');press('right');assert pos()==start
p.button_press('select');press('left');press('right');p.button_release('select');assert pos()==start
press('up');assert v('monoset',1)==level+1 and pos()==start
press('down');assert v('monoset',1)==level
p.button_release('b');p.tick(8)
# A toggles one-handed edit; horizontal edges wrap rows in the same oscillator.
press('a');assert v('monoedit')==1
press('up');assert v('monoset',1)==level+1 and pos()==start
press('down');press('right');assert pos()==(0,1,1)
press('up');assert v('monodepth',1)==1
press('down');press('right');assert pos()==(0,1,2)
press('right');assert pos()==(0,2,0)
press('left');assert pos()==(0,1,2)
# B overrides a latched edit's horizontal navigation, then restores it on release.
p.button_press('b');press('right');assert pos()==(0,1,2)
p.button_release('b');p.tick(8);press('right');assert pos()==(0,2,0)
press('a');assert not v('monoedit')
# With edit off, Up/Down moves the row instead of changing the field.
attack=v('monoset',2);press('up');assert pos()==(0,1,0) and v('monoset',2)==attack
goto(0);press('a');press('left');assert pos()==(0,6,0)
press('right');assert pos()==(0,0,0)
# Explicit Select paging remains available; MOD's single column wraps between rows.
p.button_press('select')
for _ in range(3):press('right')
p.button_release('select');p.tick(8);assert pos()==(3,0,0) and not v('monoedit')
press('a');assert v('monoedit')
press('left');assert pos()==(3,8,0)
press('right');assert pos()==(3,0,0)
# The toggle also enables accelerated edits, and A turns them off immediately.
p.memory[S['_monosource']]=0;p.button_press('up');p.tick(160)
assert v('monosource')>20 and pos()==(3,0,0)
press('a');assert not v('monoedit');before=v('monosource');p.tick(25);assert v('monosource')==before
p.button_release('up');p.tick(8)
# Every explicit page change clears edit mode, in either direction.
for direction in ('right','left'):
 for _ in range(5):
  if v('monoosc')==3 and v('cursor',7)==8:press('down')
  if not v('monoedit'):press('a')
  p.button_press('select');press(direction);p.button_release('select');p.tick(8)
  assert not v('monoedit')
# The black strip identifies the actual channel on each of the four screens.
for osc,name in enumerate(('PULSE1','PULSE2','WAVE','MOD')):
 goto(osc);p.tick(16)
 assert bytes(p.memory[S['_canvas']+80:S['_canvas']+80+len(name)])==bytes(ord(c)-32+96 for c in name)
goto(0,1);press('a');p.tick(16);p.screen.image.save('build/ui-edit-toggle.png')
p.button_press('start');p.tick(8);assert not v('monoedit')
p.button_release('start');p.tick(8)
p.stop(save=False);print('PASS: B cell lock, A toggle/edit/acceleration, row wraps, explicit paging, channel headings, menu reset')

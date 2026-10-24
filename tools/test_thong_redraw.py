"""Song input must never hide the background or restore another page's tiles."""
from pathlib import Path
exec(Path('tools/test_thong_mode.py').read_text().split('\ntry:\n')[0])
transitions=[]
def watch(_):transitions.append(p._cycles())
a=S['_ui_transition_begin'];p.hook_register(a>>16,a&65535,watch,None)
def frame():
 p.tick(1)
 assert p.memory[0xff40]&1,'Song editor blanked the background during an input redraw'
def press(k,down):
 mask={'a':16,'b':32,'right':1,'left':2,'up':4,'down':8,'select':64}[k]
 (p.button_press if down else p.button_release)(k)
 for _ in range(1800):
  frame()
  if bool(get('lastpad')&mask)==down:break
 else:raise AssertionError(('input timeout',k,down))
 for _ in range(12):frame()
def action(k):press(k,True);press(k,False)
try:
 enter_app(p,S);put('sticky_start',1);choose_song();p.tick(60);transitions.clear()
 for k in ('right','left','down','up','b','right','b'):action(k)
 press('b',True);action('right');press('b',False)
 press('a',True);action('right');press('a',False)
 press('select',True);action('up');action('down');press('select',False)
 action('up');action('right');action('a');action('left');action('down')
 for _ in range(60):frame()
 assert not transitions,('Song editor invoked a full-page tile restoration',len(transitions))
 p.screen.image.save('build/thong-redraw.png')
 print('PASS no transient blanking during navigation, plot, resize, move, zoom and header edits')
finally:p.stop(save=False)

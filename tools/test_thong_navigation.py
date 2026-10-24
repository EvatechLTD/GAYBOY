"""Stopped Song navigation retains grid tiles, stable labels and an idle header."""
from pathlib import Path
exec(Path('tools/test_thong_redraw.py').read_text().split('\ntry:\n')[0])
uploads=[];renders=[];costs=[];calls=[];returns=set()
def render_end(_):
 if calls and p.register_file.SP==calls[-1][0]:
  _,at=calls.pop();costs.append((p._cycles()-at)/4194.304)
def render_begin(_):
 renders.append(p._cycles());sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;bank=0 if ret<0x4000 else p.memory[S['__current_bank']]
 if (bank,ret) not in returns:returns.add((bank,ret));p.hook_register(bank,ret,render_end,None)
 calls.append((sp+2,p._cycles()))
a=S['_ui_upload_tile'];p.hook_register(a>>16,a&65535,lambda _:uploads.append(p._cycles()),None)
a=S['_song_render'];p.hook_register(a>>16,a&65535,render_begin,None)
def labels():return bytes(get('canvas',3*20+2+i) for i in range(16))
try:
 enter_app(p,S);put('sticky_start',1)
 # Names must use the same uppercase font mapping as other sequencer pages.
 p.memory[1,0xa010:0xa020]=b'lowercase name'.ljust(16)
 choose_song();p.tick(60);assert labels()==bytes(c-32 for c in b'LOWERCASE NAME'.ljust(16))
 expected=labels();uploads.clear();renders.clear();transitions.clear();costs.clear()
 timings=[]
 for k in ('right','right','left','down','up','left'):
  before=len(uploads);action(k);n=len(uploads)-before;timings.append(n)
  assert n<=2,('Cursor navigation reuploaded the grid',k,n)
  assert labels()==expected,'Navigation corrupted pattern label glyph IDs'
 assert any(timings),timings
 print('Stopped cursor render maximum ms',max(costs,default=0))
 assert max(costs,default=0)<16.75,'Cursor drawing exceeds one video frame'
 for _ in range(120):frame()
 before=len(renders)
 for _ in range(120):frame()
 assert len(renders)==before,'Idle grid keeps rendering'
 action('up');p.tick(60);before=len(renders);tiles=len(uploads)
 for _ in range(120):frame()
 assert len(renders)==before and len(uploads)==tiles,'Idle header keeps rebuilding the screen'
 costs.clear()
 for k in ('right','right','left','left','down'):action(k)
 print('Header navigation render maximum ms',max(costs,default=0))
 assert max(costs,default=0)<33.5,'Header navigation exceeds two video frames'
 action('b');action('right');action('b')
 p.screen.image.save('build/thong-grid.png')
 assert not transitions,'Grid input invoked a full page transition'
 print('PASS uppercase label integrity, <=2 changed tiles per cursor move, idle grid/header and outlined cells',timings)
finally:p.stop(save=False)

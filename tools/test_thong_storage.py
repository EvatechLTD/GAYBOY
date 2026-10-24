"""Full sparse storage, split records, no arbitrary timeline cap, protected pad copy."""
from pathlib import Path
exec(Path('tools/test_thong_mode.py').read_text().split('\ntry:\n')[0])
def write_storage(at,data):
 for i,v in enumerate(data,at):
  slot,off=divmod(i,288);p.memory[1+slot//4,0xa000+(slot%4)*2048+480+off]=v

def choose(n,category=0):
 tap('start')
 for _ in range(5):
  if get('navcategory')==category:break
  tap('right')
 for _ in range(32):
  if get('navchoice')==n:break
  tap('down')
 assert get('navchoice')==n,(n,get('navchoice'))
 tap('a');p.tick(30)
try:
 enter_app(p,S);put('sticky_start',1)
 write_storage(0,b'THG1'+bytes([158,0,1,0]))
 for i in range(158):write_storage(8+i*9,(i*32).to_bytes(4,'little')+(16).to_bytes(4,'little')+bytes([i%5]))
 choose_song();assert len(clips())==158
 for index in (31,63,95,127,157):
  for at,v in enumerate((index*32).to_bytes(4,'little')):put('song_view',v,at)
  put('song_view',index%5,10);put('song_view',0,11);put('song_view',0,12);put('dirty',1);p.tick(60)
  key('a',True);tap('right');key('a',False)
  assert clips()[index]==(index*32+16,16,index%5),(index,clips()[index])
 before=read_storage(0,1430)
 choose(18);put('mx',30,4);put('dirty',1);p.tick(30);choose(40,1)
 put('mx',31,4);put('dirty',1);p.tick(30);choose(41,1);assert get('page')==26;tap('up');tap('a');p.tick(60)
 assert read_storage(0,1430)==before,'Pad copy/paste overwrote global arrangement fragments'
 choose_song()
 for at,v in enumerate((16).to_bytes(4,'little')):put('song_view',v,at)
 put('song_view',1,10);put('song_view',0,11);put('song_view',0,12);put('dirty',1);p.tick(30);tap('b')
 assert read_storage(0,1430)==before,'Full arrangement overwrote an adjacent SRAM owner'
 print('PASS all158 sparse clip records, five fragment boundaries, full-memory rejection and pad clipboard isolation')
finally:p.stop(save=False)

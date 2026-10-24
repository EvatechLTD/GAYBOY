"""BUFFERING is visible throughout cold preparation; ready UI precedes audio."""
from pathlib import Path
exec(Path('tools/test_shared_ui_tiles.py').read_text().split('\ntry:\n')[0])
assert args.save,'Use --save with a populated song battery'

def text_row(row):return ''.join(chr(x%96+32) for x in p.memory[0x9800+row*32:0x9800+row*32+20])
def song():
 tap('start')
 for _ in range(24):
  if get('navchoice')==54:break
  tap('down')
 assert get('navchoice')==54;tap('a');assert get('page')==29
 for n in range(4):put('song_view',0,n)
 put('song_view',0,12);put('dirty',1);p.tick(60)

graphics=[]
def upload(_):
 if get('song_playing') and get('smooth_playback_active'):graphics.append(p._cycles())
for name in ('ui_upload_tile','ui_upload_map'):
 a=symbols['_'+name];p.hook_register(a>>16,a&65535,upload,None)

try:
 enter_app(p,symbols);put('sticky_start',1);song()
 for smooth in (False,True):
  p.button_press('select');p.tick(4);p.button_press('start' if smooth else 'a')
  buffering=0
  for _ in range(1800):
   p.tick(1);line=text_row(8 if smooth else 1)
   if 'BUFFERING' in line:
    buffering+=1;assert not get('song_playing'),'Audio started before ready status'
   if 'PLAYING' in line or 'TO STOP' in line:
    assert get('song_runtime',160),'Ready status preceded compilation'
   if get('song_playing'):break
  assert buffering>2 and get('song_playing'),(smooth,buffering,text_row(1),text_row(8))
  assert ('TO STOP' in text_row(8)) if smooth else ('PLAYING' in text_row(1))
  p.button_release('a');p.button_release('start');p.button_release('select');p.tick(120)
  p.button_press('select');p.tick(4);p.button_press('start');p.tick(30)
  p.button_release('start');p.button_release('select');p.tick(90)
  assert not get('song_playing')
  for n in range(4):put('song_view',0,n)
  put('dirty',1);p.tick(60)
  print('PASS',('Smooth' if smooth else 'Normal'),'BUFFERING visible for',buffering,'frames, ready before audio')
 assert not graphics,'Smooth playback uploaded graphics after starting'
finally:p.stop(save=False)

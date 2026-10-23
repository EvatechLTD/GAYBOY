"""Settings, zero graphics during playback, stop recovery and saved preference."""
from pathlib import Path
from io import BytesIO
import numpy as np
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])

def key(n,down):
 mask={'a':16,'b':32,'right':1,'up':4,'select':64}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
def tap(n):key(n,True);key(n,False)
try:
 enter_app(p,symbols);assert not get('smooth_playback_enabled')
 put('page',16);put('pageconfig',0);put('eval_row',0);put('dirty',1);p.tick(90)
 tap('up');assert get('eval_row')==6
 p.screen.image.save('build/smooth-playback-settings-off.png')
 tap('b');p.tick(120);assert get('smooth_playback_enabled')
 assert p.memory[3,0xbffd]==ord('S') and p.memory[3,0xbffe]==1
 p.screen.image.save('build/smooth-playback-settings-on.png')
 for c in range(7):
  word('seqeventoffsets',0,c*2);word('seqeventcounts',int(c==2),c*2);word('seqlength',64,c*2)
 p.memory[1,0xa300:0xa304]=[0,37,127,64]
 put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0
 put('page',8);put('seqtrack',2);put('selected',2);put('seqhead',0);put('seqfocus',0)
 put('seqcursor',0,2);put('seqpitch',36,2);put('seqtop',43,2);put('dirty',1);put('pattern_dirty',1);p.tick(120)
 counts={n:0 for n in ('ui_render','ui_flush','ui_upload_tile','ui_upload_map','roll_feedback_service')}
 def hit(n):counts[n]+=1
 for n in counts:
  a=symbols['_'+n];p.hook_register(a>>16,a&65535,hit,n)
 key('select',True);tap('a');key('select',False);p.tick(12)
 assert get('seqplaying') and get('smooth_playback_active')
 assert p.memory[0xff40]&0x80 and not p.memory[0xff40]&0x23
 assert not p.memory[symbols['__shadow_OAM_base']]
 counts={n:0 for n in counts};vram=bytes(p.memory[0x8000:0xa000]);cursor=get('seqcursor',2)
 key('b',True);tap('right');key('b',False);p.tick(120)
 assert get('seqcursor',2)==cursor and get('seqeventcounts',4)==1
 assert not any(counts.values()),counts
 assert bytes(p.memory[0x8000:0xa000])==vram,'Blank playback modified VRAM'
 assert len(np.unique(p.screen.ndarray.reshape(-1,4),axis=0))==1,'Display not blank'
 assert p.memory[0xff26]&4,'Blank playback lost Wave audio'
 p.screen.image.save('build/smooth-playback-blank.png')
 key('select',True);tap('a');key('select',False);p.tick(120)
 assert not get('seqplaying') and not get('smooth_playback_active')
 assert p.memory[0xff40]&1 and p.memory[symbols['__shadow_OAM_base']]
 assert counts['ui_render'] and counts['ui_flush'],'Editor was not redrawn after stop'
 p.screen.image.save('build/smooth-playback-restored.png')
 battery=b''.join(bytes(p.memory[b,0xa000:0xbfff])+bytes([p.memory[b,0xbfff]]) for b in range(4));p.stop(save=False)
 p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(battery));p.set_emulation_speed(0)
 enter_app(p,symbols);assert get('smooth_playback_enabled'),'Preference did not survive reboot'
 print('PASS default OFF, Settings toggle/persistence, blank display, zero graphics/VRAM writes, ignored editing and Select+A recovery')
finally:p.stop(save=False)

"""Smooth is an explicit Start+Select transport; normal starts stay graphical."""
from pathlib import Path
from io import BytesIO
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def key(n,down):
 mask={'a':16,'b':32,'right':1,'up':4,'select':64,'start':128}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
def tap(n):key(n,True);key(n,False)
def chord(first,second):
 key(first,True);key(second,True);key(second,False);key(first,False)
try:
 enter_app(p,symbols);assert not get('smooth_playback_requested')
 put('page',16);put('pageconfig',0);put('eval_row',0);put('dirty',1);p.tick(90)
 tap('up');assert get('eval_row')==5,'Settings still contains a seventh entry'
 assert b'SMOOTH' not in bytes(get('canvas',i)+32 for i in range(360))
 # Legacy saved ON preference must never turn an ordinary start into Smooth.
 p.memory[3,0xbffd]=ord('S');p.memory[3,0xbffe]=1
 for c in range(7):
  word('seqeventoffsets',int(c>2),c*2);word('seqeventcounts',int(c==2),c*2);word('seqlength',64,c*2)
 p.memory[1,0xa300:0xa304]=[0,37,127,64]
 put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0
 put('page',8);put('seqtrack',2);put('selected',2);put('seqhead',0);put('seqfocus',0)
 put('seqcursor',0,2);put('seqpitch',36,2);put('seqtop',43,2);put('dirty',1);put('pattern_dirty',1);p.tick(120)
 counts={n:0 for n in ('ui_render','ui_flush','ui_upload_tile','ui_upload_map','roll_feedback_service')}
 def hit(n):counts[n]+=1
 for n in counts:
  a=symbols['_'+n];p.hook_register(a>>16,a&65535,hit,n)
 chord('select','a');p.tick(30)
 assert get('seqplaying') and not get('smooth_playback_active')
 assert p.memory[0xff40]&1 and counts['ui_flush']
 chord('select','a');assert not get('seqplaying')
 print('PASS ordinary transport remains normal playback')
 # The mixer transport's B button also remains an ordinary graphical start.
 put('page',18);put('mx',0,4);put('dirty',1);p.tick(90);tap('b');p.tick(15)
 assert get('seqplaying') and not get('smooth_playback_active')
 tap('b');assert not get('seqplaying')
 put('mx',30,4);put('dirty',1);p.tick(30);tap('a');p.tick(15)
 assert get('seqplaying') and not get('smooth_playback_active'),'Pad launch entered Smooth'
 put('mx',0,4);tap('b');assert not get('seqplaying')
 print('PASS mixer transport and on-screen pad launches remain normal')
 put('page',8);put('dirty',1);p.tick(90)
 startup=[]
 def first_fire(_):
  if not get('smooth_playback_active') or startup:return
  assert get('editbuffer_valid') and not get('editbuffer_ready')
  assert bytes(p.memory[0x9900:0x9914])==bytes(ord(c)-32 for c in 'START+SELECT TO STOP')
  startup.append(p._cycles())
 a=symbols['_seq_fire'];p.hook_register(a>>16,a&65535,first_fire,None)
 chord('select','start');p.tick(12)
 assert startup and get('seqplaying') and get('smooth_playback_active') and not get('smooth_playback_requested')
 assert p.memory[0xff40]&0x80 and p.memory[0xff40]&1 and not p.memory[0xff40]&0x22
 assert not p.memory[symbols['__shadow_OAM_base']]
 counts={n:0 for n in counts};vram=bytes(p.memory[0x8000:0xa000]);cursor=get('seqcursor',2)
 key('b',True);tap('right');key('b',False);p.tick(120)
 assert get('seqcursor',2)==cursor and get('seqeventcounts',4)==1
 assert not any(counts.values()),counts
 assert bytes(p.memory[0x8000:0xa000])==vram
 assert p.memory[0xff26]&4
 chord('start','select');p.tick(90)
 assert not get('seqplaying') and not get('smooth_playback_active') and not get('navopen')
 assert p.memory[symbols['__shadow_OAM_base']] and counts['ui_render'] and counts['ui_flush']
 # Reverse button order also starts Smooth; stopping does not arm future starts.
 chord('start','select');assert get('seqplaying') and get('smooth_playback_active')
 chord('select','start');assert not get('seqplaying') and not get('smooth_playback_active')
 chord('select','a');assert get('seqplaying') and not get('smooth_playback_active')
 chord('select','a');assert not get('seqplaying')
 battery=b''.join(bytes(p.memory[b,0xa000:0xbfff])+bytes([p.memory[b,0xbfff]]) for b in range(4));p.stop(save=False)
 p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(battery));p.set_emulation_speed(0)
 enter_app(p,symbols);assert not get('smooth_playback_requested')
 chord('select','a');assert get('seqplaying') and not get('smooth_playback_active')
 print('PASS no Settings toggle, one-shot shortcut in either order, screen/cache barrier, zero ongoing graphics, stop recovery, and ignored legacy preference after reboot')
finally:p.stop(save=False)

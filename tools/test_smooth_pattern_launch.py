"""Static Smooth launcher: direct held pads, quant modifier and repeat release."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def key(n,down):
 mask={'a':16,'b':32,'right':1,'left':2,'up':4,'down':8,'select':64}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
def tap(n):key(n,True);key(n,False)
def wait_slot(slot):
 for _ in range(1200):
  p.tick(1)
  if get('mx',1)==slot and get('mx',2)==255:return
 raise AssertionError(('pad did not launch',slot,get('mx',1),get('mx',2)))
try:
 enter_app(p,symbols);put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0
 put('smooth_playback_enabled',1);put('mx',6,3);word('seqbpm',120);word('seqglobalbpm',120)
 offset=0
 for c in range(7):
  events=[[0,37,110,16]] if c==2 else [[s,11,100,1] for s in range(16)] if c==6 else []
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',16,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 put('pattern_dirty',1);p.tick(180);assert not get('pattern_dirty'),'Fixture did not save'
 template=bytes(p.memory[1,0xa000:0xa800])
 for slot in range(1,5):
  bank=1+(slot>>2);a=0xa000+(slot&3)*2048
  p.memory[bank,a:a+2047]=list(template[:-1]);p.memory[bank,a+2047]=template[-1]
  p.memory[bank,a+769]=37+slot*2
 names=('ALPHA','BETA','GAMMA','DELTA','EPSILON')
 for slot,name in enumerate(names):
  a=0xa000+(slot&3)*2048+16;p.memory[1+(slot>>2),a:a+16]=list(name.encode().ljust(16,b'\0'))
 for i,v in enumerate(b'ALPHA\0'.ljust(17,b'\0')):put('mx',v,26+i)
 requests=[];handoffs=[];uploads=[];renders=[]
 for n,fn in [('mixer_launch_request',lambda _:requests.append(p.register_file.A)),('seq_pattern_handoff',lambda _:handoffs.append(p._cycles())),('ui_upload_map',lambda _:uploads.append(p._cycles())),('ui_render',lambda _:renders.append(p._cycles()))]:
  a=symbols['_'+n];p.hook_register(a>>16,a&65535,fn,None)
 key('select',True);tap('a');key('select',False);p.tick(12);assert get('smooth_playback_active')
 p.screen.image.save('build/smooth-launch-legend.png')
 for i,name in enumerate(names):
  text=''.join(chr(get('canvas',(9+i)*20+j)+32) for j in range(2,18)).rstrip()
  assert text==name,(i,text,name)
 uploads.clear();renders.clear();vram=bytes(p.memory[0x8000:0xa000])
 for n,slot in (('up',0),('right',1),('down',2),('left',3),('b',4)):
  before=len(handoffs);key(n,True);wait_slot(slot);p.tick(90)
  assert get('seqplaying') and get('smooth_playback_active') and get('mx',1)==slot
  assert get('seqowned',2)==37+slot*2 and p.memory[0xff26]&4,('Launched pad has wrong/no Wave audio',slot,get('seqowned',2))
  assert len(handoffs)>=before+4,(n,'held pad failed to retrigger')
  key(n,False);p.tick(30);before=len(handoffs);p.tick(90);assert len(handoffs)==before,(n,'release kept rearming')
  print('PASS held direct pad and release',n,slot+1,flush=True)
 assert not uploads and not renders and bytes(p.memory[0x8000:0xa000])==vram,'Pad launch redrew static legend'
 # Quant changes must not be interpreted as pattern1/pattern3 launches.
 key('b',True);wait_slot(4);key('a',True);before=len(requests);tap('down')
 assert get('mx',3)==1 and get('mx',1)==4 and len(requests)==before
 p.tick(90);before=len(handoffs);tap('up');assert get('mx',3)==6
 p.tick(90);assert len(handoffs)>before+4
 tap('up');assert get('mx',3)==6,'Faster quant exceeded1/16'
 key('b',False);key('a',False);p.tick(30);before=len(handoffs);p.tick(90);assert len(handoffs)==before
 print('PASS live quant changes, no pad selection and1/16 cap',flush=True)
 # Left/right retain their direct pad bindings while A is held.
 key('a',True);key('right',True);wait_slot(1);key('right',False)
 key('left',True);wait_slot(3);key('left',False);key('a',False)
 print('PASS A+left/right use direct pads, not previous/next',flush=True)
 put('mx',4,3);word('mx',1,10);key('b',True)
 assert get('mx',2)==4,'Fixture failed to queue a pending fifth pad'
 key('select',True);tap('a');key('select',False);key('b',False);p.tick(150)
 assert not get('seqplaying') and not get('smooth_playback_active')
 assert get('mx',2)==255,'Stop left a stale queued launch'
 assert p.memory[symbols['__shadow_OAM_base']]
 print('PASS Select+A stop and display restoration',flush=True)
finally:p.stop(save=False)

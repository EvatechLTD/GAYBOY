"""Exercise the supplied KILLING battery without writing the user's save."""
from pathlib import Path
exec(Path('tools/test_shared_ui_tiles.py').read_text().split('\ntry:\n')[0])
assert args.save,'Supply the KILLING battery with --save; the test never writes it'
source_bytes=args.save.read_bytes()
kick_packets=[];cancelled_kicks=[]

def program(_):
 at=(p.register_file.D<<8)|p.register_file.E
 env=p.memory[0xff12];pan=p.memory[0xff25];kick=False
 for i in range(p.register_file.A):
  reg,value=p.memory[at+i*2:at+i*2+2]
  if reg==0x12:env=value
  elif reg==0x25:pan=value
  elif reg==0x14 and value&128 and env&0xf0:kick=True
 if kick:
  q=0xa500+get('song_qread')*192
  hit=(p.memory[q+3],int.from_bytes(bytes(p.memory[q+4:q+8]),'little'))
  kick_packets.append(hit)
  if not env&0xf0 or not pan&0x11:cancelled_kicks.append(hit)

a=symbols['_song_program'];p.hook_register(a>>16,a&65535,program,None)

def protected():
 # Song arrangement and note pools must survive all temporary audio caches.
 return [bytes(p.memory[1+s//4,0xa000+(s%4)*2048+480:0xa000+(s%4)*2048+1792]) for s in range(5)]

def chord(a,b):
 for k,down in ((a,True),(b,True),(b,False),(a,False)):
  mask={'start':128,'select':64,'a':16,'b':32}[k]
  (p.button_press if down else p.button_release)(k)
  for _ in range(1800):
   p.tick(1)
   if bool(get('lastpad')&mask)==down:break
  else:raise AssertionError(('Chord input timeout',k,down,state()))
 p.tick(30)

def song():
 tap('start')
 for _ in range(24):
  if get('navchoice')==54:break
  tap('down')
 assert get('navchoice')==54
 tap('a');p.tick(60);assert get('page')==29

def state():
 return {n:get(n) for n in ('page','seqplaying','song_playing','lastpad','padread','padwrite','seqservicing','editbuffer_valid','editbuffer_reading','smooth_playback_active')}

def launch_pad(label,slot=4):
 choose(18);put('mx',30+slot,4);put('dirty',1);p.tick(30)
 print(label,'before',state(),flush=True)
 tap('a');p.tick(180)
 print(label,'playing',state(),flush=True)
 assert get('mx',1)==slot and get('seqplaying') and not get('song_playing')
 tap('left');assert get('mx',4)!=30+slot,('Mixer navigation locked',state())
 put('mx',0,4);put('dirty',1);p.tick(20);tap('b')
 assert not get('seqplaying'),('Transport locked',state())

try:
 enter_app(p,symbols);put('sticky_start',1)
 before=protected()
 print('Boot',state(),flush=True)
 launch_pad('Cold mixer')
 song();choose(18);launch_pad('After editing song')
 song();chord('select','start');assert get('song_playing'),('Song failed',get('song_view',15),state())
 p.tick(3600);chord('select','start');assert not get('song_playing'),state()
 assert not cancelled_kicks,('Kick cancelled in attack packet',cancelled_kicks[:8])
 assert len(kick_packets)>120 and {s for s,pos in kick_packets}=={0,1,3,4},(len(kick_packets),{s for s,pos in kick_packets},kick_packets[-8:])
 assert all((s,pos) in kick_packets for s,pos in ((0,0),(0,16),(1,64),(3,192),(4,320))),kick_packets[:10]
 launch_pad('After playing song')
 for slot in range(4):launch_pad('Post-song pad '+str(slot+1),slot)
 assert protected()==before,'Song or resident notes changed'
 assert args.save.read_bytes()==source_bytes,'Original battery changed'
 print('PASS KILLING first-step kicks, complete song loop, all five mixer pads, navigation/stop and original save preservation')
except Exception:
 from collections import Counter
 def where():
  pc=p.register_file.PC;bank=p.memory[symbols['__current_bank']] if 0x4000<=pc<0x8000 else 0
  near=sorted((v&65535,n) for n,v in symbols.items() if n.startswith('_') and v>>16==bank and (v&65535)<=pc)
  return hex(bank),hex(pc),near[-1] if near else None
 print('LOCK',state(),where(),'SP',hex(p.register_file.SP),flush=True)
 sp=p.register_file.SP
 print('Stack',[(hex(a),hex(p.memory[a]|p.memory[a+1]<<8)) for a in range(sp,min(sp+100,0xe000),2)],flush=True)
 with open('build/killing-lock.state','wb') as f:p.save_state(f)
 samples=Counter()
 for _ in range(300):p.tick(1);samples[where()]+=1
 print('PC samples',samples.most_common(14),flush=True)
 raise
finally:p.stop(save=False)

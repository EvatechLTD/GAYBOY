"""Exercise performance MIDI through the ROM's serial receive queue."""
exec(open('tools/test_mixer_settings.py').read().split('try:\n')[0])

def send(*data):
 w=v('wr')
 for b in data:
  p.memory[S['_rx']+w]=b;w=(w+1)&255
 p.memory[S['_wr']]=w
 p.tick(16)

try:
 enter_app(p,S);choose(18)
 p.memory[S['_syncmode']]=0
 for cc,offset in [(71,0),(72,1),(77,6)]:
  for value in (0,64,127):
   send(0xbf,cc,value)
   assert v('mx',12+offset)==value,(cc,value,v('mx',12+offset))
 for cc,c in [(11,0),(17,6)]:
  for value in (127,126,0,127):
   send(0xb0,cc,value)
   assert bool(v('seqmuted')&(1<<c))==(value==127)
 for value in (127,126,0):
  send(0xb0,21,value)
  a=S['_drummutemask'];mask=p.memory[a]|p.memory[a+1]<<8
  assert bool(mask&1)==(value==127)
 # Current pad retriggers on musical boundaries while held, independent of UI.
 p.memory[0,S['_mx']+3]=7
 launches=[]
 a=S['_seq_pattern_handoff'];p.hook_register(a>>16,a&65535,lambda _:launches.append(1),None)
 send(0x90,24,100)
 assert v('seqplaying')
 p.tick(180);assert len(launches)>=3,len(launches)
 send(0x90,24,0)
 p.tick(60);n=len(launches);p.tick(120);assert len(launches)==n
 # Explicit note-off and all-notes-off both terminate held retriggering.
 for off in [(0x80,24,64),(0xb0,123,0)]:
  send(0x90,24,127);p.tick(90);before=len(launches)
  assert before>n
  send(*off);p.tick(60);n=len(launches);p.tick(120);assert len(launches)==n
 for slot in range(5):
  send(0x90,24+slot,100)
  for _ in range(300):
   if v('mx',1)==slot:break
   p.tick(1)
  assert v('mx',1)==slot,(slot,v('mx',1))
  p.tick(120);before=len(launches);p.tick(120);assert len(launches)>before
  send(0x80,24+slot,0)
 print('PASS MIDI faders, mute thresholds, held quantized retrigger and release')
finally:
 p.stop(save=False)

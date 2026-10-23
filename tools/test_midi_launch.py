"""Exercise performance MIDI through the ROM's serial receive queue."""
exec(open('tools/test_mixer_settings.py').read().split('try:\n')[0])

def send(*data):
 w=v('wr')
 for b in data:
  p.memory[S['_rx']+w]=b;w=(w+1)&255
 p.memory[S['_wr']]=w
 p.tick(16)

try:
 enter_app(p,S)
 p.memory[S['_sticky_start']]=1
 assert not v('midi_launch_enabled'),'MIDI launches must default OFF'
 p.memory[S['_syncmode']]=0
 # This fixture injects bytes into RX directly. Stop hardware serial so an
 # in-flight open-cable transfer cannot overwrite those bytes with 0xff.
 p.memory[S['_syncarmed']]=0
 p.memory[0xff02]=0
 p.memory[0xffff]=p.memory[0xffff]&~8
 # Disabled launch notes retain instrument routing and never start/switch pads.
 for note in range(24,29):
  send(0x92,note,100);send(0x82,note,0)
  assert v('mx',1)==0 and v('mx',2)==255 and not v('seqplaying')
 # Expose SYNC in the configurable quick menu, then operate the actual UI.
 p.memory[S['_pool_root']+100]=27;p.memory[S['_pool_root']+108]=ord('P');p.memory[S['_pool_root']+109]=1
 choose(27)
 tap('down');tap('down')
 configuration=tuple(v(n) for n in ('syncmode','syncslave','syncrole','seqplaying'))
 p.screen.image.save('build/sync-midi-launch-off.png')
 tap('b')
 assert v('midi_launch_enabled'),'Sync menu did not enable MIDI launching'
 assert tuple(v(n) for n in ('syncmode','syncslave','syncrole','seqplaying'))==configuration
 p.screen.image.save('build/sync-midi-launch-on.png')
 choose(18)
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
 p.memory[0,S['_mx']+3]=6
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
 # Disabling while a MIDI key is held cancels its queued/repeated launch.
 send(0x90,24,100);p.tick(180);choose(27)
 configuration=tuple(v(n) for n in ('syncmode','syncslave','syncrole','seqplaying'))
 tap('b')
 assert not v('midi_launch_enabled') and v('mx',2)==255
 assert tuple(v(n) for n in ('syncmode','syncslave','syncrole','seqplaying'))==configuration
 p.tick(120);n=len(launches);p.tick(180);assert len(launches)==n
 tap('b');assert v('midi_launch_enabled')
 p.tick(180);assert len(launches)==n,'Re-enabling revived a stale held key'
 print('PASS default OFF, Sync toggle, disabled note routing, MIDI controls, held launch/release and disable cleanup')
finally:
 p.stop(save=False)

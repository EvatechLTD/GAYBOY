"""Independent pulse gates live on tone pages and reset to full duration."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
try:
 assert [v('seqgate',i) for i in (0,1)]==[100,100]
 for c in (0,1):
  assert v('param',c*26+3)==0 and v('param',c*26+8)==0
 choose(1)
 for _ in range(4):press('down')
 assert v('cursor',1)==4
 press('left');assert v('seqgate',0)==99 and v('seqgate',1)==100
 press('a');assert v('seqgate',0)==100
 press('select');assert v('selected')==1
 for _ in range(4):press('down')
 press('left');assert v('seqgate',1)==99 and v('seqgate',0)==100
 press('a');assert v('seqgate',1)==100
 choose(10)
 press('down');assert v('seqfocus')==2
 press('down');assert v('seqfocus')==4
 press('up');assert v('seqfocus')==2
 # Measure actual pulse on/off calls against drawn duration at 120 BPM.
 from seq_storage_helpers import write_tracks
 events=[]
 def onset(_):
  c=p.register_file.A
  if c<2:events.append(('on',c,p._cycles()))
 def off(_):
  # Banked SDCC calls pass arguments above the bank-call return frame.
  c=p.memory[p.register_file.SP+6] if S['_stop']>=65536 else p.register_file.A
  if c<2:events.append(('off',c,p._cycles()))
 for name,fn in (('play',onset),('stop',off)):
  a=S['_'+name];p.hook_register(a>>16,a&65535,fn,None)
 choose(8)
 for duration in (1,4,8):
  tracks=[[] for _ in range(7)]
  tracks[0]=[[0,37,100,duration]];tracks[1]=[[0,49,100,duration]]
  write_tracks(p,S,tracks);events.clear()
  p.button_press('select');press('a');p.button_release('select');p.tick(100)
  for c in (0,1):
   start=next(t for kind,ch,t in events if kind=='on' and ch==c)
   end=next(t for kind,ch,t in events if kind=='off' and ch==c and t>start)
   ms=(end-start)*1000/4194304
   assert abs(ms-duration*125)<20,(duration,c,ms,events)
  p.button_press('select');press('a');p.button_release('select');p.tick(10)
 # Pulse tone gates remain reachable with experimental audio enabled.
 choose(16);press('a');assert v('experimental_mode')
 choose(0);choose(1)
 put('cursor',1,4);put('dirty',0,1);p.tick(20)
 previous=v('seqgate',v('selected'));press('left')
 assert v('seqgate',v('selected'))==previous-1
 press('a');assert v('seqgate',v('selected'))==100
 print('PASS: actual pulse duration matches 1/4/8 drawn steps; independent P1/P2 tone gate editing/reset, flat pulse defaults, sequencer settings skip gate')
finally:p.stop(save=False)

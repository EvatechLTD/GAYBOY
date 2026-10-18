"""Pulse kick arbitration, independent patch, thirteenth drum row and controls."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import read_tracks,write_tracks

def chord(mod,key):
 before_play=v('seqplaying')
 p.button_press(mod);p.tick(2);p.button_press(key)
 for _ in range(120):
  p.tick(1)
  if v('seqplaying')!=before_play:break
 assert v('seqplaying')!=before_play
 p.button_release(key);p.button_release(mod);p.tick(1)

try:
 choose(17);press('select');press('select')
 assert v('drumsynthvoice')==2
 assert [v('pulsekickpatch',i) for i in range(8)]==[15,48,2,1,1,2,24,1], [v('pulsekickpatch',i) for i in range(8)]
 press('right');assert v('pulsekickpatch')==15
 press('left');assert v('pulsekickpatch')==14
 press('a');assert v('pulsekickpatch')==15
 for _ in range(6):press('down')
 assert v('drumsynthrow')==6
 press('down');assert v('drumsynthrow')==7
 press('left');assert v('pulsekickpatch',7)==0
 press('b');assert p.memory[0xff10]&0x7f==0x12
 press('right');assert v('pulsekickpatch',7)==1
 press('b');assert p.memory[0xff10]&0x7f==0x1a
 p.screen.image.save('build/ui-pulsekick.png')
 choose(8)
 put('seqtrack',0,6);put('seqhead',0,0);put('drumrow',0,12);put('seqcursor',6,0);put('dirty',0,1);p.tick(15)
 press('b');assert any(e[1]==13 for e in read_tracks(p,S)[6])
 # Both tracks strike together; P1 must not overwrite the kick registers.
 tracks=[[] for _ in range(7)];tracks[0]=[[0,61,100,1],[3,65,100,1]];tracks[6]=[[0,13,127,1]];write_tracks(p,S,tracks)
 before=[v('param',i) for i in range(26)]
 chord('select','a');assert v('seqplaying')
 assert p.memory[0xff10]&0x7f==0x1a
 assert p.memory[0xff11]>>6==2
 assert [v('param',i) for i in range(26)]==before
 # The next P1 note reloads the normal tone after kick ownership expires.
 for _ in range(100):
  p.tick(1)
  if v('seqposition')==3:break
 assert v('seqposition')==3
 assert not v('pulsekickleft')
 assert v('basepitch')==64
 assert p.memory[0xff10]&0x7f==(before[4]<<4)|(before[5]<<3)|before[6]
 chord('select','a');assert not v('seqplaying');assert not v('pulsekickleft')
 # Preserve the gate of a note interrupted halfway through its sustain.
 def seed_start(pulse,kick,length=24):
  tracks=[[] for _ in range(7)];tracks[0]=pulse;tracks[6]=kick
  write_tracks(p,S,tracks);put('pulsekickpatch',6,length)
  chord('select','a');assert v('seqplaying')
 def until(predicate):
  for _ in range(180):
   if predicate():return
   p.tick(1)
  raise AssertionError('Timed out waiting for voice handoff')
 def kickleft():
  at=S['_pulsekickleft'];return sum(p.memory[at+j]<<(8*j) for j in range(4))
 def normal_note(note):
  assert v('active') and v('basepitch')==note
  assert p.memory[0xff10]&0x7f==(before[4]<<4)|(before[5]<<3)|before[6]
  assert p.memory[0xff11]>>6==before[0]
 seed_start([[0,61,99,4]],[[1,13,127,1]])
 until(lambda:kickleft()>0)
 assert not v('active') and v('seqowned')==61
 gate_at_hit=v('seqgateleft')
 until(lambda:not kickleft())
 normal_note(60)
 assert 0<v('seqgateleft')<gate_at_hit,'Resuming must not restart the note gate'
 until(lambda:v('seqowned')==0)
 assert not v('active'),'Original gate must still end normally'
 chord('select','a')
 # A P1 onset coincident with PK must resume after the hit too.
 seed_start([[0,63,88,4]],[[0,13,127,1]])
 assert kickleft() and v('seqowned')==63
 until(lambda:not kickleft());normal_note(62)
 chord('select','a')
 # A newer P1 note during a longer kick becomes the note returned to.
 seed_start([[0,61,99,4],[1,66,77,4]],[[0,13,127,4]],64)
 until(lambda:v('seqowned')==66)
 assert kickleft() and v('seqowned')==66,(kickleft(),v('seqowned'),v('seqposition'),v('seqsource'),v('seqplaying'))
 # Raw-frequency MIDI CCs may update P1 state, but cannot retune PK.
 def send_midi(data):
  for byte in data:
   at=v('wr');put('rx',at,byte);put('wr',0,(at+1)&255)
  p.tick(1)
 send_midi([0xb0,67,17,68,40])
 assert kickleft(), 'Keep test inside the long kick ownership window'
 assert p.memory[0xff14]&0x47==0x47, 'P1 raw CC changed kick frequency/length'
 until(lambda:not kickleft());normal_note(65)
 chord('select','a')
 # Never resurrect a note whose gate expired while the kick was sounding.
 seed_start([[0,61,99,1]],[[0,13,127,4]],64)
 until(lambda:not kickleft())
 assert not v('seqowned') and not v('active')
 chord('select','a')
 print('PASS: PK controls, priority, normal tone restoration, interrupted sustain, coincident/new onsets, original gate expiry and stop')
finally:p.stop(save=False)




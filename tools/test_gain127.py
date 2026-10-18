"""Validate exact gain division over its whole domain and actual DMG APU writes."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
for value in range(16130):
 assert (value+1+(value>>7))>>7 == value//127,value
# Every hardware initial-volume level and every MIDI velocity exercise the
# compiled play() routine, including velocity-zero note-offs.
for level in range(16):
 p.memory[S['_param']+1]=level
 for velocity in range(128):
  w=v('wr')
  for offset,byte in enumerate((0x90,60,velocity)):
   p.memory[S['_rx']+((w+offset)&255)]=byte
  p.memory[S['_wr']]=(w+3)&255
  for _ in range(30):
   p.tick(1)
   if v('rd')==v('wr'):break
  assert v('rd')==v('wr'),('MIDI stalled',level,velocity)
  # Consuming the last MIDI byte precedes its banked event/APU writes.
  p.tick(1)
  assert p.memory[0xff12]>>4 == level*velocity//127,(level,velocity,p.memory[0xff12])
p.stop(save=False)
print('PASS: exact gain arithmetic for all16,130products and compiled APU initial volume for all2,048level/velocitypairs')

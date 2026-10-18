"""Every Tone screen opens the complete preset picker without changing other voices."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file='))
import json
library=json.load(open('src/presets.json'))
def put(n,i,x):fixture_put(p,S,n,i,x)
def patchbytes(c):return bytes(p.memory[S['_param']+c*26:S['_param']+(c+1)*26])
try:
 for c in range(4):
  put('selected',0,c);choose(0);put('cursor',1,0)
  press('up');p.tick(8);p.screen.image.save('build/ui-tone-preset-button-'+str(c)+'.png')
  before=[patchbytes(i) for i in range(4)]
  press('a');assert v('tonepresetopen') and v('page')==1
  # Browse without loading, then cancel without changing any voice.
  press('right');press('down');press('b')
  assert not v('tonepresetopen') and before==[patchbytes(i) for i in range(4)]
  press('a');assert v('tonepresetopen')
  # All ten banks can be reached; load a role from the next bank.
  for _ in range(10):press('right')
  press('right');press('down');p.tick(12);p.screen.image.save('build/ui-tone-preset-picker.png')
  target=(v('program',c)+11)%100
  press('a');assert not v('tonepresetopen') and v('page')==1
  assert v('program',c)==target and patchbytes(c)==bytes(library[target]['values'])
  assert all(patchbytes(i)==before[i] for i in range(4) if i!=c)
 # W2 uses the same library with its own waveform/decay/table parameters.
 choose(16);press('a');assert v('experimental_mode')
 put('selected',0,4);choose(0);put('w2row',0,0);press('up');press('a');assert v('tonepresetopen')
 before=[patchbytes(i) for i in range(4)];tables=bytes(p.memory[S['_tables']:S['_tables']+96])
 press('right');press('down');press('a')
 assert v('w2program')==11 and v('w2settings',1)==library[11]['values'][1]
 assert before==[patchbytes(i) for i in range(4)] and tables==bytes(p.memory[S['_tables']:S['_tables']+96])
 print('PASS: Load Preset on all five Tone screens, 100 sounds/ten banks, cancel, explicit load, channel isolation and independent W2 adaptation')
finally:p.stop(save=False)

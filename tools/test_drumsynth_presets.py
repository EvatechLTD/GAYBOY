"""Factory drums, actual APU output, bank UI, and existing user-save compatibility."""
from pathlib import Path
import numpy as np
exec(Path('tools/test_stripped_engine.py').read_text().split('\ntry:')[0])

def data(name,size,offset=0): return bytes(get(name,offset+i) for i in range(size))
def patch(c): return data('pulsekickpatch',8) if c==7 else data('noisepatch',5,(c-5)*5)
def render():
 call('tone_preset_render')
 return ''.join(chr(b%96+32) for b in data('canvas',360))
def edge(mask):
 put('lastpad',mask);call('tone_preset_input',mask);put('lastpad',0)
def open_for(c,mode=0):
 put('page',17);put('drumsynthvoice',c-5);call('tone_user_open',mode)

try:
 put('power',1);put('master',0x77);put('experimental_mode',0)
 p.memory[0xff26]=0x80;p.memory[0xff24]=0x77
 call('eval_defaults');call('drum_init')
 # An existing user library must survive all factory loads without seeding,
 # replacing, or silently renaming any of its SRAM records.
 original=bytes((i*13+17)&255 for i in range(2080))
 p.memory[0x4000]=3;p.memory[0xa000:0xa000+len(original)]=original;p.memory[0x4000]=0
 observed={}
 for c,count in ((5,8),(6,8),(7,13)):
  assert call('drum_factory_count',c)[0]==count
  names=[]
  for index in range(count):
   call('drum_stop')
   # Stale software routes must never alter a hardware factory sound.
   put('evalpatch',91,c*16+9);put('evalpatch',128,c*16+10)
   put('evalpatch',77,c*16+11);put('coarsepitch',12,c*3);put('coarsepitch',12,c*3+1)
   assert call('drum_factory_load',c,index)[0]
   assert data('evalpatch',4,c*16+9)==bytes(4)
   assert data('coarsepitch',3,c*3)==bytes(3)
   address=0xc100
   call('drum_factory_name',c,index,address&255,address>>8)
   names.append(bytes(p.memory[address:address+9]).split(b'\0')[0].decode())
   put('drumsynthvoice',c-5);call('drum_synth_audition')
   if c==7:
    b=patch(c)
    assert p.memory[0xff10]&0x7f==(b[4]<<4)|(b[7]<<3)|b[5]
    assert p.memory[0xff12]&15==b[3]
   else:
    b=patch(c)
    assert p.memory[0xff22]==(b[1]<<4)|(b[3]<<3)|b[2]
    assert p.memory[0xff21]&15==b[4]
   audio=[p.sound.ndarray.copy()]
   for _ in range(2):p.tick(1);audio.append(p.sound.ndarray.copy())
   assert np.std(np.concatenate(audio).astype(float))>0,(c,index,'silent preset')
  observed[c]=names
  before=patch(c)
  assert not call('drum_factory_load',c,count)[0] and patch(c)==before
 p.memory[0x4000]=3;assert bytes(p.memory[0xa000:0xa000+len(original)])==original;p.memory[0x4000]=0
 assert 'RIMSHOT' in observed[7] and 'CLAPISH' in observed[6]
 assert {'CLOSED','OPEN'}<=set(observed[5])
 for c in (0,1,2,3,4,8,255):assert not call('drum_factory_load',c,0)[0]
 # Hardware patches survive user save/load and the pattern tone payload.
 for slot,c in enumerate((5,6,7)):
  assert call('drum_factory_load',c,slot)[0]
  expected=patch(c)
  assert call('user_preset_save',slot,c)[0]
  call('drum_factory_load',c,slot+1)
  assert call('user_preset_load',slot,c)[0] and patch(c)==expected
  assert not call('user_preset_load',slot,5 if c!=5 else 6)[0]
 call('tones_capture');expected=[patch(c) for c in (5,6,7)]
 for c in (5,6,7):call('drum_factory_load',c,7)
 call('tones_apply');assert [patch(c) for c in (5,6,7)]==expected
 # Each page opens its own first bank. All 13 PK entries are reachable;
 # no gap into unused melodic indices, and bank arrows wrap through users.
 for c in (5,6,7):
  open_for(c);assert ('PK' if c==7 else 'NHH' if c==5 else 'NSN')+' HARDWARE 1' in render()
  edge(2);assert 'HARDWARE 1' not in render()  # left -> user bank 4
  edge(1);assert 'HARDWARE 1' in render()
  edge(64);assert not get('tonepresetopen')
 open_for(7)
 for _ in range(12):edge(8)
 assert 'RIMSHOT' in render()
 edge(16);assert not get('tonepresetopen') and get('pulsekickpatch',1)==84
 # Load factory from bank management and save it into the existing user area.
 open_for(5,2);assert 'HARDWARE FACTORY 1' in render()
 edge(16);assert 'NHH HARDWARE 1' in render()
 edge(64);open_for(5,1);assert 'SAVE PRESET' in render() and 'HARDWARE 1' not in render()
 # Existing valid slot prompts before replacement; Select cancels safely.
 edge(16);assert 'REPLACE THIS PRESET?' in render();edge(64)
 # Standard melodic load browsing must still start in its existing ROM bank.
 put('page',1);put('selected',0);put('program',0,0);call('tone_user_open',0)
 assert 'TETRIS' in render()
 print('PASS: 29 audible hardware factory presets, per-page bank UI, all PK entries,')
 print('modulation reset, untouched user library, user/pattern round trips and melodic browsing')
 print(observed)
finally:p.stop(save=False)

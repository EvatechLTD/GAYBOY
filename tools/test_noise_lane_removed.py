"""Standalone noise is absent from editor navigation, MIDI and playback."""
from pathlib import Path
prefix=Path('tools/test_editbuffer_timing.py').read_text().split(' hits=[];probes.ROM=rom')[0]
checks=r'''
 assert not get('editirq_enabled')&8
 assert get('seqposition',3)==0 and get('seqowned',3)==0
 # Stop and cycle through real sequencer shortcuts in both directions.
 p.button_press('select');press('a');p.button_release('select');p.tick(8)
 assert not get('seqplaying')
 for direction in ('right','left'):
  visited=set()
  for _ in range(8):
   p.button_press('select');press(direction);p.button_release('select');p.tick(8)
   visited.add(get('seqtrack'))
  assert visited=={0,1,2,6},visited
 # Instrument cycling skips noise between wave and drum synthesis.
 put('page',1);put('selected',2);put('dirty',1);p.tick(12)
 p.button_press('select');press('right');p.button_release('select');p.tick(8)
 assert get('page')==17
 p.button_press('select');press('left');p.button_release('select');p.tick(8)
 assert get('page')==1 and get('selected')==2
 # Noise MIDI notes cannot claim the drum hardware anymore.
 put('syncmode',0)
 w=get('wr')
 for b in (0x93,60,127):p.memory[S['_rx']+w]=b;w=(w+1)&255
 put('wr',w);p.tick(60)
 assert not get('active',3) and not get('keycount',3)
 print('PASS noise lane absent from roll, instrument navigation, timer ownership and MIDI')
finally:p.stop(save=False)
'''
exec(prefix+checks)

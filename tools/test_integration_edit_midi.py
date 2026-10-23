"""MIDI controls while edit snapshots and native timer dispatch are active."""
from pathlib import Path
prefix=Path('tools/test_editbuffer_timing.py').read_text().split(' hits=[];probes.ROM=rom')[0]
checks=r'''
 def send(*data):
  w=get('wr')
  for b in data:
   p.memory[S['_rx']+w]=b;w=(w+1)&255
  put('wr',w);p.tick(24)
 def amplitude():
  base=get('editbuffer_base')|(get('editbuffer_base',1)<<8)
  return p.memory[2,base+6]
 assert get('editbuffer_valid') and get('editirq_enabled')&1
 put('syncmode',0)
 put('midi_launch_enabled',1)
 send(0xb0,71,0);p.tick(600)
 assert get('mx',12)==0 and amplitude()==0, ('zero',get('mx',12),amplitude(),get('editbuffer_valid'),get('page'))
 send(0xbf,71,127);p.tick(600)
 assert get('mx',12)==127 and amplitude()>0, ('full',get('mx',12),amplitude())
 send(0xb0,11,127);p.tick(60)
 assert get('seqmuted')&1 and not get('seqowned')
 send(0xb0,11,0);p.tick(100)
 assert not get('seqmuted')&1
 put('mx',1,3)
 send(0x90,24,100);p.tick(100)
 assert get('seqplaying') and get('mx',1)==0
 send(0x80,24,0);p.tick(100)
 print('PASS MIDI levels, mute/unmute and held launch coexist with edit snapshots')
finally:p.stop(save=False)
'''
exec(prefix+checks)

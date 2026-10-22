"""Playback snapshots defer edits, retain SRAM neighbors, and reset on transport."""
from pathlib import Path

prefix=Path('tools/test_editbuffer_timing.py').read_text().split(' hits=[];probes.ROM=rom')[0]
checks=r'''
 def active_base():return get('editbuffer_base')|(get('editbuffer_base',1)<<8)
 def swaps():return get('editbuffer_swaps')|(get('editbuffer_swaps',1)<<8)
 def packed(index):
  at=active_base()+index*7
  return list(p.memory[2,at:at+4])
 assert get('editbuffer_valid') and get('editirq_enabled')&1
 kits=bytes(p.memory[2,0xa800:0xad00]);clip=bytes(p.memory[3,0xb400:0xb810])
 before=swaps()
 assert packed(20)[:2]==[4,61]
 put('seqhead',0);put('seqfocus',0);put('seqcursor',4,1);put('seqpitch',60,1);put('seqapending',0);put('seqgrouptrack',255);put('dirty',1);p.tick(10);press('b')
 assert get('seqeventcounts',2)==63, {'count':get('seqeventcounts',2),'cursor':get('seqcursor',1),'pitch':get('seqpitch',1),'reading':get('editbuffer_reading'),'fields':{n:get(n) for n in ('seqhead','seqfocus','seqtrack','seqapending','seqpopup')}}
 assert swaps()==before and packed(20)[:2]==[4,61], 'Editor changed the active playback snapshot'
 p.tick(500)
 assert swaps()>before, 'Pending edit never became playable'
 assert not any(packed(i)[:2]==[4,61] for i in range(16,79)), 'Deleted note survived snapshot publication'
 assert bytes(p.memory[2,0xa800:0xad00])==kits
 assert bytes(p.memory[3,0xb400:0xb810])==clip
 print('PASS deferred deletion, next-loop publication and preserved user kits/clipboard')
 p.button_press('select');press('a');p.button_release('select');p.tick(10)
 assert not get('seqplaying') and not get('editirq_enabled') and not get('editbuffer_valid')
 assert not any(get('seqowned',i) for i in range(7))
 p.button_press('select');press('a');p.button_release('select');p.tick(800)
 assert get('seqplaying') and get('editbuffer_valid') and get('editirq_enabled')&1
 assert not any(packed(i)[:2]==[4,61] for i in range(16,79))
 print('PASS stop/restart clears stale buffered playback and rebuilds edited pattern')
 put('evalpatch',1)
 p.tick(30)
 assert not get('editirq_enabled')&1, 'ARP did not fall back to the foreground dispatcher'
 print('PASS unsupported synthesis mode uses existing playback path')
finally:p.stop(save=False)
'''
exec(prefix+checks)

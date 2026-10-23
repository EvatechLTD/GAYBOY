"""Hardware-report fixture: synth drums,2-bar Wave and one P2 note, ARP on/off."""
from pathlib import Path
import json,statistics,hashlib
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def key(n,down):
 mask={'a':16,'select':64,'up':4,'down':8}[n];start=p._cycles();(p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return (p._cycles()-start)*1000/4194304
 raise AssertionError(('input timeout',n,down))
def u16(n,i=0):return get(n,i)|(get(n,i+1)<<8)
def pixel(x,y):
 tile=p.memory[0x9800+(1+y//8)*32+x//8];base=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16;mask=128>>(x&7);off=base+(y&7)*2
 return bool(p.memory[off]&mask)+2*bool(p.memory[off+1]&mask)
def toggle(on):
 put('seqhead',1);put('dirty',1);p.tick(90);key('a',True);key('a',False);p.tick(180);assert get('evalpatch',16)==on
 put('seqhead',0);put('dirty',1);p.tick(60)
def drag(label):
 put('seqhead',0);put('seqfocus',0);put('seqgrouptrack',255);put('seqcursor',0,1);put('seqpitch',p.memory[1,0xa301]-1,1);put('seqtop',64,1);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
 acks=[];visible=[];attacks=u16('arpirq_attacks');key('a',True)
 for direction,delta in [('up',1),('down',-1)]*4:
  before=p.memory[1,0xa301];start=p._cycles();acks.append(key(direction,True));acks.append(key(direction,False))
  assert p.memory[1,0xa301]==before+delta,(label,direction,'wrong drag',before,list(p.memory[1,0xa300:0xa304]))
  x=get('rollx',2)+2;y=(get('seqtop',1)-(p.memory[1,0xa301]-1))*get('seqheight')+3
  for _ in range(1200):
   p.tick(1)
   if get('seqdrawvalid') and pixel(x,y)==3:break
  else:raise AssertionError((label,'visible note did not catch up',get('seqdrawvalid'),pixel(x,y)))
  visible.append((p._cycles()-start)*1000/4194304)
 key('a',False);p.tick(180)
 assert list(p.memory[1,0xa300:0xa304])==[0,61,110,32]
 assert u16('seqeventcounts',2)==1
 result={'mode':label,'history':get('evalpatch',29),'ack_median_ms':statistics.median(acks),'ack_max_ms':max(acks),'visible_median_ms':statistics.median(visible),'visible_max_ms':max(visible),'arp_attacks':(u16('arpirq_attacks')-attacks)&65535,'arp_mask':get('arpirq_enabled')}
 if label!='arp':assert not result['arp_mask']&2 and result['arp_attacks']==0,result
 print(result,flush=True);return result
try:
 enter_app(p,symbols);offset=0
 tracks=[[],[[0,61,110,32]],[[i,n,110,8] for i,n in zip((0,8,16,24),(37,37,40,35))],[],[],[],[[i,11,100,1] for i in range(0,32,2)]+[[i,12,100,1] for i in (4,12,20,28)]+[[i,13,110,1] for i in (0,8,16,24)]]
 for c,events in enumerate(tracks):
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',32,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 word('seqbpm',120);word('seqglobalbpm',120);word('pattern_generation',1);put('pattern_dirty',1);put('seqirqdirty',1)
 put('page',8);put('seqtrack',1);put('selected',1);put('seqhead',0);put('seqfocus',0);put('seqviewinitialized',127)
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(1200)
 rows=[drag('mono_before')];toggle(1);rows.append(drag('arp'));toggle(0);rows.append(drag('mono_after'))
 Path('build/black-note-drag-'+rom.stem+'.json').write_text(json.dumps({'rom':str(rom),'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'cases':rows},indent=2))
 print('PASS single note really moved,notes/duration preserved,and ARP stops after OFF')
finally:p.stop(save=False)

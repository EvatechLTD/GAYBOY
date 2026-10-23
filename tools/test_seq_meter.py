"""Real-ROM meter/bar editing, odd-meter generation and 256-step boundary."""
from pathlib import Path
exec(Path('tools/test_seq_gen.py').read_text().split('\ntry:')[0].replace('range(180)', 'range(1800)'))

def setting(field,direction):
 put('page',10);put('seqhead',0);put('seqfocus',field);put('dirty',1);p.tick(8)
 p.button_press('a');p.tick(4);press(direction);p.button_release('a');p.tick(12)

def line(row):
 return ''.join(chr((p.memory[S['_canvas']+row*20+i]%96)+32) for i in range(20))

try:
 enter_app(p);put('sticky_start',1);put('seqtrack',0)
 assert v('seqbeats')==4 and v('seqdenom')==4 and word('seqlength')==16
 setting(2,'up');assert word('seqlength')==32
 setting(2,'down');assert word('seqlength')==16
 assert '4/4' in line(7),line(7)
 assert '1' in line(5) and '016 STEPS/BAR' in line(16),(line(5),line(16))
 put('seqfocus',12);press('down');assert v('seqfocus')==1
 press('up');assert v('seqfocus')==12
 print('PASS default 4/4 one bar, bar edits, navigation and displayed step resolution',flush=True)
 for beats,denom,bar in [(3,4,12),(5,8,10),(7,8,14),(11,8,22),(32,2,256),(32,16,32),(1,16,1)]:
  put('seqbeats',beats);put('seqdenom',denom);setword('seqlength',bar)
  other=word('seqlength',1)
  setting(2,'up');assert word('seqlength')==min(2,256//bar)*bar,(beats,denom,word('seqlength'))
  setting(2,'down');assert word('seqlength')==bar
  assert word('seqlength',1)==other
  setting(2,'left');assert word('seqlength')==bar
  setting(2,'right');assert word('seqlength')==min(11,256//bar)*bar
  print('PASS meter',beats,denom,'bar steps',bar,flush=True)
 put('seqbeats',4);put('seqdenom',4);setword('seqlength',17)
 put('dirty',1);p.tick(20);assert 'CUSTOM' in line(5)
 setting(2,'up');assert word('seqlength')==32
 setword('seqlength',17);setting(2,'down');assert word('seqlength')==16
 put('seqbeats',31);setting(7,'up');assert v('seqbeats')==32
 setting(7,'up');assert v('seqbeats')==32
 put('seqbeats',1);setting(7,'down');assert v('seqbeats')==1
 put('seqdenom',2);setting(8,'down');assert v('seqdenom')==2
 for expected in (4,8,16):setting(8,'up');assert v('seqdenom')==expected
 setting(8,'up');assert v('seqdenom')==16
 # Meter preserves every track length, including whole and partial bars.
 put('seqbeats',4);put('seqdenom',4)
 setword('seqlength',16,0);setword('seqlength',32,1);setword('seqlength',17,2)
 setting(8,'up');assert v('seqdenom')==8
 assert [word('seqlength',c) for c in range(3)]==[16,32,17]
 setting(8,'down');assert [word('seqlength',c) for c in range(3)]==[16,32,17]
 print('PASS custom lengths, bounds, meter preserves track lengths and independent bar counts',flush=True)
 for beats,denom,bar in [(5,8,10),(11,8,22),(32,2,256)]:
  put('seqbeats',beats);put('seqdenom',denom);setword('seqlength',bar)
  write_tracks([[],[],[],[],[],[],[]]);put('page',8);put('seqfocus',0);put('navopen',0)
  open_gen();put('gentype',0);put('genrhythm',6);put('genhits',5);put('genrotation',0);put('genlength',0);trigger()
  events=read_tracks()[0];assert len(events)==5,(beats,denom,events)
  assert len({e[0] for e in events})==5 and all(e[0]<bar for e in events)
  press('select');assert not v('genopen')
  print('PASS actual Generate Euclid in meter',beats,denom,'including full-bar counter',flush=True)
 # Meter changes must not change the fixed sixteenth-note clock.
 from arp_probe_helpers import hook_attacks
 hits=[];frequencies=[];hook_attacks(p,Path('build/GAYBOY.gb'),S,1,hits.append,frequencies.append,include_editbuffer=True)
 put('syncmode',0);put('syncarmed',0);p.memory[0xff07]=0;p.memory[0xff06]=p.memory[0xff05]=240;p.memory[0xff0f]&=~4;p.memory[0xff07]=4
 for beats,denom,bar,bpm in [(4,4,16,120),(5,8,10,120),(11,8,22,120),(11,8,22,240)]:
  write_tracks([[],[[i,61,127,1] for i in range(bar)],[],[],[],[],[]])
  put('seqbeats',beats);put('seqdenom',denom);setword('seqlength',bar,1);setword('seqbpm',bpm);setword('seqglobalbpm',bpm);setword('seqcachedbpm',0)
  for c in range(3):p.memory[S['_evalpatch']+c*16]=0;p.memory[S['_evalpatch']+c*16+13]=0
  put('seqtrack',1);put('selected',1);put('page',8);put('seqhead',0);put('seqfocus',0);put('navopen',0);put('dirty',1)
  p.button_press('select');p.tick(8);press('a');p.button_release('select');p.tick(200)
  assert v('seqplaying') and v('editirq_enabled')&2
  hits.clear();p.tick(240);gaps=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])];expected=15000/bpm
  assert len(gaps)>20 and max(abs(g-expected) for g in gaps)<1.5,(beats,denom,bpm,gaps)
  print('PASS fixed 1/16 playback',beats,denom,bpm,'BPM max error ms',round(max(abs(g-expected) for g in gaps),3),flush=True)
  p.button_press('select');p.tick(8);press('a');p.button_release('select');p.tick(20);assert not v('seqplaying')
 # Live meter changes retain both halves of a32-step phrase and its timing.
 put('seqbeats',4);put('seqdenom',4);setword('seqbpm',120);setword('seqglobalbpm',120);setword('seqcachedbpm',0)
 write_tracks([[],[[0,61,127,1],[16,65,127,1]],[],[],[],[],[]])
 for c in range(7):setword('seqlength',32,c)
 put('page',8);put('seqfocus',0);put('seqhead',4);put('dirty',1);p.tick(100)
 assert '2 BARS' in line(0),line(0)
 p.button_press('select');p.tick(8);press('a');p.button_release('select');p.tick(240)
 hits.clear();p.tick(480);before=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])]
 assert len(before)>=2 and all(abs(g-2000)<2 for g in before),before
 setting(8,'up');assert v('seqplaying') and v('seqdenom')==8 and word('seqlength',1)==32
 p.tick(240);hits.clear();frequencies.clear();p.tick(480);after=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])]
 assert len(after)>=2 and all(abs(g-2000)<2 for g in after),after
 assert len(set(frequencies))==2,'second-half note missing'
 assert all(a!=b for a,b in zip(frequencies,frequencies[1:])),frequencies
 assert word('seqbpm')==120
 print('PASS LIVE 4/4 -> 4/8:32steps and both phrase halves preserved;2bars ->4bars',flush=True)
 put('page',8);put('seqfocus',0);put('seqhead',4);put('dirty',1);p.tick(60)
 assert '4 BARS' in line(0),line(0)
 p.button_press('select');p.tick(8);press('a');p.button_release('select');p.tick(20)
 p.button_press('a');p.tick(4);press('up');p.button_release('a');p.tick(40)
 assert word('seqlength',1)==40 and '5 BARS' in line(0),(word('seqlength',1),line(0))
 print('PASS sequencer header displays/edits bars',flush=True)
finally:p.stop(save=False)


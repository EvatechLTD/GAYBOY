"""Prepared arps preserve pitch order, native registers, fallback and transport."""
from pathlib import Path
from io import BytesIO
import sys
exec(Path('tools/test_arp_stress.py').read_text().split('reports=[]')[0])
observed=[]
p.stop(save=False)
p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(args.save.read_bytes()));p.set_emulation_speed(0)
hits=[];hook_attacks(p,rom,S,1,hits.append,observed.append)
patterns={0:[0,1,2,3],1:[3,2,1,0],2:[0,1,2,3,2,1],4:[3,2,1,0,1,2],5:[0,3,1,2],6:[1,2,0,3],10:[0,3,1,2,1,3]}
try:
 enter_app(p,S);put('seqtrack',1);put('selected',1);put('seqhead',1);put('seqfocus',0);put('seqdrawvalid',0);put('dirty',1);p.tick(250)
 fixture=BytesIO();p.save_state(fixture)
 # Frequencies come from the exported ROM pitch lookup, not the implementation cache.
 addr=S['_notes'];bank=addr>>16;base=addr&65535
 pitches=[60,63,67,72];freqs=[p.memory[bank,base+n*2]|p.memory[bank,base+n*2+1]<<8 for n in pitches]
 for order in range(11):
  fixture.seek(0);p.load_state(fixture)
  put('evalpatch',3,18);put('evalpatch',order,21);word('pattern_generation',(get('pattern_generation')|get('pattern_generation',1)<<8)+1)
  hits.clear();observed.clear();key('select',True);key('a',True);key('a',False);key('select',False);p.tick(50)
  assert len(observed)>10,(order,len(observed))
  assert set(observed)<=set(freqs),(order,observed,freqs)
  ranks=[freqs.index(f) for f in observed]
  if order in patterns:
   expected=patterns[order]
   assert ranks[:12]==[expected[i%len(expected)] for i in range(12)],(order,ranks[:12],expected)
   assert get('arpirq_enabled')&2,(order,'prepared path missing')
  else:assert not get('arpirq_enabled')&2,(order,'random modes must keep generic selection')
  key('select',True);key('a',True);key('a',False);key('select',False);p.tick(2)
  assert not get('seqplaying') and not get('arpirq_enabled')
  before=len(hits);p.tick(100);assert len(hits)==before,(order,'attacks continued after stop')
  print('PASS order and stop',order,flush=True)
 fixture.seek(0);p.load_state(fixture);put('evalpatch',3,18);word('pattern_generation',(get('pattern_generation')|get('pattern_generation',1)<<8)+1)
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(180)
 for page in (1,18,8):
  put('page',page);put('dirty',1);before=len(hits);p.tick(120)
  assert get('arpirq_enabled')&2 and len(hits)>before+25,(page,'page change interrupted native arp')
 print('PASS native arp continues through instrument, mixer and sequencer pages',flush=True)
 put('evalpatch',0,20);put('evalpatch',1,17);word('evalpatch',7,22);word('pattern_generation',(get('pattern_generation')|get('pattern_generation',1)<<8)+1);word('seqdeadline',1);p.tick(180)
 key('select',True);key('a',True);key('a',False);key('select',False)
 phase=bytes(get('arpclock',4+i) for i in range(4));p.tick(120)
 assert bytes(get('arpclock',4+i) for i in range(4))==phase,'Stopped freerun phase advanced'
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(120)
 assert get('arpirq_enabled')&2 and get('seqplaying'),'Retained freerun did not restart'
 print('PASS retained freerun stop/resume phase',flush=True)
finally:p.stop(save=False)

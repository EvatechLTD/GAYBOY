"""Prepared native LFO:actual pitch writes, ownership and navigation under load."""
import sys,ast,statistics,json
from pathlib import Path
import pyboy
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
from arp_probe_helpers import hook_attacks
# Observe timer writes and note attacks: a loop-boundary trigger can change
# pitch before the next timer write and must not be mistaken for LFO jitter.
data=rom.read_bytes();tree=ast.parse((Path(pyboy.__file__).parent/'core/opcodes.py').read_text())
lengths=next(ast.literal_eval(n.value.args[1]) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OPCODE_LENGTHS' for t in n.targets))
ptr=symbols['_lfo_irq_tick'];bank=ptr>>16;pc=ptr&65535;end=min(v&65535 for k,v in symbols.items() if k.startswith('_') and v>>16==bank and (v&65535)>pc)
hits=[];freqs=[];low=[0];irqcost=[];irqentry=[];returns=set()
attackcycle=[0]
def attack_time(cycle):attackcycle[0]=cycle
def attack_frequency(f):
 if not freqs or f!=freqs[-1]:hits.append(attackcycle[0]);freqs.append(f)
hook_attacks(p,rom,symbols,2,attack_time,attack_frequency,include_editbuffer=True)

def entered(_):
 sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8
 irqentry.append((sp+2,p._cycles()))
 if ret not in returns:returns.add(ret);p.hook_register(0,ret,returned,None)
def returned(_):
 if irqentry and p.register_file.SP==irqentry[-1][0]:irqcost.append(p._cycles()-irqentry.pop()[1])
p.hook_register(symbols['_lfo_irq_tick']>>16,symbols['_lfo_irq_tick']&65535,entered,None)
def observe(target):
 if target==0x1d:low[0]=p.register_file.A;return
 f=low[0]|((p.register_file.A&7)<<8)
 if not freqs or f!=freqs[-1]:hits.append(p._cycles()+12);freqs.append(f)
while pc<end:
 at=pc if not bank else bank*16384+pc-16384;op=data[at];size=2 if op==0xcb else lengths[op]
 if op==0xe0 and data[at+1] in (0x1d,0x1e):p.hook_register(bank,pc,observe,data[at+1])
 pc+=size

def key(name,down):
 mask={'a':16,'b':32,'select':64,'up':4,'down':8,'right':1,'left':2,'start':128}[name];begin=p._cycles()
 (p.button_press if down else p.button_release)(name)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return (p._cycles()-begin)*1000/4194304
 raise AssertionError(('input timeout',name,down))
def tap(name):return max(key(name,True),key(name,False))
def changed():word('pattern_generation',(get('pattern_generation')|(get('pattern_generation',1)<<8))+1);put('seqirqdirty',1);word('seqdeadline',1)
def setup(kind,division=3,timing=0,bpm=120,free=0):
 put('globalmod',2,4);put('globalmod',division,6);put('globalmod',not bool(free),7);put('globalmod',timing,8);put('globalmod',1,9);put('globalmod',free,5)
 for c in range(3):
  put('evalpatch',0,c*16);put('evalpatch',0,c*16+13);put('evalpatch',64 if kind in ('fine','both') else 0,c*16+9);put('evalpatch',1,c*16+8);put('evalpatch',0,c*16+10)
  put('coarsepitch',0,c*3);put('coarsepitch',12 if kind in ('coarse','both') else 0,c*3+1);put('coarsepitch',1,c*3+2)
 word('seqbpm',bpm);word('seqglobalbpm',bpm);word('seqcachedbpm',0);changed();p.tick(180)
 assert get('lfo_irq_mask')&4 and get('editirq_enabled')&3,(kind,get('lfo_irq_mask'),get('editirq_enabled'),get('editbuffer_irq_mask'),get('editbuffer_valid'),get('seqdeadline')|(get('seqdeadline',1)<<8),get('seqticks')|(get('seqticks',1)<<8),[get('evalpatch',c*16+13) for c in range(3)])

def measure(kind,expected,nav=False,tolerance=10):
 hits.clear();freqs.clear();irqcost.clear();acks=[]
 if nav:
  for _ in range(12):acks.extend((tap('up'),tap('down')))
  p.tick(120)
 else:p.tick(240)
 gaps=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])]
 assert len(gaps)>10,(kind,len(gaps))
 error=max(abs(g-expected) for g in gaps)
 assert error<tolerance,(kind,expected,min(gaps),max(gaps),error,'IRQmaxms',max(irqcost,default=0)*1000/4194304)
 assert len(set(freqs))==2,(kind,set(freqs))
 assert get('lfo_irq_mask')&4
 row={'kind':kind,'nav':nav,'edges':len(gaps),'median_ms':statistics.median(gaps),'max_error_ms':error,'max_input_ms':max(acks,default=0),'pitches':sorted(set(freqs)),'max_worker_ms':max(irqcost,default=0)*1000/4194304};print(row,flush=True);return row

try:
 enter_app(p,symbols);offset=0
 for c in range(7):
  events=[[0,61,127,64]] if c<3 else [[i,11,100,1] for i in range(0,16,2)] if c==6 else []
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',64 if c<3 else 16,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 put('syncmode',0);put('syncarmed',0);p.memory[0xff07]=0;p.memory[0xff06]=p.memory[0xff05]=240;p.memory[0xff0f]&=~4;p.memory[0xff07]=4
 put('seqtrack',2);put('selected',2);put('page',8);put('seqfocus',0);put('seqhead',0);put('seqpitch',60,2);put('seqtop',72,2);put('dirty',1);changed()
 key('select',True);tap('a');key('select',False);p.tick(600);assert get('seqplaying');print('initial state',get('editbuffer_valid'),get('editbuffer_irq_mask'),get('seqdeadline')|(get('seqdeadline',1)<<8),get('seqticks')|(get('seqticks',1)<<8),flush=True)
 rows=[]
 for kind in ('fine','coarse','both'):
  setup(kind);rows.append(measure(kind,31.25,tolerance=1.5));rows.append(measure(kind,31.25,True,tolerance=1.5))
 setup('fine',4);rows.append(measure('1/16',62.5))
 setup('fine',3,1);rows.append(measure('triplet',1000/48,tolerance=10))
 setup('fine',3,2);rows.append(measure('dotted',46.875,tolerance=10))
 setup('fine',3,0,240);rows.append(measure('240BPM',15.625))
 setup('fine',free=34);rows.append(measure('free34',1000/(34*60/256)/2,tolerance=10))
 # Continuous shapes exercise coefficient changes on every modulation update.
 setup('both')
 for shape in (0,1,3,4):
  put('globalmod',shape,4);changed();p.tick(90);irqcost.clear()
  latency=max(tap('up'),tap('down'));p.tick(120)
  assert get('seqplaying') and get('lfo_irq_mask')==7
  cost=max(irqcost,default=0)*1000/4194304
  assert latency<150 and cost<1.5,(shape,latency,cost)
  print({'shape':shape,'max_input_ms':latency,'max_worker_ms':cost},flush=True)
 # ADSR pitch,fine detune and external slave clock retain generic fallback.
 put('evalpatch',0,2*16+8);changed();p.tick(90);assert not get('lfo_irq_mask')&4
 put('evalpatch',1,2*16+8);changed();p.tick(90);assert get('lfo_irq_mask')&4
 word('finepitch',1,4);changed();p.tick(90);assert not get('lfo_irq_mask')&4
 word('finepitch',0,4);changed();p.tick(90);assert get('lfo_irq_mask')&4
 put('syncmode',1);put('syncslave',1);changed();p.tick(90);assert not get('lfo_irq_mask')
 Path('build/lfo-irq-test.json').write_text(json.dumps(rows,indent=2));print('PASS native LFO rates,three voices,navigation and fallback',flush=True)
finally:p.stop(save=False)

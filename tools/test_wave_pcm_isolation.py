"""DMG PCM ownership regression; disposable SRAM and real MIDI/event dispatch."""
from pathlib import Path
import json
ns={}
source=Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
exec(source.replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file='),ns)
p,S,v,choose,press,send=(ns[x] for x in ('p','S','v','choose','press','send'))
phase=['setup'];hits=[]
from seq_storage_helpers import fixture_put
def put(n,i,x):fixture_put(p,S,n,i,x)
def hook(name):
 a=S['_'+name]
 def entered(_):
  if v('waveengine')==3:hits.append({'phase':phase[0],'hook':name,'pcm_busy':bool(v('mixrunning') or v('drumon') or v('drumon',1))})
 p.hook_register(a>>16 if a>=65536 else 0,a&65535,entered,None)
try:
 # Enable deliberately to expose stale poly/W2 and CC paths hidden by native-only mode.
 choose(7);choose(18)
 for c in range(6):
  for i in range(64):put('seqnotes',c*64+i,0)
 for c in range(7):put('seqlength',c,16)
 # Factory MACHINE kit has eight populated samples; row ten is silent.
 for i in range(128):put('drumhits',i,1 if i%2==0 else 0);put('noisehits',i,0)
 put('seqbpm',0,120);put('seqbpm',1,0);put('seqmode',0,0)
 # Deliberately arm old W1 table/held/poly state before DRUM takes ownership.
 put('tablemode',2,1);put('wavepending',0,1);put('polyowner',2,1);put('keycount',2,1)
 put('keystack',16,60);put('keyvel',16,127)
 mx=S['_mx'];p.memory[mx+4]=0;press('a');assert v('seqplaying') and v('waveengine')==3
 for name in ('wave','enginenote','mixrender','softtable'):hook(name)
 phase[0]='drum_only';p.tick(90)
 assert not hits,('DRUM-only invoked normal wave path',hits)
 phase[0]='direct_wave_cc_bend'
 send([0x92,60,127,0xb2,64,127,0xe2,127,127,0xb2,69,127,0x95,60,127])
 direct=list(hits);hits.clear()
 phase[0]='poly_note_and_cc'
 for _ in range(120):
  if v('drumon') or v('drumon',1):break
  p.tick(1)
 assert v('drumon') or v('drumon',1)
 # Occupy both pulses so the poly allocator must select CH3.
 put('active',0,1);put('active',1,1);put('polynext',0,2)
 send([0x94,64,127,0xb4,64,0,0x84,64,0]);p.tick(10)
 poly=list(hits);hits.clear()
 phase[0]='native_audition'
 put('selected',0,2);choose(0);press('b');p.tick(10)
 audition=list(hits);hits.clear()
 phase[0]='sample_eof_gap'
 for i in range(128):put('drumhits',i,0)
 p.tick(240)
 assert not v('drumon') and not v('drumon',1)
 send([0x82,60,0,0xb2,64,0,0xe2,0,64,0x85,60,0,0xb4,64,0,0x84,64,0])
 assert v('waveengine')==3,'Non-note events relinquished PCM during a sequence gap'
 press('b')
 gap=list(hits)
 result={'drum_only_normal_wave_calls':0,'direct_wave_calls':direct,'poly_calls':poly,'audition_calls':audition,'eof_gap_calls':gap,'waveengine':v('waveengine'),'softon':[v('softon',i) for i in range(2)]}
 Path('build/wave-pcm-isolation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 assert not direct and not poly and not audition and not gap,'PCM ownership breached; see build/wave-pcm-isolation.json'
 # A later real W1 note may reclaim idle CH3 while transport still runs.
 assert v('seqplaying');send([0x92,67,127]);assert v('waveengine')==0
 for i in range(128):put('drumhits',i,1 if i%2==0 else 0)
 p.tick(30);assert v('waveengine')==3 and (v('drumon') or v('drumon',1))
 choose(18);p.memory[mx+4]=0;press('a');assert not v('seqplaying')
 send([0x82,67,0,0xb2,64,0]);assert v('waveengine')==3
 send([0x92,67,127]);assert v('waveengine')==0
 print('PASS: DRUM sequence and MIDI controls never invoke ordinary wave synthesis while PCM owns CH3')
finally:p.stop(save=False)

"""256-step lanes share hash buckets without playing another lane's notes."""
from pathlib import Path
from arp_probe_helpers import hook_attacks
exec(Path('tools/test_live_note_plot.py').read_text().split('\ntry:')[0])
registry={};observed=[[],[],[]]
def register(b,a,f,c):
 site=b,a
 if site not in registry:
  registry[site]=[];p.hook_register(b,a,lambda k:[fn(ctx) for fn,ctx in tuple(registry[k])],site)
 registry[site].append((f,c))
for c in range(3):hook_attacks(p,rom,symbols,c,lambda _:None,lambda f,c=c:observed[c].append(f),include_editbuffer=True,register_hook=register)
try:
 enter_app(p,symbols);offset=0
 pitches=[[48,50,52,53],[60,62,64,65],[24,26,28,29]]
 for c in range(7):
  events=[[i*64,n+1,110,4] for i,n in enumerate(pitches[c])] if c<3 else [[0,11,100,1]] if c==6 else []
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',256,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
  if c<3:
   for i in (0,9,13):put('evalpatch',0,c*16+i)
 put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0;put('experimental_mode',1);put('waveengine',0);put('mod_bypass',1)
 put('seqirqdirty',1);put('eval_moddirty',1);put('page',8);put('seqtrack',2);put('selected',2);put('seqhead',0);put('seqfocus',0);put('pattern_dirty',1);word('pattern_generation',1);word('seqbpm',120);word('seqglobalbpm',120);p.tick(90)
 key('select',True);key('start',True);key('start',False);key('select',False);p.tick(6100)
 assert get('editirq_enabled')==7,get('editirq_enabled')
 a=symbols['_notes'];bank=a>>16;at=a&65535
 for c in range(3):
  expected=[p.memory[bank,at+(n+(12 if c==2 else 0))*2]|p.memory[bank,at+(n+(12 if c==2 else 0))*2+1]<<8 for n in pitches[c]]
  assert len(observed[c])>=12,(c,len(observed[c]))
  assert all(f==expected[i%4] for i,f in enumerate(observed[c])),(c,observed[c],expected)
 print('PASS 256-step P1/P2/Wave, three wraps, colliding drum hashes, no cross-lane pitches')
finally:p.stop(save=False)

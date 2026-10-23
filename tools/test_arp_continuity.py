"""Unrelated edit generations cannot retrigger a continuous native chord."""
from pathlib import Path
exec(Path('tools/test_arp_stress.py').read_text().split('reports=[]')[0])
restarts=[]
a=S['_arp_native_sound']
p.hook_register(a>>16,a&65535,lambda _:restarts.append(p._cycles()) if p.register_file.A==1 else None,None)
try:
 enter_app(p,S);put('seqtrack',1);put('selected',1);put('seqhead',1);put('seqfocus',0);put('dirty',1);p.tick(180)
 word('seqbpm',240);word('seqglobalbpm',240);put('evalpatch',5,18);put('evalpatch',1,19)
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(200)
 assert get('arpirq_enabled')&2
 hits.clear();restarts.clear()
 for _ in range(120):
  word('pattern_generation',(get('pattern_generation')|(get('pattern_generation',1)<<8))+1);word('seqdeadline',1);p.tick(11)
 intervals=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])]
 assert not restarts,('unnecessary foreground chord retriggers',len(restarts))
 assert len(intervals)>100 and max(abs(x-1000/12) for x in intervals)<1.5,(len(intervals),min(intervals),max(intervals))
 print('PASS 120 unrelated edit generations across live 240 BPM triplet loops; no foreground retriggers; max error',round(max(abs(x-1000/12) for x in intervals),3),'ms')
finally:p.stop(save=False)

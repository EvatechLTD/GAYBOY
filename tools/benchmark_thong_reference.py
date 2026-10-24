"""Frozen tuned-main Smooth reference with the same basic song workload."""
from pathlib import Path
from io import BytesIO
import json
from arp_probe_helpers import hook_attacks
exec(Path('tools/test_prepared_drums.py').read_text().split('\ntry:\n')[0])
melody=[[],[],[]];registry={}
def register(b,a,f,c):
 site=b,a
 if site not in registry:registry[site]=[];p.hook_register(b,a,lambda k:[fn(ctx) for fn,ctx in registry[k]],site)
 registry[site].append((f,c))
for c in (1,2):hook_attacks(p,rom,S,c,lambda cy,c=c:melody[c].append(cy),include_editbuffer=True,register_hook=register)
try:
 tracks=[[],[[0,61,127,16],[16,65,127,16]],[[0,37,127,32]],[],[],[],[[s,13,127,1] for s in (0,6,10)]+[[s,12,127,1] for s in (4,12)]+[[s,11,127,1] for s in range(16)]]
 setup_fixture();put('evalpatch',0,16);put('evalpatch',0,29);word('seqlength',32,4);put('sticky_start',1)
 transport();p.tick(3600)
 result={}
 for kind,cycles,nominal in [('noise',[h['cycle'] for h in noise_hits],125),('kick',[h['cycle'] for h in kick_hits],125),('p2',melody[1],2000),('wave',melody[2],4000)]:
  gaps=[(b-a)/4194.304 for a,b in zip(cycles,cycles[1:])]
  result[kind]={'hits':len(cycles),'max_grid_error_ms':max((abs(g-round(g/nominal)*nominal) for g in gaps),default=0)}
 assert get('drum_irq_active') and len(noise_hits)>450
 Path('build/thong-reference.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:p.stop(save=False)

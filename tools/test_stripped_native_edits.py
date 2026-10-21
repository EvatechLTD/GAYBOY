"""Native edit parity with drumseq across P1/P2/Wave/Noise and chord history."""
from pathlib import Path
import json,contextlib,io
all_reports=[]
for name in ('resize','groups'):
 source=Path('tools/test_stripped_'+name+'.py').read_text()
 if name=='resize':source=source.replace('((6,5),(6,0),(0,0))','((0,0),(1,0),(2,0),(3,0))')
 else:source=source.replace('((6,5,2),(6,3,2),(6,0,2),(0,0,2),(6,0,6),(6,5,6),(0,0,6))','((0,0,2),(1,0,2),(2,0,2),(3,0,2),(0,0,6),(1,0,6),(2,0,6),(3,0,6))')
 source=source.replace("'build/stripped-resize.json'","'build/stripped-native-resize.json'").replace("'build/stripped-groups.json'","'build/stripped-native-groups.json'")
 for mode,history in ((0,0),(1,1),(0,1)):
  run=source.replace("put('seqtrack',track);", "put('seqtrack',track);put('evalpatch',%d if track<3 else 0,track*16);put('evalpatch',%d,track*16+13);"%(mode,history))
  print('TEST',name,'history',history,flush=True)
  with contextlib.redirect_stdout(io.StringIO()):exec(compile(run,'native-'+name,'exec'))
  for result in reports:
   assert result['ready_ms']<350,(name,mode,history,result)
   all_reports.append(dict(result,test=name,mode=mode,history=history))
Path('build/stripped-native-edits.json').write_text(json.dumps(all_reports,indent=2)+'\n')
print('PASS: native plot/drag/resize/group/selection pixels and local rendering; worst ready time',round(max(r['ready_ms'] for r in all_reports),2),'ms')

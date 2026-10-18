"""Build a separate hardware reproduction ROM with the recorded demo preloaded."""
from pathlib import Path
import argparse,json,subprocess,sys,hashlib
from kit_demo import KitDemo
from record_sameboy_kit import Memory
from seq_storage_helpers import read_tracks,write_tracks
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=ROOT/'gayboydemo.gb')
parser.add_argument('--work-dir',type=Path,default=ROOT/'build/hardware-demo')
args=parser.parse_args()
symbols={l.split()[1]:int(l.split()[2],16) for l in (ROOT/'build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
class Fixture:
 def __init__(self):self.memory=Memory()
p=Fixture();workflow=KitDemo(p,symbols);workflow.prepare_parts()
tracks=read_tracks(p,symbols)
recorded=json.loads((ROOT/'recordings/GAYBOY-30sec-909-live-drums-SameBoy.json').read_text())
tracks[6]=recorded['composition']['final_drum_events'];write_tracks(p,symbols,tracks)
for name,value in [('drumkit',2),('kitchoice',2),('seqmuted',0),('seqsolo',0),('seqtrack',1),('seqhead',0),('seqcursor',0),('dirty',1),('seqdrawvalid',0)]:p.memory[symbols['_'+name]]=value
p.memory[symbols['_seqcursor']+1]=0
p.memory[symbols['_seqpitch']+1]=48;p.memory[symbols['_seqtop']+1]=59
# No audio changes: copy the exact demo fixture writes into a banked boot loader.
addresses=sorted({a for a,v in p.memory.writes});groups=[]
for a in addresses:
 if groups and a==groups[-1][-1]+1:groups[-1].append(a)
 else:groups.append([a])
out=args.work_dir.resolve();out.mkdir(parents=True,exist_ok=True)
code=['#pragma bank 38','#include "api.h"']
for i,g in enumerate(groups):code.append('static const uint8_t data%d[]={%s};'%(i,','.join(str(p.memory[a]) for a in g)))
code.append('void hardware_demo_load(void) BANKED {')
for i,g in enumerate(groups):code.append('memcpy((void *)0x%04x,data%d,%d);'%(g[0],i,len(g)))
code.append('}')
(out/'demo.c').write_text('\n'.join(code))
main=(ROOT/'src/main.c').read_text();main=main.replace('void main(void){','void hardware_demo_load(void) BANKED;\nvoid main(void){',1).replace('intro_run();DISPLAY_OFF;','DISPLAY_OFF;',1).replace('ui_init();DISPLAY_ON;','ui_init();hardware_demo_load();DISPLAY_ON;',1).replace('lastframe=sys_time;{uint16_t inputframe','lastframe=sys_time;seq_transport();{uint16_t inputframe',1)
assert 'hardware_demo_load();' in main and 'seq_transport();{uint16_t' in main
(out/'main.c').write_text(main)
compiler=ROOT/'tools/gbdk/bin/lcc.exe'
for name in ('main','demo'):
 subprocess.run([str(compiler),'-Wf--opt-code-size','-Wa-l','-I'+str(ROOT/'src'),'-c','-o',str(out/(name+'.o')),str(out/(name+'.c'))],cwd=ROOT,check=True)
# Preserve the normal link order, replacing main only. Nothing in build/objects is changed.
source=(ROOT/'tools/build_rom.py').read_text();names=source.split("names='")[1].split("'.split()")[0].split()
objects=[out/'main.o' if n=='main' else ROOT/'build/objects'/(n+'.o') for n in names]+[out/'demo.o']
output=args.output.resolve()
subprocess.run([str(compiler),'-Wl-m','-Wl-j','-Wm-ynGAYBOYDEMO','-Wm-yt0x1B','-Wm-yo64','-Wm-ya4','-o',str(output),*map(str,objects)],cwd=ROOT,check=True)
s={l.split()[1]:int(l.split()[2],16) for l in output.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
for a in addresses:
 assert 0xa000<=a<0xe000
# All fixture pointers must still address the same symbols after linking the variant.
for name,address in symbols.items():
 if name.startswith('_') and 0xa000<=address<0xe000 and name in s:assert s[name]==address,(name,address,s[name])
assert s['s__GSFINAL']+s['l__GSFINAL']<=0x4000
assert s['s__HEAP_END']<=0xd800
assert all(v<=0x4000 for n,v in s.items() if n.startswith('l__CODE_'))
r=output.read_bytes();assert len(r)==1048576 and r[0x147]==0x1b and r[0x149]==3
assert (sum(r)-r[0x14e]-r[0x14f])&65535==int.from_bytes(r[0x14e:0x150],'big')
report={'rom':str(output),'sha256':hashlib.sha256(r).hexdigest(),'bpm':95,'kit':'TR-909','gates':[88,90], 'tracks':tracks,'fixture_bytes':len(addresses),'autoplay':True,'intro_skipped':True,
        'audio_source_sha256':{name:hashlib.sha256((ROOT/'src'/name).read_bytes()).hexdigest() for name in ('main.c','global.c')}}
(out/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='tracks'},indent=2))

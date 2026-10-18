"""Detect live tile replacement against the real visible map during the demo.

Tile data shared by an outgoing screen must stay immutable until detached.
Also measure the same sequencer dispatch cadence in emulated CPU cycles.
"""
import argparse
from collections import Counter
from io import BytesIO
import json
from pathlib import Path
from pyboy import PyBoy
from quick_demo import QuickDemo

ap=argparse.ArgumentParser()
ap.add_argument('--rom',default='build/GAYBOY.gb')
ap.add_argument('--report',default='build/display-transitions.json')
ap.add_argument('--allow-exposed',action='store_true')
ap.add_argument('--extra-pages',action='store_true',help='Continue playback through settings, synth, mixer, save and roll transitions')
args=ap.parse_args()
symbols={line.split()[1]:int(line.split()[2],16) for line in Path(args.rom).with_suffix('.noi').read_text().splitlines() if line.startswith('DEF ')}
p=PyBoy(args.rom,window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
p.tick(150);p.button_press('start');p.tick(15);p.button_release('start');p.tick(30)
d=QuickDemo(p,symbols)
for _ in d.prepare():p.tick()
d.frames=0;d.log=[];d.stage_times=[];d.sequence=d.run()
exposed=[];dispatch=[];blanks=0;blank_run=0;max_blank_run=0;blank_locations=Counter()
def hook(name,fn):
 address=symbols['_'+name];p.hook_register(address>>16,address&65535,fn,None)
def check_upload(first,count,source):
 lcd=p.memory[0xff40]
 if lcd&0x81!=0x81:return
 base=0x9c00 if lcd&8 else 0x9800
 referenced=set(p.memory[base+row*32+col] for row in range(18) for col in range(20))
 for i in range(count or 256):
  tile=(first+i)&255
  if tile not in referenced:continue
  address=0x8000+tile*16 if lcd&16 else 0x9000+(tile if tile<128 else tile-256)*16
  if list(p.memory[address:address+16])!=list(p.memory[source+i*16:source+i*16+16]):
   exposed.append({'frame':d.frames,'tile':tile,'page':d.v('page'),'track':d.v('seqtrack'),'navopen':d.v('navopen')})
def uploads(_):
 sp=p.register_file.SP
 check_upload(p.memory[sp+2],p.memory[sp+3],p.memory[sp+4]|p.memory[sp+5]<<8)
def safe_uploads(_):
 sp=p.register_file.SP
 if not p.memory[sp+9]:check_upload(p.memory[sp+6],1,p.memory[sp+7]|p.memory[sp+8]<<8)
hook('set_bkg_data',uploads)
if '_ui_upload_tile' in symbols:hook('ui_upload_tile',safe_uploads)
hook('seq_fire',lambda _:dispatch.append((p._cycles(),p.register_file.A)))
try:
 while not d.done and d.frames<2300:
  d.step();p.tick()
  assert p.memory[0xff40]&0x80, 'A transition disabled the LCD and changed emulation timing'
  if p.memory[0xff40]&0x81!=0x81:
   blanks+=1;blank_run+=1;max_blank_run=max(max_blank_run,blank_run)
   blank_locations[str((d.v('page'),d.v('seqtrack')))]+=1
  else:blank_run=0
 assert d.done
 if args.extra_pages:
  for target in [16,17,10,8,18,20,18,8]:
   for _ in d.choose(target):
    p.tick();d.frames+=1
    assert p.memory[0xff40]&0x80
   assert d.v('seqplaying')
  for direction in ['down','down','up','up']:
   for _ in d.chord('select',direction):p.tick();d.frames+=1
  p.tick(60)
 assert p.memory[0xff40]&1, 'Background was not restored after publication'
finally:p.stop(save=False)
times=[cycle for cycle,track in dispatch if track==0]
gaps=[(b-a)/4194304*1000 for a,b in zip(times,times[1:])]
report={'exposed_uploads':len(exposed),'locations':dict(Counter((str((x['page'],x['track'],x['navopen']))) for x in exposed)),
        'examples':exposed[:30],'blank_frames':blanks,'max_blank_frames':max_blank_run,
        'blank_locations':dict(blank_locations),'dispatches':len(times),
        'max_step_ms':max(gaps,default=0),'min_step_ms':min(gaps,default=0),'stages':d.stage_times}
Path(args.report).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
if not args.allow_exposed:assert not exposed, 'Tile graphics overwritten while the display still references them'

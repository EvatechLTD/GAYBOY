"""Arp saturation, UI latency and recovery using an immutable saved pattern."""
import argparse,json,statistics,hashlib
from pathlib import Path
from io import BytesIO
from pyboy import PyBoy
from boot_helpers import enter_app
from arp_probe_helpers import hook_attacks
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--save',type=Path,required=True);ap.add_argument('--output',default='build/arp-stress.json')
ap.add_argument('--capped',action='store_true',help='Only rates supported by the capped build');ap.add_argument('--free',action='store_true');ap.add_argument('--retain',action='store_true');ap.add_argument('--arp-only',action='store_true');ap.add_argument('--gesture',choices=('navigation','paint','multiselect','drag'),default='navigation');args=ap.parse_args()
rom=Path(args.rom);rom_digest=hashlib.sha256(rom.read_bytes()).hexdigest();save_digest=hashlib.sha256(args.save.read_bytes()).hexdigest();S={l.split()[1]:int(l.split()[2],16) for l in rom.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(args.save.read_bytes()));p.set_emulation_speed(0)
def get(n,i=0):
 a=S['_'+n]+i;return p.memory[0,a] if 0xa000<=a<0xc000 else p.memory[a]
def put(n,x,i=0):
 a=S['_'+n]+i
 if 0xa000<=a<0xc000:p.memory[0,a]=x&255
 else:p.memory[a]=x&255
def word(n,x,i=0):put(n,x,i);put(n,x>>8,i+1)
def key(k,down,limit=360):
 mask={'a':16,'b':32,'select':64,'left':2,'right':1,'down':8,'up':4}[k];start=p._cycles()
 (p.button_press if down else p.button_release)(k)
 for _ in range(limit):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return round((p._cycles()-start)*1000/4194304,3)
 return None
hits=[];flushes=[]
def attack(_):
 if p.register_file.A==1:hits.append(p._cycles())
hook_attacks(p,rom,S,1,hits.append)
for name,fn in [('ui_flush',lambda _:flushes.append(p._cycles()))]:
 a=S['_'+name];p.hook_register(a>>16,a&65535,fn,None)
reports=[]
try:
 enter_app(p,S);put('seqtrack',1);put('selected',1);put('seqhead',1);put('seqfocus',0);put('seqdrawvalid',0);put('dirty',1);p.tick(250)
 assert get('seqeventcounts',2)==4,('expected four-note saved P2 chord',get('seqeventcounts',2))
 if args.arp_only:put('seqmuted',125)
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(350);assert get('seqplaying')
 fixture=BytesIO();p.save_state(fixture)
 for bpm in (120,240):
  for timing in ((0,) if args.free else (0,1)):
   for div in ((1000,125,63) if args.free and args.capped else (125,63,32,16,8,4,2,1) if args.free else (6,5,4) if args.capped and timing==1 else (6,5,4,3) if args.capped else (6,5,4,3,2,1,0)):
    fixture.seek(0);p.load_state(fixture)
    word('seqbpm',bpm);word('seqglobalbpm',bpm);word('seqcachedbpm',0)
    put('evalpatch',int(args.free),17)
    put('evalpatch',int(not args.retain),20)
    if args.free:word('evalpatch',div,22)
    else:put('evalpatch',div,18)
    put('evalpatch',timing,19);word('pattern_generation',(get('pattern_generation')|get('pattern_generation',1)<<8)+1);put('dirty',1)
    p.tick(120);hits.clear();flushes.clear();start=p._cycles();p.tick(360)
    intervals=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])]
    nominal=div if args.free else (960*(2**div)/bpm)*(2/3 if timing==1 else 1)*1000/1024
    idle={'attacks':len(hits),'nominal_ms':round(nominal,3),'median_ms':round(statistics.median(intervals),3) if intervals else None,'max_interval_ms':round(max(intervals),3) if intervals else None,'max_error_ms':round(max(abs(x-nominal) for x in intervals),3) if intervals else None,'backlog_ticks':get('seqticks')+get('seqticks',1)*256,'native_mask':get('arpirq_enabled') if '_arpirq_enabled' in S else 0}
    nav=[]
    before_generation=get('pattern_generation')|get('pattern_generation',1)<<8
    before_paint_count=get('seqeventcounts')|get('seqeventcounts',1)<<8
    if args.gesture!='navigation':
     put('seqtrack',0 if args.gesture=='paint' else 1);put('selected',0 if args.gesture=='paint' else 1);put('seqhead',0);put('seqcursor',0,get('seqtrack'));put('seqpitch',75 if args.gesture=='multiselect' else 60,get('seqtrack'));put('seqgrouptrack',255);put('seqapending',0);put('seqdrawvalid',0);put('dirty',1);p.tick(150)
     key('a',True)
     if args.gesture=='paint':key('b',True)
    hits.clear();gesture_start=p._cycles()
    for k in (('up','down','up','down') if args.gesture=='drag' else ('down','down','right','right') if args.gesture=='multiselect' else ('right','left','right','left')):
     nav.append(key(k,True));nav.append(key(k,False))
    if args.gesture=='paint':key('b',False)
    if args.gesture!='navigation':key('a',False)
    gesture_intervals=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])];gesture_count=len(hits)
    gesture_applied=(get('seqeventcounts')|get('seqeventcounts',1)<<8)!=before_paint_count if args.gesture=='paint' else get('seqgrouptrack')==1 if args.gesture=='multiselect' else (get('pattern_generation')|get('pattern_generation',1)<<8)!=before_generation if args.gesture=='drag' else True
    put('seqtrack',1);put('selected',1);put('seqhead',1);put('seqdrawvalid',0);put('dirty',1)
    recover=key('a',True);release=key('a',False);p.tick(180)
    mode=get('evalpatch',16)
    row={'bpm':bpm,'division':str(div)+'ms' if args.free else '1/'+str(256//(2**div)),'timing':'triplet' if timing else 'straight','arp_only':args.arp_only,'gesture':args.gesture,'gesture_attacks':gesture_count,'gesture_max_error_ms':round(max((abs(x-nominal) for x in gesture_intervals),default=0),3),'idle':idle,'navigation_ack_ms':nav,'mono_recovery_ack_ms':recover,'release_ack_ms':release,'recovered_to_mono':mode==0,'playing':get('seqplaying')}
    row['gesture_applied']=gesture_applied
    row['retrigger']=not args.retain
    reports.append(row);Path(args.output).write_text(json.dumps({'save':str(args.save),'save_sha256':save_digest,'rom':str(rom),'rom_sha256':rom_digest,'probe':'APU hardware trigger writes','cases':reports},indent=2));print(row,flush=True)
finally:p.stop(save=False)


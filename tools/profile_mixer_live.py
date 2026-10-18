"""Foreground stage costs during actual mixed-audio mixer launch/navigation."""
from pathlib import Path
import argparse,json,statistics,re
from seq_storage_helpers import write_tracks,write_word
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/promo-candidate1/GAYBOY.gb');ap.add_argument('--output',default='build/mixer-live-profile.json');ap.add_argument('--lst',default='build/promo-candidate1/mixer.lst');args=ap.parse_args()
env={};src=Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0].replace('range(60)','range(600)').replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file=');src=src.replace('build/GAYBOY.gb',args.rom).replace('build/GAYBOY.noi',str(Path(args.rom).with_suffix('.noi')));exec(src,env)
p,S,choose,press=env['p'],env['S'],env['choose'],env['press'];mx=S['_mx'];CPU=4194304
phase='setup';records=[];current=[];hooks={};outer=[];stages=[]
def v(n,i=0):return p.memory[S['_'+n]+i]
def sm(i,x):p.memory[mx+i]=x
def addhook(bank,addr,fn):
 k=(bank,addr)
 if k not in hooks:hooks[k]=[];p.hook_register(bank,addr,lambda key:[f() for f in list(hooks[key])],k)
 hooks[k].append(fn)
def profile(name):
 a=S['_'+name]
 def entered():
  sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;bank=v('__current_bank') if '_ __current_bank' in S else (p.memory[0xff90] if 0x4000<=ret<0x8000 else 0)
  item={'name':name,'phase':phase,'start':p._cycles(),'sp_return':sp+2+{'mx_text':3,'mx_num':2,'mx_fader':2}.get(name,0),'end':None};records.append(item)
  def returned():
   if item['end'] is None and p.register_file.SP==item['sp_return']:item['end']=p._cycles()
  addhook(bank,ret,returned)
 addhook(a>>16,a&65535,entered)
def settled_slot(slot):
 for _ in range(1200):
  p.tick(1)
  if p.memory[mx+1]==slot and p.memory[mx+2]==255:break
 assert p.memory[mx+1]==slot and p.memory[mx+2]==255,'Stopped fixture load did not complete'
 p.tick(60)
def pattern(duty):
 tracks=[[] for _ in range(7)];tracks[0]=[[s,61+s%5,100,4] for s in range(0,64,4)];tracks[1]=[[s,68+s%3,100,1] for s in range(64)];tracks[6]=[[s,1 if s%8==0 else 4,127,4] for s in range(0,64,4)]+[[s,13,127,1] for s in range(1,64,4)];write_tracks(p,S,tracks)
 for c in range(7):write_word(p,S['_seqlength']+c*2,64)
 write_word(p,S['_seqbpm'],220);p.memory[S['_param']]=duty
try:
 choose(18);pattern(0);choose(20);press('b');sm(4,31);press('a');settled_slot(1);pattern(2);choose(20);sm(6,1);press('b');sm(4,30);press('a');settled_slot(0);sm(4,0);press('a');assert v('seqplaying');p.tick(30)
 lst=Path(args.lst).read_text();locals={name:int(addr,16) for addr,name in re.findall(r'^\s+([0-9A-F]{8})\s+\d+ (_[a-zA-Z0-9_]+):',lst,re.M)}
 bias=(S['_mixer_render']&65535)-locals['_mixer_render'];assert bias==0x4000,'Listing must match the immutable ROM'
 static_names=('pads','pad_toggle','pad_upload_columns','fader','text','num')
 for n in static_names:S['_mx_'+n]=(S['_mixer_render']&0xffff0000)|(locals['_'+n]+bias)
 for n in ('mixer_render','ui_flush','ui_render','ui_input','ui_upload_tile','readpart','mixfill')+tuple('mx_'+n for n in static_names):
  if '_'+n in S:profile(n)
 # A fixed-bank service entry provides the next foreground work marker after
 # publishing; no wall-clock host time participates in these measurements.
 if '_service' in S:profile('service')
 phase='focus_navigation';sm(4,30);press('right');p.tick(10)
 phase='same_pattern_BEAT_queue';sm(3,1);sm(4,30);press('a')
 phase='navigation_after_same_queue';press('right');p.tick(30)
 phase='new_pattern_BAR_queue';sm(3,2);sm(4,31);press('a')
 phase='navigation_after_new_queue';press('right');p.tick(180)
 complete=[r for r in records if r['end'] is not None]
 renders=[r for r in complete if r['name']=='mixer_render']
 for r in renders:
  inside=[x for x in complete if x['start']>=r['start'] and x['end']<=r['end']]
  flush=next((x for x in complete if x['name']=='ui_flush' and x['start']>=r['end']),None)
  following=next((x for x in complete if flush and x['name'] in ('service','ui_render') and x['start']>=flush['end']),None)
  spans=sorted((x['start'],x['end']) for x in inside if x['name']=='mixfill');merged=[]
  for begin,end in spans:
   if merged and begin<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],end)
   else:merged.append([begin,end])
  stages.append({'static_callees':{n:{'calls':sum(x['name']=='mx_'+n for x in inside),'inclusive_ms':sum(x['end']-x['start'] for x in inside if x['name']=='mx_'+n)*1000/CPU} for n in static_names},'mixfill_union_ms':sum(end-begin for begin,end in merged)*1000/CPU,'tile_upload_ms':sum(x['end']-x['start'] for x in inside if x['name']=='ui_upload_tile')*1000/CPU,'phase':r['phase'],'mixer_render_ms':(r['end']-r['start'])*1000/CPU,'render_to_flush_entry_ms':(flush['start']-r['start'])*1000/CPU if flush else None,'ui_flush_ms':(flush['end']-flush['start'])*1000/CPU if flush else None,'flush_to_next_foreground_ms':(following['start']-flush['end'])*1000/CPU if following else None,'tile_upload_calls':sum(x['name']=='ui_upload_tile' for x in inside),'readpart_calls':sum(x['name']=='readpart' for x in inside),'mixfill_calls':sum(x['name']=='mixfill' for x in inside),'mixfill_inclusive_ms':sum(x['end']-x['start'] for x in inside if x['name']=='mixfill')*1000/CPU})
 report={'model':'DMG','bpm':220,'length':64,'workload':'samples1/4 + PK + P1sustain + P2eachstep','stages':stages,'incomplete_calls':{n:sum(r['name']==n and r['end'] is None for r in records) for n in ('mixer_render','ui_flush','mixfill')}};Path(args.output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:p.stop(save=False)

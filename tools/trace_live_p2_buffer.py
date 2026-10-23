"""Trace a real P2 drag in a captured live save, through preparation and sound."""
from pathlib import Path
import json
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
from arp_probe_helpers import hook_attacks
rows=[];attacks=[];start=[0]
priv={name:int(offset,16) for _,name,offset,*_ in (l.split() for l in Path('build/objects/storage.sym').read_text().splitlines() if '_eb_' in l and len(l.split())>=4) if name in ('_eb_left','_eb_generation','_eb_activegeneration','_eb_building')}
def private(n,size=1):
 a=symbols['_seqeventcounts']+priv['_'+n];return sum(p.memory[a+i]<<(8*i) for i in range(size))
def val(n,i=0,size=1):return sum(get(n,i+j)<<(8*j) for j in range(size))
def sample():
 r={'ms':(p._cycles()-start[0])*1000/4194304,'pos':val('seqposition',1),'generation':val('pattern_generation',size=2),'active_generation':private('eb_activegeneration',2),'build_generation':private('eb_generation',2),'left':private('eb_left',2),'building':private('eb_building'),'ready':val('editbuffer_ready'),'valid':val('editbuffer_valid'),'swaps':val('editbuffer_swaps',size=2),'pitch':val('basepitch',1),'pad':val('lastpad'),'apending':val('seqapending'),'amoved':val('seqamoved'),'cursor':get('seqcursor',1),'cursorpitch':get('seqpitch',1),'note':p.memory[1,0xa301]}
 if not rows or any(r[k]!=rows[-1][k] for k in r if k!='ms'):rows.append(r)
def tick(n=1):
 for _ in range(n):p.tick(1);sample()
def key(n,down):
 mask={'a':16,'select':64,'up':4}[n];(p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  tick()
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
try:
 enter_app(p,symbols);print('Session',{'lengths':[val('seqlength',2*c,2) for c in range(7)],'counts':[val('seqeventcounts',2*c,2) for c in range(7)],'depth':get('evalpatch',25),'notes':list(p.memory[1,0xa300:0xa30c])},flush=True)
 put('seqviewinitialized',127);put('page',8);put('seqtrack',1);put('selected',1);put('seqhead',0);put('seqfocus',0);put('seqcursor',0,1);put('seqpitch',60,1);put('seqtop',75,1);put('seqdrawvalid',0);put('dirty',1);tick(120)
 key('select',True);key('a',True);key('a',False);key('select',False)
 for _ in range(1800):
  tick()
  if get('editbuffer_valid'):break
 print('Initial preparation',rows[-1],flush=True)
 for _ in range(240):
  tick()
  if get('seqposition',1)==5:break
 start[0]=p._cycles();rows.clear()
 root=[None]*3;attackcycle=[0]
 def pitch_input(_):
  c=p.register_file.A
  if c<3:root[c]=(p.register_file.D<<8)|p.register_file.E
 p.hook_register(symbols['_lfo_irq_pitch']>>16,symbols['_lfo_irq_pitch']&65535,pitch_input,None)
 def triggered(cycle):attackcycle[0]=cycle
 def played(frequency):attacks.append({'ms':(attackcycle[0]-start[0])*1000/4194304,'note':root[1],'frequency':frequency,'generation':private('eb_activegeneration',2)})
 hook_attacks(p,rom,symbols,1,triggered,played,include_editbuffer=True)
 sample();key('a',True);key('up',True);tick(2);key('up',False);tick(2);key('a',False);tick(720)
 edited=next(r for r in rows if r['generation']!=rows[0]['generation'])
 prepared=next(r for r in rows if r['ready'] and r['build_generation']==edited['generation'])
 sounded=next(a for a in attacks if a['note']==61 and a['generation']==edited['generation'])
 metrics={'edit_to_ready_ms':prepared['ms']-edited['ms'],'edit_to_sound_ms':sounded['ms']-edited['ms']}
 assert metrics['edit_to_ready_ms']<1500,metrics
 assert metrics['edit_to_sound_ms']<3000,metrics
 eligible=[a for a in attacks if a['ms']>=prepared['ms'] and a['note'] in (60,61)]
 assert eligible and eligible[0]['note']==61,eligible
 Path('build/p2-live-session-trace.json').write_text(json.dumps({'rows':rows,'attacks':attacks,'metrics':metrics},indent=2))
 print('PASS next eligible loop uses edited P2 note',metrics,flush=True)
 print('Change/preparation/publication',[(round(r['ms'],1),r['generation'],r['left'],r['building'],r['ready'],r['swaps'],r['note'],r['apending'],r['amoved']) for i,r in enumerate(rows) if i==0 or any(r[k]!=rows[i-1][k] for k in ('generation','building','ready','swaps','note'))],flush=True)
 print('Attacks',attacks,flush=True)
finally:p.stop(save=False)

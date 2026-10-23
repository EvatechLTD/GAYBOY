"""Matched DMG audible-register timing: graphics ON versus Smooth Playback."""
from pathlib import Path
from io import BytesIO
import ast,json,statistics,sys,hashlib
import pyboy
from arp_probe_helpers import hook_attacks
steady='--steady-arp' in sys.argv
if steady:sys.argv.remove('--steady-arp')
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
S=symbols;rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest();notes=[];arp=[];edges=[];lastfreq=[None];low=[0]
counts={n:0 for n in ('ui_render','ui_flush','ui_upload_tile','ui_upload_map','roll_feedback_service')}
def key(n,down):
 mask={'select':64,'a':16}[n];(p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
def pitch(cycle,freq):
 if freq!=lastfreq[0]:edges.append(cycle);lastfreq[0]=freq
wavecycle=[0]
registry={}
def register(bank,addr,fn,ctx):
 site=(bank,addr)
 if site not in registry:
  registry[site]=[];p.hook_register(bank,addr,lambda site:[f(c) for f,c in tuple(registry[site])],site)
 registry[site].append((fn,ctx))
hook_attacks(p,rom,S,0,notes.append,include_editbuffer=True,register_hook=register)
hook_attacks(p,rom,S,1,arp.append,include_editbuffer=True,register_hook=register)
hook_attacks(p,rom,S,2,lambda c:wavecycle.__setitem__(0,c),lambda f:pitch(wavecycle[0],f),include_editbuffer=True,register_hook=register)
data=rom.read_bytes();tree=ast.parse((Path(pyboy.__file__).parent/'core/opcodes.py').read_text())
lengths=next(ast.literal_eval(n.value.args[1]) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OPCODE_LENGTHS' for t in n.targets))
ptr=S['_lfo_irq_tick'];bank=ptr>>16;pc=ptr&65535;end=min(v&65535 for k,v in S.items() if k.startswith('_') and v>>16==bank and v&65535>pc)
def observe(target):
 if target==0x1d:low[0]=p.register_file.A
 else:pitch(p._cycles()+12,low[0]|((p.register_file.A&7)<<8))
while pc<end:
 at=bank*16384+pc-16384 if bank else pc;op=data[at];size=2 if op==0xcb else lengths[op]
 if op==0xe0 and data[at+1] in (0x1d,0x1e):register(bank,pc,observe,data[at+1])
 pc+=size
def count(n):counts[n]+=1
for n in counts:
 a=S['_'+n];register(a>>16,a&65535,count,n)
def u16(n):return get(n)|(get(n,1)<<8)
def stats(hits,expected):
 gaps=[(b-a)/4194.304 for a,b in zip(hits,hits[1:])];errors=sorted(abs(g-expected) for g in gaps)
 assert len(gaps)>20,('Insufficient actual audio events',len(gaps))
 return {'intervals':len(gaps),'max_error_ms':round(max(errors),6),'p95_error_ms':round(errors[int(.95*(len(errors)-1))],6),'rms_error_ms':round((sum(x*x for x in errors)/len(errors))**.5,6),'errors_over_1ms':sum(x>1 for x in errors),'mean_interval_ms':round(statistics.mean(gaps),6)}
try:
 enter_app(p,S);boot=BytesIO();p.save_state(boot);reports=[]
 for effect in (('arp',) if steady else ('arp','lfo')):
  for div in (4,3):
   for trial in range(3):
    for smooth in (0,1):
     boot.seek(0);p.load_state(boot);offset=0
     tracks=[[[s,49,110,1] for s in range(0,32,4)],[[0,n,110,32] for n in ((61,65,68) if effect=='arp' else (61,))],[[0,37,110,32]],[],[],[],[[s,11,100,1] for s in range(32)]+[[s,12,100,1] for s in (4,12,20,28)]]
     if steady:
      for c in (1,2):
       for e in tracks[c]:e[3]=0
     for c,events in enumerate(tracks):
      word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',256 if steady and c in (1,2) else 32,c*2)
      for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
     put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0;put('experimental_mode',1);put('mod_bypass',0)
     for c in range(3):
      put('evalpatch',int(effect=='arp' and c==1),c*16);put('evalpatch',0,c*16+1);put('evalpatch',div,c*16+2);put('evalpatch',0,c*16+3);put('evalpatch',0,c*16+4);put('evalpatch',0,c*16+5);put('evalpatch',0,c*16+13)
      put('evalpatch',1,c*16+8);put('evalpatch',64 if effect=='lfo' else 0,c*16+9)
      put('coarsepitch',0,c*3);put('coarsepitch',12 if effect=='lfo' else 0,c*3+1);put('coarsepitch',1,c*3+2)
     for i,v in ((4,2),(6,div),(7,1),(8,0),(9,1)):put('globalmod',v,i)
     put('eval_moddirty',1);put('seqirqdirty',1);word('pattern_generation',u16('pattern_generation')+1)
     put('page',8);put('seqtrack',1);put('selected',1);put('seqhead',0);put('seqfocus',0);put('seqpitch',60,1);put('seqtop',67,1);put('seqcursor',0,1);put('dirty',1);put('pattern_dirty',1)
     word('seqbpm',120);word('seqglobalbpm',120);p.tick(180+trial*7);put('smooth_playback_enabled',smooth)
     key('select',True);key('a',True);key('a',False);key('select',False);p.tick(240)
     assert get('seqplaying') and get('smooth_playback_active')==smooth
     if effect=='arp':assert get('arpirq_enabled')&2
     else:assert get('lfo_irq_mask')==7
     notes.clear();arp.clear();edges.clear();lastfreq[0]=None;counts={n:0 for n in counts};before=u16('editirq_underruns');start=p._cycles();p.tick(900)
     row={'effect':effect,'division':'1/'+str(1<<(8-div)),'trial':trial,'smooth':bool(smooth),'window_ms':round((p._cycles()-start)/4194.304,3),'note_timing':stats(notes,500),'modulation_timing':stats(arp if effect=='arp' else edges,(125 if div==4 else 62.5)/(2 if effect=='lfo' else 1)),'graphics_calls':dict(counts),'irq_underruns':(u16('editirq_underruns')-before)&65535}
     if smooth:assert not any(counts.values()),row
     assert not row['irq_underruns'],row
     row['nonlooping_arp_control']=steady
     row['rom_sha256']=rom_sha256
     reports.append(row);Path('build/smooth-playback-'+('steady-arp-' if steady else '')+'comparison.json').write_text(json.dumps(reports,indent=2));print(json.dumps(row),flush=True)
finally:p.stop(save=False)

"""Exercise global MOD UI bypass with retained settings, notes and live ARP."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
from arp_probe_helpers import hook_attacks
hits=[];frequencies=[]
queued={k:v for k,v in symbols.items() if k not in ('_play','_arp_native_sound','_arp_irq_tick','_arp_irq_due')}
hook_attacks(p,rom,queued,1,hits.append,frequencies.append,include_editbuffer=True)
def u16(n):return get(n)|(get(n,1)<<8)
def key(n,down):
 mask={'a':16,'select':64,'up':4,'down':8}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
def toggle(off):
 put('page',2);put('eval_row',10);put('dirty',1);p.tick(15)
 key('a',True);key('a',False);p.tick(30)
 assert get('mod_bypass')==off
 assert get('seqplaying')
def settings():return bytes(get('evalpatch',i) for i in range(128))+bytes(get('coarsepitch',i) for i in range(24))+bytes(get('globalmod',i) for i in range(10))
try:
 enter_app(p,symbols);offset=0
 for c in range(7):
  events=[[0,n,127,64] for n in (61,65,68)] if c==0 else [[i,61,127,8] for i in range(0,64,8)] if c==1 else [[0,61,127,64]] if c==2 else []
  word('seqeventoffsets',offset,2*c);word('seqeventcounts',len(events),2*c);word('seqlength',64,2*c)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 put('evalpatch',1,0);put('evalpatch',1,13)
 for c in (1,2):
  put('evalpatch',1,16*c+8);put('evalpatch',64,16*c+9)
  put('coarsepitch',12,3*c+1);put('coarsepitch',1,3*c+2)
 put('globalmod',2,4);put('globalmod',3,6);put('globalmod',1,7);put('globalmod',1,9)
 word('seqbpm',120);word('seqglobalbpm',120);word('pattern_generation',1);put('seqirqdirty',1)
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(1200)
 assert get('lfo_irq_mask')&6==6
 original=settings();toggle(1)
 assert settings()==original
 assert get('lfo_irq_mask')==get('eval_lfousers')==get('eval_envusers')==0
 phase=get('lphase');updates=u16('lfo_irq_updates');arp=u16('arpirq_attacks');hits.clear();frequencies.clear();p.tick(540)
 assert get('lphase')==phase and u16('lfo_irq_updates')==updates
 assert u16('arpirq_attacks')>arp,'ARP stopped during modulation bypass'
 at=symbols['_notes']+60*2;expected=p.memory[at]|p.memory[at+1]<<8
 assert len(frequencies)>=5 and set(frequencies)=={expected},(expected,frequencies)
 toggle(0);assert settings()==original and get('lfo_irq_mask')&6==6
 updates=u16('lfo_irq_updates');p.tick(90);assert u16('lfo_irq_updates')>updates
 # ADSR pitch/level also disappears from the work masks while settings survive.
 for c in (1,2):put('evalpatch',0,16*c+8);put('evalpatch',128,16*c+10);put('coarsepitch',0,3*c+2)
 word('pattern_generation',2);put('eval_moddirty',1);put('seqirqdirty',1);p.tick(180)
 assert get('eval_envusers')&6==6
 original=settings();toggle(1);assert settings()==original
 assert p.memory[0xff1c]&0x60==get('param',2*26+15)<<5,('Wave did not restore instrument level',p.memory[0xff1c],get('param',2*26+15))
 assert not get('eval_envusers') and not get('eval_lfousers') and not get('lfo_irq_mask')
 toggle(0);assert settings()==original and get('eval_envusers')&6==6
 print('PASS UI on/off, retained LFO/ADSR settings, base pitch, zero modulation work, live ARP, resume without transport restart')
finally:p.stop(save=False)

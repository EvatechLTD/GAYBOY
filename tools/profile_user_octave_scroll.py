"""Profile octave scrolling in the user's captured SameBoy song, MOD OFF."""
from pathlib import Path
from io import BytesIO
import json,sys
hide='--no-keyboard' in sys.argv
if hide:sys.argv.remove('--no-keyboard')
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
S=symbols
profile=Path('tools/audit_prep_work.py').read_text().split('class Profile:',1)[1].split("source=Path('tools/test_editbuffer_timing.py')",1)[0];profile='class Profile:'+profile
start=profile.index('  # Count actual table-rebuild');end=profile.index(' def rebuilt',start);profile=profile[:start]+profile[end:]
profile=profile.replace("'native_edit_flush')", "'native_edit_flush','seq_render','seq_pixels','roll_keyboard','roll_intern','roll_scroll_cells','roll_navigation_abort','roll_clear_transition','roll_selection_prepare','seq_meterbuild')")
exec(profile)
root=Path('../DATA/EXPERIMENTS/octave-scroll-20261023');session=json.loads((root/'session.json').read_text());old={l.split()[1]:int(l.split()[2],16) for l in (root/'user-session.noi').read_text().splitlines() if l.startswith('DEF ')};w=(root/'wram.bin').read_bytes();cart=(root/'cartram.bin').read_bytes()
def captured(n,i=0,size=1):
 a=old['_'+n]+i;return int.from_bytes(cart[a-0xa000:a-0xa000+size] if 0xa000<=a<0xc000 else w[a-0xc000:a-0xc000+size],'little')
def key(n,down):
 mask={'a':16,'select':64,'up':4,'down':8}[n];start=p._cycles();(p.button_press if down else p.button_release)(n)
 for _ in range(1800):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return (p._cycles()-start)/4194.304
 raise AssertionError(('input timeout',n,down))
def map_visible():
 return all(p.memory[0x9800+y*32+x]==get('canvas',y*20+x) for y in range(18) for x in range(20))
def settled(top):return get('seqdrawvalid') and get('seqviewtop')==top and not get('rollbuilding') and map_visible()
def scroll(n):
 start=p._cycles();ack=key(n,True);key(n,False);target=get('seqtop',1)
 for _ in range(2400):
  p.tick(1)
  if settled(target):return {'ack_ms':round(ack,3),'visible_ms':round((p._cycles()-start)/4194.304,3),'top':target}
 raise AssertionError(('scroll never published',n,target,get('seqviewtop'),get('seqdrawvalid')))
try:
 enter_app(p,S)
 for bank in range(4):p.memory[bank,0xa000:0xc000]=cart[bank*8192:(bank+1)*8192]
 for c in range(7):word('seqeventcounts',session['counts'][c],c*2);word('seqeventoffsets',sum(session['counts'][:c]),c*2);word('seqlength',session['lengths'][c],c*2)
 for n,count in (('param',104),('evalpatch',128),('globalmod',10),('coarsepitch',24),('finepitch',6),('expconfig',16)):
  if '_'+n in old and '_'+n in S:
   for i in range(count):put(n,captured(n,i),i)
 for n in ('seqbeats','seqdenom','seqzoom','seqvelocityhidden','experimental_mode','seqmode','waveengine','mod_bypass','seqmuted','seqsolo'):put(n,captured(n))
 word('seqbpm',120);word('seqglobalbpm',120);put('eval_moddirty',1);put('seqirqdirty',1);word('pattern_generation',1);put('pattern_dirty',1)
 if hide:
  address=S['_roll_keyboard'];p.memory[address>>16,address&65535]=0xc9
 put('page',8);put('seqtrack',1);put('selected',1);put('seqhead',2);put('seqfocus',0);put('seqgrouptrack',255);put('seqviewinitialized',127);put('seqcursor',5,1);put('seqpitch',53,1);put('seqtop',53,1);put('seqdrawvalid',0);put('seqfontdirty',0);put('dirty',1);p.tick(600)
 assert get('mod_bypass')==1
 fixture=BytesIO();p.save_state(fixture);profiler=Profile();reports=[]
 for playing in (False,True):
  fixture.seek(0);p.load_state(fixture)
  if playing:key('select',True);key('a',True);key('a',False);key('select',False);p.tick(600)
  assert get('mod_bypass')==1
  profiler.begin();up=[scroll('up') for _ in range(12)];up_profile=profiler.end()
  put('seqhead',0);put('seqpitch',get('seqtop',1)-get('seqrows')+1,1);put('dirty',1);p.tick(120)
  profiler.begin();down=[scroll('down') for _ in range(12)];down_profile=profiler.end()
  row={'playing':playing,'mod_bypass':get('mod_bypass'),'keyboard_hidden':hide,'up':up,'down':down,'up_profile':up_profile,'down_profile':down_profile};reports.append(row)
  print('RESULT',playing,'up',[r['visible_ms'] for r in up],'down',[r['visible_ms'] for r in down],flush=True)
 Path('build/octave-scroll-'+rom.stem+('-no-keyboard' if hide else '')+'.json').write_text(json.dumps(reports,indent=2))
finally:p.stop(save=False)

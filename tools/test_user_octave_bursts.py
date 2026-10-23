"""Rapid octave taps must not discard the retained scroll image."""
from pathlib import Path
import sys
strict='--strict' in sys.argv
if strict:sys.argv.remove('--strict')
s=Path('tools/profile_user_octave_scroll.py').read_text();a=s.index(' for playing in (False,True):');b=s.index(" Path('build/octave-scroll-",a)
s=s[:a]+''' for playing in (False,True):
  fixture.seek(0);p.load_state(fixture)
  if playing:key('select',True);key('a',True);key('a',False);key('select',False);p.tick(600)
  for direction in ('up','down'):
   if direction=='down':put('seqhead',0);put('seqpitch',get('seqtop',1)-get('seqrows')+1,1);put('dirty',1);p.tick(120)
   target=get('seqtop',1)+(8 if direction=='up' else -8);profiler.begin();start=p._cycles()
   for _ in range(8):p.button_press(direction);p.tick(2);p.button_release(direction);p.tick(2)
   for _ in range(2400):
    p.tick(1)
    if get('seqtop',1)==target and settled(target) and get('padread')==get('padwrite'):break
   else:raise AssertionError(('rapid scroll did not catch up',direction,target,get('seqtop',1),get('seqviewtop')))
   profile=profiler.end();clears=profile['functions'].get('roll_clear_transition',{}).get('calls',0)
   row={'playing':playing,'direction':direction,'elapsed_ms':round((p._cycles()-start)/4194.304,3),'cache_clears':clears,'profile':profile};reports.append(row)
   print('BURST',playing,direction,row['elapsed_ms'],'cache clears',clears,flush=True)
   if strict:assert not clears,('navigation discarded retained cache',row)
'''+s[b:]
s=s.replace("'build/octave-scroll-'", "'build/octave-bursts-'")
exec(compile(s,'tools/profile_user_octave_scroll.py','exec'))

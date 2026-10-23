"""Retained multi-note octave scrolling must match a fresh full render, keyboard included."""
from pathlib import Path
s=Path('tools/profile_user_octave_scroll.py').read_text()
helper='''def pixels():
 result=bytearray()
 for y in range(get('seqgridheight')):
  for x in range(160):
   tile=p.memory[0x9800+(1+y//8)*32+x//8];base=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16;mask=128>>(x&7);at=base+(y&7)*2
   result.append(bool(p.memory[at]&mask)+2*bool(p.memory[at+1]&mask))
 return bytes(result)
'''
s=s.replace('try:\n enter_app',helper+'\ntry:\n enter_app',1)
a=s.index(' for playing in (False,True):');b=s.index(" Path('build/octave-scroll-",a)
s=s[:a]+''' for playing in (False,True):
  fixture.seek(0);p.load_state(fixture)
  if playing:key('select',True);key('a',True);key('a',False);key('select',False);p.tick(600)
  for base in (0,12):
   put('seqcursor',5 if base==0 else 17,1);put('seqtop',53,1);put('seqpitch',53,1);put('seqhead',2);put('seqdrawvalid',0);put('seqfontdirty',0);put('dirty',1);p.tick(1200)
   for direction in ('up','down'):
    if direction=='down':put('seqhead',0);put('seqpitch',get('seqtop',1)-get('seqrows')+1,1);put('dirty',1);p.tick(120)
    for i in range(24):
     row=scroll(direction)
     if i in (0,7,15,23):
      before=pixels();retained=BytesIO();p.save_state(retained);top=get('seqtop',1)
      put('seqdrawvalid',0);put('seqfontdirty',0);put('dirty',1)
      for _ in range(2400):
       p.tick(1)
       if settled(top):break
      else:raise AssertionError('reference redraw never completed')
      assert pixels()==before,('scroll differs from fresh render',playing,base,direction,i,top)
      retained.seek(0);p.load_state(retained)
    assert get('mod_bypass')==1
    print('PASS exact note and keyboard pixels',playing,base,direction,flush=True)
 reports=[{'passed':True,'mod_bypass':get('mod_bypass')}]
'''+s[b:]
s=s.replace("'build/octave-scroll-'", "'build/octave-pixels-'")
exec(compile(s,'tools/profile_user_octave_scroll.py','exec'))

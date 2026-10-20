"""Mixer navigation retains cursor, strip viewport and pad page."""
exec(open('tools/test_mixer_settings.py').read().split('try:\n')[0])
def focus(n):
 p.memory[0,S['_mx']+4]=n;p.memory[S['_dirty']]=1;p.tick(40)
def strip():return bytes(p.memory[S['_canvas']+80:S['_canvas']+100])
try:
 enter_app(p,S);choose(18)
 initial=strip();focus(60);scroll=strip();assert scroll!=initial
 choose(8);choose(18);assert v('mx',4)==60 and strip()==scroll
 focus(37);assert v('mixer_pad_pages')==1
 focus(60);choose(8);choose(18)
 assert v('mx',4)==60 and strip()==scroll and v('mixer_pad_pages')==1
 choose(45);tap('down');tap('down');tap('b')
 assert v('page')==18 and v('mx',4)==60 and strip()==scroll and v('mixer_pad_pages')==1
 # File UI and its naming cursor must not become the Mixer cursor.
 focus(36);choose(20);tap('a');tap('select');choose(18)
 assert v('mx',4)==36 and v('mixer_pad_pages')==1
 # Header focus retains the channel viewport too.
 focus(0);assert strip()==scroll
 choose(8);choose(18);assert v('mx',4)==0 and strip()==scroll
 print('PASS: Mixer channel viewport, pad page and cursor survive SEQ, settings and file navigation')
finally:p.stop(save=False)

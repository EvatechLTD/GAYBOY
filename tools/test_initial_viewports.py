"""First-visit pitch ranges and remembered track viewports."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].split('# Instrument fixtures explicitly')[0])
try:
 choose(0);choose(8)
 assert v('seqtrack')==0 and v('seqtop')-v('seqrows')+1==36
 put('seqtop',0,65);put('seqpitch',0,60);put('seqdrawvalid',0,0);put('dirty',0,1);p.tick(30)
 put('seqnotes',64,61)
 p.button_press('select');press('right');p.button_release('select');p.tick(30)
 assert v('seqtrack')==1 and v('seqtop',1)-v('seqrows')+1==48
 put('seqtop',1,76);put('seqpitch',1,70);put('seqdrawvalid',0,0);put('dirty',0,1);p.tick(30)
 p.button_press('select');press('left');p.button_release('select');p.tick(30)
 assert v('seqtrack')==0 and v('seqtop')==65 and v('seqpitch')==60
 put('seqpitch',0,65);put('dirty',0,1);p.tick(15);press('up')
 assert v('seqhead')==1 and v('seqtop')==65
 press('up');assert v('seqhead')==1 and v('seqtop')==66
 press('down');assert not v('seqhead') and v('seqpitch')==66
 print('PASS: initial C2/C3 lowest notes, remembered per-track viewport/cursor, header entry and whole-row upward scrolling')
finally:p.stop(save=False)

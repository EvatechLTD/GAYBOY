"""Inactive steps retain their notes and render in gray across the loop edge."""
exec(open('tools/test_seq_incremental.py').read().split('choose(8); settle()')[0])
choose(8);settle()
put('seqzoom',0,3);put('seqlength',0,32)
put('seqnotes',4,61);put('seqduration',4,1)
put('seqnotes',14,61);put('seqduration',14,4)
put('seqnotes',20,61);put('seqduration',20,1)
invalidate(True)
row=(v('seqtop')-60)*8+11
active_x=16+4*144//32+2
inactive_x=16+20*144//32+2
assert background()[row,inactive_x]==3
put('seqlength',0,16);invalidate()
px=background()
assert v('seqnotes',20)==61 and v('seqduration',14)==4
assert px[row,active_x]==3 and px[row,inactive_x]==2
# The same sustained note changes shade as it crosses the active loop edge.
assert px[row,16+15*144//32+2]==3
assert px[row,16+16*144//32+2]==2
put('seqlength',0,32);invalidate()
assert v('seqnotes',20)==61 and background()[row,inactive_x]==3
p.stop(save=False)
print('PASS: shrinking preserves all notes; inactive notes and continuation bodies remain visible in gray')

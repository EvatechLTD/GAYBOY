from pathlib import Path
s=Path('tools/test_wave_edit_audible_latency.py').read_text()
s=s.replace(' for phase in (2,6,10,14):',' for target,phase in [(t,h) for t in (0,4,8,12) for h in (2,6,10,14)]:')
s=s.replace("before=u16('editbuffer_swaps');key('a',True);key('up',True)","put('seqcursor',target,2);put('seqpitch',tracks[2][target//4][1]-1,2);put('dirty',1);p.tick(1)\n  before=u16('editbuffer_swaps');key('a',True);key('up',True)")
s=s.replace("p.memory[1,0xa301]==38", "p.memory[1,0xa301+target]==tracks[2][target//4][1]+1")
s=s.replace("get('basepitch',2)==37 and get('seqsource',2)==0", "get('basepitch',2)==tracks[2][target//4][1] and get('seqsource',2)==target")
s=s.replace("row={'phase':phase", "row={'target':target,'phase':phase")
s=s.replace("'build/wave-edit-latency-'", "'build/wave-edit-matrix-'")
exec(compile(s,'tools/test_wave_edit_audible_latency.py','exec'))

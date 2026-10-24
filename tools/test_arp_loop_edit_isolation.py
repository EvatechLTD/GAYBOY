"""Preserving an unchanged looping ARP must still admit real chord edits."""
from pathlib import Path
exec(Path('tools/benchmark_normal_playback.py').read_text().split('\ntry:\n')[0])
observed=[]
hook_attacks(p,rom,S,1,lambda _:None,observed.append,include_editbuffer=True,register_hook=register)
try:
 setup_fixture();put('seqtrack',1);put('selected',1);put('seqcursor',0,1);put('seqpitch',60,1);put('seqtop',72,1);put('dirty',1);p.tick(90)
 transport();p.tick(120);tap('b');assert get('seqeventcounts',2)==2
 p.tick(600)
 a=S['_notes'];bank=a>>16;at=a&65535
 def freq(n):return p.memory[bank,at+n*2]|p.memory[bank,at+n*2+1]<<8
 expected={freq(64),freq(67)}
 assert set(observed[-12:])==expected,(observed[-12:],expected)
 print('PASS chord erase replaces prepared ARP after its next loop boundary')
 tap('b');assert get('seqeventcounts',2)==3
 p.tick(600);expected.add(freq(60))
 assert set(observed[-18:])==expected,(observed[-18:],expected)
 print('PASS chord plot restores all three tones; unchanged-chord optimization does not hide edits')
finally:p.stop(save=False)

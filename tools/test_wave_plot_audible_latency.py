"""Actual B plotting into a one-bar Wave bassline, with no ARP or dragging."""
from pathlib import Path
s=Path('tools/test_wave_edit_audible_latency.py').read_text()
s=s.replace("'a':16,'up':4", "'a':16,'b':32,'up':4")
s=s.replace("zip((0,4,8,12),(37,41,44,41))", "zip((4,8,12),(41,44,41))")
s=s.replace("before=u16('editbuffer_swaps');key('a',True);key('up',True)","word('seqdefaultdur',4,4);before=u16('editbuffer_swaps');key('b',True)")
s=s.replace("p.memory[1,0xa301]==38", "p.memory[1,0xa30d]==37")
s=s.replace("p.button_release('up')", "p.button_release('b')")
s=s.replace("not get('lastpad')&4", "not get('lastpad')&32")
s=s.replace("get('basepitch',2)==37", "get('basepitch',2)==36")
s=s.replace("key('a',False)\n Path", "key('b',False)\n Path")
s=s.replace("'build/wave-edit-latency-'", "'build/wave-plot-latency-'")
exec(compile(s,'tools/test_wave_edit_audible_latency.py','exec'))

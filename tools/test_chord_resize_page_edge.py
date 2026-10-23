"""Chord resizing waits for Dpad release at16, then crosses on a fresh press."""
from pathlib import Path
s=Path('tools/repro_chord_resize_hold.py').read_text()
s=s.replace("key('right',False);p.tick(60);print('RELEASE60'", "assert all(e[3]==16 for e in chord()),('held resize escaped page edge',mode,chord())\n  assert get('seqbase')==get('seqviewbase')==0 and get('rollcursorvisible') and get('rollcursorcell')==15,('invalid edge feedback',mode,state())\n  key('right',False);key('right',True)\n  for _ in range(1800):\n   p.tick(1)\n   if get('seqviewbase')==16 and get('seqdrawvalid'):break\n  else:raise AssertionError(('destination page did not publish',mode,state()))\n  assert get('seqcursor',1)==16 and all(e[3]==17 for e in chord()),('fresh press did not enter first cell',mode,chord(),state())\n  key('right',False);p.tick(60);print('RELEASE60'")
s=s.replace("'build/chord-resize-held-'", "'build/chord-resize-edge-release-'")
exec(compile(s,'tools/repro_chord_resize_hold.py','exec'))

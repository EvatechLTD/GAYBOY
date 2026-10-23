"""Dragging changes data, but never rebuilds note pixels until D-pad release.
Exercise single/group moves and resizes, including drums, through real input.
"""
from pathlib import Path
source = Path('tools/test_editbuffer_drag_release.py').read_text()
source = source.replace('try:\n enter_app', '''rebuilds=[]
def on_rebuild(name):
 if get('seqeditpreview'):rebuilds.append(name)
for name in ('seq_pixels','drum_render','native_edit_flush'):
 ptr=symbols['_'+name];bank,address=ptr>>16,ptr&65535
 p.hook_register(bank,address,on_rebuild,name)
try:
 enter_app''',1)
source = source.replace("assert swaps()==before,(c,kind,'published during movement')", "assert swaps()==before,(c,kind,'published during movement')\n   assert get('seqeditpreview') and get('seqpreviewdirty'),(c,kind,'preview missing')\n   assert not rebuilds,(c,kind,'note rebuild during drag',rebuilds)")
source = source.replace("waitkey('right',False)\n   for", "waitkey('right',False)\n   assert not get('seqeditpreview'),(c,kind,'release not recognized')\n   for")
exec(compile(source,'tools/test_editbuffer_drag_release.py','exec'))

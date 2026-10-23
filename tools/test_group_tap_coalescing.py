"""Rapid queued group taps preserve edits and the exact selection pixels.
The pixel oracle is the unchanged initial grid plus the selection XOR mask.
"""
from pathlib import Path
import sys
single='--single' in sys.argv
if single:sys.argv.remove('--single')
source=Path('tools/test_editbuffer_timing.py').read_text()
helper='''def grid_pixels():
 result=bytearray()
 for y in range(get('seqgridheight')):
  for x in range(16,160):
   tile=p.memory[0x9800+(1+y//8)*32+x//8];base=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16;mask=128>>(x&7);off=base+(y&7)*2
   result.append(bool(p.memory[off]&mask)+2*bool(p.memory[off+1]&mask))
 return bytes(result)
'''
source=source.replace('try:\n enter_app',helper+'\ntry:\n enter_app',1)
source=source.replace(' fixture=BytesIO();p.save_state(fixture)', ''' moves=[]
 p.hook_register(S['_eval_seq_group_move']>>16,S['_eval_seq_group_move']&65535,lambda _:moves.append(p._cycles()),None)
 fixture=BytesIO();p.save_state(fixture)''')
source=source.replace('  start_count=event_total();', '  original=bytes(p.memory[1,0xa300:0xa300+event_total()*4]);original_pixels=grid_pixels()\n  start_count=event_total();')
source=source.replace('for i in range(28):','for i in range(8):')
source=source.replace("elif phase=='group_move':press('up' if i%2==0 else 'down')", "elif phase=='group_move':\n    k='up' if i%2==0 else 'down';p.button_press(k);p.tick(2);p.button_release(k);p.tick(2)")
source=source.replace("  for key in ('a','b'):p.button_release(key)", "  if phase=='group_move':\n   p.tick(600)\n   assert len(moves)==8,('queued taps lost or repeated',len(moves))\n   assert bytes(p.memory[1,0xa300:0xa300+event_total()*4])==original,'reversible group taps changed source data'\n  for key in ('a','b'):p.button_release(key)")
source=source.replace('  intervals=[', '''  if phase=='group_move':
   p.tick(600);expected=bytearray(original_pixels)
   left=get('rollx',4);right=get('rollx',8);top=(get('seqtop',1)-60)*get('seqheight')
   for y in range(top,top+get('seqheight')):
    for x in range(left,right):expected[y*144+x-16]^=3
   assert grid_pixels()==bytes(expected),'queued taps corrupted notes or selection pixels'
   print('PASS all eight queued taps processed; source restored and exact selection pixels verified',flush=True)
  intervals=[''')
if single:
 source=source.replace("S['_eval_seq_group_move']", "S['_seq_move']")
 source=source.replace("put('seqgrouptrack',editor);put('seqgroupx0'", "put('seqgrouptrack',255);put('seqgroupx0'")
 source=source.replace('expected[y*144+x-16]^=3','expected[y*144+x-16]^=0')
 source=source.replace('exact selection pixels verified','exact single-note pixels verified')
exec(compile(source,'tools/test_editbuffer_timing.py','exec'))

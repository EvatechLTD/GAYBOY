from pathlib import Path
s=Path('tools/repro_chord_resize_ui.py').read_text()
helper='''def grid_pixels():
 result=bytearray()
 for y in range(get('seqgridheight')):
  for x in range(16,160):
   tile=p.memory[0x9800+(1+y//8)*32+x//8];base=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16;mask=128>>(x&7);off=base+(y&7)*2
   result.append(bool(p.memory[off]&mask)+2*bool(p.memory[off+1]&mask))
 return bytes(result)
def expected_grid():
 expected=bytearray(blank)
 for e in chord():
  y=(get('seqtop',1)-(e[1]-1))*get('seqheight');end=e[3] or 256
  left=get('rollx',0)+1;right=get('rollx',min(end,get('seqcols')))-(end<=get('seqcols'))
  for yy in range(y+1,y+get('seqheight')-1):
   for x in range(left,right):expected[yy*144+x-16]=3
 if get('seqgrouptrack')==1:
  left=get('rollx',get('seqgroupx0'));right=get('rollx',get('seqgroupx1')+1)
  top=(get('seqtop',1)-get('seqgroupy1'))*get('seqheight');bottom=(get('seqtop',1)-get('seqgroupy0')+1)*get('seqheight')
  for yy in range(top,bottom):
   for x in range(left,right):expected[yy*144+x-16]^=3
 return bytes(expected)
def pixel_report(label):
 actual=grid_pixels();expected=expected_grid();diff=[(i%144+16,i//144,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
 print(label,'PIXEL_DIFF',len(diff),diff[:6],flush=True);return len(diff)
'''
s=s.replace('try:\n enter_app',helper+'\ntry:\n enter_app',1)
s=s.replace("key('select',True);tap('a');key('select',False);p.tick(180)","key('select',True);tap('a');key('select',False);p.tick(180);blank=grid_pixels()",1)
s=s.replace("box();print('selected'", "box();assert not pixel_report('INITIAL '+str(mode));print('selected'")
s=s.replace("key('b',False);p.tick(600);final=state();profile=profiler.end()", "key('b',False);p.tick(600);pixel_report('AFTER '+str(mode));final=state();profile=profiler.end()")
s=s.replace("navafter=[tap('down') for _ in range(4)]", "navafter=[tap('down') for _ in range(4)];p.tick(300);pixel_report('PAGE RETURN '+str(mode))")
s=s.replace("'build/chord-resize-'+rom.stem+'.json'", "'build/chord-resize-pixels-'+rom.stem+'.json'")
exec(compile(s,'tools/repro_chord_resize_ui.py','exec'))

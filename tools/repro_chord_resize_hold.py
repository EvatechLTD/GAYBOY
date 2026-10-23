from pathlib import Path
s=Path('tools/repro_chord_resize_ui.py').read_text()
a=s.index('  profiler.begin();rows=[]')
b=s.index('  # Compare ordinary cell input',a)
s=s[:a]+'''  profiler.begin();rows=[]
  key('right',True)
  for frames in (120,300):
   p.tick(frames);row={'held_frames':frames,'state':state(),'durations':[e[3] for e in chord()]};rows.append(row);print('HELD',mode,row,flush=True)
  key('right',False);p.tick(60);print('RELEASE60',mode,state(),[e[3] for e in chord()],flush=True)
  key('b',False);p.tick(600);final=state();profile=profiler.end()
'''+s[b:]
s=s.replace("'build/chord-resize-'+rom.stem+'.json'", "'build/chord-resize-held-'+rom.stem+'.json'")
exec(compile(s,'tools/repro_chord_resize_ui.py','exec'))

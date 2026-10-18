from boot_helpers import enter_app, enable_experimental
from pathlib import Path
import json
from pyboy import PyBoy
S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null');p.set_emulation_speed(0);enter_app(p);enable_experimental(p)
for row in json.loads(Path('src/presets.json').read_text()):
 for b in [0xc0,row['id']]:
  w=p.memory[S['_wr']];p.memory[S['_rx']+w]=b;p.memory[S['_wr']]=(w+1)&255
 p.tick(12)
 assert list(p.memory[S['_param']:S['_param']+26])==row['values']
 assert list(p.memory[S['_mods']:S['_mods']+6])==row['mod']
 assert list(p.memory[S['_tables']:S['_tables']+24])==[v&255 for step in row['table'] for v in step]
 assert p.memory[S['_tablemode']]==row['tmode'] and p.memory[S['_tablelen']]==row['tlen']
 assert bytes(p.memory[S['_patchcache']:S['_patchcache']+18]).split(b'\0')[0].decode()==row['name']
p.stop(save=False);print('PASS: all 100 packed presets retain names, parameters, macros and tables')

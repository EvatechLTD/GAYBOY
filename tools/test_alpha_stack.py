"""Stack-entry sampling during disposable-SRAM dense live Mixer stress."""
from pathlib import Path
import json,re

source=Path('tools/test_mixer_live.py').read_text()
instrument='''
 lows={}
 def stack_entry(name):
  sp=p.register_file.SP
  lows[name]=min(lows.get(name,0xe000),sp)
 for name in ('engine_timer','seq_frame','tones_pack','tones_decode','tones_apply','readpart','writepart','snapshot','prefetch','switchslot'):
  addr=S.get('_'+name)
  if addr is None:
   lines=Path('build/objects/mixer.lst').read_text().splitlines()
   line=next((l for l in lines if re.search('_'+name+':$',l)),None)
   if line:addr=(18<<16)|0x4000|int(line.split()[0],16)
  if addr is not None:hook(addr>>16 if addr>=65536 else 0,addr&65535,lambda n=name:stack_entry(n))
 env['choose'](16);env['press']('a');assert v('experimental_mode')
'''
source=source.replace(' try:\n  assert p.memory[0xff4d]',instrument+' try:\n  assert p.memory[0xff4d]')
source=source.replace('  return result','  result["stack_entry_minima"]={k:hex(v) for k,v in lows.items()}\n  result["stack_minimum"]=min(lows.values())\n  return result')
env={'__name__':'stack_instrumented'}
exec(source,env)
result=env['run'](180,True)
Path('build/alpha-stack.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k.startswith('stack')},indent=2))
assert result['stack_minimum']>=0xde20,'Stack reached fixed DSP tables or IRQ reserve'

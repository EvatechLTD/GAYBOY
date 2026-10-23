"""Native timer countdown matches the capped baseline, including wrap and due."""
import argparse,random
from mod_port_harness import Engine
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--before',default='build/GAYBOY-arp-limits.gb');ap.add_argument('--after',default='build/GAYBOY.gb');args=ap.parse_args()
engines=[Engine(args.before),Engine(args.after)];rng=random.Random(391)
# Private counter addresses are recovered from the linked countdown instructions.
for e,rom in zip(engines,(args.before,args.after)):
 data=Path(rom).read_bytes();a=e.S['_arp_irq_tick'];code=data[a:a+100]
 if code[0]==0x4f: # compiler-generated baseline
  i=code.index(bytes.fromhex('6f fa'));clock=int.from_bytes(code[i-2:i],'little')
  i=code.index(bytes.fromhex('21'),i);wait=int.from_bytes(code[i+1:i+3],'little')
 else:
  i=code.index(bytes.fromhex('21'));clock=int.from_bytes(code[i+1:i+3],'little')
  i=code.index(bytes.fromhex('21'),i+3);wait=int.from_bytes(code[i+1:i+3],'little')
 assert 0xc000<=clock<0xd800 and 0xc000<=wait<0xd800,(clock,wait)
 e.S['_timer_clock']=clock;e.S['_timer_wait']=wait
try:
 for case in range(160):
  elapsed=rng.randrange(256);clock=rng.randrange(65536);wait=rng.randrange(65536);enabled=int(case%7!=0)
  if case<8:elapsed,wait=[(0,1),(1,1),(2,1),(255,255),(255,256),(255,65535),(1,65535),(1,2)][case]
  outputs=[]
  for e in engines:
   e.reset();e.put('seqplaying',1);e.put('arpirq_enabled',enabled);e.word('timer_clock',clock);e.word('timer_wait',wait)
   e.p.register_file.A=elapsed;e.call('arp_irq_tick')
   outputs.append((e.get('timer_clock')|(e.get('timer_clock',1)<<8),e.get('timer_wait')|(e.get('timer_wait',1)<<8),e.get('arpirq_enabled')))
  assert outputs[0]==outputs[1],(case,elapsed,wait,outputs)
 print('PASS 160 countdown, deadline, disabled, zero-tick and clock-wrap cases')
finally:
 for e in engines:e.p.stop(save=False)

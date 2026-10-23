"""Prepared note attacks preserve legacy orders, velocities and clock behavior."""
from test_mod_port_arp import Engine
class Prepared(Engine):
 def __init__(self,rom):
  super().__init__(rom);self.pending=[];self.returns=set()
  ptr=self.S['_arp_native_sound'];bank=ptr>>16
  def entry(_):
   r=self.p.register_file;sp=r.SP;ret=self.p.memory[sp]|self.p.memory[sp+1]<<8
   self.pending.append((sp+4,(self.time,r.A,r.E,self.p.memory[sp+2])))
   if ret not in self.returns:
    self.p.hook_register(bank,ret,returned,None);self.returns.add(ret)
  def returned(_):
   if self.pending and self.p.register_file.SP==self.pending[-1][0]:
    _,note=self.pending.pop()
    if self.p.register_file.A:self.notes.append(note)
  self.p.hook_register(bank,ptr&65535,entry,None)
import argparse
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--before',default='build/arp-before.gb');ap.add_argument('--after',default='build/GAYBOY.gb');args=ap.parse_args()
before=(Prepared if '_arp_native_sound' in Path(args.before).with_suffix('.noi').read_text() else Engine)(args.before);after=Prepared(args.after)
try:
 cases=0
 for order in range(11):
  for clock,timing in ((0,0),(0,1),(0,2),(1,0)):
   a=before.run(order,clock,timing);b=after.run(order,clock,timing)
   assert a==b,(order,clock,timing,a,b)
   cases+=1
 for order in (0,3,8):
  a=before.run(order,0,0,0);b=after.run(order,0,0,0)
  assert a==b,(order,'retain',a,b)
  cases+=1
 print('PASS',cases,'orders/clock/velocity/retain configurations match baseline')
finally:before.p.stop(save=False);after.p.stop(save=False)

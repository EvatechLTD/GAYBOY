"""Compare populated arp order, velocity and timing against archived main."""
from mod_port_harness import Engine as Base

class Engine(Base):
 def __init__(self,rom):
  super().__init__(rom)
  self.notes=[];self.time=0
  a=self.S['_play']
  def note(_):
   r=self.p.register_file
   self.notes.append((self.time,r.A,r.E,self.p.memory[r.SP+2]))
  self.p.hook_register(a>>16,a&65535,note,None)
 def run(self,order,clock,timing,retrigger=1):
  p=self.p;p.memory[0xc000:0xe000]=self.base;p.memory[0xa000:0xc000]=self.ram
  self.notes.clear();self.time=0
  self.put('syncmode',0);self.put('seqplaying',1);self.put('seqservicing',1)
  self.word('seqbpm',300);self.word('seqstepunits',51);self.word('seqthreshold',15360)
  for c in range(7):self.word('seqeventcounts',3 if c==0 else 0,c*2);self.word('seqeventoffsets',0 if c==0 else 3,c*2);self.word('seqlength',16,c*2)
  p.memory[0x4000]=1
  for i,(note,vel) in enumerate([(49,127),(53,64),(56,100)]):p.memory[0xa300+i*4:0xa304+i*4]=[0,note,vel,16]
  p.memory[0x4000]=0
  self.put('evalpatch',1);self.put('evalpatch',clock,1);self.put('evalpatch',2,2);self.put('evalpatch',timing,3)
  self.put('evalpatch',retrigger,4);self.put('evalpatch',order,5);self.put('evalpatch',7,6);self.put('evalpatch',0,7)
  self.put('mx',127,12);self.put('mx',3,19);self.put('power',1)
  if '_dispatch_enabled' in self.S:self.put('dispatch_enabled',1)
  self.call('storage_sorted_dirty');self.call('eval_chord_dirty',(0,));self.call('eval_seq_fire',(0,))
  for tick in range(1,65):
   self.time=tick
   if '_seq_arp_consume' in self.S:self.call('seq_arp_consume',(1,0,tick,0))
   else:self.call('eval_seq_tick',(1,0))
  return list(self.notes)

def main():
 baseline=Engine('build/mod-port-baseline/GAYBOY.gb');candidate=Engine('build/GAYBOY.gb')
 try:
  cases=0
  for order in range(11):
   for clock,timing in [(0,0),(0,1),(0,2),(1,0)]:
    before=baseline.run(order,clock,timing);after=candidate.run(order,clock,timing)
    assert before==after,(order,clock,timing,before,after)
    cases+=1
  for order in (0,3,8):
   assert baseline.run(order,0,0,0)==candidate.run(order,0,0,0)
   cases+=1
  # A song/chord rebuild wakes an empty arp. Retain mode resumes its paused
  # clock; retrigger mode resets it. Do not compare idle elapsed time with old
  # main, which intentionally kept advancing those empty clocks.
  for retrigger in (0,1):
   candidate.run(0,0,0,retrigger)
   candidate.call('eval_seq_off',(0,))
   candidate.word('arpclock',321)
   candidate.call('eval_seq_tick',(64,0))
   assert candidate.get('arpclock')|candidate.get('arpclock',1)<<8==321
   candidate.call('eval_chord_dirty',(0,))
   candidate.call('eval_seq_fire',(0,))
   assert candidate.get('arpcount')==3
   assert candidate.get('arpclock')|candidate.get('arpclock',1)<<8==(0 if retrigger else 321)
   candidate.call('eval_seq_tick',(1,0))
   assert candidate.get('arpclock')|candidate.get('arpclock',1)<<8==(300 if retrigger else 621)
  print('PASS:',cases,'arp configurations: eleven orders, straight/triplet/dotted/free-ms clocks and retained phase match pre-port main exactly')
 finally:baseline.p.stop(save=False);candidate.p.stop(save=False)

if __name__=="__main__":main()

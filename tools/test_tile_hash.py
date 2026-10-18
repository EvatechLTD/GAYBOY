"""Check the actual tile hash CPU routine and its real DRUM-grid distribution."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(8);p.tick(90)
p.memory[S['_seqtrack']]=6;p.memory[S['_seqdrawvalid']]=0;p.memory[S['_dirty']]=1;p.tick(200)
ids=list(p.memory[S['_seqscreen']+20:S['_seqscreen']+360])
def tile_index(t):return t-64 if 64<=t<96 else t-128 if 160<=t<244 else t-136 if t>=252 else None
patterns=[bytes(p.memory[0xb000+tile_index(t)*16:0xb000+tile_index(t)*16+16]) for t in ids if tile_index(t) is not None]
def new_hash(data):
 h=167
 for b in data:
  carry=h>>7;h=(((h<<1)|(h>>7))+b+carry)&255
 return h
def old_hash(data):
 h=0
 for b in data:h=(((h<<1)|(h>>7))&255)^b
 return h
def comparisons(fn):
 chains={};count=0
 for data in patterns:
  bucket=chains.setdefault(fn(data),[])
  for item in bucket:
   count+=1
   if item==data:break
  else:bucket.insert(0,data)
 return count,max(map(len,chains.values()))
old,new=comparisons(old_hash),comparisons(new_hash)
assert new[0]<old[0]//2,(old,new)
# Exercise actual SM83 instructions independently of the rest of the app.
p.memory[0,0x3ff0]=0x18;p.memory[0,0x3ff1]=0xfe
p.memory[0xffff]=0;p.memory[0xff07]=0;p.memory[0xff0f]=0;p.memory[0x2000]=13;p.memory[0x3000]=0;p.memory[0xff90]=13
cases=list(dict.fromkeys(patterns))
for mask in range(256):cases.extend((bytes([mask,0])*8,bytes([0,mask])*8,bytes([mask,mask])*8))
for data in cases:
 p.memory[0xba00:0xba10]=data;sp=0xdf00;p.memory[sp:sp+2]=[0xf0,0x3f]
 p.register_file.SP=sp;p.register_file.D=0xba;p.register_file.E=0;p.register_file.PC=S['_roll_hash']&65535;p.tick(1)
 assert p.register_file.SP==sp+2 and p.register_file.A==new_hash(data),data.hex()
p.stop(save=False)
print('PASS: actual CPU hash for',len(cases),'tiles; real DRUM lookup comparisons/chains',old,'->',new)

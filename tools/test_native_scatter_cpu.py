"""Check every native patch destination and compare finalized application paths."""
from io import BytesIO
from pathlib import Path
import argparse,binascii,json,random,re
from pyboy import PyBoy
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');args=ap.parse_args()
S={l.split()[1]:int(l.split()[2],16) for l in Path(args.rom).with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
source=Path('src/tones.c').read_text().split('static void apply_prepared(void)',1)[1].split('static void finalize_prepared(void)',1)[0]
fields=[(address.strip(),int(size)) for address,size in re.findall(r'ld hl,#([^\n]+)\n\s*\.rept (\d+)',source)]+[('_pulsekickpatch',8)]
def address(expression):
 symbol,*offset=expression.split('+');return S[symbol]+sum(int(n) for n in offset)
destinations=[address(expression)+i for expression,size in fields for i in range(size)]
assert len(destinations)==450 and len(set(destinations))==450
p=PyBoy(args.rom,window='null',sound_emulated=False,cgb=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0)
p.memory[0]=10;p.memory[0x4000]=0;p.memory[0xffff]=0;p.memory[0xff0f]=0;p.memory[0xff50]=1;p.memory[0xff40]=0
p.memory[0xc000:0xe000]=[0]*8192;p.memory[0xc000:0xc004]=[0x18,0,0x18,0xfe];returns=[]
p.hook_register(0,0xc000,lambda _:returns.append((p.register_file.A,p._cycles())),None)
mode_change=[False]
def change_mode_during_map(_):
 if mode_change[0]:p.memory[S['_waveengine']]=2;mode_change[0]=False
at=S['_pool_native_map'];p.hook_register(at>>16,at&65535,change_mode_during_map,None)
def call(name,arguments=()):
 pointer=S['_'+name];bank=pointer>>16;p.memory[0x2000]=bank;p.memory[0x3000]=0;p.memory[0xff90]=bank
 frame=[0,0xc0,0,0,0,0]+list(arguments);p.memory[0xdfe0:0xdfe0+len(frame)]=frame;p.register_file.SP=0xdfe0;p.register_file.PC=pointer&65535
 returns.clear();started=p._cycles()
 for _ in range(600):
  p.tick(1)
  if returns:break
 assert returns,(name,hex(p.register_file.PC));return returns[-1][0],(returns[-1][1]-started)*1000/4194304
def physical(page):return (1,page*64) if page<128 else (2,(page-128)*64) if page<224 else (3,(page-224)*64)
def object_fixture(data,pages):
 header=bytes((ord('T'),1,194,1));crc=binascii.crc_hqx(header+data,65535);content=header+crc.to_bytes(2,'little')+data
 for i,page in enumerate(pages):
  bank,offset=physical(page);block=(pages[i+1] if i+1<len(pages) else 65535).to_bytes(2,'little')+content[i*62:(i+1)*62].ljust(62,b'\x00')
  p.memory[0x4000]=bank;p.memory[0xa000+offset:0xa000+offset+64]=list(block)
 p.memory[0x4000]=0
 return pages[0]
def raw_fixture(data):p.memory[0xba00:0xba00+442]=list(data[:442]);p.memory[0xbbd0:0xbbd8]=list(data[442:])
def state_bytes():
 return bytes(p.memory[0xc004:0xde00])+bytes(p.memory[S['_noisepatch']:S['_noisepatch']+10])
rng=random.Random(450);vectors=[bytes(450),bytes([255])*450]+[rng.randbytes(450) for _ in range(6)]
layouts=[list(range(4,12)),[127,128,223,224,299,300,301,303]];scatter_times=[];apply_times=[];cases=0
try:
 initial=BytesIO();p.save_state(initial);initial=initial.getvalue()
 for pages in layouts:
  for data in vectors:
   p.load_state(BytesIO(initial));object=object_fixture(data,pages);p.memory[0xa000]=0x5a
   okay,elapsed=call('tones_scatter_object',(object&255,object>>8));assert okay
   actual=bytes(p.memory[at] for at in destinations)
   assert actual==data,('Native450-byte scatter mismatch',next((i for i,(a,b) in enumerate(zip(actual,data)) if a!=b),None),pages)
   assert p.memory[0xa000]==0x5a,'RAMbank0 not restored';scatter_times.append(elapsed);cases+=1
  # Exact finalized parity in native and both software WAVE owners. Random
  # field bytes are safe here: experimental mode is off and no voices run.
  for owner in (0,1,2,3):
   p.load_state(BytesIO(initial));data=vectors[2];object=object_fixture(data,pages);p.memory[S['_waveengine']]=owner
   base=BytesIO();p.save_state(base);base=base.getvalue()
   raw_fixture(data);call('tones_apply');expected=state_bytes()
   p.load_state(BytesIO(base));okay,elapsed=call('tones_apply_object',(object&255,object>>8));assert okay
   assert state_bytes()==expected,('Finalized native application mismatch',owner,pages)
   apply_times.append((owner,round(elapsed,3)));cases+=1
 # Mapping can dispatch a queued engine-mode MIDI message. The low-level
 # path must reject before its first destination write; its parent must
 # then complete through the established software-engine application path.
 p.load_state(BytesIO(initial));data=vectors[3];object=object_fixture(data,layouts[1]);before=bytes(p.memory[at] for at in destinations)
 mode_change[0]=True;okay,_=call('tones_scatter_object',(object&255,object>>8));assert not okay
 assert bytes(p.memory[at] for at in destinations)==before,'Rejected scatter modified native destinations';cases+=1
 p.load_state(BytesIO(initial));object=object_fixture(data,layouts[1]);base=BytesIO();p.save_state(base);base=base.getvalue()
 p.memory[S['_waveengine']]=2;raw_fixture(data);call('tones_apply');expected=state_bytes()
 p.load_state(BytesIO(base));mode_change[0]=True;okay,_=call('tones_apply_object',(object&255,object>>8));assert okay
 assert state_bytes()==expected,'Mode-change fallback did not match existing software application';cases+=1
 print(json.dumps({'result':'PASS','native_destination_bytes':450,'cases':cases,'mode_change_cases':2,'max_scatter_ms':round(max(scatter_times),3),'apply_ms':apply_times}))
finally:p.stop(save=False)

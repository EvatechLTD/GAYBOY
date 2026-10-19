"""Execute actual tonal/PCM onset paths and verify their scheduled gate lengths."""
from io import BytesIO
from pathlib import Path
import argparse,json
from pyboy import PyBoy
from seq_storage_helpers import write_tracks,write_word,read_word
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');args=ap.parse_args()
S={l.split()[1]:int(l.split()[2],16) for l in Path(args.rom).with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy(args.rom,window='null',sound_emulated=False,cgb=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0)
p.memory[0]=10;p.memory[0x4000]=0;p.memory[0xffff]=0;p.memory[0xff0f]=0;p.memory[0xff50]=1;p.memory[0xff40]=0
p.memory[0xc000:0xc004]=[0x18,0,0x18,0xfe];returned=[]
p.hook_register(0,0xc000,lambda _:returned.append(p._cycles()),None)
def store(name,value,size=1,index=0):
 at=S['_'+name]+index*size;p.memory[at:at+size]=list(value.to_bytes(size,'little'))
def call(name,argument,banked):
 address=S['_'+name];bank=address>>16;p.memory[0x2000]=bank;p.memory[0x3000]=0;p.memory[0xff90]=bank
 frame=[0,0xc0]+([0,0,0,0,argument] if banked else [])
 p.memory[0xdfe0:0xdfe0+len(frame)]=frame;p.register_file.SP=0xdfe0;p.register_file.A=argument;p.register_file.PC=address&65535
 returned.clear();p.tick(1);assert returned,(name,hex(p.register_file.PC))
def fixture(bpm):
 store('seqbpm',bpm,2);store('seqcachedbpm',bpm,2);store('seqstepunits',15360//bpm,2)
 store('seqeventcache',0);store('seqrecordtrack',255);store('seqplaying',0);store('seqmode',0);store('seqmuted',0);store('seqsolo',0);store('seqposition',0,index=1)
 store('druminit',1);store('drumkit',1);store('waveengine',3);store('drumenabled',1);store('drumon',0,index=0);store('drumon',0,index=1);store('drummutemask',0,2);store('drumsolomask',0,2)
 # Mixer is not open, so its velocity/pan helpers use neutral defaults.
 store('mx',0,index=0)
count=0
try:
 for bpm in (30,31,60,120,121,180,220,299,300):
  for duration in (1,2,3,4,8,16,127,128,255,256):
   for gate in (0,1,50,99,100):
    fixture(bpm);store('seqgate',gate,index=1);store('seqgateunits',(15360//bpm)*gate//100,2,index=1)
    tracks=[[] for _ in range(7)];tracks[1]=[[0,61,100,duration&255]];write_tracks(p,S,tracks)
    call('seq_fire',1,False);at=S['_seqgateleft']+4;actual=int.from_bytes(bytes(p.memory[at:at+4]),'little');expected=max(1,(15360//bpm)*duration*gate//100)
    assert actual==expected,('tonal',bpm,duration,gate,actual,expected);count+=1
   fixture(bpm);tracks=[[] for _ in range(7)];tracks[6]=[[0,1,100,duration&255]];write_tracks(p,S,tracks)
   call('drum_fire',0,True);actual=read_word(p,S['_drumend']);expected=min(3584,(171900//bpm)*duration//2)
   assert actual==expected,('PCM',bpm,duration,actual,expected);count+=1
 print(json.dumps({'result':'PASS','production_onset_gate_cases':count}))
finally:p.stop(save=False)

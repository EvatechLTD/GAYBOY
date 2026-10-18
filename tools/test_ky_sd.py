from pathlib import Path
from collections import deque
import struct
from pyboy import PyBoy
S={l.split()[1]:int(l.split()[2],16) for l in Path('build/KY-SD-TEST.noi').read_text().splitlines() if l.startswith('DEF ')}
def fat16():
 sectors={};b=bytearray(512);b[:3]=bytes((0xEB,0x3C,0x90));b[3:11]=b'KYTEST  '
 struct.pack_into('<HBHBHHBHHH',b,11,512,1,1,1,512,8192,0xF8,32,32,64)
 b[54:62]=b'FAT16   ';b[510:]=b'\x55\xaa';sectors[0]=b
 f=bytearray(512);struct.pack_into('<4H',f,0,0xFFF8,0xFFFF,0xFFFF,0xFFFF);sectors[1]=f
 def entry(name,attr,cluster,size):
  e=bytearray(32);e[:11]=name;e[11]=attr;struct.pack_into('<H',e,26,cluster);struct.pack_into('<I',e,28,size);return e
 root=bytearray(512);root[:32]=entry(b'WAVES      ',16,2,0);sectors[33]=root
 d=bytearray(512);d[:32]=entry(b'TEST    GBW',32,3,16);sectors[65]=d
 wave=bytes((i*17 for i in range(16)));sectors[66]=wave+bytes(496)
 return sectors,wave
def fat32():
 sectors={};b=bytearray(512);b[:3]=bytes((0xEB,0x58,0x90));b[3:11]=b'KYTEST  '
 struct.pack_into('<HBHBHHBHHH',b,11,512,1,32,1,0,0,0xF8,0,32,64)
 struct.pack_into('<I',b,32,131072);struct.pack_into('<I',b,36,1024);struct.pack_into('<I',b,44,2)
 b[82:90]=b'FAT32   ';b[510:]=b'\x55\xaa';sectors[0]=b
 f=bytearray(512);struct.pack_into('<5I',f,0,0xFFFFFF8,0xFFFFFFF,0xFFFFFFF,0xFFFFFFF,0xFFFFFFF);sectors[32]=f
 def entry(name,attr,cluster,size):
  e=bytearray(32);e[:11]=name;e[11]=attr;struct.pack_into('<H',e,26,cluster);struct.pack_into('<I',e,28,size);return e
 root=bytearray(512);root[:32]=entry(b'WAVES      ',16,3,0);sectors[1056]=root
 d=bytearray(512);d[:32]=entry(b'TEST    GBW',32,4,16);sectors[1057]=d
 wave=bytes((i*17 for i in range(16)));sectors[1058]=wave+bytes(496)
 return sectors,wave
class Card:
 def __init__(self,sectors,sdhc=True):self.sectors=sectors;self.sdhc=sdhc;self.q=deque();self.cmd=[];self.selected=False;self.commands=[];self.reply=255
 def control(self,flags):
  selected=not flags&1
  if not selected:self.q.clear();self.cmd=[]
  self.selected=selected
 def transfer(self,x):
  if not self.selected:return 255
  if self.q:return self.q.popleft()
  if not self.cmd and not 0x40<=x<0x80:return 255
  self.cmd.append(x)
  if len(self.cmd)==6:
   c=self.cmd[0]&63;a=int.from_bytes(bytes(self.cmd[1:5]),'big');self.commands.append((c,a));self.cmd=[]
   if c==0:self.q.extend([1])
   elif c==8:self.q.extend([1,0,0,1,170] if self.sdhc else [5])
   elif c==55:self.q.extend([1])
   elif c==41:self.q.extend([0])
   elif c==58:self.q.extend([0,64 if self.sdhc else 0,255,128,0])
   elif c==16:self.q.extend([0])
   elif c==17:
    sector=a if self.sdhc else a//512;self.q.extend([0,255,254]);self.q.extend(self.sectors.get(sector,bytes(512)));self.q.extend([255,255])
   else:raise AssertionError(('Unexpected SD command',c,a))
  return 255

def run(sdhc,kind=16,mbr=False):
 sectors,wave=(fat16 if kind==16 else fat32)();
 if mbr:
  sectors={k+2048:v for k,v in sectors.items()};boot=bytearray(512);boot[450]=6 if kind==16 else 12;struct.pack_into('<II',boot,454,2048,8192 if kind==16 else 131072);boot[510:]=b'\x55\xaa';sectors[0]=boot
 card=Card(sectors,sdhc);p=PyBoy('build/KY-SD-TEST.gb',window='null',sound_emulated=True);p.set_emulation_speed(0)
 p.hook_register(0,S['_ky_control'],lambda ctx:card.control(p.register_file.A),None)
 p.hook_register(0,S['_ky_spi'],lambda ctx:setattr(card,'reply',card.transfer(p.register_file.A)),None)
 p.hook_register(0,S['_ky_spi_reply'],lambda ctx:setattr(p.register_file,'A',card.reply),None)
 def v(n):return p.memory[S['_'+n]]
 def press(k):p.button_press(k);p.tick(24);p.button_release(k);p.tick(24)
 p.tick(180);assert v('ky_result')==0,(v('ky_result'),v('ky_stage'),v('ky_r1'));assert v('ky_count')==1
 assert bytes(p.memory[S['_ky_names']:S['_ky_names']+5])==b'WAVES'
 press('a');assert v('ky_count')==1 and bytes(p.memory[S['_ky_names']:S['_ky_names']+8])==b'TEST.GBW'
 press('a');assert v('ky_showfile') and bytes(p.memory[S['_ky_bytes']:S['_ky_bytes']+16])==wave
 press('a');assert p.memory[0xFF26]&4
 press('b');assert not v('ky_showfile') and not p.memory[0xFF26]&4
 press('b');assert p.memory[S['_ky_path']]==0
 assert all(c in (0,8,55,41,58,16,17) for c,a in card.commands)
 p.screen.image.save('build/ui-ky-fat16-'+str(sdhc)+'.png');p.stop(save=False)
 print('PASS: KY SPI '+('SDHC block' if sdhc else 'SDSC byte')+' addressing, FAT'+str(kind)+(' MBR' if mbr else ' volume')+' mount, directories, wave file read/preview, parent navigation; no SD write commands')
run(True);run(False);run(True,32);run(True,32,True);run(True,16,True)

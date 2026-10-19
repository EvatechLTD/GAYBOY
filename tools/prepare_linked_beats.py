"""Build distinct eight-pad beat batteries for the two virtual-link endpoints."""
from pathlib import Path
from io import BytesIO
from pyboy import PyBoy
from boot_helpers import enter_app
from seq_storage_helpers import write_tracks,write_word
from sparse_image import SparseImage
import random,json,shutil,time
# Reuse input acknowledgement and Finder navigation, without running its tests.
exec(Path('tools/test_mixer_settings.py').read_text().split('try:\n')[0])
reports=[]
try:
 for side,seed,kit in [('LEFT',104729,1),('RIGHT',130363,2)]:
  rng=random.Random(seed)
  enter_app(p,S)
  for slot in range(8):
   choose(18);p.memory[S['_mx']+4]=30+slot;tap('b');p.tick(80)
   assert v('mx',1)==slot and not v('seqplaying')
   tracks=[[] for _ in range(7)]
   kick=([0,8] if side=='LEFT' else [0,6,10])+rng.sample([2,3,14],1+slot%2)
   snare=[4,12] if side=='LEFT' else [4,11 if slot%2 else 12]
   hats=range(0 if side=='LEFT' else 1,16,2)
   for step in sorted(set(kick)):tracks[6].append([step,1,rng.randint(103,124),2])
   for step in snare:tracks[6].append([step,2,rng.randint(94,116),2])
   for step in hats:tracks[6].append([step,3,rng.randint(55,88),1])
   tracks[6].append([(2+slot*2)%16,6 if side=='LEFT' else 7,70+slot*3,2])
   tracks[6].sort(key=lambda e:(e[0],e[1]))
   write_tracks(p,S,tracks);p.memory[S['_seqeventcache']]=0
   for c in range(7):
    write_word(p,S['_seqlength']+c*2,16);p.memory[S['_mx']+12+c]=127;p.memory[S['_mx']+19+c]=3
   for n in ['seqmuted','seqsolo','seqmode']:p.memory[S['_'+n]]=0
   write_word(p,S['_drummutemask'],0);write_word(p,S['_drumsolomask'],0)
   write_word(p,S['_seqbpm'],120);write_word(p,S['_seqglobalbpm'],120);write_word(p,S['_seqcachedbpm'],0)
   p.memory[S['_drumkit']]=kit
   title=f'{side[0]}{slot+1:02} GROOVE'.encode().ljust(17,b'\0');p.memory[S['_mx']+26:S['_mx']+43]=list(title)
   choose(20);p.memory[S['_mx']+6]=v('sparse_patterns');tap('b')
   assert v('page')==18 and not v('seqplaying')
  choose(18);p.memory[S['_mx']+4]=30;tap('b');p.tick(80)
  title=f'{side} TEST BEATS'.encode().ljust(17,b'\0');p.memory[S['_sparse_song_name']:S['_sparse_song_name']+17]=list(title)
  choose(25);p.memory[S['_mx']+6]=1;tap('b');assert v('page')==18
  p.memory[S['_pool_root']+7]=0;p.memory[S['_pool_root']+8]=4;p.memory[S['_mixer_layout_dirty']]=1
  for _ in range(1800):
   p.tick(1)
   if not v('mixer_layout_dirty'):break
  assert not v('mixer_layout_dirty') and not v('seqplaying')
  battery=bytearray()
  for bank in range(4):
   p.memory[0x4000]=bank;battery.extend(p.memory[0xa000:0xc000])
  p.memory[0x4000]=0
  image=SparseImage(bytes(battery));patterns=[]
  for slot in range(8):
   obj=image.object(image.word(image.root,16+slot*2),'P')
   assert obj[:16].split(b'\0')[0].decode()==f'{side[0]}{slot+1:02} GROOVE'
   patterns.append({'name':obj[:16].split(b'\0')[0].decode(),'events':list(obj[102:]),'kit':kit})
  reports.append({'side':side,'seed':seed,'patterns':patterns})
  folder=Path('build/linked-test')/side;folder.mkdir(parents=True,exist_ok=True)
  dest=folder/(side+'.sav')
  if dest.exists():shutil.copy2(dest,folder/(side+f'.before-beats-{time.time_ns()}.sav'))
  dest.write_bytes(battery);shutil.copy2('build/GAYBOY.gb',folder/(side+'.gb'))
  p.stop(save=False)
  if side=='LEFT':
   p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0)
 assert len({bytes(pat['events']) for side in reports for pat in side['patterns']})==16
 Path('build/linked-test/beat-fixtures.json').write_text(json.dumps(reports,indent=2)+'\n')
 print('PASS: 16 distinct simple beats saved through ROM UI; LEFT TR-808, RIGHT TR-909, eight named pads each')
finally:p.stop(save=False)

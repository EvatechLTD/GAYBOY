"""Prepared pattern launches install the new tone before their first note."""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--bpm',type=int,default=120);ap.add_argument('--output',default='build/pattern-audio-handoff.json');args=ap.parse_args()
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].replace('range(60)','range(600)').replace('enter_app(p)','enter_app(p,S)').replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file=').replace('build/GAYBOY',str(Path(args.rom).with_suffix('')).replace('\\','/')))
from seq_storage_helpers import write_tracks,write_word
mx=S['_mx'];launches=[]
def setm(i,x):p.memory[mx+i]=x
release=[];attacks=[];transports=[];results=[];pulseoffs=[];prepared=[]
def hook(name,callback):
 a=S['_'+name];p.hook_register(a>>16,a&65535,callback,None)
def played(_):
 if release and p.register_file.A==0:attacks.append(p._cycles())
try:
 choose(18)
 for name in ('seqbpm','seqglobalbpm'):write_word(p,S['_'+name],args.bpm)
 tracks=[[] for _ in range(7)]
 tracks[0]=[[0,61,100,16]];tracks[6]=[[i,1,127,1] for i in range(16)]
 write_tracks(p,S,tracks)
 p.memory[S['_param']]=2;p.memory[S['_param']+1]=12;p.memory[S['_param']+3]=0
 choose(20);press('b')
 # Use the current sparse-storage UI. Writing a legacy 2560-byte SRAM
 # slot here would overwrite pool objects and invalidate later launches.
 choose(18);setm(4,31);press('a')
 write_tracks(p,S,tracks)
 p.memory[S['_param']]=1;p.memory[S['_param']+1]=12;p.memory[S['_param']+3]=0
 choose(20);setm(6,1);press('b')
 choose(18);setm(4,30);press('a')
 choose(18);setm(4,0);press('a');assert v('seqplaying')
 hook('seq_pattern_release',lambda _:release.append(p._cycles()))
 hook('play',played)
 # The native batch bypasses play(). Observe the actual P1 trigger stores
 # as well, excluding silent releases from the same fixed writer.
 if '_seq_native_hardware' in S:
  start=S['_seq_native_hardware'];end=min(a for k,a in S.items() if k.startswith('_') and start<a<0x4000)
  rom=Path(args.rom).read_bytes()
  def native_attack(_):
   if release and p.memory[0xa400]&1 and p.register_file.A&128:attacks.append(p._cycles()+12)
  for pc in range(start,end-1):
   if rom[pc:pc+2]==bytes((0xe0,0x14)):p.hook_register(0,pc,native_attack,None)
 hook('seq_off',lambda _:pulseoffs.append(p._cycles()) if release and not attacks and p.register_file.A==0 else None)
 hook('seq_transport',lambda _:transports.append(p._cycles()))
 if '_seq_native_launch_copy' in S:
  hook('seq_native_launch_copy',lambda _:prepared.append((p._cycles(),p.memory[0xa600],v('seqnativehits')|v('seqnativehits',1)<<8,v('seqnativemisses')|v('seqnativemisses',1)<<8)))
 for quant,target in ((4,1),(2,0),(1,1),(0,0),(0,1)):
  release.clear();attacks.clear();transports.clear();pulseoffs.clear();prepared.clear()
  setm(3,quant);setm(4,30+target);request=p._cycles();press('a')
  for _ in range(360):
   p.tick(1)
   if p.memory[mx+1]==target and attacks and not v('seqservicing'):break
  assert attacks and release,(quant,target,release,attacks,{n:v(n) for n in ('seqplaying','seqservicing','pool_error','sparse_enabled')},list(p.memory[mx:mx+12]))
  assert v('seqplaying') and not transports,('transport restarted',quant,transports)
  assert not pulseoffs,('native onset was silenced before replacement',quant,pulseoffs)
  gap=(attacks[0]-release[0])*1000/4194304
  assert gap<1000/59.7275,('audible handoff gap',quant,gap,prepared)
  assert p.memory[0xff26]&1,'Incoming pulse must sound'
  assert p.memory[S['_param']]==(1 if target else 2),('Wrong incoming tone',target)
  results.append(dict(quant=quant,target=target,release_to_attack_ms=round(gap,3),request_to_attack_ms=round((attacks[0]-request)*1000/4194304,3)))
 Path(args.output).write_text(json.dumps(dict(bpm=args.bpm,rom=args.rom,launches=results),indent=2)+'\n')
 print('PASS: OFF/1-8/1-4/1-1 launches retain transport and incoming tone:',json.dumps(results))
finally:p.stop(save=False)


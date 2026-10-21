"""Executed by make_drum_samples; prepared WAVs are self-contained build inputs."""
import json, subprocess, shutil, sys
recipe="lsbatch-punch-v3"
chain="highpass=f=20,acompressor=threshold=-22dB:ratio=6:attack=3:release=70,volume=18dB,asoftclip,lowpass=f=5000,aresample=11468:filter_size=64:cutoff=0.95"
kitdefs=[
 ('TR-808','Roland TR-808',['TR-808Kick05','TR-808Snare03','TR-808Hat_C01','TR-808Hat_O01','TR-808Clap01','TR-808Tom01','TR-808Tom05','TR-808Cow']),
 ('TR-909','Roland TR-909',['TR-909Kick 01','TR-909Snare 01','TR-909Hat C 01','TR-909Hat O 03','TR-909Clap','TR-909Tom Low 01','TR-909Tom Hi 01','TR-909Rim']),
 ('TR-707','Roland TR-707',['TR-707Kick01','TR-707Snare01','TR-707Hat_C','TR-707Hat_O','TR-707Clap','TR-707Tom_Lo','TR-707Tom_Hi','TR-707Cow']),
 ('LINNDRUM','Linn Linndrum',['kick','sd','chh','ohh','clap','toml','tomh','tamb']),
 ('OBERHEIM DMX','Oberheim DMX',['DMXKick01','DMXSnare01','DMXHat_C','DMXHat_O','DMXClap','DMXTomLo','DMXTomHi','DMXRim'])]
prepared=root/'assets/kits';prepared.mkdir(parents=True,exist_ok=True)
metadata=[];manifest=[]
recipefile=prepared/"mastering.json"
remaster="--remaster" in sys.argv or not recipefile.exists() or json.loads(recipefile.read_text()).get("recipe")!=recipe
measurements=[]
for k,(title,directory,files) in enumerate(kitdefs):
 bank=32+k;banks[bank]=[];offs=[];lens=[]
 for slot,stem in enumerate(files):
  path=prepared/f'{k+1}-{slot+1}-{stem}.wav'
  source=Path('G:/AUDIO/300 Drum Machines')/directory/(stem+'.wav')
  if not path.exists() or remaster:
   before=None
   if path.exists():
    backup=root/'build/kit-remaster-before'/path.name;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(path,backup)
    with wave.open(str(backup),'rb') as w:before=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768
   raw=subprocess.check_output([shutil.which('ffmpeg'),'-v','error','-i',str(source),'-af',chain,'-ac','1','-f','f32le','-'])
   pcm=np.frombuffer(raw,'<f4').copy();pcm-=np.mean(pcm)
   peak=np.max(np.abs(pcm));hits=np.flatnonzero(np.abs(pcm)>peak*.002)
   if not len(hits):raise ValueError(source)
   pcm=pcm[max(0,hits[0]-8):min(len(pcm),hits[-1]+58)]
   pcm=pcm[:int(11468*.65)]
   fade=min(80,len(pcm)//8)
   pcm[-fade:]*=np.linspace(1,0,fade);pcm[:4]*=np.linspace(0,1,4)
   pcm*=10**(-1/20)/np.max(np.abs(pcm))
   def attack_rms(x):
    x=x[:min(len(x),1376)]
    return float(np.sqrt(np.mean(x*x)))
   measurements.append(dict(kit=title,slot=slot+1,before_rms=attack_rms(before) if before is not None else None,after_rms=attack_rms(pcm)))
   with wave.open(str(path),'wb') as w:
    w.setparams((1,2,11468,0,'NONE','not compressed'));w.writeframes((pcm*32767).astype('<i2').tobytes())
  with wave.open(str(path),'rb') as w:
   assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,11468)
   pcm=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(np.int32)
  x=((pcm+32768)>>12).astype(np.uint8);x=np.pad(x,(0,(-len(x))%32),constant_values=8)
  x=np.roll(x.reshape(-1,32),1,axis=1).reshape(-1);packed=(x[::2]<<4)|x[1::2]
  offs.append(len(banks[bank]));lens.append(len(packed));banks[bank].extend(packed.tolist())
  manifest.append(dict(kit=title,slot=slot+1,source=str(source),prepared=str(path.relative_to(root)),samples=len(pcm),mastering=recipe))
 # Two unused legacy sample rows remain silent; noise rows retain their mapping.
 offs += [len(banks[bank])]*2;lens += [16]*2;banks[bank]+=[136]*16
 assert len(banks[bank])<16300,(title,len(banks[bank]))
 metadata.append(([bank]*10,offs,lens))
# Direct 4-bit kits are approved packed assets: never remaster through WAV.
kit_banks = [32,33,34,35,36,39,62]
for title, bank in [('SLAP808',39),('SLAM909',62)]:
 folder=root/'DRUMSAMPLES/DIRECT4BIT'/title
 kit=json.loads((folder/'kit.json').read_text())
 data=(folder/'kit-bank.bin').read_bytes()
 assert kit['rate']==11468 and kit['bits']==4 and len(data)==kit['bytes']<16300
 banks[bank]=list(data)
 offs=[sound['offset'] for sound in kit['sounds']]+[row['offset'] for row in kit['unused_rows']]
 lens=[sound['length'] for sound in kit['sounds']]+[row['length'] for row in kit['unused_rows']]
 assert len(offs)==len(lens)==10
 for sound in kit['sounds']:
  packed=(folder/(f"{sound['slot']:02d}-{sound['role']}.4bit")).read_bytes()
  assert data[sound['offset']:sound['offset']+sound['length']]==packed
  manifest.append(dict(kit=title,slot=sound['slot'],prepared=str((folder/(f"{sound['slot']:02d}-{sound['role']}.4bit")).relative_to(root)),samples=sound['samples'],mastering='direct-4bit-v1'))
 metadata.append(([bank]*10,offs,lens))
kitmeta=''
for i,(name,typ) in enumerate([('bank','uint8_t'),('offset','uint16_t'),('length','uint16_t')]):
 kitmeta+=f'const {typ} kit{name}[{len(metadata)}][10]={{'+','.join('{'+arr(m[i])+'}' for m in metadata)+'};\n'
 kitmeta+=f'#define drum{name} (DRUM_MAPPED?drumsource{name}:drumkit?kit{name}[drumkit-1]:amen{name})\n'
(prepared/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

recipefile.write_text(json.dumps(dict(recipe=recipe,filter=chain,peak_dbfs=-1,maximum_seconds=.65,tail_fade_samples=80),indent=2)+'\n')
if measurements:
 (root/'build/kit-remaster-loudness.json').write_text(json.dumps(measurements,indent=2)+'\n')
 gains=[20*np.log10(m['after_rms']/m['before_rms']) for m in measurements if m['before_rms']]
 print('Remastered',len(measurements),'hits; mean first-120ms RMS change:',round(float(np.mean(gains)),2),'dB before playback gain')

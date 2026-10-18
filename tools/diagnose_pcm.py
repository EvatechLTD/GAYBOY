"""Capture executed PCM reload timing and emulator audio; no ROM source changes.

The nibble counts below follow documented DMG timing, not analog measurements.
"""
import argparse,csv,json,wave
from pathlib import Path
import numpy as np
args=argparse.ArgumentParser();args.add_argument('--fixture',choices=['real','ramp','flat8','flat0','flat15'],default='real');args.add_argument('--level',type=int,choices=[1,2,3],default=1);args=args.parse_args()
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def put(name,index,value):fixture_put(p,S,name,index,value)
def chord(mod,key):
 p.button_press(mod);p.tick(3);press(key);p.button_release(mod);p.tick(5)
choose(8);chord('select','left');assert v('seqtrack')==6
for i in range(128):put('drumhits',i,0);put('noisehits',i,0)
put('drumhits',0,10);put('drumvel',0,127);put('drumdur',0,4);put('seqlength',6,64)
packets=[];off=[];triggers=[];routes=[]
def packet(_):
 at=S['_mixbuffer']+v('mixwrite')*16
 if args.fixture!='real':
  if args.fixture=='ramp':n=[(i-1)&15 for i in range(32)]
  else:n=[int(args.fixture[4:])]*32
  for i in range(16):p.memory[at+i]=(n[i*2]<<4)|n[i*2+1]
 put('pcmoutlevel',0,args.level)
 packets.append([p.memory[at+i] for i in range(16)])
a=S['_drum_duration']-1;p.hook_register(a>>16,a&65535,packet,None)
rom=Path('build/GAYBOY.gb').read_bytes();a=S['_drum_timer'];bank=a>>16;pc=a&65535;base=bank*16384+(pc&16383)
code=rom[base:base+((S['_drum_irq']&65535)-pc)]
mask=code.index(bytes.fromhex('f0 25 f5 e6 bb e0 25 af e0 1a'));trigger=code.index(bytes.fromhex('e0 1e f1 e0 25'),mask)
p.hook_register(bank,pc+mask+8,lambda _:off.append(p._cycles()+12),None)
p.hook_register(bank,pc+trigger,lambda _:triggers.append((p._cycles()+12,[p.memory[0xff30+i] for i in range(16)])),None)
p.hook_register(bank,pc+trigger+5,lambda _:routes.append(p._cycles()),None)
p.button_press('select');p.tick(3);p.button_press('a');audio=[]
for i in range(45):
 p.tick(1);audio.append(p.sound.ndarray.copy())
 if i==3:p.button_release('a')
 if i==5:p.button_release('select')
out=Path('build/pcm-diagnostics');out.mkdir(exist_ok=True);tag=args.fixture+'-level'+str(args.level)
rows=[]
for i,(cycle,values) in enumerate(triggers):
 nextoff=off[i+1] if i+1<len(off) else None
 active=nextoff-cycle if nextoff is not None else None
 divider=176;sample_cycles=divider*2;first_read=sample_cycles+5
 reads=max(0,1+(active-first_read)//sample_cycles) if active is not None and active>=first_read else 0
 rows.append({'block':i,'dac_off_cycle':off[i],'trigger_cycle':cycle,'next_dac_off_cycle':nextoff,'active_cycles':active,'documented_sample_reads_before_next_off':reads if active is not None else None,'hardware_divider':divider,'wave_bytes':bytes(values).hex()})
with (out/(tag+'.csv')).open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
x=np.concatenate(audio).astype(np.int16);rate=p.sound.sample_rate
with wave.open(str(out/(tag+'.wav')),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate);w.writeframes((x*128).astype('<i2').tobytes())
y=x[rate//12:rate//3].astype(float).mean(axis=1);y-=y.mean();freq=np.fft.rfftfreq(len(y),1/rate);mag=np.abs(np.fft.rfft(y*np.hanning(len(y))));peaks=np.argsort(mag[1:])[-8:]+1
result={'fixture':args.fixture,'hardware_level':args.level,'uploads':len(rows),'underruns':word('mixunderruns'),'sample_rate':rate,'peak_audio_frequency_hz':[round(float(freq[i]),1) for i in peaks[::-1]],'rms_pcm':round(float(np.sqrt(np.mean(y*y))),4),'reload_cycle_gaps':sorted(set(int(b[0]-a[0]) for a,b in zip(triggers,triggers[1:]))),'active_window_cycles':sorted(set(r['active_cycles'] for r in rows if r['active_cycles'] is not None)),'documented_reads_per_window':sorted(set(r['documented_sample_reads_before_next_off'] for r in rows if r['active_cycles'] is not None))}
(out/(tag+'.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result));p.stop(save=False)

from boot_helpers import enter_app, enable_experimental
from pathlib import Path
from pyboy import PyBoy
import numpy as np
import wave
S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True);p.set_emulation_speed(0);enter_app(p);enable_experimental(p)
def v(n,i=0):return p.memory[S['_'+n]+i]
def word(n,i=0):return v(n,2*i)|(v(n,2*i+1)<<8)
def send(data):
 for b in data:
  w=v('wr');p.memory[S['_rx']+w]=b;p.memory[S['_wr']]=(w+1)&255;p.tick(8)
def capture(name,frames=90):
 data=[]
 for _ in range(frames):p.tick(1);data.append(p.sound.ndarray.copy())
 a=np.concatenate(data);rate=p.sound.sample_rate
 with wave.open('build/'+name+'.wav','wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate);f.writeframes((a.astype(np.int16)*256).tobytes())
 return a,rate
send([0xb4,122,127,0xc4,0,0xb4,117,0,118,0,0x94,60,127,64,127,67,127,72,127])
assert v('waveengine')==2 and all(v('active',i) for i in range(3)) and all(v('softon',i) for i in range(2))
assert [v('basepitch',i) for i in range(2)]==[60,64] and [v('softnote',i) for i in range(2)]==[67,72]
b=word('engineblocks');u=word('mixunderruns');p.tick(120);blocks=word('engineblocks')-b;drops=word('mixunderruns')-u
print('MIX two seconds: blocks',blocks,'underruns',drops);assert blocks>490 and drops<5
capture('mix4-chord',60)
send([0x94,76,127]);assert v('basepitch')==76
send([0x84,60,0]);assert v('active')==1
send([0xb4,64,127,0x84,67,0]);assert v('softon')==1 and v('softheld')==0
phase=word('softphase');send([0xe4,127,127]);assert word('softphase')!=phase
send([0xb4,64,0]);assert v('softon')==0 and v('softon',1)==1
send([0xb4,123,0]);assert not any(v('softon',i) for i in range(2))
# Direct channel-three mixing: establish two independently pitched spectral peaks.
send([0xe2,0,64,0xb2,125,0,126,0,0x92,60,127,64,127])
a,rate=capture('mix2-wave',90);audio=a.astype(float).mean(axis=1);audio-=audio.mean();spec=abs(np.fft.rfft(audio*np.hanning(len(audio))));freq=np.fft.rfftfreq(len(audio),1/rate)
peaks=[]
for hz in (261.626,329.628):
 region=(freq>hz-10)&(freq<hz+10);peak=freq[np.flatnonzero(region)[np.argmax(spec[region])]];peaks.append(float(peak));assert abs(peak-hz)<6;assert spec[region].max()>10*np.median(spec[(freq>100)&(freq<1000)])
print('MIX independent pitch peaks:',peaks)
# Heavy CC burst plus graphical updates must keep the audio producer serviced.
u=word('mixunderruns');w=v('wr');data=[0xe2]+[x for i in range(60) for x in [i,64]]
for b in data:p.memory[S['_rx']+w]=b;w=(w+1)&255
p.memory[S['_wr']]=w;p.tick(60);assert v('rd')==w
print('MIX burst underruns:',word('mixunderruns')-u);assert word('mixunderruns')-u<=4 # 121 bytes injected instantly, faster than a real DIN MIDI link.
# Bounded queue latency after rendering/macro work; the producer must not starve MIDI.
w=v('wr')
for b in [0xe2,0,64]:p.memory[S['_rx']+w]=b;w=(w+1)&255
p.memory[S['_wr']]=w
latency=0
while v('rd')!=w and latency<8:p.tick(1);latency+=1
print('MIX receive latency (emulator frames):',latency);assert latency<=3
p.memory[S['_page']]=6;p.memory[S['_dirty']]=1;p.tick(36);p.screen.image.save('build/ui-fx-mix.png')
# Editing timbre/bend does not dispatch another software note or reset voices.
triggers=[];addr=S['_enginenote'];p.hook_register((addr>>16 if addr>=65536 else addr>>14),addr&65535,lambda c:c.append(True),triggers)
send([0xb2,125,64,126,32,0xe2,64,80]);assert not triggers
send([0xb2,122,64,0x92,60,127,64,127,67,127])
assert v('waveengine')==1 and v('fastcount',v('fastbank'))==3
b=word('engineblocks');p.tick(60);assert word('engineblocks')-b>230
capture('fast-arp',60);p.tick(24);p.screen.image.save('build/ui-fx-fast.png')
send([0xb2,64,127,0x82,60,0]);assert v('fastcount',v('fastbank'))==3
send([0xb2,64,0]);assert v('fastcount',v('fastbank'))==2
send([0xb2,123,0]);assert v('active',2)==0
# Per-channel FX now adjusts fine tuning without changing the shared engine.
p.memory[S['_page']]=6;p.memory[S['_cursor']+6]=0
p.memory[S['_selected']]=2;p.memory[S['_cursor']+6]=0
p.button_press('left');p.tick(12);p.button_release('left');p.tick(12);assert v('waveengine')==1
assert word('finepitch',2)==65535
send([0xb2,122,0]);assert v('waveengine')==0 and p.memory[0xff07]&4==0
p.stop(save=False);print('PASS: 4-note allocator, stealing, sustain, two simultaneous mixed pitches, timer arp, clean mode transitions')

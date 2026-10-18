exec(open('tools/test_experimental.py').read().split("assert not v('expactive')")[0])
# Note echoes reserve pulse 2, survive key-up, decay, and alternate sides.
put('monoset',15,0)
cfg({15:30,16:12,17:3,18:1})
send([0x94,60,127]);send([0x84,60,0]);pans=set();peaks=set()
for _ in range(120):
 p.tick(1)
 if v('expecho'):pans.add(p.memory[0xff25]&0x22);peaks.add(v('monovol',1))
assert pans=={2,32},pans
assert peaks and max(peaks)<=12,peaks
p.tick(100);assert not v('expecho')
# Echo level is independent of the dry pulse-2 level, including zero.
put('monoset',8,0)
send([0x94,60,127]);send([0x84,60,0]);levels=set()
for _ in range(100):
 p.tick(1)
 if v('expecho'):levels.add(v('monovol',1))
assert len(levels)>=3 and max(levels)==12,levels
put('monoset',8,12)
# Key-up during a native attack releases from the estimated current level.
put('exprelease',0,40);put('monoset',2,7);put('monoset',3,0)
cfg({15:0,16:0,17:0,18:0})
send([0x94,60,127]);send([0x84,60,0]);assert v('monostage')==6 and v('monovol')<=6
p.tick(60);assert not v('monovol')
put('monoset',2,0)
# Experimental pulse ADSR changes level without repeating native pulse triggers.
put('exprelease',0,30)
cfg({15:0,16:0,17:0,18:0,19:1,2:3,3:4,4:32})
send([0x94,60,127]);p.tick(30);assert v('monovol')==6 and v('expstage')==3
send([0x84,60,0]);p.tick(6);assert v('monostage')==6
p.tick(50);assert not v('monovol') and not v('monodown')
put('exprelease',0,0)
# Optional faster native control clocks advance at their intended wall-clock rate.
put('monoset',1,0);put('monoset',8,0);put('monoset',15,3)
for rate in (1,2):
 cfg({19:0,1:1,2:0,3:0,4:64,6:12,20:rate})
 send([0x94,48,127]);start=word('exptime');p.tick(120);elapsed=(word('exptime')-start)&65535
 print('control rate',rate,'elapsed control ticks',elapsed);assert 440<=elapsed<=520
 send([0x84,48,0]);p.tick(10)
# DSP pitch, actual low-pass response, and full delay/feedback workload.
put('monoset',19,2)
cfg({0:1,1:0,6:15,20:0,21:7,22:0,23:0,24:0,25:0})
send([0x94,60,127]);dry=capture('exp-dsp-spectrum-open',60)
def bands(audio):
 x=audio.astype(float).mean(axis=1);x-=x.mean();spec=abs(np.fft.rfft(x*np.hanning(len(x))));freq=np.fft.rfftfreq(len(x),1/p.sound.sample_rate)
 fundamental=(freq>250)&(freq<275);hi=(freq>450)&(freq<950)
 peak=freq[np.flatnonzero(fundamental)[np.argmax(spec[fundamental])]]
 return peak,(spec[hi]**2).sum()/(spec[fundamental]**2).sum()
peak,openratio=bands(dry);assert abs(peak-261.626)<6,peak
cfg({21:6});filtered=capture('exp-dsp-spectrum-filtered',60);_,closedratio=bands(filtered)
print('DSP harmonic energy ratios open/filtered:',openratio,closedratio);assert closedratio<openratio*0.85
cfg({21:5,22:5,23:12,24:8,25:10});p.tick(20);b=word('expblocks');u=word('expdrops');capture('exp-dsp-filter-delay',120)
print('DSP full FX blocks/drops:',word('expblocks')-b,word('expdrops')-u)
assert word('expblocks')-b>115 and word('expdrops')-u<10
# Pitch bend must alter DDS frequency without replacing the PCM playback divider.
hits=[];addr=S['_pitchvalue'];p.hook_register(0,addr,lambda ctx:ctx.append(True),hits)
step=word('exppcmstep');send([0xe4,127,127]);assert word('exppcmstep')!=step and not hits
p.hook_deregister(0,addr)
# Turning the wave oscillator down also mutes delayed DSP audio.
goto(2,1);p.memory[S['_monoset']+15]=1;edit(-1);p.tick(30)
assert p.memory[0xff1c]&0x60==0
send([0xb4,123,0]);p.tick(12);assert not v('mixrunning') and not any(v('expechoon',i) for i in range(16))
p.stop(save=False);print('PASS: note echoes/pan/decay, zombie ADSR and release, 128/256 Hz control, DSP pitch/filter/resonance/delay, pitch bend, mute and panic')

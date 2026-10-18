exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
import wave
choose(7)
def put(n,i,x):p.memory[S['_'+n]+i]=x
def cfg(values):
 for i,x in values.items():put('expconfig',i,x)
 goto(4,26);edit(-1 if v('expconfig',26) else 1);p.tick(12)
def capture(name,frames=60):
 chunks=[]
 for _ in range(frames):p.tick(1);chunks.append(p.sound.ndarray.copy())
 a=np.concatenate(chunks)
 with wave.open('build/'+name+'.wav','wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(p.sound.sample_rate);f.writeframes((a.astype(np.int16)*256).tobytes())
 return a
assert not v('expactive') and not any(v('exprelease',i) for i in range(3))
# Native note-off is immediate unless amplitude release/delay is explicitly enabled.
send([0x94,60,1]);assert v('monovel')==127 and v('monovol')==12
send([0x84,60,0]);p.tick(8);assert not v('monodown')
# The new MOD velocity flag changes pulse and wave gain on the next note.
goto(3,10);edit(1);assert v('monosource',10)==1
send([0x94,60,32]);assert v('monovel')==32 and v('monovol')==3 and v('monovol',2)==1
send([0x84,60,0]);edit(-1)
# Real harmonic filter frames and phase scan change native wave RAM.
put('monoset',1,0);put('monoset',8,0);put('monoset',19,2)
cfg({1:1,6:4});assert v('expwaveon')
send([0x94,48,127]);p.tick(25);dark=bytes(p.memory[S['_expcache']:S['_expcache']+16])
cfg({6:15});p.tick(20);bright=bytes(p.memory[S['_expcache']:S['_expcache']+16]);assert dark!=bright
cfg({10:16,11:2});images=set()
for _ in range(80):p.tick(1);images.add(bytes(p.memory[S['_expcache']:S['_expcache']+16]))
assert len(images)>2,len(images)
capture('exp-native-filter-phase',60)
send([0x84,48,0]);p.tick(12);assert not v('monodown')
# Software wave ADSR sustains while held and releases after note-off.
cfg({1:1,2:4,3:6,4:32,5:30,10:0,11:0})
send([0x94,48,127]);p.tick(50);assert v('expstage',2)==3 and v('expenv',2)==32
send([0x84,48,0]);p.tick(8);assert v('expstage',2)==4 and v('expenv',2)>0
p.tick(50);assert not v('monodown') and not v('active',2)
# Hardware pulse release is available on its own oscillator screen.
put('monoset',1,12);goto(0,6);edit(1);assert v('exprelease')==1
# Use 40 frames so the release can be observed after MIDI delivery.
put('exprelease',0,40);cfg({1:0,5:0,6:15})
send([0x94,60,127]);send([0x84,60,0]);p.tick(6);assert v('monostage')==6
p.tick(60);assert not v('monodown') and not v('monovol')
put('exprelease',0,0)
# Pulse offsets move in opposite directions and respond to the chorus clock.
cfg({12:12,13:8,14:2});send([0x94,60,127]);p.tick(20)
assert p.memory[S['_expoffset']:S['_expoffset']+4]!=[0,0,0,0]
first=bytes(p.memory[S['_expoffset']:S['_expoffset']+4]);p.tick(40);assert first!=bytes(p.memory[S['_expoffset']:S['_expoffset']+4])
send([0x84,60,0]);p.tick(10)
# Software engine produces a pitched stream and drains its delay after note-off.
cfg({0:1,1:0,5:0,6:15,10:0,11:0,12:0,13:0,14:0,21:7,22:0,23:0,24:0})
send([0x94,60,127]);p.tick(20);b=word('expblocks');u=word('expdrops');audio=capture('exp-dsp-dry',120)
print('DSP blocks/drops in two seconds:',word('expblocks')-b,word('expdrops')-u)
assert word('expblocks')-b>115
assert word('expdrops')-u<8
assert np.any(audio)
send([0x84,60,0]);p.tick(20);assert not v('mixrunning')
cfg({23:8,24:8,25:8});send([0x94,48,127]);p.tick(30);send([0x84,48,0]);p.tick(8);assert v('mixrunning')
capture('exp-dsp-delay',60);p.tick(100);assert not v('mixrunning')
cfg({0:0,1:0,5:0,6:15,7:0,8:0,10:0,12:0,13:0,15:0,19:0,20:0,23:0,24:0,25:0})
p.tick(30);assert not v('expconfig') and not v('mixrunning')
p.screen.image.save('build/ui-experimental.png');p.stop(save=False)
print('PASS: EXP navigation, velocity, filtered frames, phase scan, wave ADSR, pulse release, detune/chorus, DSP stream and delay tail')

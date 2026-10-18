exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from collections import Counter
choose(7);p.memory[S['_monosource']+8]=0;goto(3,4)
for _ in range(4):edit(1)
assert v('monosource',4)==4 and v('previewshape')==0
p.tick(16);p.screen.image.save('build/ui-lfo-sine.png')
# Even a target whose base is at its maximum sweeps both halves of its legal range.
for c in range(3):p.memory[S['_monoset']+7*c+1]=0
p.memory[S['_monoset']+18]=32;p.memory[S['_monodepth']+18]=32
for wave in (0,1,4):
 for i,x in enumerate([0,0,64,0,wave,1,2,0]):p.memory[S['_monosource']+i]=x
 send([0x94,60,127]);p.tick(8);counts=Counter()
 for _ in range(288):p.tick(1);counts[v('monoeffective',18)]+=1
 print('LFO',wave,'distinct PW values',len(counts),'boundary dwell',counts[1],counts[32])
 assert len(counts)>=28 and min(counts)==1 and max(counts)==32
 assert counts[1]<80 and counts[32]<80
# LFO depth is independent of ADSR, including zero sustain.
p.memory[S['_monosource']+2]=0;send([0x94,67,127]);p.tick(16)
values=set()
for _ in range(256):p.tick(1);values.add(v('monoeffective',18))
assert len(values)>=28
assert not p.memory[0xff07]&4 and not v('waveengine')
p.stop(save=False);print('PASS: sine selection/preview, complete triangle/saw/sine cycles without clipping plateaus, independence from ADSR')

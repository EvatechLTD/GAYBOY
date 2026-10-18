exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])

def signed(n,c):
 x=v(n,c*2)|(v(n,c*2+1)<<8);return x-65536 if x&32768 else x
def putword(n,c,x):
 p.memory[S['_'+n]+c*2]=x&255;p.memory[S['_'+n]+c*2+1]=(x>>8)&255
def alias(item,channel):
 p.button_press('start')
 for _ in range(100):
  p.tick(1)
  if v('navopen'):break
 for _ in range(16):
  if v('navchoice')==item:break
  press('down')
 assert v('navchoice')==item
 p.button_release('start');p.tick(60);assert v('selected')==channel and v('page')==1

def peak(frames=120):
 a=[]
 for _ in range(frames):p.tick(1);a.append(p.sound.ndarray.copy())
 samples=np.concatenate(a).astype(float).mean(axis=1);samples-=samples.mean()
 spectrum=abs(np.fft.rfft(samples*np.hanning(len(samples))));freq=np.fft.rfftfreq(len(samples),1/p.sound.sample_rate)
 band=np.flatnonzero((freq>400)&(freq<480));return float(freq[band[np.argmax(spectrum[band])]])
# Native pulse: one visible tick produces an actual frequency change.
alias(11,0);choose(6);send([0x90,69,127]);p.tick(30);before=peak()
press('right');assert signed('finepitch',0)==1
assert (signed('finelo',0),signed('finehi',0))==(-17,16)
after=peak();assert after>before+0.8,(before,after)
print('Pulse A4 hardware tick:',before,'->',after,'Hz')
for _ in range(30):press('right')
assert signed('finepitch',0)==16
for _ in range(50):press('left')
assert signed('finepitch',0)==-17
# Pitch-dependent bounds clip on a new higher note; no invalid UI offsets remain.
send([0x80,69,0,0x90,84,127]);p.tick(20)
assert signed('finepitch',0)==-7
assert signed('finelo',0)==-7 and signed('finehi',0)==7
press('a');assert signed('finepitch',0)==0
send([0x80,84,0])
# Channel settings are independent and survive contextual page changes.
alias(12,1);choose(6);press('right');assert signed('finepitch',1)==1 and signed('finepitch',0)==0
alias(13,2);choose(6);send([0x92,69,127]);press('right')
assert (signed('finelo',2),signed('finehi',2))==(-8,8)
send([0x82,69,0]);press('a')
# DDS W1/W2 tuning changes phase increments independently by exactly one.
send([0xb2,122,127,0x92,60,127]);p.tick(10)
base=word('softstep');press('right');p.tick(10);assert word('softstep')==base+1
alias(14,4);choose(6)
p.memory[S['_w2settings']+2]=120
send([0x95,60,127]);p.tick(20);base=v('softstep',2)|(v('softstep',3)<<8)
other=word('softstep');drops=word('mixunderruns');press('right');p.tick(10)
assert word('mixunderruns')==drops
assert (v('softstep',2)|(v('softstep',3)<<8))==base+1
assert word('softstep')==other and signed('finepitch',2)==1 and signed('finepitch',4)==1
p.screen.image.save('build/ui-fine-wave2.png')
# Noise exposes native rate controls, not false fractional pitch.
alias(15,3);choose(6);old=v('param',3*26+18);press('right')
assert v('param',3*26+18)==old+1 and signed('finepitch',3)==0
p.stop(save=False)
print('PASS: audible native tuning, exact hardware limits, note-dependent clipping, isolated channel FX and one-step DDS tuning')

exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def put(n,i,x):p.memory[S['_'+n]+i]=x
def phase(c,i,x):
 a=(c*7+i)*2;put('monophase',a,x&255);put('monophase',a+1,x>>8)
def getphase(c,i):
 a=(c*7+i)*2;return v('monophase',a)|(v('monophase',a+1)<<8)
choose(7)
put('monosource',8,0)
# Third column wraps in degrees and never modifies base value or depth.
goto(0,0,2);assert v('monocol')==2
edit(-1);assert getphase(0,0)==359
edit(1);assert getphase(0,0)==0
edit(1);assert getphase(0,0)==1 and v('monoset')==0 and v('monodepth')==0
phase(0,0,180);put('dirty',0,1);p.tick(24);p.screen.image.save('build/ui-mono-phase.png')
# MOD screen exposes the eighth setting, KEY/FREE, without obscuring it.
goto(3,7)
edit(1);assert v('monosource',7)==1
p.tick(24);p.screen.image.save('build/ui-lfo-mode.png')
edit(-1);assert v('monosource',7)==0
# Observe the phase at entry to the first oscillator apply on each real note.
starts=[];addr=S['_monoapply']
p.hook_register((addr>>16 if addr>=65536 else addr>>14),addr&65535,lambda ctx:ctx.append((v('lfophase'),v('lfocycle'))),starts)
put('monosource',5,3)
for _ in range(2):
 starts.clear();send([0x94,60,127]);assert starts[0]==(0,0)
 p.tick(13)
# FREE preserves the running clock at note start, including while no keys are held.
put('monosource',7,1);p.tick(7);starts.clear();send([0x94,64,127]);assert starts[0]!=(0,0)
send([0xb4,123,0]);old=(v('lfophase'),v('lfocycle'));p.tick(12);assert old!=(v('lfophase'),v('lfocycle'))
p.hook_deregister((addr>>16 if addr>=65536 else addr>>14),addr&65535)
# Two pulse duties with identical base/depth and 180-degree offsets move oppositely.
for i,x in enumerate([0,0,64,0,2,2,2,0]):put('monosource',i,x)
for c in range(3):
 for i in range(7):put('monodepth',c*7+i,0);phase(c,i,0)
for c in range(2):put('monoset',c*7+4,1);put('monodepth',c*7+4,2)
phase(1,4,180)
send([0x94,60,127]);seen=set();settled=0
for _ in range(140):
 p.tick(1)
 pair=(p.memory[0xff11]>>6,p.memory[0xff16]>>6)
 if v('monodown'):
  seen.add(pair)
  if pair in ((3,0),(0,3)):settled+=1
  else:assert v('lfophase')<8 or 128<=v('lfophase')<136 # Sequential register writes at transitions.
assert (3,0) in seen and (0,3) in seen and settled>=135
# With the LFO off, target phase never offsets the ADSR envelope.
put('monosource',8,1);put('monosource',5,0);put('monosource',2,32);send([0x94,67,127]);p.tick(12)
assert p.memory[0xff11]>>6==p.memory[0xff16]>>6==2
# A 90-degree offset produces a quarter-cycle shift rather than a new LFO rate.
put('monosource',8,0);put('monosource',5,2);put('monosource',2,64);phase(1,4,90)
send([0x94,60,127]);pairs=set()
for _ in range(150):
 p.tick(1)
 if v('monodown'):pairs.add((p.memory[0xff11]>>6,p.memory[0xff16]>>6))
assert {(3,3),(3,0),(0,3),(0,0)}<=pairs
# The remaining shapes also evaluate their own phase offsets, including S/H boundaries.
phase(1,4,180)
for waveform in (0,1,3,4):
 put('monosource',4,waveform);put('monosource',5,4)
 send([0x94,60,127]);pairs=set()
 for _ in range(160):
  p.tick(1)
  if v('monodown'):pairs.add((p.memory[0xff11]>>6,p.memory[0xff16]>>6))
 assert len(pairs)>1 and any(a!=b for a,b in pairs), (waveform,pairs)
assert not p.memory[0xff07]&4 and not v('waveengine') and not v('mixrunning')
p.stop(save=False);print('PASS: phase UI/wrap, KEY reset, FREE continuity, 180/90-degree offsets, envelope independence, native audio')

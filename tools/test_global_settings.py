exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
assert not v('experimental_mode'), 'Experimental Mode must default off on a fresh boot'
choose(7);send([0x94,60,127]);choose(16);press('a')
assert not v('experimental_mode') and not v('monomode') and not v('waveengine') and not v('mixrunning') and not v('expactive')
assert not p.memory[0xff07]&4
# Software engine CCs and extra software MIDI channels cannot re-enable audio processing.
send([0xb2,122,127,0x95,36,127,0x94,60,127]);assert not v('waveengine') and not v('mixrunning')
choose(0);choose(1)
for _ in range(60):
 text=''.join(chr((v('canvas',i)%96)+32) for i in range(360))
 if 'ENV DIRECTION' in text and 'ENV PERIOD' in text:break
 p.tick(1)
assert 'ENV DIRECTION' in text and 'ENV PERIOD' in text and 'ADSR' not in text
p.button_press('start');p.tick(8)
seen=set()
for _ in range(24):seen.add(v('navchoice'));press('down')
p.button_release('start');p.tick(20)
assert not seen.intersection({2,5,6,7,9,14}) and {16,17,18,19,20}.issubset(seen)
choose(8)
from seq_storage_helpers import write_tracks
tracks=[[] for _ in range(7)]
for c in range(4):tracks[c]=[[i,61+c,100,1] for i in range(16)]
write_tracks(p,S,tracks)
calls=[]
for name in ('mixrender','w2_frame','exp_fill','modulate'):
 a=S['_'+name];p.hook_register(a>>16 if a>=65536 else 0,a&65535,lambda n:calls.append(n),name)
p.button_press('select');p.tick(5);press('a');p.button_release('select');p.tick(120)
assert v('seqplaying') and not calls and word('engineblocks')==0
assert word('seqclock') or any(v('seqposition',i) for i in range(4))
p.screen.image.save('build/ui-native-settings.png')
p.button_press('select');p.tick(5);press('a');p.button_release('select');p.tick(10)
choose(16);press('a');assert v('experimental_mode')
p.stop(save=False);print('PASS: global native mode stops and hides DSP, exposes native envelopes, blocks software MIDI/CC engines, and runs sequencer without DSP calls')

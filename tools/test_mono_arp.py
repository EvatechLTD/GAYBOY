exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(7);goto(3,9)
edit(1);assert v('monosource',9)==1
def rate(x):p.memory[S['_monosource']+9]=x
rate(0);send([0x94,60,127,64,127,67,127]);p.tick(30)
assert all(v('held',c)==67 for c in range(3))
rate(5);edit(1);seen=[];last=None
for _ in range(120):
 p.tick(1);note=v('held')
 assert all(v('held',c)==note for c in range(3))
 if note!=last:seen.append(note);last=note
assert set(seen)=={60,64,67} and 11<=len(seen)<=14,seen
for a,b in zip(seen,seen[1:]):assert (a,b) in {(60,64),(64,67),(67,60)},seen
# Releasing one note removes it immediately; releasing all notes silences the arp.
send([0x84,64,0]);seen=set()
for _ in range(80):p.tick(1);seen.add(v('held'))
assert seen=={60,67},seen
# Disabling arp immediately restores the most recently held note.
rate(1);edit(-1);assert all(v('held',c)==67 for c in range(3))
send([0x84,60,0,67,0]);p.tick(20);assert not v('monodown') and not v('monocount')
# Faster settings advance more often; one held note stays steady.
rate(24);send([0x94,60,127,64,127,67,127]);transitions=0;last=v('held')
for _ in range(120):
 p.tick(1);note=v('held');transitions+=note!=last;last=note
assert 45<=transitions<=50,transitions
send([0x84,64,0,67,0]);p.tick(40);assert all(v('held',c)==60 for c in range(3))
# With one held note, arp must not retrigger a completed decay.
p.memory[S['_monoset']+2]=0;p.memory[S['_monoset']+3]=1;rate(4);send([0x94,60,127]);p.tick(30)
levels=set()
for _ in range(150):p.tick(1);levels.add(v('monovol'))
assert levels=={0},levels
send([0x84,60,0]);p.tick(20)
# No footer tips or divider occupy the new setting area.
goto(3,9);p.tick(16)
assert bytes(p.memory[S['_visible']+280:S['_visible']+288])==bytes(ord(c)-32 for c in 'ARP RATE')
assert not any(p.memory[S['_visible']+320:S['_visible']+360])
p.screen.image.save('build/ui-mono-arp.png')
p.stop(save=False);print('PASS: arp rate UI, off/held-note behavior, note order, unison, release removal, 6/24 Hz timing and cleared bottom rows')

exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(7)
p.memory[S['_monodepth']+4]=4
p.memory[S['_monosource']+5]=1
send([0x94,60,127]);p.tick(20);send([0x84,60,0]);p.tick(4)
assert not v('monodown') and not v('modtail') and not p.memory[0xff25]
# Genuine amplitude release remains available when base level is zero.
p.memory[S['_monoset']+1]=0;p.memory[S['_monodepth']+1]=16
send([0x94,60,127]);p.tick(40);send([0x84,60,0]);assert v('modtail')
p.tick(40);assert not v('monodown')
p.stop(save=False);print('PASS: LFO rate cannot add a note tail; timbre envelopes stop on note-off; explicit amplitude release still works')

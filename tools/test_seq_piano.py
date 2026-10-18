exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(8);press('left');assert v('seqhead')==6
for _ in range(16):press('up')
assert v('seqhead')==6 and v('seqpitch')==76 and v('seqtop')==76
press('a');assert not v('active')
p.button_press('a');p.tick(8);assert v('active') and v('basepitch')==76
p.button_release('a');p.tick(8);assert not v('active')
for _ in range(20):press('down')
assert v('seqhead')==6 and v('seqpitch')==56 and v('seqtop')==69
p.screen.image.save('build/ui-seq-piano-focus.png');press('right');assert v('seqhead')==0
assert not any(v('seqnotes',i) for i in range(384))
p.stop(save=False);print('PASS: selectable piano, immediate A audition/release, bidirectional pitch scrolling, no header entry and return to cells')

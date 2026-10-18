exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(8);press('a');original=v('seqvelocity')
while v('seqpitch')+v('seqrows')-1>v('seqtop'):press('down')
press('down');assert v('seqhead')==5
press('a');assert v('seqedit')
press('up');assert v('seqvelocity')==original+1
press('right');press('left');assert v('seqhead')==5 and v('seqcursor')==0
press('a');press('up');assert v('seqhead')==0
p.screen.image.save('build/ui-seq-velocity-focus.png');p.stop(save=False)
print('PASS: selectable velocity lane, per-note editing independent of pitch cursor, horizontal selection and return to grid')

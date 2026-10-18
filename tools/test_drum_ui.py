"""Drum grid separators and per-row velocity-lane controls, disposable SRAM."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def put(n,i,x):fixture_put(p,S,n,i,x)
def chord(k):
 p.button_press('b');p.tick(4);press(k);p.button_release('b');p.tick(5)
try:
 choose(8)
 p.button_press('select');press('left');p.button_release('select');p.tick(8)
 assert v('seqtrack')==6 and v('seqcols')==16
 press('b');assert v('drumhits')==1
 before=v('drumvel')
 # Enter the velocity lane at the right edge without changing selected drum.
 for _ in range(16):press('right')
 assert v('seqhead')==5 and v('drumrow')==0
 for _ in range(15):press('left')
 assert v('seqcursor',6)==0
 # A cannot latch slider editing; releasing B always restores navigation.
 press('a');assert not v('seqedit')
 chord('down');assert v('drumvel')==before-1 and v('seqhead')==5
 press('up');assert v('seqhead')==0 and v('drumrow')==0
 lane_pcm=p.screen.ndarray[120:144,:,:].copy()
 # Noise uses its independent velocity storage and doesn't touch PCM velocity.
 put('noisehits',0,1);put('noisevel',0,32);put('noisedur',0,1)
 for _ in range(10):press('down')
 assert v('drumrow')==10
 assert not np.array_equal(lane_pcm,p.screen.ndarray[120:144,:,:]),'Velocity pixels did not follow selected row through retained-grid redraw'
 put('seqhead',0,5);put('dirty',0,1);p.tick(12)
 before=v('noisevel');chord('down');assert v('noisevel')==before-1
 assert v('drumvel')==99
 p.screen.image.save('build/ui-drum-velocity.png')
 press('up');p.screen.image.save('build/ui-drum-row-lines.png')
 print('PASS: drum row separators, selected PCM/noise velocity sliders, lane focus and editable velocities')
finally:p.stop(save=False)

"""Noise release preserves DAC bias and does not restart overlapping voices."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])

try:
 choose(17)
 assert v('drumsynthvoice') == 0
 # A decaying preview retains its envelope register after release.
 press('b')
 assert p.memory[0xff21] == 0x81, hex(p.memory[0xff21])
 assert not v('drumnoiseowned')
 # A sustained patch must latch silence without disabling the DAC.
 put('noisepatch',4,0)
 press('b')
 assert p.memory[0xff21] == 8
 # Releasing HH while a snare gate survives must not reload its envelope
 # or replace the timbre. Mark the running hardware with sentinel settings.
 p.button_press('b');p.tick(8)
 addr=S['_noiseleft']+4
 for i,x in enumerate((255,255,0,0)):p.memory[addr+i]=x
 p.memory[0xff21]=0x51
 p.memory[0xff22]=0x35
 p.button_release('b');p.tick(8)
 assert p.memory[0xff21] == 0x51
 assert p.memory[0xff22] == 0x35
 print('PASS: decaying release, DAC-preserving sustained release, overlapping voice preservation')
finally:
 p.stop(save=False)

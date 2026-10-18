exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(7);goto(3,8)
assert v('monosource',8)==1
press('a');assert not v('monosource',8) and not v('monoedit')
goto(3,0);before=bytes(p.memory[S['_monosource']:S['_monosource']+4])
p.button_press('b')
for key in ('up','down','left','right'):press(key)
p.button_release('b');p.tick(8)
assert bytes(p.memory[S['_monosource']:S['_monosource']+4])==before
press('a');press('up');press('down');press('a')
assert bytes(p.memory[S['_monosource']:S['_monosource']+4])==before
p.tick(16)
assert any(220<=x<243 for x in p.memory[S['_canvas']+120:S['_canvas']+200])
p.screen.image.save('build/ui-mod-lfo.png')
# LFO sweeps at full depth with all ADSR values zero.
for i in range(4):p.memory[S['_monosource']+i]=0
p.memory[S['_monosource']+4]=0;p.memory[S['_monosource']+5]=2
p.memory[S['_monodepth']+4]=4
send([0x94,60,127]);values=set()
for _ in range(150):p.tick(1);values.add(v('monoeffective',4))
assert values=={0,1,2,3},values
send([0x84,60,0]);p.tick(12);assert not v('monodown') and not v('modtail')
# ADSR ignores a nonzero LFO rate; zero sustain returns to the base value.
goto(3,8);press('a');assert v('monosource',8)==1
goto(3,0);p.tick(16)
assert not any(220<=x<243 for x in p.memory[S['_canvas']+120:S['_canvas']+200])
p.button_press('b');press('right');p.button_release('b');p.tick(8)
assert v('monosource')==10
p.memory[S['_monosource']]=0
send([0x94,60,127]);p.tick(20);values=set()
for _ in range(150):p.tick(1);values.add(v('monoeffective',4))
assert values=={2},values
p.screen.image.save('build/ui-mod-adsr.png')
send([0x84,60,0]);p.tick(12)
# Switching to LFO during an ADSR release must not leave a hanging tail.
goto(3,8);p.memory[S['_monoset']+1]=0;p.memory[S['_monodepth']+1]=16;p.memory[S['_monosource']+2]=32;p.memory[S['_monosource']+3]=255
send([0x94,60,127]);p.tick(20);send([0x84,60,0]);assert v('modtail')
press('a');p.tick(12);assert not v('modtail') and not v('monodown')
p.stop(save=False);print('PASS: ADSR checkbox, grey/locked ADSR fields, editable active ADSR, exclusive ADSR/LFO, full LFO depth and immediate LFO release')

exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(7);goto(3)
p.memory[S['_monosource']]=0
p.button_press('b');p.button_press('up');p.tick(10);initial=v('monosource');assert initial==1
p.tick(30);early=v('monosource')-initial
p.tick(30);midstart=v('monosource');p.tick(30);middle=v('monosource')-midstart
p.tick(30);latestart=v('monosource');p.tick(30);late=v('monosource')-latestart
print('Repeat increments per half-second: initial',early,'middle',middle,'late',late)
assert 0<early<middle and late>=middle
p.button_release('up');p.button_release('b');p.tick(12);stopped=v('monosource');p.tick(30);assert v('monosource')==stopped
edit(-1);assert v('monosource')==stopped-1
# Releasing B while Up is still held stops edits without moving the cursor.
p.button_press('b');p.button_press('up');p.tick(100);p.button_release('b');p.tick(12)
stopped=v('monosource');row=v('cursor',7);p.tick(30);assert v('monosource')==stopped and v('cursor',7)==row
p.button_release('up');p.tick(12)
# B holds the same cell even if Left/Right is pressed during accelerated edits.
goto(0,0,0);p.button_press('b');p.button_press('up');p.tick(140)
press('right');press('left');assert v('monocol')==0 and v('cursor',7)==0 and v('monoosc')==0
assert not v('monodepth')
p.button_release('b');p.button_release('up');p.tick(12)
# Navigation overlay isolates the underlying value even with B held.
goto(3);before=v('monosource');p.button_press('start');p.tick(12)
p.button_press('b');p.button_press('up');p.tick(100);assert v('monosource')==before
p.button_release('b');p.button_release('up');p.tick(8)
while v('navchoice')!=7:press('down')
p.button_release('start');p.tick(20)
# Repeating a depth reaches its limit; repeating phase changes degrees, not base values.
goto(0,0,1);p.button_press('b');p.button_press('up');p.tick(220)
p.button_release('b');p.button_release('up');p.tick(12);assert v('monodepth')==5
goto(0,0,2);p.button_press('b');p.button_press('up');p.tick(150)
p.button_release('b');p.button_release('up');p.tick(12)
a=S['_monophase'];angle=p.memory[a]|p.memory[a+1]<<8;assert 10<angle<359
p.tick(30);assert angle==(p.memory[a]|p.memory[a+1]<<8)
p.stop(save=False);print('PASS: B+Up/Down acceleration, release/cell reset, menu isolation, depth limits and phase repeats')

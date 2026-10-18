exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(7)
def pos():return (v('monoosc'),v('cursor',7),v('monocol'))
def settings():return (bytes(p.memory[S['_monoset']:S['_monoset']+21]),bytes(p.memory[S['_monodepth']:S['_monodepth']+21]),bytes(p.memory[S['_monophase']:S['_monophase']+42]),bytes(p.memory[S['_monosource']:S['_monosource']+8]))
original=settings()
assert pos()==(0,0,0)
press('right');assert pos()==(0,0,1)
press('right');assert pos()==(0,0,2)
press('right');assert pos()==(1,0,0)
press('left');assert pos()==(0,0,2)
press('left');press('left');press('left');assert pos()==(4,0,0)
press('right');assert pos()==(0,0,0)
goto(0,3,1);press('right');press('right');assert pos()==(1,3,0)
press('left');assert pos()==(0,3,2)
p.button_press('select');press('right');assert pos()==(1,3,2)
press('right');assert pos()==(2,3,2)
press('right');assert pos()==(3,3,0)
press('right');assert pos()==(4,3,0)
press('right');assert pos()==(0,3,0)
p.button_release('select');p.tick(8)
goto(3,7);p.button_press('select');press('left');p.button_release('select');p.tick(8)
assert pos()==(2,5,0)
press('left');assert pos()==(1,5,2)
assert settings()==original
# Bare D-pad never edits; B+Up/Down edits without moving the selected cell.
goto(0,1);before=v('monoset',1);edit(1);assert v('monoset',1)==before+1 and pos()==(0,1,0)
edit(-1);assert v('monoset',1)==before
press('b');assert v('auditionvoice')==255 and not any(v('active',i) for i in range(4))
goto(0,0,2);edit(-1);a=S['_monophase'];assert (p.memory[a]|p.memory[a+1]<<8)==359
edit(1);assert (p.memory[a]|p.memory[a+1]<<8)==0
# Native duty widths have distinct cached graphical previews, with no old header text.
goto(0,4);edit(-1);edit(-1)
images=[]
for duty,width in enumerate((4,8,16,24)):
 p.tick(16);assert v('previewshape')==3 and v('previewwidth')==width
 images.append(bytes(p.memory[S['_wavepixels']:S['_wavepixels']+1280]))
 p.screen.image.save('build/ui-native-pulse-'+str(duty)+'.png')
 if duty<3:edit(1)
assert len(set(images))==4
# Wave graphics follow the selected native bank entry.
goto(2,3);p.tick(16);before=bytes(p.memory[S['_wavepixels']:S['_wavepixels']+1280]);edit(1);p.tick(16)
assert v('previewshape')==1 and bytes(p.memory[S['_wavepixels']:S['_wavepixels']+1280])!=before
p.screen.image.save('build/ui-native-wave.png')
# Render timing after cache warm-up: UI remains responsive idle and under held notes.
spans=[];start=[]
def begin(ctx):ctx.append(p.frame_count)
def end(ctx):
 if start:spans.append(p.frame_count-start.pop())
a=S['_ui_render'];b=S['_ui_flush'];p.hook_register((a>>16 if a>=65536 else a>>14),a&65535,begin,start);p.hook_register((b>>16 if b>=65536 else b>>14),b&65535,end,None)
p.tick(120);idle=list(spans);send([0x94,60,127]);p.tick(12);spans.clear();p.tick(120);held=list(spans)
print('Render frames: idle max',max(idle),'held max',max(held),'samples',len(idle),len(held))
assert max(idle)<=2 and max(held)<=3
assert not p.memory[0xff07]&4 and not v('waveengine')
p.stop(save=False);print('PASS: cell navigation, row-preserving edge/page jumps, modifier edits, phase wrap, preview duty/waves, responsive rendering')

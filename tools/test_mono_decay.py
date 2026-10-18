exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(7)
p.memory[S['_monoset']+8]=0;p.memory[S['_monoset']+15]=0
p.memory[S['_monoset']+2]=2;p.memory[S['_monoset']+3]=3
p.memory[S['_monodepth']+4]=4
p.memory[S['_monosource']+8]=0;p.memory[S['_monosource']+5]=8
calls=[];a=S['_monopulse'];p.hook_register((a>>16 if a>=65536 else a>>14),a&65535,lambda ctx:ctx.append(p.frame_count),calls)
send([0x94,60,127]);p.tick(80)
assert v('monostage')==4 and v('monovol')==0 and not v('active')
assert len(calls)<=4,calls
p.tick(150);assert v('monostage')==4 and not v('monovol')
send([0x84,60,0]);p.tick(8)
# Level modulation also preserves elapsed A/D time and cannot revive a finished note.
p.memory[S['_monodepth']+4]=0;p.memory[S['_monodepth']+1]=16
p.memory[S['_monoset']+2]=1;p.memory[S['_monoset']+3]=1
send([0x94,60,127]);p.tick(120)
assert v('monostage')==4 and not v('monovol')
p.tick(150);assert not v('monovol')
# A fresh note may start a new envelope normally.
p.memory[S['_monodepth']+1]=0
send([0x94,64,127]);assert v('monostage') in (1,2) and v('monovol')>0
p.hook_deregister((a>>16 if a>=65536 else a>>14),a&65535);p.stop(save=False)
print('PASS: LFO duty does not retrigger A/D, level modulation preserves envelope time, finished decay stays silent, fresh notes retrigger')

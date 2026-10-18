exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(10)
choose(7)
saved={n:bytes(p.memory[S['_'+n]:S['_'+n]+length]) for n,length in (('monoset',21),('monodepth',21),('monosource',11),('expconfig',27),('exprelease',3))}
choose(9);assert v('expconfig')==1 and v('noisesaved') and not v('noiseon')
chord('select','a');assert v('noiseon') and v('monocount')==1
p.tick(40);b=word('expblocks');u=word('expdrops');p.tick(120)
print('Noise Lab DSP blocks/drops',word('expblocks')-b,word('expdrops')-u)
assert word('expblocks')-b>=120 and word('expdrops')==u
before=v('noisevalues');press('right');assert v('noisevalues')==before+1
press('down');press('a');before=v('noisevalues',1);press('up');assert v('noisevalues',1)==before+1
press('a');p.screen.image.save('build/ui-noiselab.png')
chord('select','b');assert v('noiseon')
for i in range(16):assert v('noisevalues',i)<=(83,31,3,7,7,15,31,32,64,32,32,64,15,12,32,32)[i]
chord('select','a');assert not v('noiseon') and not v('monocount')
choose(7);assert not v('noisesaved') and not v('mixrunning')
for n,data in saved.items():assert bytes(p.memory[S['_'+n]:S['_'+n]+len(data)])==data,n
choose(9);assert not v('noiseon')
chord('select','a');p.button_press('select');p.tick(8);p.button_press('start')
for _ in range(120):
 p.tick(1)
 if not v('monocount'):break
p.button_release('start');p.button_release('select');p.tick(16)
assert not v('monocount') and not v('mixrunning')
p.stop(save=False);print('PASS: Noise Lab menu, independent patch, DSP drone, edit/randomize, panic and patch restoration')

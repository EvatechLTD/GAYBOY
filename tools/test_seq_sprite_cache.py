"""Playback moves the line and cursor without regenerating sprite graphics."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])

def put(name,i,x):fixture_put(p,S,name,i,x)
choose(8);p.tick(90)
put('seqnotes',0,61);put('seqvelocity',0,100);put('seqduration',0,1)
put('seqdrawvalid',0,0);put('dirty',0,1);p.tick(90)
p.button_press('select');p.tick(5);press('a');p.button_release('select');p.tick(40)
assert v('seqplaying')
uploads=[];a=S['_ui_upload_tile']
def upload(_):
 if p.memory[p.register_file.SP+9]:uploads.append(p.frame_count)
p.hook_register(a>>16,a&65535,upload,None)
cursor=bytes(p.memory[0xc000+17*4:0xc000+37*4]);line=[]
for _ in range(120):
 p.tick(1);line.append(p.memory[0xc001])
 assert bytes(p.memory[0xc000+17*4:0xc000+37*4])==cursor
assert len(set(line))>4 and not uploads, ('sprite graphics uploaded during static playback',uploads)
oldx=p.memory[0xc000+17*4+1];press('right');p.tick(20)
assert p.memory[0xc000+17*4+1]==oldx+9
assert not uploads, 'Moving a same-size cursor regenerated its bitmap'
p.stop(save=False)
print('PASS: playhead changes only position; stationary cursor and same-size moves reuse sprite graphics')

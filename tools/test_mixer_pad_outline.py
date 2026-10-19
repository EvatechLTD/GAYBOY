"""Pad number/title placement and incremental focus outlines on the real ROM."""
exec(open('tools/test_mixer_settings.py').read().split('try:\n')[0])
def pixel(pad,x,y):
 bank=v('padbank');t=(y//8)*20+pad*5+x//8
 tile=(168+t if t<24 else 180+t) if bank else (64+t if t<32 else 128+t)
 base=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16
 return bool(p.memory[base+(y%8)*2]&(128>>(x%8)))
def focus(slot):
 p.memory[0,S['_mx']+4]=30+slot;p.memory[S['_dirty']]=1;p.tick(60)
try:
 enter_app(p,S);choose(18);p.memory[0,S['_mx']+26:S['_mx']+43]=list(b'TITLE'+bytes(12));p.memory[S['_pad_names_valid']]=0;focus(0)
 assert all(pixel(0,x,0) and pixel(0,x,15) for x in range(40))
 assert all(pixel(0,0,y) and pixel(0,39,y) for y in range(16))
 one=[2,6,2,2,7]
 for row,g in enumerate(one,1):
  assert [pixel(0,18+k,row) for k in range(3)]==[bool(g&(4>>k)) for k in range(3)]
 p.screen.image.save('build/mixer-outline-debug.png')
 assert any(pixel(0,x,y) for x in range(5,35) for y in range(7,14))
 focus(1);assert not any(pixel(0,x,0) for x in range(40));assert all(pixel(1,x,0) for x in range(40))
 assert bytes(p.memory[S['_canvas']+260:S['_canvas']+265])==bytes(ord(c)-32 for c in 'LOCAL')
 p.screen.image.save('build/mixer-pad-outline.png')
 # Hidden slots must not become phantom pads for the 255 no-playing sentinel.
 p.memory[S['_mixer_hidden']+2]=240;p.memory[S['_mixer_hidden']+3]=15;p.memory[S['_pad_names_valid']]=0;p.memory[S['_dirty']]=1;p.tick(60)
 assert not any(pixel(i,x,y) for i in range(4) for x in range(40) for y in range(16))
 p.memory[S['_mixer_device']]=1;p.memory[S['_dirty']]=1;p.tick(60)
 assert bytes(p.memory[S['_canvas']+260:S['_canvas']+265])==bytes(ord(c)-32 for c in 'LOCAL')
 print('PASS: internal number/title, focus outline, LOCAL/LINK bank heading and no phantom hidden pads')
finally:p.stop(save=False)

exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
# Check fetched PCM against its exact ROM source before packing.
rom=Path('build/GAYBOY.gb').read_bytes();checked=[];packed_before=[None];full_level=[]
def check_pcm(_):
 if packed_before[0] is not None:
  slot,expected=packed_before[0]
  assert bytes(v('mixbuffer',slot*16+i) for i in range(16))==expected, 'single-hit attenuation returned'
 mask=v('drumpackmask')
 if mask in (1,2):
  voice=mask-1
  packed_before[0]=(v('mixwrite'),bytes(p.memory[0xac00+voice*16+i] for i in range(16)))
  full_level.append(mask)
 else:packed_before[0]=None
 for voice in range(2):
  if not v('drumon',voice):continue
  bank=v('drumbankvoice',voice)
  if bank<32:continue
  pos=p.memory[0xac42+voice*2]|p.memory[0xac43+voice*2]<<8
  # mixer advances the read cursor after fetching this block
  base=(S['_drumdata'+str(bank)]&65535)-0x4000
  expected=rom[bank*0x4000+base+pos-16:bank*0x4000+base+pos]
  actual=bytes(p.memory[0xac00+voice*16+i] for i in range(16))
  assert actual==expected,(bank,pos,actual,expected)
  checked.append(bank)
a=S['_drum_pack'];p.hook_register(a>>16,a&65535,check_pcm,None)
choose(23)
assert v('page')==23
while v('kitchoice'):press('up')
for kit in range(1,6):
 press('down');press('a');assert v('drumkit')==kit
 for slot in range(8):
  press('b');assert v('drumbankvoice')==31+kit or v('drumbankvoice',1)==31+kit
  p.tick(55);press('right')
 p.screen.image.save(f'build/kit-{kit}.png')
choose(8);p.tick(30);assert not v('seqtileoverflow')
choose(23);press('down');press('a');assert v('drumkit')==0
assert set(checked)==set(range(32,37)),set(checked)
assert full_level,'No full-level single-hit blocks verified'
p.stop(save=False)
print('PASS: Start menu KITS, five presets, all 40 auditions, bank selection, roll return, Amen restore')

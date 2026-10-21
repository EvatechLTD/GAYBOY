from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
enter_app(p,S)
choose=menu
# Check fetched PCM against its exact ROM source before packing.
rom=Path('build/GAYBOY.gb').read_bytes();checked=[];packed_before=[None];full_level=[]
# The approved direct-DAC bytes must reach the ROM without WAV conversion.
for name,bank in [('SLAP808',39),('SLAM909',62)]:
 approved=(Path('DRUMSAMPLES/DIRECT4BIT')/name/'kit-bank.bin').read_bytes()
 base=bank*0x4000+(S['_drumdata'+str(bank)]&0x3fff)
 assert rom[base:base+len(approved)]==approved,name
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
kit_banks=[32,33,34,35,36,39,62]
for kit in range(1,8):
 press('down');press('a');assert v('drumkit')==kit
 for slot in range(8):
  press('b');assert v('drumbankvoice')==kit_banks[kit-1] or v('drumbankvoice',1)==kit_banks[kit-1]
  p.tick(55);press('right')
 p.screen.image.save(f'build/kit-{kit}.png')
choose(8);p.tick(30);assert not v('seqtileoverflow')
choose(23);press('down');press('a');assert v('drumkit')==0
assert set(checked)==set(kit_banks),set(checked)
assert full_level,'No full-level single-hit blocks verified'
p.stop(save=False)
print('PASS: Start menu KITS, seven presets, all 56 auditions, bank selection, roll return, Amen restore')

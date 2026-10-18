"""Optional PK tone extension: exact sync/async codec and corrupt-data rejection."""
from pathlib import Path
exec(Path('tools/test_tones_incremental.py').read_text().split('\ntry:',1)[0])
factory=bytes((15,48,2,1,1,2,24,1))
maximum=bytes((15,96,3,7,7,7,64,1))
try:
 for patch in (factory,bytes(8),maximum,bytes((8,35,1,4,2,3,12,0))):
  p.memory[S['_pulsekickpatch']:S['_pulsekickpatch']+8]=patch
  call('tones_pack');packed=bytes(p.memory[0xbd00:0xbe20])
  assert (packed[224:236]==bytes(12))==(patch==factory)
  call('tones_pack_begin');result,_=finish()
  assert result==1 and bytes(p.memory[0xbd00:0xbe20])==packed
  p.memory[0xb871:0xb991]=packed
  result,_=call('tones_decode');assert result==1
  assert bytes(p.memory[0xbbd0:0xbbd8])==patch
  call('tones_decode_begin');result,_=finish()
  assert result==1 and bytes(p.memory[0xbbd0:0xbbd8])==patch
 # Old records have zero padding and acquire the Mario-style factory kick.
 legacy=bytearray(packed);legacy[224:236]=bytes(12);p.memory[0xb871:0xb991]=legacy
 result,_=call('tones_decode');assert result==1
 assert bytes(p.memory[0xbbd0:0xbbd8])==factory
 for field in range(8):
  bad=bytearray(packed);bad[227+field]=maximum[field]+1
  bad[235]=(sum(bad[227:235])&255)^0xa5
  p.memory[0xb871:0xb991]=bad;call('tones_decode_begin');result,_=finish()
  assert result==2,('Accepted out-of-range PK setting',field)
 for index in (224,225,226,235):
  bad=bytearray(packed);bad[index]^=1;p.memory[0xb871:0xb991]=bad
  result,_=call('tones_decode');assert not result,('Accepted corrupt PK extension',index)
 print('PASS: PK sync/async round-trip, legacy factory defaults, eight range limits and corrupt-extension rejection')
finally:p.stop(save=False)

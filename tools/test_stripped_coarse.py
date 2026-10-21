"""Shared coarse-pitch modulation, pitch math and current preset/patch storage."""
from pathlib import Path
exec(Path('tools/test_stripped_engine.py').read_text().split('\ntry:')[0])
try:
 put('experimental_mode',1);put('power',1);call('eval_defaults')
 assert get('globalmod',7)==1 and get('globalmod',6)==8
 assert all(get('coarsepitch',i)==0 for i in range(24))
 # Octave transposition halves/doubles the hardware period.
 for c in (0,1,2,7):
  put('coarsepitch',12,c*3);assert call('coarse_apply',c,0,4)[0] is not None
  call('coarse_apply',c,0,4)
  # 16-bit return is BC under the banked ABI.
  result=p.register_file.B*256+p.register_file.C
  assert result==1536,(c,result)
  put('coarsepitch',-12,c*3);call('coarse_apply',c,0,4);assert p.register_file.B*256+p.register_file.C==0
  put('coarsepitch',0,c*3)
 # ADSR source with both positive and negative semitone strengths.
 put('coarsepitch',12,1);call('eval_note',0,1)
 assert call('eval_amount',0,1)[0]==12
 call('coarse_apply',0,0,4);assert p.register_file.B*256+p.register_file.C==1536
 put('coarsepitch',-12,1);assert call('eval_amount',0,1)[0]==244
 put('coarsepitch',0,1)
 # Noise quantizes to available clock/divisor combinations and retains width.
 put('coarsepitch',12,3*3);call('coarse_apply',3,0x49,0);code=p.register_file.B*256+p.register_file.C
 assert code&8 and ((code&7)*2 if code&7 else 1)<<(code>>4)==16,code
 # All settings round-trip through existing spare tone-record bytes.
 settings=bytes((i*7)&255 for i in range(24))
 for i,b in enumerate(settings):put('coarsepitch',b,i)
 call('tones_capture')
 for i in range(24):put('coarsepitch',0,i)
 call('tones_apply');assert bytes(get('coarsepitch',i) for i in range(24))==settings
 # Preset tail stores the current instrument's coarse controls.
 for c in (0,1,2,3,5,6,7):
  put('coarsepitch',7,c*3);put('coarsepitch',-11,c*3+1);put('coarsepitch',1,c*3+2)
  assert call('user_preset_save',c,c)[0]
  for i in range(3):put('coarsepitch',0,c*3+i)
  assert call('user_preset_load',c,c)[0]
  assert [get('coarsepitch',c*3+i) for i in range(3)]==[7,245,1]
 print('PASS: tempo 1/1 default, signed coarse modulation, pitch periods, noise width, tone and preset round trips')
finally:p.stop(save=False)


"""512-event native playback: actual DMG pulse-trigger timing at300BPM."""
from pathlib import Path
import json,statistics
from test_pcm_timing import pulse_write_sites
from seq_storage_helpers import write_tracks,write_word
CPU=4194304
exec(Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0].replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file='))
try:
 assert not v('experimental_mode') and p.memory[0xff4d]==255
 choose(18)
 tracks=[[] for _ in range(7)]
 for c in range(4):tracks[c]=[[s,49+c*7+s%12,100,1] for s in range(0,256,2)]
 write_tracks(p,S,tracks)
 for c in range(7):write_word(p,S['_seqlength']+c*2,256)
 write_word(p,S['_seqbpm'],300)
 pulses=[];measuring=[False]
 def apu(site):
  op,extra,cycles=site;r=p.register_file
  target=(r.B<<8)|r.C if op==0x02 else (r.D<<8)|r.E if op==0x12 else r.HL if op in (0x22,0x32,0x36,0x77) else 0xff00+extra if op==0xe0 else 0xff00+r.C if op==0xe2 else extra
  value=extra if op==0x36 else r.A
  if measuring[0] and target==0xff14 and value&128:pulses.append((p._cycles()+cycles,v('seqposition')))
 for pc,op,extra,cycles in pulse_write_sites(S):p.hook_register(0,pc,apu,(op,extra,cycles))
 p.memory[S['_mx']+4]=0;press('a');assert v('seqplaying')
 p.tick(60);begin=p._cycles();measuring[0]=True;p.tick(720);elapsed=p._cycles()-begin;measuring[0]=False
 assert len(pulses)>100
 for a,b in zip(pulses,pulses[1:]):assert b[1]==(a[1]+2)%256,('lostevent',a,b)
 residual=[t-pulses[0][0]-i*CPU/10 for i,(t,_) in enumerate(pulses)]
 intervals=[(b[0]-a[0])*1000/CPU for a,b in zip(pulses,pulses[1:])]
 result={'model':'DMG forced cgb=False','events':512,'steps':256,'bpm':300,'seconds':elapsed/CPU,'actual_apu_p1_onsets':len(pulses),'expected_onsets':elapsed/(CPU/10),'interval_ms_min':min(intervals),'interval_ms_max':max(intervals),'phase_jitter_ms_peak_to_peak':(max(residual)-min(residual))*1000/CPU,'phase_drift_ms':(residual[-1]-residual[0])*1000/CPU,'pending_clock_units':word('seqticks'),'waveengine':v('waveengine'),'limits':'Emulated cycle timing; no claim of analog hardware validation.'}
 result['meets_note_rate']=abs(len(pulses)-result['expected_onsets'])<2
 result['meets_timing']=result['interval_ms_max']<=112 and result['phase_jitter_ms_peak_to_peak']<=12
 Path('build/dense-storage-timing.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 assert result['meets_note_rate'] and result['meets_timing'],result
finally:p.stop(save=False)

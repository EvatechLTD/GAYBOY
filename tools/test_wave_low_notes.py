"""Check released Wave C1/C2 pitch, sustained audio and pattern-slot integrity."""
from pathlib import Path
from io import BytesIO
import json
import numpy as np
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])

try:
 enter_app(p,symbols);boot=BytesIO();p.save_state(boot);reports=[]
 assert not get('midi_launch_enabled'),'MIDI launching must default OFF'
 for note in (24,25,26,27,28,36):
  for bypass,launch in ((0,0),(0,1),(1,0),(1,1)):
   boot.seek(0);p.load_state(boot)
   for c in range(7):
    word('seqeventoffsets',0,c*2);word('seqeventcounts',int(c==2),c*2);word('seqlength',64,c*2)
   p.memory[1,0xa300:0xa304]=[0,note+1,127,64]
   put('syncmode',0);put('syncslave',0);put('syncarmed',0);p.memory[0xff02]=0
   word('seqbpm',120);word('seqglobalbpm',120);put('pattern_dirty',1);put('mod_bypass',bypass);put('midi_launch_enabled',launch)
   put('seqtrack',2);put('selected',2);put('page',8);put('seqhead',0);put('seqfocus',0)
   put('seqpitch',note,2);put('seqtop',note+7,2);put('dirty',1);p.tick(120)
   initial_slot=p.memory[0,0xac81]
   p.button_press('select');p.tick(3);p.button_press('a');p.tick(4)
   p.button_release('a');p.button_release('select');p.tick(60)
   audio=[];enabled=0
   for _ in range(120):
    p.tick(1);audio.append(p.sound.ndarray.copy());enabled+=bool(p.memory[0xff26]&4)
    assert p.memory[0,0xac81]==initial_slot,'Wave playback changed pattern slot'
    assert p.memory[0,0xac82]==255,('Wave playback unexpectedly queued a pattern',p.memory[0,0xac82],get('page'),get('navopen'),get('seqplaying'))
   samples=np.concatenate(audio).astype(float).mean(axis=1);samples-=samples.mean()
   spectrum=abs(np.fft.rfft(samples*np.hanning(len(samples))))
   freq=np.fft.rfftfreq(len(samples),1/p.sound.sample_rate);peak=float(freq[np.argmax(spectrum)])
   rms=float(np.sqrt(np.mean(samples**2)));expected=440*2**((note-69)/12)
   row={'note':note,'mod_bypass':bypass,'midi_launch_enabled':launch,'engine':get('waveengine'),'peak_hz':round(peak,3),'rms':round(rms,3),'channel_enabled_frames':enabled,'slot':initial_slot}
   print(json.dumps(row),flush=True);reports.append(row)
   assert enabled>=118 and rms>1,('Wave is silent',row)
   assert abs(peak-expected)<1,('Wave frequency incorrect',row,expected)
 Path('build/wave-low-notes.json').write_text(json.dumps(reports,indent=2))
finally:p.stop(save=False)

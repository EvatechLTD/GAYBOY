"""Compare direct resident event lookups and wave uploads on the DMG CPU."""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--output');args=ap.parse_args()
prefix=Path('tools/test_stripped_resident.py').read_text().split('import json')[0]
prefix=prefix.replace("Path('build/GAYBOY.noi')","Path(args.rom).with_suffix('.noi')").replace("'build/GAYBOY.gb',",'args.rom,')
exec(prefix)
try:
 put('experimental_mode',1);put('power',1);put('frameadvance',1)
 call('eval_defaults');call('drum_init');call('startup');call('sparse_boot');call('mixer_init')
 # Populate a full track directly, preserving all 256 record indices.
 for c in range(7):
  put('seqeventcounts',0,c*2);put('seqeventcounts',1 if c==0 else 0,c*2+1)
  put('seqeventoffsets',0,c*2);put('seqeventoffsets',0 if c==0 else 1,c*2+1)
 p.memory[0x4000]=1
 for i in range(256):p.memory[0xa300+i*4:0xa304+i*4]=[i,40+i%40,127,1]
 p.memory[0x4000]=0
 call('storage_sorted_dirty')
 _,prepare=call('storage_sorted_prepare')
 times=[]
 for step in range(0,256,17):
  ok,ms=call('seq_note_event',0,step,0,0xb1);assert ok
  assert list(p.memory[0xb100:0xb104])==[step,40+step%40,127,1]
  times.append(ms)
 # Editing a step must invalidate the lookup, including same-count edits.
 p.memory[0xb100:0xb104]=[19,62,100,2]
 assert call('seq_event_put',0,0,0,0,0xb1)[0]
 call('storage_sorted_prepare')
 assert not call('seq_note_event',0,0,0,0xb1)[0]
 assert call('seq_note_event',0,19,0,0xb1)[0]
 assert p.memory[0xb101]==59 # lowest of inserted62 and existing59
 call('seq_track_clear',0)
 # Collision across tracks: hash(P1,37)==hash(P2,0).
 for c,step,note in ((0,37,60),(1,0,64),(0,37,55)):
  p.memory[0xb100:0xb104]=[step,note,127,1]
  assert call('seq_event_put',c,255,255,0,0xb1)[0]
 for i in range(30):
  p.memory[0xb100:0xb104]=[i,11,127,1];assert call('seq_event_put',6,255,255,0,0xb1)[0]
 call('storage_sorted_prepare')
 for c,step,note in ((0,37,55),(1,0,64)):
  assert call('seq_note_event',c,step,0,0xb1)[0]
  assert p.memory[0xb101]==note
 p.memory[0xb110:0xb112]=[0,0]
 for note in (60,55):
  assert call('seq_event_next_step',0,37,0x10,0xb1,0,0xb1)[0]
  assert p.memory[0xb101]==note
 assert not call('seq_event_next_step',0,37,0x10,0xb1,0,0xb1)[0]
 put('waveengine',0);put('custom',0);put('param',6,2*26+14)
 _,first=call('wave');wave_times=[call('wave')[1] for _ in range(12)]
 put('custom',1)
 for i in range(16):put('customwave',i*11,i)
 call('wave');assert list(p.memory[0xff30:0xff40])==[i*11 for i in range(16)]
 put('customwave',233,7);call('wave');assert p.memory[0xff37]==233
 call('drum_enable');p.memory[0xff1a]=0
 p.memory[0xff30:0xff40]=[0]*16
 put('waveengine',0);call('wave');assert p.memory[0xff37]==233
 report={'index_prepare_ms':prepare,'event_lookup_mean_ms':sum(times)/len(times),'event_lookup_max_ms':max(times),'first_wave_upload_ms':first,'unchanged_wave_mean_ms':sum(wave_times)/len(wave_times)}
 print(json.dumps(report,indent=2))
 if args.output:Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
finally:p.stop(save=False)

"""Actual drag attacks and release-time resize auditions follow pitch and BPM."""
from pathlib import Path
exec(Path('tools/test_live_note_plot.py').read_text().split('\ntry:')[0])

def wait_silent(expected_ms):
 start=p._cycles()
 for _ in range(1500):
  p.tick(1)
  c=get('seqtrack')
  if not get('seq_live_timed') and not get('seqauditionnote') and (c>=3 or not get('active',c) and not get('keycount',c)):break
 else:raise AssertionError('Timed audition never ended')
 ms=(p._cycles()-start)/4194.304
 assert abs(ms-expected_ms)<35,('Wrong resize audition duration',ms,expected_ms)
 silent_owner(get('seqtrack'));return round(ms,2)

try:
 enter_app(p,symbols);boot=BytesIO();p.save_state(boot);calls=[]
 a=symbols['_seq_plot_audition'];p.hook_register(a>>16,a&65535,lambda _:calls.append(p._cycles()),None)
 for c,note in ((0,60),(1,60),(2,24),(6,0)):
  setup(c,note);tap('b');before=len(calls)
  key('a',True);tap('right')
  assert len(calls)==before+1 and get('seqauditionnote')==note+1,('Move did not retrigger',c)
  key('a',False);silent_owner(c)
  key('b',True);tap('right');tap('right');tap('right');before=len(calls)
  assert not get('seq_live_timed'),'Resize retriggered before B release'
  key('b',False)
  assert len(calls)==before+1 and get('seq_live_timed') and get('seqauditionnote')==note+1
  ms=wait_silent(500);print('PASS drag retrigger and four-cell resize release',c,ms,'ms',flush=True)
 # An unmoved A gesture auditions only on release, with the stored duration.
 for c,note in ((0,60),(1,60),(2,24),(6,0)):
  setup(c,note);tap('b');before=len(calls)
  key('a',True);assert len(calls)==before,'A press auditioned before release'
  key('a',False)
  assert len(calls)==before+1 and get('seq_live_timed')
  assert get('seqauditionnote')==note+1
  print('PASS A tap release audition',c,wait_silent(125),'ms',flush=True)
  before=len(calls);tap('a');assert len(calls)==before+1
  wait_silent(125)
 # Empty-cell A taps preview the current pitch and remembered length only.
 for c,note in ((0,60),(1,60),(2,24),(6,0),(6,3)):
  setup(c,note);word('seqdefaultdur',4,c*2);before=len(calls)
  key('a',True);assert len(calls)==before
  key('a',False)
  assert len(calls)==before+1 and get('seq_live_timed')
  assert get('seqauditionnote')==note+1 and get('seqeventcounts',c*2)==0
  print('PASS empty-cell tap without insertion',c,note,wait_silent(500),'ms',flush=True)
 # Empty-cell taps clear an existing selection silently; the next tap previews.
 for c,note in ((0,60),(2,24),(6,0)):
  setup(c,note);put('seqgrouptrack',c);put('seqgroupx0',4);put('seqgroupx1',6)
  put('seqgroupy0',note);put('seqgroupy1',note);put('dirty',1);p.tick(30)
  before=len(calls);tap('a')
  assert get('seqgrouptrack')==255 and len(calls)==before
  assert not get('seq_live_timed') and not get('seqauditionnote')
  tap('a');assert len(calls)==before+1 and get('seq_live_timed')
  print('PASS deselection is silent, subsequent empty tap previews',c,flush=True)
 for bpm,steps in ((60,4),(240,4),(120,2)):
  setup(2,24);word('seqbpm',bpm);word('seqglobalbpm',bpm);tap('b')
  key('b',True)
  for _ in range(steps-1):tap('right')
  key('b',False);assert get('seq_live_timed')
  print('PASS resize timing',bpm,steps,wait_silent(15000*steps/bpm),'ms',flush=True)
 # Pitch movement retriggers the new pitch and retains the stored note.
 setup(2,24);tap('b');key('a',True)
 p.button_press('up')
 for _ in range(1200):
  p.tick(1)
  if get('lastpad')&4:break
 assert get('seqauditionnote')==26 and get('held',2)==25
 p.button_release('up');p.tick(10);key('a',False);silent_owner(2)
 print('PASS dragged pitch auditions new note',flush=True)
 # A selection resize also previews the note under the cursor on release.
 setup(2,24);tap('b');p.memory[1,0xa304:0xa308]=[0,29,127,1];word('seqeventcounts',2,4)
 put('evalpatch',1,2*16+13);put('seqgrouptrack',2);put('seqgroupx0',0);put('seqgroupx1',0);put('seqgroupy0',24);put('seqgroupy1',28)
 put('seqdrawvalid',0);put('dirty',1);p.tick(120)
 key('b',True);tap('right');key('b',False);assert get('seq_live_timed')
 assert p.memory[1,0xa303]==2 and p.memory[1,0xa307]==2
 print('PASS group resize release',wait_silent(250),'ms',flush=True)
 # Expiry of an older audition must not discard a new resize being held.
 setup(2,24);tap('b');key('b',True)
 for _ in range(3):tap('right')
 key('b',False);key('b',True);tap('right');p.tick(60)
 assert not get('seq_live_timed');key('b',False);assert get('seq_live_timed')
 print('PASS pending resize survives previous preview expiry',wait_silent(625),'ms',flush=True)
 setup(2,24);tap('b');key('b',True);tap('right');word('sys_time',65530)
 key('b',False);assert get('seq_live_timed')
 print('PASS preview deadline across frame-counter wrap',wait_silent(250),'ms',flush=True)
 # Starting playback cancels an outstanding timed resize preview.
 setup(2,24);tap('b');key('b',True);tap('right');key('b',False)
 assert get('seq_live_timed');key('select',True);tap('a');key('select',False)
 assert get('seqplaying') and not get('seq_live_timed') and not get('seqauditionnote')
 p.tick(180);assert get('seqplaying') and get('mx',1)==0 and get('mx',2)==255
 print('PASS transport cancels timed preview without MIDI launches',flush=True)
finally:p.stop(save=False)

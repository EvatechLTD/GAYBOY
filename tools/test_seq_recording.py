"""Piano B records at the moving playhead; holding B determines note length."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import read_tracks,write_tracks,write_word

def put(n,i,x):fixture_put(p,S,n,i,x)
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(8)
def wait_until(predicate,limit=240):
 for _ in range(limit):
  p.tick(1)
  if predicate():return
 raise AssertionError('Timed out waiting for recording state')
try:
 choose(8);write_tracks(p,S,[[] for _ in range(7)])
 put('seqhead',0,6);put('seqpitch',0,64);put('seqcursor',0,7);put('dirty',0,1);p.tick(20)
 # Stopped piano B auditions without populating the pattern.
 p.button_press('b');wait_until(lambda:v('lastpad')&32)
 assert not read_tracks(p,S)[0] and v('active'), 'Stopped B should only audition'
 p.button_release('b');wait_until(lambda:not(v('lastpad')&32));p.tick(10)
 assert not read_tracks(p,S)[0] and not v('active')
 put('seqlength',0,8);write_word(p,S['_seqbpm'],120)
 chord('select','a');assert v('seqplaying')
 put('seqhead',0,6);put('seqcursor',0,7)
 wait_until(lambda:2<=v('seqposition')<=3)
 p.button_press('b');wait_until(lambda:v('lastpad')&32)
 start=v('seqrecordstart');assert start!=7,'Recording used edit cursor instead of playhead'
 assert v('seqrecordtrack')==0 and v('active')
 wait_until(lambda:v('seqposition')>=start+3)
 p.button_release('b');wait_until(lambda:not(v('lastpad')&32));p.tick(8)
 events=read_tracks(p,S)[0];event=next(e for e in events if e[0]==start)
 assert event[1]==65 and 3<=(event[3] or 256)<=8-start,event
 assert not any(e[0]==7 for e in events),events
 assert v('seqrecordtrack')==255
 # The recorded event must trigger normally on the following loop.
 played=[]
 def onset(_):
  if p.register_file.A==0 and v('seqposition')==start and v('seqrecordtrack')==255:played.append(p._cycles())
 p.hook_register(0,S['_play'],onset,None);p.tick(100)
 assert played,'Recorded event did not play on the next loop'
 # Opening the menu must end a held recording even if B is released there.
 put('seqhead',0,6);p.button_press('b');wait_until(lambda:v('seqrecordtrack')==0)
 p.button_press('start');wait_until(lambda:v('navopen'))
 p.button_release('b');p.tick(8);assert v('seqrecordtrack')==255
 p.button_release('start');wait_until(lambda:not v('navopen'))
 chord('select','a');assert not v('seqplaying')
 print('PASS: stopped B audition only, live playhead placement, held duration, next-loop playback')
finally:p.stop(save=False)


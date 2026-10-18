"""Exercise GEN through actual UI and verify isolation, theory and rollback."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import write_tracks, read_tracks
try:
 choose(8)
 tracks=[[[0,49,100,1],[20,53,90,1]],[[2,61,99,1]],[],[],[],[],[]]
 write_tracks(p,S,tracks)
 put('seqtrack',0,0);put('seqlength',0,16)
 # Start on the roll, then open GEN while playing.
 p.button_press('select');press('a');p.button_release('select');p.tick(4)
 assert v('seqplaying')
 stops=[]
 address=S['_seq_stop'];p.hook_register(address>>16,address&65535,lambda _:stops.append(True),None)
 press('select');assert v('page')==10
 p.button_press('select');press('a');p.button_release('select');p.tick(4)
 assert v('genopen') and v('seqplaying') and not stops
 put('genrow',0,8);press('a');assert v('genpreview') and v('seqplaying') and not stops
 result=read_tracks(p,S)
 assert result[1:]==tracks[1:],result
 assert [20,53,90,1] in result[0]
 active=[e for e in result[0] if e[0]<16]
 assert active and all((e[1]-1-9)%12 in (0,2,3,5,7,8,10) for e in active),active
 position=v('seqposition',1);p.tick(12);assert v('seqposition',1)!=position
 p.tick(90)
 p.screen.image.save('build/gen-preview.png')
 press('b');assert not v('genopen') and v('seqplaying') and not stops
 assert read_tracks(p,S)==tracks,read_tracks(p,S)
 # Keep a repeatable candidate and then generate DRUM independently.
 p.button_press('select');press('a');p.button_release('select');p.tick(4)
 put('genrow',0,8);press('a');first=read_tracks(p,S)
 press('a');assert read_tracks(p,S)==first
 put('genrow',0,9);press('a');assert not v('genopen')
 assert read_tracks(p,S)==first
 put('seqtrack',0,6)
 p.button_press('select');press('a');p.button_release('select');p.tick(4)
 put('genrow',0,8);press('a');drums=read_tracks(p,S)
 assert drums[:6]==first[:6] and drums[6]
 assert all(1<=e[1]<=13 for e in drums[6])
 # Opening the global menu cancels any uncommitted preview.
 p.button_press('start');p.tick(20);p.button_release('start');p.tick(20)
 assert not v('genopen') and read_tracks(p,S)==first
 assert v('seqplaying') and not stops
 print('PASS: GEN isolation, scales, inactive notes, deterministic seed, audition, keep, drum generation and cancellation')
finally:p.stop(save=False)

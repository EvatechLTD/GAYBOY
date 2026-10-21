"""Generated simultaneous triads must survive storage, rollback and the instrument arp."""
from pathlib import Path
exec(Path('tools/test_seq_gen.py').read_text().split('\ntry:\n')[0])

def chord_role():
 # MELODY -> BASS -> ARP -> CHORD through actual UI edits.
 for _ in range(3):edit(0,'right')
 assert v('gentype')==3 and v('genrhythm')==7 and v('genlength')==5 and v('gencontour')==0

def refresh():edit(1,'right');edit(1,'left')

try:
 enter_app(p);put('sticky_start',1)
 original=[[[2,49,100,1],[100,53,90,1]],[[1,62,80,1]],[],[],[],[],[[4,2,90,1]]]
 for track in range(3):
  write_tracks(original);put('seqtrack',track);setword('seqlength',64,track)
  open_gen();chord_role();assert v('genpreview') and not v('generror')
  # Default A-minor block chords: A C E, held for sixteen steps.
  generated=[e for e in read_tracks()[track] if e[0]<64]
  assert generated==[[s,n,p.memory[S['_seqdefaultvel']+track],16] for s in (0,16,32,48) for n in (58,61,65)]
  assert all(read_tracks()[c]==original[c] for c in range(7) if c!=track)
  assert all(e in read_tracks()[track] for e in original[track] if e[0]>=64)
  edit(3,'right');edit(3,'right');assert v('genprogression')==2
  expected=((58,61,65),(65,68,72),(66,70,73),(63,66,70))
  generated=[e for e in read_tracks()[track] if e[0]<64]
  assert [[e[1] for e in generated if e[0]==s] for s in (0,16,32,48)]==[list(c) for c in expected]
  # Minor and Dorian share the tonic triad, but IV changes minor -> major
  # and VI has the raised sixth as its root.
  minor=read_tracks();edit(2,'right');assert v('genscale')==2
  dorian=read_tracks()[track]
  assert [e for e in dorian if e[0]==0]==[e for e in minor[track] if e[0]==0]
  assert [e[1] for e in dorian if e[0]==32]==[67,70,73]
  assert [e[1] for e in dorian if e[0]==48]==[63,67,70]
  edit(2,'left');assert read_tracks()==minor
  # All notes at each chord onset share its gate and velocity.
  for s in (0,16,32,48):assert len({(e[2],e[3]) for e in generated if e[0]==s})==1
  edit(7,'right');assert v('gencontour')==1
  assert [e[1] for e in read_tracks()[track] if e[0]==0]==[61,65,70]
  edit(7,'right');assert v('gencontour')==2
  assert [e[1] for e in read_tracks()[track] if e[0]==0]==[65,70,73]
  # Quarter-note harmonic changes create four complete triads in a one-bar loop.
  edit(4,'left');edit(4,'left');assert v('genchange')==0
  generated=[e for e in read_tracks()[track] if e[0]<64]
  assert len(generated)==48 and all(e[3]==4 for e in generated)
  if track==0:p.screen.image.save('build/newgen-chord.png')
  press('select');assert read_tracks()==original
 # A chord consumes three event slots; failed previews must preserve every original note.
 full=[[[0,49,100,1]],[[i,61,99,1] for i in range(246)],[],[],[],[],[]]
 write_tracks(full);put('seqtrack',0);setword('seqlength',16,0);open_gen()
 assert v('genpreview')
 chord_role();assert not v('generror') # one held triad fits
 good=read_tracks();edit(5,'left') # EUCLID: 5 triads = 15 slots; only 10 are available
 assert v('generror') and read_tracks()==good
 put('genrow',12);press('a');assert v('genopen')
 press('select');assert read_tracks()==full
 # The held triad is the instrument arp's complete input, not just its root.
 write_tracks([[],[],[],[],[],[],[]]);put('seqtrack',0);setword('seqlength',16,0)
 patch=S['_evalpatch'];p.memory[patch]=1 # Existing instrument MODE=ARP; keep its settings.
 open_gen();chord_role();put('genrow',12);press('a');assert not v('genopen')
 put('seqmuted',126);put('seqsolo',0)
 p.button_press('select');p.tick(3);press('a');p.button_release('select');p.tick(8)
 assert v('seqplaying')
 heard=set()
 for _ in range(100):
  p.tick(1)
  if p.memory[S['_active']]:heard.add(p.memory[S['_held']])
 assert heard=={57,60,64},heard
 assert p.memory[S['_arpcount']]==3
 assert p.memory[patch]==1
 print('PASS: three-note chords on P1/P2/WAVE, progressions, inversions, held durations, isolation, rollback, triple-slot capacity rejection and all three notes played by the instrument arp')
finally:p.stop(save=False)

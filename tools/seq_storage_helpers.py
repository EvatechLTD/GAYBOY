"""Direct disposable-RAM fixtures for the256-step sparse event storage."""
def read_word(p,address):return p.memory[address]|p.memory[address+1]<<8

def write_word(p,address,value):p.memory[address]=value&255;p.memory[address+1]=value>>8

def mark_pattern_changed(p,symbols):
 # Direct fixture writes bypass the UI/MIDI mutation hooks used by the ROM.
 if '_seqirqready' in symbols and not p.memory[symbols['_syncmode']]:
  p.memory[symbols['_seqirqready']]=0
  p.memory[symbols['_seqirqdirty']]=1
 if '_pattern_dirty' in symbols:
  p.memory[symbols['_pattern_dirty']]=1
  if '_pattern_generation' in symbols:
   at=symbols['_pattern_generation'];write_word(p,at,(read_word(p,at)+1)&65535)

def read_tracks(p,symbols):
 tracks=[]
 for c in range(7):
  start=read_word(p,symbols['_seqeventoffsets']+c*2)
  count=read_word(p,symbols['_seqeventcounts']+c*2)
  events=[]
  for i in range(start,start+count):
   at=symbols['_seqevents_lo']+i*4 if i<256 else 0xa800+(i-256)*4
   events.append(list(p.memory[at:at+4]))
  tracks.append(events)
 return tracks

def write_tracks(p,symbols,tracks):
 assert len(tracks)==7
 assert sum(map(len,tracks))<=512
 offset=0
 for c,events in enumerate(tracks):
  write_word(p,symbols['_seqeventoffsets']+c*2,offset)
  write_word(p,symbols['_seqeventcounts']+c*2,len(events))
  for event in events:
   assert len(event)==4 and 0<=event[0]<=255 and 1<=event[1]<=(13 if c==6 else 128) and 0<=event[2]<=127 and 0<=event[3]<=255
   at=symbols['_seqevents_lo']+offset*4 if offset<256 else 0xa800+(offset-256)*4
   p.memory[at:at+4]=event;offset+=1
 p.memory[symbols['_seqeventfull']]=0
 mark_pattern_changed(p,symbols)

def melodic_events(notes,velocities=None,durations=None,default_velocity=100,default_duration=1):
 events=[]
 for step,note in enumerate(notes):
  if not note:continue
  velocity=velocities[step] if velocities and velocities[step] else default_velocity
  duration=durations[step] if durations and durations[step] else default_duration
  assert 1<=duration<=256
  events.append([step,note,velocity,duration&255])
 return events


LEGACY_MELODIC=('seqnotes','seqvelocity','seqduration')
LEGACY_DRUM=('drumhits','drumvel','drumdur','noisehits','noisevel','noisedur')
TYPED_WORDS=('seqlength','seqdefaultdur')

def fixture_value(p,symbols,name,index=0):
 if name in TYPED_WORDS:return read_word(p,symbols['_'+name]+index*2)
 if name=='seqgateleft':
  at=symbols['_'+name]+index*4
  return sum(p.memory[at+j]<<(8*j) for j in range(4))
 if name in LEGACY_MELODIC:
  c,step=divmod(index,64);event=next((e for e in read_tracks(p,symbols)[c] if e[0]==step and e[1]),None)
  if event is None:return 0
  field=LEGACY_MELODIC.index(name)+1
  return (event[field] or 256) if field==3 else event[field]
 if name in LEGACY_DRUM:
  step,voice=divmod(index,2);noise=name.startswith('noise')
  events=[e for e in read_tracks(p,symbols)[6] if e[0]==step and (e[1]>=11 if noise else e[1]<=10)]
  event=next((e for e in events if e[1]==11+voice),None) if noise else (events[voice] if voice<len(events) else None)
  if event is None:return 0
  if name.endswith('hits'):return 1 if noise else event[1]
  if name.endswith('vel'):return event[2]
  return event[3] or 256
 return p.memory[symbols['_'+name]+index]

def fixture_put(p,symbols,name,index,value):
 if name in TYPED_WORDS or name in ('seqgate','seqbpm','seqbeats','seqdenom','param','mods','program','noisepatch','pulsekickpatch','drumkit','master','vin'):
  mark_pattern_changed(p,symbols)
 if "_seqeventcounts" not in symbols:p.memory[symbols["_"+name]+index]=value;return
 if name in TYPED_WORDS:write_word(p,symbols['_'+name]+index*2,value);return
 if name in LEGACY_MELODIC:
  tracks=read_tracks(p,symbols);c,step=divmod(index,64);event=next((e for e in tracks[c] if e[0]==step and e[1]),None)
  if name=='seqnotes':
   if not value:
    if event is not None:tracks[c].remove(event)
   elif event is None:tracks[c].append([step,value,p.memory[symbols['_seqdefaultvel']+c],read_word(p,symbols['_seqdefaultdur']+c*2)&255])
   else:event[1]=value
  elif event is not None:event[2 if name=='seqvelocity' else 3]=value&255
  write_tracks(p,symbols,tracks);return
 if name in LEGACY_DRUM:
  tracks=read_tracks(p,symbols);step,voice=divmod(index,2);noise=name.startswith('noise');events=[e for e in tracks[6] if e[0]==step and (e[1]>=11 if noise else e[1]<=10)]
  event=next((e for e in events if e[1]==11+voice),None) if noise else (events[voice] if voice<len(events) else None)
  if name.endswith('hits'):
   if not value:
    if event is not None:tracks[6].remove(event)
   elif event is None:tracks[6].append([step,11+voice if noise else value,100,1])
   elif not noise:event[1]=value
  elif event is not None:event[2 if name.endswith('vel') else 3]=value&255
  write_tracks(p,symbols,tracks);return
 p.memory[symbols['_'+name]+index]=value

"""Matched musical playback:120/live fast arp versus240/live or Generate notes.
Uses the frozen pre-resolution ROM and real Generate UI; never changes a save.
"""
from pathlib import Path
from io import BytesIO
import json,hashlib,statistics
prefix=Path('tools/profile_arp_ui.py').read_text().split('rows=[]')[0]
prefix=prefix.replace("ap.add_argument('--internal'","ap.add_argument('--two-case',action='store_true');ap.add_argument('--internal'")
exec(prefix)
from arp_probe_helpers import hook_attacks
assert '_seqres32' not in S,'Do not include the paused meter prototype in this comparison'
def tap(k):
 assert key(k,True) is not None;assert key(k,False) is not None;p.tick(8)
def transport():
 acks=[key('select',True),key('a',True),key('a',False)];p.tick(8);acks.append(key('select',False));p.tick(30);return any(x is None for x in acks)
def editgen(k):
 assert key('a',True) is not None;tap(k);assert key('a',False) is not None;p.tick(20)
def tracks():
 bank=1+(get('mx',1)>>2);base=0xa300+(get('mx',1)&3)*2048
 return [[list(p.memory[bank,base+i*4:base+i*4+4]) for i in range(get('seqeventoffsets',c*2)|(get('seqeventoffsets',c*2+1)<<8),(get('seqeventoffsets',c*2)|(get('seqeventoffsets',c*2+1)<<8))+(get('seqeventcounts',c*2)|(get('seqeventcounts',c*2+1)<<8)))] for c in range(7)]
def write_tracks(data,lengths):
 bank=1+(get('mx',1)>>2);base=0xa300+(get('mx',1)&3)*2048;off=0
 for c,events in enumerate(data):
  word('seqeventoffsets',off,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',lengths[c],c*2)
  for e in events:p.memory[bank,base+off*4:base+off*4+4]=e;off+=1
 put('seqeventcache',0);put('seqirqready',0);put('seqirqdirty',1);word('pattern_generation',(get('pattern_generation')|(get('pattern_generation',1)<<8))+1)
def render_generate(length,rhythm,beats):
 put('page',8);put('seqtrack',1);put('selected',1);put('theorytrack',1);put('seqhead',0);put('seqfocus',0);put('seqbeats',beats);put('seqdenom',4);put('sticky_start',1)
 put('navopen',1);put('navcategory',1);put('navchoice',47);put('dirty',1);tap('a');assert get('genopen') and get('seqtrack')==1
 # Set deterministic controls, then invoke the production generator via KEY edit.
 for n,v in [('gentype',2),('genprogression',0),('genchange',3),('genrhythm',rhythm),('genlength',5),('gencontour',1),('genvariation',0),('genregister',4),('genscale',0)]:put(n,v)
 for seed in range(12):
  word('genseed',seed);put('genroot',11);put('genrow',1);editgen('up') # B -> C wraps and generates.
  events=tracks()[1];pitches=sorted({e[1] for e in events})
  if len(pitches)==3 and events[0][1]==pitches[0]:break
 else:raise AssertionError(('Cannot align generated ascending triad',events))
 assert not get('generror') and len(events)==8,(length,rhythm,events)
 gap=1<< (2-rhythm)
 assert [e[0] for e in events]==list(range(0,length,gap)),events
 assert [e[1] for e in events]==[pitches[i%3] for i in range(8)],events
 assert all(e[2]==127 and e[3]==gap for e in events),events
 put('genrow',12);tap('a');assert not get('genopen')
 return events,pitches

def measure_audio(state,expected_gap,pitches):
 q=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)));q.set_emulation_speed(0)
 hits=[];freqs=[];hook_attacks(q,rom,S,1,hits.append,freqs.append,include_editbuffer=True)
 state.seek(0);q.load_state(state);q.tick(240);hits.clear();freqs.clear();q.tick(480)
 intervals=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])]
 ptr=S['_notes'];bank=ptr>>16;base=ptr&65535;lookup=[q.memory[bank,base+(n-1)*2]|q.memory[bank,base+(n-1)*2+1]<<8 for n in pitches]
 ranks=[lookup.index(f) if f in lookup else -1 for f in freqs];phrase=[0,1,2,0,1,2,0,1]
 matches=any(all(r==phrase[(i+phase)%8] for i,r in enumerate(ranks)) for phase in range(8))
 q.stop(save=False)
 assert len(intervals)>10 and -1 not in ranks,('wrong pitches or missing notes',ranks[:32],lookup)
 return {'attacks':len(hits),'median_ms':statistics.median(intervals),'min_ms':min(intervals),'max_ms':max(intervals),'max_error_ms':max(abs(x-expected_gap) for x in intervals),'pitch_order_matches':matches,'first_pitch_ranks':ranks[:48],'outlier_intervals_ms':[round(x,3) for x in intervals if abs(x-expected_gap)>2]}

rows=[]
try:
 enter_app(p,S);original=tracks();lengths=[get('seqlength',c*2)|(get('seqlength',c*2+1)<<8) for c in range(7)]
 assert not get('seqplaying');base=BytesIO();p.save_state(base)
 generated={}
 for rate,rhythm,beats,length in [(4,0,4,32),(8,1,2,16),(16,2,1,8)]:
  base.seek(0);p.load_state(base);data=[[e[:] for e in lane] for lane in original];data[1]=[];sizes=lengths[:];sizes[1]=length;write_tracks(data,sizes);put('seqdefaultvel',127,1)
  events,pitches=render_generate(length,rhythm,beats);generated[rate]=(events,pitches,beats)
 for clock in ('internal','link-master'):
  for view in ('menu','grid'):
   for rate,division in ([(16,3)] if args.two_case else [(4,5),(8,4),(16,3)]):
    events,pitches,beats=generated[rate];length240=len(events)*(events[1][0]-events[0][0]);length120=length240//2
    for kind,bpm,scale in ([('live120',120,1),('generated240',240,2)] if args.two_case else [('live120',120,1),('live240',240,2),('generated240',240,2)]):
     base.seek(0);p.load_state(base);data=[];sizes=[]
     for c,lane in enumerate(original):
      data.append([[e[0]*scale,e[1],e[2],(e[3] if e[3] else 256)*scale] for e in lane] if c!=1 else [])
      sizes.append(lengths[c]*scale)
     data[1]=[e[:] for e in events] if kind=='generated240' else [[0,n,127,length120 if scale==1 else length240] for n in pitches]
     sizes[1]=length120 if scale==1 else length240
     assert all(e[0]<256 and 0<e[3]<=256 for lane in data for e in lane)
     write_tracks(data,sizes)
     for c in range(3):put('evalpatch',int(c==1 and kind!='generated240'),c*16);put('evalpatch',int(c==1 and kind!='generated240'),c*16+13)
     put('evalpatch',division+(scale==2),18);put('evalpatch',0,17);put('evalpatch',0,19);put('evalpatch',1,20);put('evalpatch',0,21)
     word('seqbpm',bpm);word('seqglobalbpm',bpm);word('seqcachedbpm',0);put('seqbeats',beats);put('seqdenom',4);put('navopen',0)
     if clock=='internal':
      put('syncmode',0);put('syncarmed',0);p.memory[0xff07]=0;p.memory[0xff06]=p.memory[0xff05]=240;p.memory[0xff0f]&=~4;p.memory[0xff07]=4
     put('page',8 if view=='grid' else 1);put('seqtrack',1);put('selected',1);put('seqhead',0);put('seqfocus',0);put('seqdrawvalid',0);put('dirty',1);p.tick(150)
     # Start from the sequencer; Select+A in a settings page is not transport.
     put('page',8);start_timeout=transport();put('page',8 if view=='grid' else 1);put('navopen',int(view=='menu'));put('navcategory',0);put('navchoice',1);put('dirty',1);p.tick(240)
     assert get('seqplaying')
     state=BytesIO();p.save_state(state);audio=measure_audio(state,1000/rate,pitches)
     prof.begin();p.tick(480);idle=prof.end()
     prof.begin();acks=[]
     for k in ('down','up')*6:acks.extend((key(k,True),key(k,False)))
     nav=prof.end()
     # These exclusive buckets are disjoint. They exclude uninstrumented caller wrappers.
     funcs=idle['functions'];audio_names=set(funcs)-{'ui_input','ui_render','ui_flush','seq_pixels','native_mode_feedback'}
     cost=sum(funcs[n]['exclusive_cycles'] for n in audio_names)*100/idle['elapsed_cycles']
     row={'clock':clock,'view':view,'rate_hz':rate,'kind':kind,'bpm':bpm,'P2_events':len(data[1]),'total_events':sum(map(len,data)),'arp_native_mask':get('arpirq_enabled'),'edit_native_mask':get('editirq_enabled'),'audio':audio,'measured_audio_cpu_pct':cost,'idle':idle,'navigation':nav,'input_ack_ms':acks,'median_input_ms':statistics.median(v for v in acks if v is not None),'max_input_ms':max(v for v in acks if v is not None),'timeouts':sum(v is None for v in acks),'transport_ack_timeout':start_timeout}
     rows.append(row);Path(args.output).write_text(json.dumps({'rom':str(rom),'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(args.save.read_bytes()).hexdigest(),'generator':'production Generate ARP LINE, C major, ascending, no variation, applied through UI','cases':rows},indent=2))
     print(clock,view,rate,kind,'audioCPU',round(cost,2),'input',round(row['median_input_ms'],1),round(row['max_input_ms'],1),'audioerr',round(audio['max_error_ms'],3),flush=True)
finally:p.stop(save=False)

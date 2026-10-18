"""Release gates: real-button launch, actual APU onsets and PCM/PK/P1 integration."""
from pathlib import Path
import argparse,json,sys,hashlib
import test_pcm_timing as pcm
from io import BytesIO
from pyboy import PyBoy
from seq_storage_helpers import write_tracks,write_word

ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--output',default='build/launch-acceptance.json');ap.add_argument('--quick',action='store_true');ap.add_argument('--report-only',action='store_true');args=ap.parse_args();pcm.ROM=Path(args.rom)
CPU=4194304
S={l.split()[1]:int(l.split()[2],16) for l in Path(args.rom).with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
results=[];failures=[]
FRAME_MS=1000/59.7275
for length,bpm in ([(16,120),(32,180),(64,220)] if args.quick else [(n,b) for n in (16,32,64) for b in (120,180,220)]):
 p=PyBoy(args.rom,window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0)
 def v(n,i=0):return p.memory[S['_'+n]+i]
 def put(n,i,x):p.memory[S['_'+n]+i]=x
 def m(i):return v('mx',i)
 def sm(i,x):put('mx',i,x)
 def press(key):
  mask={'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'start':128}[key];start=p._cycles();p.button_press(key)
  for _ in range(600):
   p.tick(1)
   if v('lastpad')&mask:break
  assert v('lastpad')&mask
  ack=(p._cycles()-start)*1000/CPU;p.button_release(key)
  for _ in range(600):
   p.tick(1)
   if not v('lastpad')&mask:break
  assert not v('lastpad')&mask
  p.tick(2);return start,ack
 def choose(n):
  p.button_press('start')
  for _ in range(600):
   p.tick(1)
   if v('navopen'):break
  for _ in range(32):
   if v('navchoice')==n:break
   press('down')
  assert v('navchoice')==n;p.button_release('start');p.tick(40);assert v('page')==n
 def settled_slot(slot):
  for _ in range(1200):
   p.tick(1)
   if m(1)==slot and m(2)==255:break
  assert m(1)==slot and m(2)==255,('stopped slot load did not complete',slot,m(1),m(2))
  p.tick(60) # Fixture setup only: finish retained graphics before mutating data.
 def pattern(duty):
  tracks=[[] for _ in range(7)]
  tracks[0]=[[s,61+s%5,100,4] for s in range(0,length,4)]
  tracks[1]=[[s,68+s%3,100,1] for s in range(length)]
  tracks[6]=[[s,1 if s%8==0 else 4,127,4] for s in range(0,length,4)]+[[s,13,127,1] for s in range(1,length,4)]
  write_tracks(p,S,tracks)
  for c in range(7):write_word(p,S['_seqlength']+c*2,length)
  write_word(p,S['_seqbpm'],bpm);put('param',0,duty)
 try:
  for _ in range(2800):
   p.tick(1)
   if v('introready'):break
  p.button_press('start')
  for _ in range(120):
   p.tick(1)
   if not v('introactive') and v('page')==8:break
  p.button_release('start');p.tick(50)
  choose(18);pattern(0);choose(20);press('b')
  sm(4,31);press('a');settled_slot(1);pattern(2);choose(20);sm(6,1);press('b')
  sm(4,30);press('a');settled_slot(0);sm(4,0);press('a');assert v('seqplaying');p.tick(30)
  notes=[];starts=[];boundaries=[];releases=[];transports=[];input_entries=[];pcm_ready=[];p1_resumes=[];measuring=False
  def hook(name,fn):
   a=S['_'+name];p.hook_register(a>>16,a&65535,fn,None)
  def apu_write(site):
   op,extra,cost=site;r=p.register_file
   at=(r.B<<8)|r.C if op==0x02 else (r.D<<8)|r.E if op==0x12 else r.HL if op in (0x22,0x32,0x36,0x77) else 0xff00+extra if op==0xe0 else 0xff00+r.C if op==0xe2 else extra
   value=extra if op==0x36 else r.A
   if not measuring or not value&128:return
   if at==0xff19:notes.append((p._cycles()+cost,m(1),v('seqposition',1)))
   elif at==0xff14 and v('seqposition')%4:p1_resumes.append(p._cycles()+cost)
  for pc,op,extra,cost in pcm.pulse_write_sites(S):p.hook_register(0,pc,apu_write,(op,extra,cost))
  def irq(_):
   if measuring and v('waveengine')==3 and v('power') and v('mixrunning') and v('mixready',v('mixread')):pcm_ready.append(p._cycles())
  p.hook_register(0,0x50,irq,None)
  def word(n):return v(n)|(v(n,1)<<8)
  hook('seq_pattern_start',lambda _:starts.append((p._cycles(),len(boundaries))))
  hook('mixer_boundary',lambda _:boundaries.append((p._cycles(),m(10)|(m(11)<<8),m(2))))
  hook('seq_pattern_release',lambda _:releases.append(p._cycles()))
  hook('seq_transport',lambda _:transports.append(p._cycles()))
  hook('mixer_input',lambda _:input_entries.append(p._cycles()) if p.memory[p.register_file.SP+7]&16 and m(4)>=30 else None)
  for quant in (0,1,2):
   for same in (True,False):
    p.tick(30);notes.clear();starts.clear();boundaries.clear();releases.clear();transports.clear();input_entries.clear();pcm_ready.clear();p1_resumes.clear()
    target=m(1) if same else 1-m(1);sm(3,quant);sm(4,30+target)
    before_blocks=word('engineblocks');before_drops=word('mixunderruns');measuring=True
    click,ack=press('a');_,navigation_ack=press('right')
    for _ in range(360):
     p.tick(1)
     if starts and m(2)==255 and not v('seqservicing'):break
    assert starts,(length,bpm,quant,same,'launch timeout');p.tick(45);measuring=False
    assert v('param')==target*2,('Incoming pulse tone did not follow saved pattern',length,bpm,quant,same,target,v('param'))
    intervals=[(b[0]-a[0])*1000/CPU for a,b in zip(notes,notes[1:])]
    first=next((n[0] for n in notes if n[0]>=starts[0][0]),None)
    unit=4 if quant==1 else 16
    eligible=[b for b in boundaries[:starts[0][1]] if b[0]>=(input_entries[0] if input_entries else click) and (b[1]+1)%unit==0] if quant else []
    result=dict(length=length,bpm=bpm,quant=('OFF','BEAT','BAR')[quant],same_pattern=same,button_ack_ms=round(ack,3),physical_to_action_entry_ms=round((input_entries[0]-click)*1000/CPU,3) if input_entries else None,click_to_launch_ms=round((starts[0][0]-click)*1000/CPU,3),launch_to_first_p2_ms=round((first-starts[0][0])*1000/CPU,3) if first else None,max_note_interval_ms=round(max(intervals,default=0),3),nominal_step_ms=60000/bpm/4,interval_jitter_ms=round(max(intervals,default=0)-min(intervals,default=0),3),boundaries_before_launch=starts[0][1],eligible_boundaries_passed_before_launch=max(0,len(eligible)-1),release_calls=len(releases),transport_calls=len(transports))
    result['navigation_after_request_ack_ms']=round(navigation_ack,3)
    action=input_entries[0] if input_entries else click
    # Quantized cold launches receive a documented 50ms preparation lead.
    # Any subsequent eligible boundary is a firm release requirement.
    eligible_after_lead=[b for b in eligible if b[0]>=action+(0 if same else 0.05*CPU)]
    missed_after_lead=max(0,len(eligible_after_lead)-1)
    skipped=[(a[2],b[2]) for a,b in zip(notes,notes[1:]) if b[2]!=0 and b[2]!=(a[2]+1)%length]
    result.update(onset_measurement='Actual NRx4 hardware trigger writes',audio_uploads=(word('engineblocks')-before_blocks)&65535,eligible_pcm_uploads=len(pcm_ready),audio_underruns=(word('mixunderruns')-before_drops)&65535,p1_mid_note_restores=len(p1_resumes),skipped_p2_steps=skipped,eligible_boundaries_missed_after_50ms_lead=missed_after_lead,rom_sha256=hashlib.sha256(Path(args.rom).read_bytes()).hexdigest())
    last_boundary=boundaries[starts[0][1]-1] if starts[0][1] else None
    result['quantized_boundary_aligned']=not quant or bool(last_boundary and (last_boundary[1]+1)%unit==0)
    result['physical_to_first_actual_p2_ms']=(first-click)*1000/CPU if first else None
    result['quant_boundary_to_first_actual_p2_ms']=(first-last_boundary[0])*1000/CPU if quant and first and last_boundary else None
    result['failures']=[]
    if quant and not result['quantized_boundary_aligned']:result['failures'].append('launch_not_on_eligible_quantized_boundary')
    if quant and result['quant_boundary_to_first_actual_p2_ms'] is not None and result['quant_boundary_to_first_actual_p2_ms']>FRAME_MS:result['failures'].append('quantized_actual_attack_late_over_one_frame')
    if not quant and (result['physical_to_first_actual_p2_ms'] is None or result['physical_to_first_actual_p2_ms']>50.3):result['failures'].append('OFF_physical_to_actual_sound_over_3_frames')
    if ack>50.3:result['failures'].append('button_ack_over_3_frames')
    if navigation_ack>50.3:result['failures'].append('navigation_ack_over_3_frames')
    if quant==0 and result['click_to_launch_ms']>50.3:result['failures'].append('OFF_launch_over_3_frames')
    if quant and missed_after_lead:result['failures'].append('missed_eligible_quantized_boundary')
    if result['launch_to_first_p2_ms'] is None or result['launch_to_first_p2_ms']>FRAME_MS:result['failures'].append('incoming_attack_over_one_frame')
    if result['max_note_interval_ms']>60000/bpm/4+FRAME_MS:result['failures'].append('audio_interval_extended_over_one_frame')
    if skipped:result['failures'].append('skipped_p2_steps')
    if result['audio_underruns'] or abs(result['audio_uploads']-len(pcm_ready))>1:result['failures'].append('PCM_delivery')
    if not result['p1_mid_note_restores']:result['failures'].append('no_PK_to_sustaining_P1_restore_observed')
    failures.extend((length,bpm,quant,same,f) for f in result['failures'])
    results.append(result);Path(args.output).write_text(json.dumps(results,indent=2));print(json.dumps(result),flush=True)
    assert not transports and v('seqplaying')
 finally:p.stop(save=False)

print(json.dumps({"cases":len(results),"failed_checks":len(failures),"failures":failures},indent=2))
if failures and not args.report_only:raise SystemExit(1)

"""Real A-drag repaint latency with PCM, PK, sustained P1 and actual P2 APU triggers."""
from pathlib import Path
from io import BytesIO
import argparse,json,hashlib,wave
import numpy as np
from pyboy import PyBoy
from boot_helpers import enter_app
from seq_storage_helpers import write_tracks,write_word
import test_pcm_timing as pcm

ap=argparse.ArgumentParser();ap.add_argument('--rom',type=Path,default=Path('build/GAYBOY.gb'));ap.add_argument('--output',default='build/selection-performance.json');ap.add_argument('--report-only',action='store_true');ap.add_argument('--capture',action='store_true');ap.add_argument('--length',type=int,choices=(16,32,64),default=16);ap.add_argument('--track',choices=('pulse','drum'),default='pulse');ap.add_argument('--dense',action='store_true');args=ap.parse_args()
pcm.ROM=args.rom
S={l.split()[1]:int(l.split()[2],16) for l in args.rom.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
CPU=4194304;FRAME_MS=1000/59.7275
p=PyBoy(str(args.rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0);enter_app(p)
def v(n,i=0):return p.memory[S['_'+n]+i]
def put(n,i,x):p.memory[S['_'+n]+i]=x
def hook(n,fn):
 a=S['_'+n];p.hook_register(a>>16,a&65535,fn,None)
def button(key,mask):
 p.button_press(key)
 for _ in range(600):
  tick(1)
  if v('lastpad')&mask:break
 assert v('lastpad')&mask
 p.button_release(key)
 for _ in range(600):
  tick(1)
  if not v('lastpad')&mask:break
 tick(2)
def choose(n):
 p.button_press('start')
 for _ in range(600):
  tick(1)
  if v('navopen'):break
 for _ in range(32):
  if v('navchoice')==n:break
  button('down',8)
 assert v('navchoice')==n
 p.button_release('start');tick(120);assert v('page')==n
p2=[];eligible=[];pending={};gestures=[];measuring=False;audio=[];tapping=False;input_trace=[];selection_profiles=[];return_hooks={}
def tick(frames):
 if args.capture and measuring:
  for _ in range(frames):p.tick(1);audio.append(p.sound.ndarray.copy())
 else:p.tick(frames)

def apu_write(site):
 op,extra,cycles=site;r=p.register_file
 target=(r.B<<8)|r.C if op==0x02 else (r.D<<8)|r.E if op==0x12 else r.HL if op in (0x22,0x32,0x36,0x77) else 0xff00+extra if op==0xe0 else 0xff00+r.C if op==0xe2 else extra
 value=extra if op==0x36 else r.A
 if measuring and target==0xff19 and value&128:p2.append((p._cycles()+cycles,v('seqposition',1)))
def timer(_):
 if measuring and v('waveengine')==3 and v('power') and v('mixrunning') and v('mixready',v('mixread')):eligible.append(p._cycles())
def flushed(_):
 if measuring:selection_entered(None,'ui_flush')
 if pending and pending.get('flush') is None and tuple(v(n) for n in ('seqgroupx0','seqgroupx1','seqgroupy0','seqgroupy1'))!=pending['prior']:pending['flush_started']=p._cycles()
hook('ui_flush',flushed)
def input_seen(_):
 if tapping:
  sp=p.register_file.SP
  input_trace.append({'cycles':p._cycles(),'p':p.memory[sp+6],'edge':p.memory[sp+7],'lastpad':v('lastpad'),'cursor':v('seqcursor',6 if args.track=='drum' else 0),'read':v('padread'),'write':v('padwrite')})
hook('ui_input',input_seen)
def selection_entered(_,name='roll_selection_update'):
 if not measuring:return
 sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;bank=p.memory[0xff90] if 0x4000<=ret<0x8000 else 0
 item={'visual_key':pending.get('start') if name=='ui_flush' and pending and pending.get('flush') is None and tuple(v(n) for n in ('seqgroupx0','seqgroupx1','seqgroupy0','seqgroupy1'))!=pending['prior'] else None,'name':name,'start':p._cycles(),'gesture':len(gestures),'fontdirty':v('seqfontdirty'),'cache_marker':v('rollcache'),'drawvalid':v('seqdrawvalid'),'returned':None,'duration_ms':None};selection_profiles.append(item)
 key=(bank,ret)
 if key not in return_hooks:
  return_hooks[key]=[];p.hook_register(bank,ret,lambda k:[f() for f in list(return_hooks[k])],key)
 def returned():
  if item['returned'] is None and p.register_file.SP==sp+2:
   item['returned']=p.register_file.A;item['duration_ms']=(p._cycles()-item['start'])*1000/CPU
   if item['visual_key'] is not None and pending.get('start')==item['visual_key'] and pending.get('flush') is None:pending['flush']=p._cycles()
 return_hooks[key].append(returned)
if '_roll_selection_update' in S:hook('roll_selection_update',selection_entered)
for name in ('seq_render','roll_commit','drum_velocity_render'):
 if '_'+name in S:hook(name,lambda _,n=name:selection_entered(None,n))
for pc,op,extra,cycles in pcm.pulse_write_sites(S):p.hook_register(0,pc,apu_write,(op,extra,cycles))
p.hook_register(0,0x50,timer,None)
try:
 choose(8)
 tracks=[[] for _ in range(7)]
 tracks[0]=[[s,61+s%8,100,4] for s in range(0,args.length,1 if args.dense else 4)]
 tracks[1]=[[s,68+s%3,100,1] for s in range(args.length)]
 tracks[6]=[[s,1 if s%8==0 else 4,127,4] for s in range(0,args.length,4)]+[[s,13,127,1] for s in range(1,args.length,4)]
 write_tracks(p,S,tracks)
 for c in range(7):write_word(p,S['_seqlength']+c*2,args.length)
 write_word(p,S['_seqbpm'],180);put('seqgate',1,100);put('seqtrack',0,6 if args.track=='drum' else 0);put('seqcursor',6 if args.track=='drum' else 0,0);put('drumrow',0,12);put('seqpitch',0,59);put('seqtop',0,71);put('seqhead',0,0);put('seqgrouptrack',0,255);put('seqdrawvalid',0,0);put('dirty',0,1);tick(120)
 p.button_press('select');tick(5);button('a',16);p.button_release('select');tick(30);assert v('seqplaying')
 put('seqcursor',6 if args.track=='drum' else 0,0);put('drumrow',0,12);put('seqpitch',0,59);put('seqtop',0,71);put('seqhead',0,0);put('dirty',0,1);tick(120)
 before=v('engineblocks')|(v('engineblocks',1)<<8);drops=v('mixunderruns')|(v('mixunderruns',1)<<8);measuring=True
 p.button_press('a');tick(5)
 for key,mask in [('right',1)]*4+[('up',4)]*4+[('down',8)]*2+[('left',2)]*2:
  prior=tuple(v(n) for n in ('seqgroupx0','seqgroupx1','seqgroupy0','seqgroupy1'));pending.clear();pending['start']=p._cycles();pending['prior']=prior;pending['logical']=None;pending['flush']=None;ack=None
  p.button_press(key)
  for _ in range(600):
   tick(1)
   if ack is None and v('lastpad')&mask:ack=p._cycles()
   if pending['logical'] is None and tuple(v(n) for n in ('seqgroupx0','seqgroupx1','seqgroupy0','seqgroupy1'))!=prior:pending['logical']=p._cycles()
   if pending['flush'] is not None and ack is not None:break
  assert pending['flush'] is not None,(key,prior,pending)
  gestures.append({'key':key,'ack_ms':(ack-pending['start'])*1000/CPU,'logical_ms':(pending['logical']-pending['start'])*1000/CPU,'render_ready_ms':(pending.get('flush_started',pending['flush'])-pending['start'])*1000/CPU,'visual_ms':(pending['flush']-pending['start'])*1000/CPU})
  if args.capture:p.screen.image.save(str(Path(args.output).with_name('selection-gesture-%02d.png'%(len(gestures)-1))))
  p.button_release(key)
  for _ in range(600):
   tick(1)
   if not v('lastpad')&mask:break
  tick(2)
 p.button_release('a');tick(30)
 pending.clear()
 # Queue one-frame press/release taps while A stays held. The VBlank input
 # producer must retain these transitions even if foreground drawing is busy.
 tr=6 if args.track=='drum' else 0
 put('seqgrouptrack',0,255);put('seqapending',0,0);put('seqcursor',tr,0);put('seqpitch',0,59);put('drumrow',0,12);put('seqhead',0,0);put('seqdrawvalid',0,0);put('dirty',0,1);tick(120)
 tapping=True
 p.button_press('a');tick(1)
 for direction in ['right']*8+['up']*4:
  p.button_press(direction);tick(1);p.button_release(direction);tick(1)
 for _ in range(600):
  tick(1)
  if v('padread')==v('padwrite') and not v('dirty') and v('seqcursor',tr)==8 and (v('drumrow') if tr==6 else v('seqpitch'))==(8 if tr==6 else 63):break
 tapping=False
 tap_state={'cursor':v('seqcursor',tr),'pitch_or_row':v('drumrow') if tr==6 else v('seqpitch'),'queue_empty':v('padread')==v('padwrite')}
 taps_preserved=tap_state['cursor']==8 and tap_state['pitch_or_row']==(8 if tr==6 else 63) and tap_state['queue_empty']
 p.button_release('a');tick(30);measuring=False
 after=v('engineblocks')|(v('engineblocks',1)<<8);afterdrops=v('mixunderruns')|(v('mixunderruns',1)<<8)
 assert v('seqgrouptrack')==(6 if args.track=='drum' else 0)
 intervals=[(b[0]-a[0])*1000/CPU for a,b in zip(p2,p2[1:])]
 skipped=[(a[1],b[1]) for a,b in zip(p2,p2[1:]) if b[1]!=(a[1]+1)%args.length]
 # Compare the settled incremental image against a full renderer of identical
 # musical and selection state. Freeze transport only after audio measurement.
 put('seqplaying',0,0);put('dirty',0,1);tick(120);incremental=p.screen.ndarray.copy();p.screen.image.save('build/selection-performance-incremental.png')
 put('seqdrawvalid',0,0);put('dirty',0,1);tick(120);full=p.screen.ndarray.copy();p.screen.image.save('build/selection-performance-full.png')
 pixel_diff=int(np.any(incremental!=full,axis=2).sum())
 result={'rom_sha256':hashlib.sha256(args.rom.read_bytes()).hexdigest(),'model':'DMG','bpm':180,'length':args.length,'track':args.track,'dense':args.dense,'workload':' sustained P1 + PK + alternating real PCM samples 1/4 + P2 each step; held A rectangle drag','gestures':gestures,'max_ack_ms':max(g['ack_ms'] for g in gestures),'max_visual_ms':max(g['visual_ms'] for g in gestures),'actual_p2_trigger_count':len(p2),'p2_interval_max_ms':max(intervals),'nominal_step_ms':60000/180/4,'skipped_p2_steps':skipped,'audio_uploads':(after-before)&65535,'eligible_pcm_uploads':len(eligible),'audio_underruns':(afterdrops-drops)&65535,'selection_full_render_pixel_difference':pixel_diff,'one_frame_taps':tap_state,'one_frame_taps_preserved':taps_preserved,'tap_input_trace':input_trace,'selection_profiles':selection_profiles,'limits':{'button_ack_ms':50.3,'visual_ms':50.3,'max_extra_note_interval_ms':FRAME_MS}}
 result['passes']=result['max_ack_ms']<=50.3 and result['max_visual_ms']<=50.3 and not skipped and max(intervals)<=60000/180/4+FRAME_MS and result['audio_underruns']==0 and abs(result['audio_uploads']-len(eligible))<=1 and pixel_diff==0 and taps_preserved
 if audio:
  with wave.open(str(Path(args.output).with_suffix('.wav')),'wb') as wav:
   wav.setparams((2,2,p.sound.sample_rate,0,'NONE','not compressed'));wav.writeframes((np.concatenate(audio).astype(np.int16)*256).astype('<i2').tobytes())
 Path(args.output).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 if not result['passes'] and not args.report_only:raise SystemExit(1)
finally:p.stop(save=False)

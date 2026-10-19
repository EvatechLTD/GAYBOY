"""Forced-DMG two-PCM plus P1/P2 timing and complete Timer IRQ CPU budget."""
from pathlib import Path
import argparse
import hashlib
import json
import statistics
import ast
import pyboy
from seq_storage_helpers import write_tracks,write_word
ROM=Path('build/GAYBOY.gb')
HARDWARE_DEMO=False

def pulse_write_sites(symbols):
 rom=ROM.read_bytes()
 tree=ast.parse((Path(pyboy.__file__).parent/"core/opcodes.py").read_text())
 lengths=next(ast.literal_eval(n.value.args[1]) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="OPCODE_LENGTHS" for t in n.targets))
 sites=[]
 for name in ('_play','_seq_irq_tick','_seq_native_hardware'):
  if name not in symbols:continue
  pc=symbols[name]
  end=min(v for k,v in symbols.items() if k.startswith("_") and pc<v<0x4000)
  while pc<end:
   op=rom[pc];length=2 if op==0xcb else lengths[op]
   if op in (0x02,0x12,0x22,0x32,0x36,0x77,0xe0,0xe2,0xea):
    extra=rom[pc+1] if length>1 else 0
    if op==0xea:extra|=rom[pc+2]<<8
    cycles=16 if op==0xea else 12 if op in (0x36,0xe0) else 8
    sites.append((pc,op,extra,cycles))
   assert length>0,(pc,op)
   pc+=length
 return sites

def pulse_position(p,symbols,channel):
 # IRQ attacks can precede foreground cursor bookkeeping. Attribute the
 # actual hardware write to its published target step in that path only.
 start=symbols.get('_seq_irq_tick')
 if start is not None:
  end=min(v for k,v in symbols.items() if k.startswith('_') and start<v<0x4000)
  if start<=p.register_file.PC<end:
   return p.memory[symbols['_seqirqstep']+channel]
 return p.memory[symbols['_seqposition']+channel]

CPU_HZ=4194304
BLOCK_CYCLES=11712
SAMPLE_HZ=CPU_HZ/(2*183)

def run(scroll,frames=360,view="sequencer",control=None):
 env={}
 source=Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
 source=source.replace('build/GAYBOY.noi',ROM.with_suffix('.noi').as_posix()).replace('build/GAYBOY.gb',ROM.as_posix())
 if HARDWARE_DEMO:source=source.replace(';enter_app(p)',';p.tick(180)')
 source=source.replace(';enter_app(p)',';enter_app(p,S)')
 source=source.replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file=')
 exec(source,env)
 if HARDWARE_DEMO:env['send']([0xb0,103,127])
 p,S,v,word,press,choose=(env[k] for k in ('p','S','v','word','press','choose'))
 def put(n,i,x):p.memory[S['_'+n]+i]=x
 callbacks={}
 def hook(bank,addr,fn,ctx=None):
  key=(bank,addr)
  if key not in callbacks:
   callbacks[key]=[]
   p.hook_register(bank,addr,lambda k:[f(c) for f,c in list(callbacks[k])],key)
  callbacks[key].append((fn,ctx))
 irqs=[];irqstack=[];starts=[];eligible_uploads=[];idle_periods=[];priming_periods=[];tail_periods=[];p1=[];p2=[];first=[None,None];measurement=[None]
 entry_first=[None,None];startup=[];irq_onsets=[0,0]
 def irq_return(_):
  if irqstack and irqstack[-1][1]==p.register_file.SP:
   start,_,two=irqstack.pop()
   if measurement[0] is not None and start>=measurement[0]:irqs.append((p._cycles()+16-start,two))
 def irq_start(_):
  if v('waveengine')!=3 or not v('seqplaying'):return
  # At the vector the only stack word is the hardware-pushed interrupted PC.
  # The common dispatcher restores that exact SP immediately before RETI.
  begin=p._cycles()-20
  irqstack.append((begin,p.register_file.SP,bool(v('drumon') and v('drumon',1))))
  if measurement[0] is not None and begin>=measurement[0]:
   starts.append(begin)
   # A stopped/finished source intentionally uploads nothing. At IRQ entry,
   # a prepared block is the exact production condition for an upload.
   if v('power') and v('mixrunning'):
    (eligible_uploads if v('mixready',v('mixread')) else tail_periods if v('drumtail') else priming_periods).append(begin)
   else:idle_periods.append(begin)
 def played(_):
  c=p.register_file.A
  if c<2 and entry_first[c] is None:entry_first[c]=p._cycles()
 def apu_write(site):
  op,extra,cycles=site;r=p.register_file
  target=(r.B<<8)|r.C if op==0x02 else (r.D<<8)|r.E if op==0x12 else r.HL if op in (0x22,0x32,0x36,0x77) else 0xff00+extra if op==0xe0 else 0xff00+r.C if op==0xe2 else extra
  value=extra if op==0x36 else r.A
  if target not in (0xff14,0xff19) or not value&128:return
  c=target==0xff19;when=p._cycles()+cycles
  start=S.get('_seq_irq_tick')
  if measurement[0] is not None and start is not None:
   end=min(x for k,x in S.items() if k.startswith('_') and start<x<0x4000)
   if start<=p.register_file.PC<end:irq_onsets[c]+=1
  if c==0:
   if first[0] is None:first[0]=when
   if measurement[0] is not None:p1.append((when,pulse_position(p,S,0)))
  else:
   if first[1] is None and pulse_position(p,S,1)==1:first[1]=when
   if measurement[0] is not None:p2.append((when,pulse_position(p,S,1)))
 def startup_seen(name):
  if first[1] is None:startup.append((name,p.register_file.A,p._cycles(),word('seqticks'),word('seqclock'),v('waveengine')))
 try:
  assert p.memory[0xff4d]==255
  choose(8);p.tick(90)
  tracks=[[] for _ in range(7)]
  for c in range(7):write_word(p,S['_seqlength']+c*2,16)
  put('seqbpm',0,300&255);put('seqbpm',1,300>>8)
  for s in range(16):
   tracks[0].append([s,61+s%4,100,1])
   if s:tracks[1].append([s,68+s%4,100,1])
  # Two prepared PCM samples exceed200ms, keeping both voices busy.
  for s in range(0,16,4):
   for sample in (4,10):tracks[6].append([s,sample,127,4])
  write_tracks(p,S,tracks)
  dispatch=ROM.read_bytes()[0x80:0xa0]
  reti=0x80+dispatch.index(bytes([0xd9]));assert reti==0x9b
  hook(0,reti,irq_return)
  hook(0,0x50,irq_start)
  addr=S['_play'];hook(0,addr,played)
  for pc,op,extra,cycles in pulse_write_sites(S):hook(0,pc,apu_write,(op,extra,cycles))
  for name in ('seq_transport','seq_fire','drum_fire','drum_enable','seq_gates','seq_frame','seq_next_deadline','mixer_boundary','seq_off','drum_tick'):
   addr=S['_'+name];hook(addr>>16 if addr>=65536 else 0,addr&65535,startup_seen,name)
  if view=="mixer":
   choose(18);p.tick(60);assert v('page')==18
   # Use the real Mixer transport button, with P1 volume/pan selected afterward.
   press('a')
  else:
   p.button_press('select');p.tick(5);press('a');p.button_release('select');p.tick(12)
  assert v('seqplaying') and v('waveengine')==3
  assert first[0] is not None and first[1] is not None
  first_interval=(first[1]-first[0])*1000/CPU_HZ
  p1.clear();p2.clear();irqs.clear();starts.clear()
  before=word('engineblocks');drops=word('mixunderruns');measurement[0]=p._cycles()
  if view=="mixer" and control:
   p.memory[S['_mx']+4]=4 if control=="volume" else 5
   if control=="volume":p.memory[S['_mx']+12]=100
   p.button_press('b')
   direction=None
   for frame in range(frames):
    # Pan alternates3/2; volume makes longer held gestures around100, keeping
    # both pulse voices audible rather than saturating a field or muting it.
    period=45 if control=="volume" else 12
    key='down' if (frame//period)&1==0 else 'up'
    if key!=direction:
     if direction:p.button_release(direction)
     p.button_press(key);direction=key
    p.tick(1)
   if direction:p.button_release(direction)
   p.button_release('b')
  else:
   if scroll:p.button_press('right')
   p.tick(frames)
   if scroll:p.button_release('right')
  elapsed=p._cycles()-measurement[0]
  assert len(p1)>=frames//4 and len(irqs)>frames
  for i,(_,pos) in enumerate(p1):assert pos==(p1[0][1]+i)%16,('skipped pulse step',i,pos,p1[max(0,i-3):i+2])
  residual=[t-(p1[0][0]+i*CPU_HZ/20) for i,(t,_) in enumerate(p1)]
  mean=statistics.mean(residual)
  samples=[cost for cost,_ in irqs];two=[cost for cost,both in irqs if both]
  intervals=[b[0]-a[0] for a,b in zip(p1,p1[1:])]
  result={
   'model':'DMG forced cgb=False','clock_hz':CPU_HZ,'sample_rate_hz':SAMPLE_HZ,
   'block_cycles':BLOCK_CYCLES,'bpm':300,'frames':frames,
   'ui':('Mixer held '+control if control else 'Mixer idle') if view=='mixer' else 'held right / viewport redraws' if scroll else 'idle sequencer',
   'onset_measurement':'Actual NRx4 hardware trigger writes',
   'first_p1_to_p2_step1_ms':first_interval,
   'first_play_entry_interval_ms':None if None in entry_first else (entry_first[1]-entry_first[0])*1000/CPU_HZ,
   'startup_trace_ms':[(n,c,(t-first[0])*1000/CPU_HZ,ticks,clock,engine) for n,c,t,ticks,clock,engine in startup],
   'pulse1_onsets':len(p1),
    'irq_pulse1_onsets':irq_onsets[0],
    'irq_pulse2_onsets':irq_onsets[1],'expected_pulse1_onsets':elapsed/(CPU_HZ/20),
   'pulse1_interval_ms_min':min(intervals)*1000/CPU_HZ,
   'pulse1_interval_ms_max':max(intervals)*1000/CPU_HZ,
   'pulse1_phase_jitter_ms_peak_to_peak':(max(residual)-min(residual))*1000/CPU_HZ,
   'pulse1_phase_jitter_ms_rms':(statistics.mean((x-mean)**2 for x in residual)**.5)*1000/CPU_HZ,
   'full_irq_count':len(samples),'full_irq_cycles_min':min(samples),
   'full_irq_cycles_mean':statistics.mean(samples),'full_irq_cycles_max':max(samples),
   'two_voice_irq_count':len(two),'two_voice_irq_cycles_max':max(two) if two else None,
   'full_irq_cpu_percent':sum(samples)*100/elapsed,
   'worst_irq_budget_percent':max(samples)*100/BLOCK_CYCLES,
   'audio_blocks':(word('engineblocks')-before)&65535,
   'expected_audio_blocks':len(eligible_uploads),
   'elapsed_timer_periods':elapsed/BLOCK_CYCLES,
   'intentional_idle_timer_periods':len(idle_periods),
   'priming_timer_periods':len(priming_periods),
   'tail_stop_timer_periods':len(tail_periods),
   'audio_underruns':(word('mixunderruns')-drops)&65535,
   'pending_clock_units_end':word('seqticks'),
  }
  result['meets_first_step_target']=35<=first_interval<=58
  result['meets_irq_budget']=max(samples)<BLOCK_CYCLES
  result['meets_audio_delivery']=result['audio_underruns']==0 and abs(result['audio_blocks']-result['expected_audio_blocks'])<3
  result['meets_note_rate']=abs(result['pulse1_onsets']-result['expected_pulse1_onsets'])<2
  return result
 finally:p.stop(save=False)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--frames',type=int,default=360)
 parser.add_argument('--output',default='build/pcm-timing-final.json')
 parser.add_argument('--mixer-only',action='store_true')
 parser.add_argument('--rom',type=Path,default=ROM)
 parser.add_argument('--hardware-demo',action='store_true',help='Boot an intro-skipped autoplay fixture, then panic before testing')
 args=parser.parse_args();results=[];ROM=args.rom;HARDWARE_DEMO=args.hardware_demo
 cases=[(False,'mixer',None),(False,'mixer','volume'),(False,'mixer','pan')]
 if not args.mixer_only:cases=[(False,'sequencer',None),(True,'sequencer',None)]+cases
 for scroll,view,control in cases:
  try:results.append(run(scroll,args.frames,view,control))
  except AssertionError as e:results.append({'ui':'scroll' if scroll else 'idle','failure':str(e)})
 report={'rom_sha256':hashlib.sha256(ROM.read_bytes()).hexdigest(),'limitations':'Cycle-budget emulation, not physical or analog hardware validation. Full IRQ includes hardware acknowledge, vector/dispatcher, audio transfer and sample mixing.', 'results':results}
 Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 if any('failure' in r or not all(r[k] for k in ('meets_first_step_target','meets_irq_budget','meets_audio_delivery','meets_note_rate')) for r in results):raise SystemExit(1)


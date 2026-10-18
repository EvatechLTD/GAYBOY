import faulthandler
faulthandler.enable()
faulthandler.dump_traceback_later(60, exit=True)
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].replace('range(60)','range(240)'))
p.tick(200)
# This regression compares the preserved Amen source; factory boot may use 808.
choose(23)
while v('kitchoice'):press('up')
press('a');assert v('drumkit')==0
assert not v('experimental_mode'),'Hardware and sample mode should be the startup default'
def put(n,i,x):fixture_put(p,S,n,i,x)
def chord(mod,k):
 p.button_press(mod);p.tick(5);press(k);p.button_release(mod);p.tick(8)
def wait():p.tick(100)
def clear_drums():
 from seq_storage_helpers import read_tracks,write_tracks
 tracks=read_tracks(p,S);tracks[6]=[];write_tracks(p,S,tracks)
choose(8);chord('select','left');assert v('seqtrack')==6
wait();assert not v('seqtileoverflow')
press('b');assert v('drumhits')==1
# First sample occupies multiple cells; place another row at the same onset.
press('down');press('b');assert v('drumhits',1)==2
# A third overlapping sample replaces the most recently plotted hit.
press('down');press('b');assert sorted([v('drumhits'),v('drumhits',1)])==[1,3]
# Distinct time onsets whose tails overlap also evict the newest.
press('down');press('right');p.button_press('b');p.tick(5);press('right');p.button_release('b');p.tick(8);assert v('seqdefaultdur',6)>=2
press('right');press('down');press('b')
for t in range(64):
 active=[i for i in range(128) if v('drumhits',i) and i//2<=t<i//2+v('drumdur',i)]
 assert len(active)<=2,(t,active)
p.screen.image.save('build/ui-drum-roll.png')
# Note edits retain immutable grid tiles: repeatedly add/delete without flashing.
clear_drums()
put('seqdrawvalid',0,0);put('dirty',0,1);wait()
uploads=[];a=S['_set_bkg_data'];p.hook_register(0,a,lambda _:uploads.append(p.frame_count),None)
editwrites=[]
for _ in range(40):
 before=len(uploads);press('b');editwrites.append(len(uploads)-before)
 assert not v('seqtileoverflow')
assert max(editwrites)<10,editwrites
print('DRUM VRAM tile uploads per edit:',max(editwrites),flush=True)
p.hook_deregister(0,S['_set_bkg_data'])
# Exercise all zooms with dense hits; a full kit must stay within the 120-tile pool.
for i in range(128):
 put('drumhits',i,(i%10)+1);put('drumvel',i,127);put('drumdur',i,1)
put('seqdrawvalid',0,0);put('dirty',0,1);wait()
chord('select','up');wait()
for _ in range(4):
 assert not v('seqtileoverflow'),(v('seqzoom'),v('seqtilecount'))
 chord('select','down');wait()
# Populate known two-sample chord and inspect the actual pre-packed audio samples.
clear_drums()
for i,sample in enumerate((1,4)):
 put('drumhits',i,sample);put('drumvel',i,127);put('drumdur',i,4)
blocks=[];previous=[None];mixstart=[];mixcost=[];twocost=[];packtimes=[];heard=[]
def mix_begin(_):mixstart.append((p._cycles(),bool(v('drumon') and v('drumon',1))))
def mix_end(_):
 if mixstart:
  when,two=mixstart.pop();cost=p._cycles()-when;mixcost.append(cost)
  if two:twocost.append(cost)
a=S['_drum_mix'];p.hook_register(a>>16,a&65535,mix_begin,None)
a=S['_drum_duration']-1
assert p.memory[a>>16,a&65535]==0xc9
p.hook_register(a>>16,a&65535,mix_end,None)
source=[];firstraw=[True];source_errors=[]
import wave
for name in ('KK1','SC1'):
 with wave.open('breaks/AMEN172chop/processed-lsdj/'+name+'.wav','rb') as f:
  x=((np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(np.int32)+32768)>>12).astype(np.uint8)
  x=np.pad(x,(0,(-len(x))%32),constant_values=8);x=np.roll(x.reshape(-1,32),1,axis=1).reshape(-1);source.append(((x[::2]<<4)|x[1::2]).tolist())
def packed(_):
 heard.append(p.sound.ndarray.copy())
 packtimes.append(p._cycles())
 if previous[0] is not None:
  slot,expected=previous[0]
  assert [v('mixbuffer',slot*16+i) for i in range(16)]==expected
  blocks.append(expected)
 raw=[[v('drumraw',c*16+i) for i in range(16)] for c in range(2)]
 expected=[]
 for i in range(16):
  a,b=raw[0][i],raw[1][i]
  expected.append(((((a>>4)+(b>>4))//2)<<4)|(((a&15)+(b&15))//2))
 if v('drumpackmask')!=3:expected=raw[1] if v('drumpackmask')==2 else raw[0]
 previous[0]=(v('mixwrite'),expected)
 # First block must match the antialiased 11468 Hz input, with only 4-bit quantization.
 if firstraw[0]:
  firstraw[0]=False
  if raw[0]!=source[0][:16] or raw[1]!=source[1][:16]:source_errors.append((raw,[x[:16] for x in source],[v('drumbankvoice',c) for c in range(2)]))
a=S['_drum_pack'];p.hook_register(a>>16,a&65535,packed,None)
# Verify the actual executed CPU writes, including all four CH3 pan states.
# PyBoy models registers and PCM, but this does not validate DMG analog spikes.
rom=Path('build/GAYBOY.gb').read_bytes()
timer_symbol=S['_drum_timer'];timer_bank=timer_symbol>>16;timer_pc=timer_symbol&65535
physical=timer_bank*16384+(timer_pc&16383)
timer_code=rom[physical:physical+((S['_drum_irq']&65535)-timer_pc)]
mask_pattern=bytes.fromhex('f0 25 f5 e6 bb e0 25 af e0 1a')
mask_at=timer_code.index(mask_pattern)
trigger_at=timer_code.index(bytes.fromhex('e0 1e f1 e0 25'),mask_at)
route_state=[None];route_errors=[];route_blocks=[]
test_routes=[0xbf,0xfb,0xff,0xbb,0x2d,0x69,0x6d,0x29]
def route_check(ok,detail):
 if not ok and len(route_errors)<10:route_errors.append(detail)
def route_begin(_):
 if len(route_blocks)<len(test_routes):p.memory[0xff25]=test_routes[len(route_blocks)]
 route_state[0]={'saved':p.memory[0xff25],'writes':0,'triggered':False}
def route_off(_):
 q=route_state[0];route_check(q is not None,'DAC off without saved routing')
 if q:
  route_check(p.register_file.A==0,'DAC off value')
  route_check(p.memory[0xff25]==q['saved']&0xbb,('routing before DAC off',q,p.memory[0xff25]))
def wave_write(address):
 q=route_state[0]
 if q is None:return
 route_check(p.memory[0xff25]==q['saved']&0xbb,('routing during wave write',q,p.memory[0xff25]))
 route_check(not p.memory[0xff1a]&128,'wave write while DAC enabled')
 route_check(address==0x30+q['writes'],('wave address order',address,q['writes']))
 q['writes']+=1
def route_trigger(_):
 q=route_state[0]
 if q:
  route_check(q['writes']==16,('trigger before 16 wave bytes',q))
  route_check(p.memory[0xff25]==q['saved']&0xbb,'CH3 routed during trigger')
  route_check(p.register_file.A==0x87 and p.memory[0xff1a]&128,'invalid DAC/retrigger state')
  q['triggered']=True
def route_restore(_):
 q=route_state[0]
 if q:
  route_check(q['triggered'],'routing restored before trigger')
  route_check(p.register_file.A==q['saved'],('saved pan changed',q,p.register_file.A))
  route_check(p.memory[0xff25]==q['saved']&0xbb,'other channel routing changed')
def route_done(_):
 q=route_state[0]
 if q:
  route_check(p.memory[0xff25]==q['saved'],('routing restore mismatch',q,p.memory[0xff25]))
  route_blocks.append(q['saved']);route_state[0]=None
for offset,callback in [(mask_at,route_begin),(mask_at+8,route_off),(trigger_at,route_trigger),(trigger_at+3,route_restore),(trigger_at+5,route_done)]:
 p.hook_register(timer_bank,timer_pc+offset,callback,None)
wave_offsets=[(i+1,timer_code[i+2]) for i in range(mask_at+10,trigger_at-2) if timer_code[i:i+2]==bytes.fromhex('2a e0') and 0x30<=timer_code[i+2]<=0x3f]
assert len(wave_offsets)==16
for offset,address in wave_offsets:p.hook_register(timer_bank,timer_pc+offset,wave_write,address)
b=word('engineblocks');u=word('mixunderruns')
chord('select','a');assert v('seqplaying') and v('waveengine')==3
audio=[]
for _ in range(40):p.tick(1);audio.append(p.sound.ndarray.copy())
assert word('engineblocks')>b and blocks and np.ptp(np.array(blocks))>3
assert np.ptp(np.concatenate(heard+audio).astype(float))>0
print('Drum block/drop delta:',word('engineblocks')-b,word('mixunderruns')-u)
print('PCM mix cycles min/mean/max:',min(mixcost),round(sum(mixcost)/len(mixcost)),max(mixcost))
print('Two active PCM voice cycles min/mean/max:',min(twocost),round(sum(twocost)/len(twocost)),max(twocost))
assert max(mixcost)<11712,mixcost
assert word('mixunderruns')==u
assert abs((packtimes[-1]-packtimes[0])-(len(packtimes)-1)*11712)<11712*3
print('PCM duration seconds:',round((packtimes[-1]-packtimes[0])/4194304,4))
# Check the fractional sequencer clock at the new hardware period independently
# of foreground consumption: every interrupt contributes exactly 183/64 units.
put('seqservicing',0,1);p.tick(1)
clock_before=word('seqticks')*64+v('seqfraction');clock_irqs=[]
a=S['_drum_timer'];p.hook_register(a>>16,a&65535,lambda _:clock_irqs.append(p._cycles()),None)
p.tick(6)
clock_after=word('seqticks')*64+v('seqfraction')
assert abs((clock_after-clock_before)-183*len(clock_irqs))<=183
put('seqservicing',0,0)
p.hook_deregister(S['_drum_timer']>>16,S['_drum_timer']&65535)
print('PCM fractional clock:',len(clock_irqs),'interrupts,',round((clock_after-clock_before)/64,3),'sequencer units')
# Measurements are complete; remove opcode hooks before later mode transitions.
for address in (S['_drum_mix'],S['_drum_duration']-1,S['_drum_pack']):
 p.hook_deregister(address>>16,address&65535)
for offset in [mask_at,mask_at+8,trigger_at,trigger_at+3,trigger_at+5]+[x[0] for x in wave_offsets]:
 p.hook_deregister(timer_bank,timer_pc+offset)
chord('select','a');assert not v('seqplaying') and not any(v('drumon',i) for i in range(2))
# Exercise later samples and any additional sample bank, still without waveform processing.
source.clear()
for name in ('KC1','PSH'):
 with wave.open('breaks/AMEN172chop/processed-lsdj/'+name+'.wav','rb') as f:
  x=((np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(np.int32)+32768)>>12).astype(np.uint8)
  x=np.pad(x,(0,(-len(x))%32),constant_values=8);x=np.roll(x.reshape(-1,32),1,axis=1).reshape(-1);source.append(((x[::2]<<4)|x[1::2]).tolist())
for i,sample in enumerate((8,10)):put('drumhits',i,sample)
firstraw[0]=True;previous[0]=None;u=word('mixunderruns')
chord('select','a');p.tick(60)
assert word('mixunderruns')==u
for sample,expected in zip((7,9),source):
 bank=p.memory[S['_amenbank']>>16,(S['_amenbank']&65535)+sample]
 at=S['_amenoffset'];offset=p.memory[at>>16,(at&65535)+sample*2]|p.memory[at>>16,(at&65535)+sample*2+1]<<8
 base=S['_drumdata'+str(bank)]&65535
 assert list(p.memory[bank,base+offset:base+offset+len(expected)])==expected
assert not source_errors,source_errors
print('All-bank source bytes and hook-free two-voice playback: PASS')
assert not route_errors,route_errors
assert len(route_blocks)>=100 and set(x&0x44 for x in route_blocks)=={0,4,64,68}
print('PCM register order:',len(route_blocks),'blocks; route off,16 wave bytes,trigger,exact pan restore')
chord('select','a')
# Drum proof playback owns CH3 and excludes all DDS oscillators.
assert not any(v('softon',i) for i in range(2))
# Two independent native noise rows blend their register controls on overlap.
clear_drums()
for i in range(2):put('noisehits',i,1);put('noisevel',i,127);put('noisedur',i,4)
chord('select','a');p.tick(3)
a=[v('noisepatch',i) for i in range(5)];b=[v('noisepatch',5+i) for i in range(5)]
mean=[(x+y+1)//2 for x,y in zip(a,b)]
assert p.memory[0xff22]==(mean[1]<<4)|(mean[3]<<3)|mean[2]
assert p.memory[0xff21]&7==mean[4]
chord('select','a');choose(17);assert v('page')==17
old=v('noisepatch');press('right');assert v('noisepatch')==old+1
press('select');assert v('drumsynthvoice')==1
p.screen.image.save('build/ui-drumsynth.png')
# PCM and all twelve drum rows remain available with experimental DSP off/on.
for mode in (1,0):
 choose(16);press('a');assert v('experimental_mode')==mode
 choose(8)
 if v('seqtrack')!=6:chord('select','left')
 wait();assert v('seqtrack')==6 and v('seqrows')==12 and v('seqheight')==8
 put('drumrow',0,0);put('dirty',0,1);press('down');assert v('drumrow')==1
 press('up');assert v('drumrow')==0
 clear_drums()
 put('drumhits',0,10);put('drumvel',0,127);put('drumdur',0,4)
 previous[0]=None;b=word('engineblocks');u=word('mixunderruns')
 chord('select','a')
 for frame in range(30):
  p.tick(1)
 assert v('waveengine')==3 and word('engineblocks')>b and word('mixunderruns')==u
 chord('select','a')
assert not route_errors,route_errors
p.screen.image.save('build/ui-native-drum-roll.png')
faulthandler.cancel_dump_traceback_later()
p.stop(save=False)
print('PASS: all drum rows/zooms, newest overlap replacement, prepared PCM, two-voice mixing, safe DAC register order, noise averaging, samples with DSP off/on')

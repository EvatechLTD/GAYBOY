"""All native channels, simultaneous arps, PCM ownership and LFO fallback."""
from pathlib import Path
from io import BytesIO
exec(Path('tools/test_arp_stress.py').read_text().split('reports=[]')[0])
p.stop(save=False)
for target,pcm in ((0,False),(1,False),(2,False),(2,True)):
 p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(args.save.read_bytes()));p.set_emulation_speed(0)
 attacks=[];frequencies=[];hook_attacks(p,rom,S,target,attacks.append,frequencies.append)
 try:
  enter_app(p,S);offset=0
  for c in range(7):
   events=[[0,n,127,16] for n in (49,53,56,61)] if c<3 else [[0,1,100,1],[8,2,100,1]] if c==6 and pcm else []
   word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',16,c*2)
   for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
  for c in range(3):put('evalpatch',1,c*16);put('evalpatch',3,c*16+2);put('evalpatch',1,c*16+13)
  put('seqmuted',0);put('seqsolo',0);word('seqbpm',120);word('seqglobalbpm',120);word('pattern_generation',(get('pattern_generation')|get('pattern_generation',1)<<8)+1)
  a=S['_eval_drum_dirty'];code=list(p.memory[a>>16,a&65535:(a&65535)+5]);assert code[0]==0x21 and code[3:]==[0x36,1],code;p.memory[code[1]|code[2]<<8]=1
  put('seqtrack',target);put('selected',target);put('seqhead',0);put('seqfocus',0);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  attacks.clear();frequencies.clear();key('select',True);key('a',True);key('a',False);key('select',False);p.tick(300)
  a=S['_notes'];bank=a>>16;base=a&65535
  expected={p.memory[bank,base+(n+(12 if target==2 else 0))*2]|p.memory[bank,base+(n+(12 if target==2 else 0))*2+1]<<8 for n in (48,52,55,60)}
  assert len(attacks)>30 and set(frequencies)==expected,(target,pcm,len(attacks),set(frequencies),expected)
  assert get('arpirq_enabled')&(1<<target),(target,pcm,'no native owner')
  put('mx',0,12+target);word('pattern_generation',(get('pattern_generation')|get('pattern_generation',1)<<8)+1);word('seqdeadline',1);p.tick(120)
  n=len(attacks);p.tick(120);assert len(attacks)==n,(target,pcm,'zero mixer level remained audible')
  put('mx',127,12+target);word('pattern_generation',(get('pattern_generation')|get('pattern_generation',1)<<8)+1);word('seqdeadline',1);p.tick(120)
  assert len(attacks)>n,(target,pcm,'mixer level did not recover')
  if target==1:
   put('coarsepitch',12,4);put('coarsepitch',1,5);word('pattern_generation',(get('pattern_generation')|get('pattern_generation',1)<<8)+1);p.tick(120)
   assert not get('arpirq_enabled')&2,'LFO voice retained prepared ownership'
   n=len(attacks);p.tick(120);assert len(attacks)>n,'LFO fallback stopped arp'
  key('select',True);key('a',True);key('a',False);key('select',False);p.tick(10)
  assert not get('seqplaying') and not get('arpirq_enabled')
  print('PASS simultaneous native arps, channel',target,'PCM',pcm,flush=True)
 finally:p.stop(save=False)

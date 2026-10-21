"""Real DMG PCM takeover: sustained return, expired gates and later wave onsets."""
from pathlib import Path
import json
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
reports=[]
for case,waves,drums in (
 ('sustain',[[0,49,127,16]],[[0,1,100,1],[8,2,100,1]]),
 ('expired',[[0,49,127,1]],[[0,1,100,4]]),
 ('later',[[4,53,127,4]],[[0,1,100,2]])):
 exec(prefix)
 try:
  enter_app(p,S);events=waves+drums
  for c in range(7):
   n=len(waves) if c==2 else len(drums) if c==6 else 0;off=0 if c<=2 else len(waves)
   put('seqeventoffsets',off,c*2);put('seqeventoffsets',0,c*2+1);put('seqeventcounts',n,c*2);put('seqeventcounts',0,c*2+1)
  for i,e in enumerate(events):p.memory[1,0xa300+i*4:0xa304+i*4]=e
  put('seqtrack',2);put('seqdrawvalid',0);put('dirty',1);p.tick(120)
  takeovers=[];resumes=[]
  for name,log in (('drum_enable',takeovers),('eval_audio_resume_wave',resumes)):
   ptr=S['_'+name];p.hook_register(ptr>>16,ptr&65535,lambda target:target.append(p._cycles()),log)
  p.button_press('select');p.tick(3);p.button_press('a');states=[]
  for frame in range(115):
   if frame==3:p.button_release('a');p.button_release('select')
   p.tick(1);states.append((frame,v('waveengine'),v('mixrunning'),v('active',2),bool(p.memory[0xff26]&4),v('seqposition',2)))
  assert takeovers and resumes,(case,'missing takeover/return')
  if case=='sustain':
   assert len(takeovers)>=2 and len(resumes)>=2,(case,takeovers,resumes,states[::10],v('seqplaying'),v('seqposition',6))
   assert sum(not engine and active and sounding for _,engine,_,active,sounding,_ in states)>40,states
  elif case=='expired':assert all(not sounding for _,engine,_,active,sounding,pos in states if pos>=2 and engine==0 and not active),states
  else:assert any(not engine and active and sounding and pos>=4 for _,engine,_,active,sounding,pos in states),states
  assert any(engine==3 and running for _,engine,running,_,_,_ in states),(case,'sample skipped')
  reports.append(dict(case=case,pcm_takeovers=len(takeovers),returns=len(resumes),pcm_underruns=v('mixunderruns')|(v('mixunderruns',1)<<8)))
  assert not reports[-1]['pcm_underruns'],reports[-1]
 finally:p.stop(save=False)
Path('build/stripped-wave-return.json').write_text(json.dumps(reports,indent=2)+'\n');print('PASS: PCM takeover, sustained wave return, expired gates and later onsets',reports)

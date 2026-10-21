"""Action-led 45-second Instagram edit; original performance audio throughout."""
from pathlib import Path
import json,subprocess
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'build/feature-reel';WORK.mkdir(exist_ok=True)
OUT=ROOT/'recordings/GAYBOY-45sec-FEATURES-instagram-v2.mp4'
PERF=ROOT/'recordings/GAYBOY-program-demo-172-mixer-volume.mp4'
KIT=ROOT/'recordings/GAYBOY-60sec-new-kit-capture.mp4'
# Source intervals preserve the actual controls and the sound they produced.
shots=[
 (PERF,0,3,None,'01 / LIVE NOTE EDITING','WRITE IT.\nHEAR IT. INSTANTLY.','Drop notes straight into a playing loop.','Your ideas never have to wait.'),
 (PERF,1.5,3,None,'02 / NOTE LENGTH','BIG BASS.\nTINY BUTTONS.','Stretch notes while the groove runs.','Short hits. Long notes. Total control.'),
 (PERF,6.8,3,None,'03 / REAL-TIME MIXER','TAKE CONTROL\nOF THE WHOLE MIX.','Move the fader. Hear the difference.','Every channel earns its place.'),
 (PERF,9.8,3,None,'04 / QUEUED PATTERNS','THE DROP.\nRIGHT ON TIME.','Queue a pattern. Land on the boundary.','Tight transitions built right in.'),
 (WORK/'synth.mp4',0,4.8,None,'05 / PULSE KICK SYNTH','DESIGN YOUR\nOWN THUMP.','Tune the pitch. Audition every change.','Real sound design on a Game Boy.'),
 (WORK/'synth.mp4',4.8,4.2,None,'05 / PULSE KICK SYNTH','MAKE THAT\nKICK HIT HARDER.','Shape the decay. Find your sweet spot.','Tiny machine. Serious punch.'),
 (PERF,16.5,4,None,'06 / LIVE DRUM PROGRAMMING','BUILD THE BEAT.\nWITHOUT STOPPING.','Punch in kicks while playback rolls.','Hear your rhythm come alive.'),
 (PERF,20.5,4,None,'06 / LIVE DRUM PROGRAMMING','GIVE YOUR\nGROOVE SOME TEETH.','Add open-hat accents in real time.','A few buttons. A bigger beat.'),
 (KIT,44,4,'crop=960:864:60:560','07 / SAMPLE-BASED DRUMS','REAL SAMPLES.\nRIDICULOUSLY SMALL.','Two sample voices. Custom drum kits.','Give this little box a huge personality.'),
 (KIT,48,4,'crop=960:864:60:560','07 / SAMPLE-BASED DRUMS','MORE FLAVOUR.\nMORE FIREPOWER.','Add percussion to a sampled kit.','Your kit. Your groove. Your sound.'),
 (PERF,25,4,None,'GAYBOY / MUSIC WORKSTATION','A WHOLE LOT\nOF MUSIC MACHINE.','Live editing. Synthesis. Samples. Mixing.','All that attitude. In your pocket.'),
 (PERF,25,4,None,'PLAY ONLINE / DOWNLOAD THE .gb','SMALL CONSOLE.\nMASSIVE POSSIBILITIES.','GAYBOY. Absolutely free.','buttholechopper.com/gayboy'),
]
assert abs(sum(s[2] for s in shots)-45)<.001
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('consolab.ttf' if bold else 'consola.ttf'),n)
def card(i,shot):
 _,_,duration,_,label,title,sub,tag=shot
 im=Image.new('RGB',(540,960),'#101010');d=ImageDraw.Draw(im)
 d.text((30,77),'GAYBOY',font=font(23,True),fill='#f2f2eb')
 d.text((510,86),f'{i+1:02d} / {len(shots):02d}',font=font(12),fill='#ef94bc',anchor='ra')
 d.text((30,123),label,font=font(13,True),fill='#ef94bc')
 d.multiline_text((28,158),title,font=font(35,True),fill='#f2f2eb',spacing=1)
 d.rectangle((26,287,513,726),fill='#777777')
 # Screen is composited inside this border by FFmpeg.
 d.text((30,759),sub,font=font(17),fill='#f2f2eb')
 d.text((30,793),tag,font=font(16),fill='#b7b7b0')
 d.line((30,848,510,848),fill='#3a3a3a',width=2)
 for n in range(len(shots)):
  x=30+n*40
  d.rectangle((x,845,x+30,850),fill='#ef94bc' if n<=i else '#333333')
 d.text((30,879),'SOUND ON / ACTUAL GAME BOY AUDIO',font=font(12),fill='#888888')
 path=WORK/f'card-{i:02d}.png';im.save(path);return path

manifest=[];start=0
for i,shot in enumerate(shots):
 source,seek,duration,crop,label,title,sub,tag=shot
 bg=card(i,shot);part=WORK/f'part-{i:02d}.mp4'
 screen=((crop+',') if crop else '')+'format=gray,scale=480:432:flags=neighbor,fps=30,setsar=1'
 filters=f'[0:v]{screen}[lcd];[1:v][lcd]overlay=30:291,scale=1080:1920:flags=neighbor,format=yuv420p[v];[0:a]afade=t=in:d=0.012,afade=t=out:st={duration-.025}:d=0.025[a]'
 subprocess.run(['ffmpeg','-v','error','-y','-ss',str(seek),'-t',str(duration),'-i',str(source),'-loop','1','-framerate','30','-i',str(bg),'-filter_complex_threads','1','-filter_complex',filters,'-map','[v]','-map','[a]','-t',str(duration),'-r','30','-c:v','libx264','-preset','fast','-threads','2','-crf','17','-c:a','aac','-b:a','192k','-ar','48000',str(part)],check=True)
 manifest.append({'at':round(start,3),'duration':duration,'source':str(source),'source_start':seek,'feature':label,'headline':title,'caption':sub,'tagline':tag});start+=duration
 print(f'{i+1}/{len(shots)}: {label}',flush=True)
listing=WORK/'feature-edit.ffconcat';listing.write_text('ffconcat version 1.0\n'+'\n'.join(f"file 'part-{i:02d}.mp4'" for i in range(len(shots)))+'\n')
subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-t','45','-c:v','copy','-af','loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st=44.7:d=0.3','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(OUT)],check=True)
OUT.with_suffix('.json').write_text(json.dumps({'duration':45,'resolution':[1080,1920],'fps':30,'edit':'Feature demonstrations from existing real-button performances plus newly captured current-ROM pulse-kick synthesis. Idle navigation cut; no playback acceleration.','timeline':manifest},indent=2)+'\n')
print(OUT)

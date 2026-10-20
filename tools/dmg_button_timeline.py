"""Replay logged physical button states into DMG-style control artwork."""
import json,math,subprocess,shutil
from pathlib import Path
from PIL import Image


def ease_out(t):
 if t<=0:return 0
 if t>=1:return 1
 # CSS ease-out: cubic-bezier(0,0,.58,1), matching the site D-pad.
 low,high=0.,1.
 for _ in range(15):
  s=(low+high)/2;x=3*(1-s)*s*s*.58+s**3
  if x<t:low=s
  else:high=s
 s=(low+high)/2
 return 3*(1-s)*s*s+s**3

class Controls:
 def __init__(self):
  self.keys={};self.motion={side:dict(start=0.,origin=(0.,0.),target=(0.,0.)) for side in ['LEFT','RIGHT']}
 def held(self,side):return tuple(sorted({button for (owner,vk),button in self.keys.items() if owner==side}))
 def pose(self,side,t):
  motion=self.motion[side];blend=ease_out((t-motion['start'])/.09)
  return tuple(a+(b-a)*blend for a,b in zip(motion['origin'],motion['target']))
 def accept(self,event):
  side=event['side'];key=side,event['vk'];t=event['video_seconds']
  if event['event']=='down':self.keys[key]=event['button']
  else:self.keys.pop(key,None)
  held=self.held(side)
  target=(-10. if 'DOWN' in held else 10. if 'UP' in held else 0.,10. if 'RIGHT' in held else -10. if 'LEFT' in held else 0.)
  if target!=self.motion[side]['target']:self.motion[side]=dict(start=t,origin=self.pose(side,t),target=target)

def render_controls(folder,keys,start,frame_count,painter):
 data=json.loads(Path(keys).read_text());events=sorted(data['events'],key=lambda e:e['video_seconds'])
 bases=[Image.open(folder/('controls-base-'+side+'.png')).convert('RGBA') for side in ['LEFT','RIGHT']]
 state=Controls();cursor=0;cache=[{},{}];changes=[];previous=None
 (folder/'button-timeline.json').write_text(json.dumps(dict(source=str(Path(keys).resolve()),trim_seconds=start,transition_seconds=.09,behavior='single-cross CSS-style perspective tilt; DMG buttons depress 3 px and darken',events=[dict(side=e['side'],button=e['button'],event=e['event'],repeat=e['repeat'],seconds=e['video_seconds']-start) for e in events if start<=e['video_seconds']<start+frame_count/30]),indent=2))
 command=[shutil.which('ffmpeg'),'-hide_banner','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','960x290','-framerate','30','-i','pipe:0','-an','-c:v','libx264rgb','-preset','ultrafast','-crf','0','-pix_fmt','rgb24','-threads','4',str(folder/'button-controls.mkv')]
 with (folder/'controls-render.log').open('w') as log:
  encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=log)
  try:
   for frame in range(frame_count):
    t=start+frame/30
    while cursor<len(events) and events[cursor]['video_seconds']<=t:state.accept(events[cursor]);cursor+=1
    image=Image.new('RGB',(960,290));signature=[]
    for i,side in enumerate(['LEFT','RIGHT']):
     held=state.held(side);tilt=tuple(round(x,2) for x in state.pose(side,t));key=held,tilt;signature.append(key)
     if key not in cache[i]:cache[i][key]=painter(bases[i],held,tilt)
     image.paste(cache[i][key],(i*480,0))
    if signature!=previous:changes.append(dict(frame=frame,seconds=frame/30,left=signature[0],right=signature[1]));previous=signature
    if frame==0:image.save(folder/'controls-preview.png')
    if any(abs(angle)>6 for item in signature for angle in item[1]) and not (folder/'controls-lean-example.png').exists():
     image.save(folder/'controls-lean-example.png');(folder/'lean-example-time.txt').write_text(str(frame/30))
    encoder.stdin.write(image.tobytes())
  finally:encoder.stdin.close()
  result=encoder.wait()
  if result:raise RuntimeError('Control animation render failed; see controls-render.log')
 (folder/'button-frame-states.json').write_text(json.dumps(dict(frame_count=frame_count,changes=changes,cached_poses=[len(c) for c in cache]),indent=2))
 print('Rendered button replay:',frame_count,'frames,',len(changes),'visual transitions;', [len(c) for c in cache],'poses',flush=True)

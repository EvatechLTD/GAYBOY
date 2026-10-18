"""Frame an existing vertical emulator capture in a slim shell with feature copy.

The LCD pixels and recorded audio come directly from the existing capture.
"""
import argparse,json,shutil,subprocess,colorsys,math
import numpy as np
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from heights_demo import EightOhEightDemo as DMXHeightsDemo
ROOT=Path(__file__).resolve().parents[1]

def shell(caption):
 im=Image.new('RGBA',(540,960),(0,0,0,0));d=ImageDraw.Draw(im)
 # Nintendo DMG: 90 x 148 mm. All control placement uses the same scale.
 scale=528/90;ox=6;oy=(960-148*scale)/2
 def pt(x,y):return (ox+x*scale,oy+y*scale)
 def rect(x0,y0,x1,y1):return (*pt(x0,y0),*pt(x1,y1))
 def contour(x0,y0,x1,y1,r,br):
  pts=[]
  for cx,cy,rad,start in [(x1-r,y0+r,r,-90),(x1-br,y1-br,br,0),
                         (x0+r,y1-r,r,90),(x0+r,y0+r,r,180)]:
   for angle in np.linspace(start,start+90,25):
    pts.append(pt(cx+rad*math.cos(math.radians(angle)),cy+rad*math.sin(math.radians(angle))))
  return pts
 d.polygon(contour(0,0,90,148,3,18),fill='#2c7974')
 d.polygon(contour(.35,.35,89.65,147.65,2.8,17.8),fill='#62b8ab')
 d.line([pt(3,.7),pt(87,.7)],fill='#b2dfc9',width=2)
 d.line([pt(.8,3),pt(.8,144)],fill='#94d5c1',width=2)
 # Top mold seam and the original power-switch location.
 d.line([pt(0,8),pt(90,8)],fill='#358f88',width=2)
 d.line([pt(7,0),pt(7,7)],fill='#358f88',width=2)
 d.line([pt(83,0),pt(83,7)],fill='#358f88',width=2)
 d.rounded_rectangle(rect(12,1.7,29,6.5),radius=9,outline='#4da69a',width=2)
 tiny=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',8)
 small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',10)
 brand=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',24)
 navy='#193d69'
 d.text(pt(20.5,4.3),'OFF - ON',font=tiny,fill='#3a8c86',anchor='mm')
 # Bezel and battery LED follow the reference front elevation.
 d.polygon(contour(7,12,83,70,2,12),fill='#276c6b')
 d.line([pt(11,15),pt(29,15)],fill='#cf758e',width=2)
 d.line([pt(11,16.5),pt(29,16.5)],fill=navy,width=2)
 d.line([pt(72,15),pt(79,15)],fill='#cf758e',width=2)
 d.line([pt(72,16.5),pt(79,16.5)],fill=navy,width=2)
 d.text(pt(50,15.7),'DOT MATRIX WITH STEREO SOUND',font=tiny,fill='#b8d1b1',anchor='mm')
 d.ellipse(rect(11.4,32,13.8,34.4),fill='#a2333b',outline='#532d3b',width=1)
 d.text(pt(13,37.1),'BATTERY',font=tiny,fill='#a4c9b2',anchor='mm')
 # LCD is 47.7 x 42.95 mm; exact 160:144 aspect, centered on the body.
 d.rectangle((128,156,411,411),fill='#173c38')
 d.rectangle((130,158,409,409),fill='#bfffe0')
 d.text(pt(6.5,74.9),'GAYBOY',font=brand,fill=navy,anchor='lm')
 d.text(pt(44.5,75.4),'4-BIT SAMPLE ENGINE',font=tiny,fill=navy,anchor='lm')
 # Feature copy uses the real shell's empty area between logo and controls.
 font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',18)
 position=pt(45,84.6)
 box=d.multiline_textbbox(position,caption,font=font,anchor='mm',align='center',spacing=6)
 assert box[0]>=33 and box[2]<=479 and box[1]>=135 and box[3]<=623,(caption,box)
 d.multiline_text(position,caption,font=font,fill=navy,anchor='mm',align='center',spacing=6)
 # Reference-measured D-pad: 22 mm wide; center (17.9, 101.0) mm.
 cx,cy=17.9,101.;arm=7.3;half=11
 d.rectangle(rect(cx-half,cy-arm/2,cx+half,cy+arm/2),fill='#b59e35')
 d.rectangle(rect(cx-arm/2,cy-half,cx+arm/2,cy+half),fill='#b59e35')
 d.rectangle(rect(cx-half+.5,cy-arm/2+.5,cx+half-.5,cy+arm/2-.5),fill='#f3d448')
 d.rectangle(rect(cx-arm/2+.5,cy-half+.5,cx+arm/2-.5,cy+half-.5),fill='#f3d448')
 d.ellipse(rect(cx-2.2,cy-2.2,cx+2.2,cy+2.2),fill='#ddc23f')
 # A/B centers and diagonal spacing match the original DMG front photo.
 for x,y,label,color in [(77.45,95.8,'A','#b6df45'),(62.9,102.5,'B','#dd5352')]:
  d.ellipse(rect(x-6.2,y-6.2,x+6.2,y+6.2),fill='#43968c')
  d.ellipse(rect(x-5.5,y-5.5,x+5.5,y+5.5),fill=color,outline='#2c7974',width=2)
  d.arc(rect(x-4.9,y-4.9,x+4.9,y+4.9),195,300,fill='#d8e79b',width=1)
  d.text(pt(x+4.5,y+8.6),label,font=small,fill=navy,anchor='mm')
 # 15.3 mm center spacing, 11 x 3.5 mm caps, tilted 27 degrees.
 for x,y,label in [(31.84,122.,'SELECT'),(47.14,122.3,'START')]:
  angle=math.radians(27);length=(11-3.5)/2
  dx=length*math.cos(angle);dy=length*math.sin(angle)
  d.line([pt(x-dx,y+dy),pt(x+dx,y-dy)],fill='#3c938b',width=round(4.6*scale))
  d.line([pt(x-dx,y+dy),pt(x+dx,y-dy)],fill=navy,width=round(3.5*scale))
  for xx,yy in [(x-dx,y+dy),(x+dx,y-dy)]:
   d.ellipse(rect(xx-1.75,yy-1.75,xx+1.75,yy+1.75),fill=navy)
  d.text(pt(x+1,127.8),label,font=small,fill=navy,anchor='mm')
 # Six original diagonal speaker slots.
 for i in range(6):
  x=57+i*4.5;y=133-i*2.5
  d.line([pt(x,y),pt(x+6.2,y+11.5)],fill='#3c918a',width=round(1.6*scale))
  d.line([pt(x+.25,y),pt(x+6.45,y+11.5)],fill='#205e67',width=round(1.1*scale))
 d.rounded_rectangle(rect(33,141.4,45,146.2),radius=9,outline='#4da69a',width=2)
 d.text(pt(39,143.8),'PHONES',font=tiny,fill='#3a8c86',anchor='mm')
 return im


def raster_texture(path):
 # Native 90x160 pixels, blown up 12x with nearest-neighbor in the export.
 palette=np.array([(104,55,169),(53,40,121),(112,164,178),(88,141,67),
                   (184,199,111),(184,105,58),(136,60,73),(154,103,179)],dtype=float)
 y,x=np.mgrid[0:160,0:90];duration=10;fps=30
 encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y',
  '-f','rawvideo','-pix_fmt','rgb24','-s','90x160','-r',str(fps),'-i','-',
  '-an','-c:v','ffv1','-threads','1','-pix_fmt','bgr0',str(path)],stdin=subprocess.PIPE)
 for frame in range(duration*fps):
  theta=2*math.pi*frame/(duration*fps)
  wave=y+12*np.sin(x/8+theta)+8*np.sin(x/17-2*theta)+5*np.sin(y/19+theta)
  phase=wave/6+8*frame/(duration*fps)
  index=np.floor(phase).astype(int)%len(palette)
  level=np.array([.45,.75,1.,.75])[np.floor((phase%1)*4).astype(int)]
  pixels=(palette[index]*level[:,:,None]).astype('uint8')
  encoder.stdin.write(pixels.tobytes())
 encoder.stdin.close();assert encoder.wait()==0


def mobile_outro(image_path):
 # Real mobile-site screenshot fills the entire 9:16 frame.
 im=Image.open(image_path).convert('RGBA').resize((540,960),Image.Resampling.LANCZOS)
 overlay=Image.new('RGBA',im.size,(0,0,0,0));d=ImageDraw.Draw(overlay)
 d.rounded_rectangle((33,139,479,203),radius=9,fill=(4,24,28,238),outline='#65dcb1',width=2)
 d.rounded_rectangle((33,489,479,621),radius=9,fill=(4,24,28,242),outline='#65dcb1',width=2)
 bold=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',28)
 title=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',19)
 regular=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',13)
 tiny=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',11)
 url=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',16)
 d.text((256,172),'ABSOLUTELY FREE.',font=bold,fill='#bfffe0',anchor='mm')
 download='download' in str(image_path)
 lines=(('DOWNLOAD THE .gb.','Play on a real Game Boy.','Compatible flash cart required.') if download else
        ('PLAY ONLINE. OR TAKE IT HOME.','Free browser emulator + .gb download.','Real Game Boy? Bring a flash cart.'))
 for text,font,y in ((lines[0],title,511),(lines[1],regular,541),(lines[2],tiny,563),
                     ('buttholechopper.com/gayboy',url,600)):
  box=d.textbbox((256,y),text,font=font,anchor='mm')
  assert box[0]>=33 and box[2]<=480 and box[1]>=135 and box[3]<=623,(text,box)
  d.text((256,y),text,font=font,fill='#bfffe0' if y in (511,600) else '#a9ead3',anchor='mm')
 return Image.alpha_composite(im,overlay)


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--input',type=Path,default=ROOT/'recordings/GAYBOY-60sec-intro-drums-teal-capture.mp4')
 ap.add_argument('--output',type=Path,default=ROOT/'recordings/GAYBOY-60sec-BMO-intro-groove.mp4')
 args=ap.parse_args();meta=json.loads(args.input.with_suffix('.json').read_text());out=ROOT/'build/808-shell';out.mkdir(exist_ok=True)
 dummy=DMXHeightsDemo.__new__(DMXHeightsDemo);dummy.stage_times=[];dummy.frames=0
 cues=[{'at':0.,'copy':'Pocket-sized. Mildly unreasonable.\nMeet your next musical distraction.'}]
 cut=meta['intro_duration_seconds'];offset=cut+meta['live_preroll_seconds']
 cues.append({'at':cut,'copy':dummy.opening_caption})
 for stage in meta['stages']:
  if 'story' not in stage:continue
  dummy.label(stage['story'])
  text=dummy.story
  if text.startswith(('Eight TR-808 sounds.','Eight Oberheim DMX sounds.')):
   text='Load 4-bit wave samples.\nGive tiny drums a big problem.'
  text=text.replace('Eight Oberheim DMX sounds.\nGood manners sold separately.','Load 4-bit wave samples.\nGive tiny drums a big problem.')
  assert not any(n in text.lower() for n in ('oberheim','tr-808','tr-909','dmx')),text
  if text==cues[-1]['copy']:continue
  cues.append({'at':offset+stage['frame']/59.7275,'copy':text})
 cues=[c for c in cues if c['at']<54]
 cues.extend([{'at':54.,'copy':'Absolutely free. Play online or download the .gb for a real Game Boy. buttholechopper.com/gayboy','outro':'mobile-play.png'},
              {'at':57.,'copy':'Absolutely free. Play online or download the .gb for a real Game Boy. buttholechopper.com/gayboy','outro':'mobile-download.png'}])
 concat=['ffconcat version 1.0']
 for i,cue in enumerate(cues):
  f=out/f'shell-{i:02d}.png'
  (mobile_outro(out/cue['outro']) if 'outro' in cue else shell(cue['copy'])).save(f)
  end=cues[i+1]['at'] if i+1<len(cues) else 60
  concat.extend(["file '"+f.name+"'",f'duration {end-cue["at"]:.9f}'])
 concat.append("file '"+f.name+"'")
 listing=out/'shell.ffconcat';listing.write_text('\n'.join(concat)+'\n')
 texture=out/'black.png';Image.new('RGB',(90,160),'black').save(texture)
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(args.input),'-f','concat','-safe','0','-i',str(listing),'-loop','1','-framerate','30','-i',str(texture),
  '-filter_complex_threads','1','-filter_complex',"[2:v]fps=60,scale=1080:1920:flags=neighbor[bg];[1:v]fps=60,scale=1080:1920:flags=neighbor[body];[bg][body]overlay=0:0[device];[0:v]crop=960:864:60:560,scale=560:504:flags=neighbor[lcd];[device][lcd]overlay=260:316:shortest=1:enable='lt(t,54)'[v]",
  '-map','[v]','-map','0:a:0','-t','60','-c:v','libx264','-preset','fast','-threads','2','-crf','16','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(args.output)],check=True)
 meta.update(caption_style='Playful feature copy',caption_timeline=cues,
  shell={'lcd_pixels':[560,504],'lcd_position':[260,316],'lcd_fraction_of_video_width':560/1080,
         'source':'Centered DMG front elevation; 90x148 mm body, reference-measured control centers',
         'body_bounds_540x960':[6,(960-148*(528/90))/2,534,(960+148*(528/90))/2],
         'body_mm':[90,148], 'control_reference':'https://commons.wikimedia.org/wiki/File:Nintendo_Gameboy.jpg',
         'skin':'BMO teal; yellow D-pad, red B, lime A, navy Start/Select',
         'safe_rectangle':[66,269,960,1248], 'background':'Solid black'},outro={'at_seconds':54,'url':'https://buttholechopper.com/gayboy/','mobile_site':'Actual published site, full-frame mobile view, 390x694 viewport','message':'Absolutely free: play online or download the .gb for real Game Boy with compatible flash cartridge'},audio_processing='AAC stream copied unchanged from SameBoy capture')
 args.output.with_suffix('.json').write_text(json.dumps(meta,indent=2))
 shutil.copyfile(args.input.with_suffix('.wav'),args.output.with_suffix('.wav'))
 print(json.dumps({'output':str(args.output),'captions':cues},indent=2))

if __name__=='__main__':main()

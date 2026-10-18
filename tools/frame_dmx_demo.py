"""Frame an existing vertical emulator capture in a slim shell with feature copy.

The LCD pixels and recorded audio come directly from the existing capture.
"""
import argparse,json,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from heights_demo import DMXHeightsDemo
ROOT=Path(__file__).resolve().parents[1]

def shell(caption):
 im=Image.new('RGB',(540,960),'#0f380f');d=ImageDraw.Draw(im)
 ink='#29372d';plastic='#b9bea3';edge='#65735b'
 d.rounded_rectangle((10,109,535,947),radius=34,fill='#071f0b')
 d.rounded_rectangle((6,101,532,938),radius=32,fill=edge)
 d.rounded_rectangle((8,103,528,934),radius=30,fill=plastic,outline='#d3d8bc',width=2)
 d.line((20,125,517,125),fill='#8f997c',width=1)
 brand=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',24)
 small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',10)
 tiny=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',8)
 copyfont=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',22)
 d.text((29,143),'GAYBOY',font=brand,fill='#304635',anchor='lm')
 d.text((506,143),'PORTABLE GROOVE TROUBLE',font=tiny,fill='#52624b',anchor='rm')
 d.multiline_text((270,199),caption,font=copyfont,fill=ink,anchor='mm',align='center',spacing=7)
 d.rounded_rectangle((17,249,523,719),radius=14,fill='#505c49',outline='#727e64',width=2)
 d.text((270,261),'DOT MATRIX WITH ATTITUDE',font=tiny,fill='#c9cfb4',anchor='mm')
 # 480x432 LCD: exactly the same width as the original capture.
 d.rectangle((28,270,511,705),fill='#152b17')
 d.rectangle((30,272,509,703),fill='#b1d12d')
 d.text((29,733),'STEREO SOUND',font=small,fill='#42543f',anchor='lm')
 d.text((507,733),'128 BPM / OBERHEIM DMX',font=small,fill='#42543f',anchor='rm')
 # D-pad with a small molded highlight.
 d.rounded_rectangle((54,779,132,805),radius=4,fill='#15261d')
 d.rounded_rectangle((80,753,106,831),radius=4,fill='#15261d')
 d.line((83,758,101,758),fill='#52604b',width=2)
 d.line((59,783,77,783),fill='#52604b',width=2)
 d.ellipse((83,782,103,802),fill='#253b2c',outline='#0e2117',width=1)
 for x,y,label in [(443,773,'A'),(371,808,'B')]:
  d.ellipse((x-27,y-25,x+27,y+29),fill='#899377')
  d.ellipse((x-23,y-24,x+23,y+22),fill='#693c57',outline='#492c40',width=2)
  d.arc((x-19,y-20,x+19,y+18),195,300,fill='#8f657a',width=2)
  d.text((x,y+35),label,font=small,fill='#304635',anchor='mm')
 for x,label in [(218,'SELECT'),(286,'START')]:
  d.line((x-15,865,x+15,855),fill='#8b9579',width=15)
  d.line((x-15,862,x+15,852),fill='#4a594a',width=10)
  d.text((x,881),label,font=tiny,fill='#42543f',anchor='mm')
 for i in range(5):
  x=383+i*15
  d.line((x,870,x+25,905),fill='#899577',width=6)
  d.line((x+1,870,x+26,905),fill='#52634e',width=3)
 d.line((32,918,322,918),fill='#9da98a',width=1)
 return im


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--input',type=Path,default=ROOT/'recordings/GAYBOY-60sec-intro-Oberheim-DMX.mp4')
 ap.add_argument('--output',type=Path,default=ROOT/'recordings/GAYBOY-60sec-Oberheim-DMX-GameBoy.mp4')
 args=ap.parse_args();meta=json.loads(args.input.with_suffix('.json').read_text());out=ROOT/'build/dmx-shell';out.mkdir(exist_ok=True)
 dummy=DMXHeightsDemo.__new__(DMXHeightsDemo);dummy.stage_times=[];dummy.frames=0
 cues=[{'at':0.,'copy':'Pocket-sized. Mildly unreasonable.\nMeet your next musical distraction.'}]
 cut=meta['intro_duration_seconds'];offset=cut+meta['live_preroll_seconds']
 cues.append({'at':cut,'copy':dummy.opening_caption})
 for stage in meta['stages']:
  if 'story' not in stage:continue
  dummy.label(stage['story'])
  text=dummy.story
  if text==cues[-1]['copy']:continue
  cues.append({'at':offset+stage['frame']/59.7275,'copy':text})
 cues=[c for c in cues if c['at']<60]
 concat=['ffconcat version 1.0']
 for i,cue in enumerate(cues):
  f=out/f'shell-{i:02d}.png';shell(cue['copy']).save(f)
  end=cues[i+1]['at'] if i+1<len(cues) else 60
  concat.extend(["file '"+f.name+"'",f'duration {end-cue["at"]:.9f}'])
 concat.append("file '"+f.name+"'")
 listing=out/'shell.ffconcat';listing.write_text('\n'.join(concat)+'\n')
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(args.input),'-f','concat','-safe','0','-i',str(listing),
  '-filter_complex_threads','1','-filter_complex','[1:v]fps=60,scale=1080:1920:flags=neighbor[body];[0:v]crop=960:864:60:560[lcd];[body][lcd]overlay=60:544:shortest=1[v]',
  '-map','[v]','-map','0:a:0','-t','60','-c:v','libx264','-preset','fast','-threads','2','-crf','16','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(args.output)],check=True)
 meta.update(caption_style='Playful feature copy',caption_timeline=cues,
  shell={'lcd_pixels':[960,864],'lcd_position':[60,544],'lcd_fraction_of_video_width':960/1080,
         'source':'Emulator framebuffer crop; original display width preserved'},audio_processing='AAC stream copied unchanged from SameBoy capture')
 args.output.with_suffix('.json').write_text(json.dumps(meta,indent=2))
 shutil.copyfile(args.input.with_suffix('.wav'),args.output.with_suffix('.wav'))
 print(json.dumps({'output':str(args.output),'captions':cues},indent=2))

if __name__=='__main__':main()

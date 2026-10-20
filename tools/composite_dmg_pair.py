"""Composite recorded screens into cel-shaded DMG shells, with optional input replay."""
import argparse,json,math,subprocess,shutil
import numpy as np
from functools import lru_cache
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

S=3;W,H=1920,1080
INK='#17202e';BODY='#d9d9cd';LIGHT='#f5f3e6';SHADE='#afb3aa';BLUE='#273667'
art=Image.new('RGBA',(W*S,H*S));draw=ImageDraw.Draw(art)
FLAT=False;ANIMATE=False
def pts(p):return [(round(x*S),round(y*S)) for x,y in p]
def poly(p,fill,outline=None,width=3):
 q=pts(p);draw.polygon(q,fill=fill)
 if outline:draw.line(q+[q[0]],fill=outline,width=width*S,joint='curve')
def line(p,fill,width=2):draw.line(pts(p),fill=fill,width=width*S,joint='curve')
def rect(box,fill,outline=None,width=2,r=0):
 b=tuple(round(v*S) for v in box)
 if r:draw.rounded_rectangle(b,round(r*S),fill=fill,outline=outline,width=width*S)
 else:draw.rectangle(b,fill=fill,outline=outline,width=width*S)
def ellipse(box,fill,outline=None,width=2):draw.ellipse(tuple(round(v*S) for v in box),fill=fill,outline=outline,width=width*S)
def text(x,y,content,size=16,fill=INK,font='arialbd.ttf'):
 file=Path('C:/Windows/Fonts')/font
 f=ImageFont.truetype(str(file),size*S)
 draw.text((round(x*S),round(y*S)),content,font=f,fill=fill)
def cubic(p0,p1,p2,p3,n=80):
 return [((1-t)**3*p0[0]+3*(1-t)**2*t*p1[0]+3*(1-t)*t*t*p2[0]+t**3*p3[0],(1-t)**3*p0[1]+3*(1-t)**2*t*p1[1]+3*(1-t)*t*t*p2[1]+t**3*p3[1]) for t in [i/n for i in range(n+1)]]

def cross(cx,cy,a,b):return [(cx-b,cy-a),(cx+b,cy-a),(cx+b,cy-b),(cx+a,cy-b),(cx+a,cy+b),(cx+b,cy+b),(cx+b,cy+a),(cx-b,cy+a),(cx-b,cy+b),(cx-a,cy+b),(cx-a,cy-b),(cx-b,cy-b)]

@lru_cache(maxsize=256)
def dpad_sprite(tilt_x,tilt_y,directions):
 """Transform one molded cross, never four independently moving buttons."""
 global art,draw
 previous=art,draw;art=Image.new('RGBA',(160*S,160*S));draw=ImageDraw.Draw(art);cx=cy=80
 poly(cross(cx+3,cy+5,68,23),'#a1a79d')
 poly(cross(cx,cy,68,23),'#303944',INK,4)
 poly([(cx-18,cy-62),(cx+18,cy-62),(cx+18,cy-25),(cx+62,cy-25),(cx+62,cy-17),(cx-17,cy-17),(cx-17,cy+62),(cx-23,cy+62),(cx-23,cy+19),(cx-62,cy+19),(cx-62,cy-17),(cx-18,cy-17)],'#505c67')
 ellipse((cx-17,cy-17,cx+17,cy+17),'#252f3a',INK,2)
 poly([(cx-8,cy-43),(cx+8,cy-43),(cx,cy-53)],'#cad2cc' if 'UP' in directions else '#899195')
 poly([(cx-8,cy+43),(cx+8,cy+43),(cx,cy+53)],'#cad2cc' if 'DOWN' in directions else '#19232f')
 poly([(cx-43,cy-8),(cx-43,cy+8),(cx-53,cy)],'#cad2cc' if 'LEFT' in directions else '#899195')
 poly([(cx+43,cy-8),(cx+43,cy+8),(cx+53,cy)],'#cad2cc' if 'RIGHT' in directions else '#19232f')
 sprite=art;art,draw=previous
 if not tilt_x and not tilt_y:return sprite
 ax,ay=math.radians(tilt_x),math.radians(tilt_y);p=268*S;center=80*S
 corners=[(0,0),(160*S,0),(160*S,160*S),(0,160*S)];dest=[]
 for px,py in corners:
  x,y=px-center,py-center
  rx=math.cos(ay)*x+math.sin(ay)*math.sin(ax)*y;ry=math.cos(ax)*y;rz=-math.sin(ay)*x+math.cos(ay)*math.sin(ax)*y
  dest.append((center+rx*p/(p-rz),center+ry*p/(p-rz)))
 matrix=[];values=[]
 for (x,y),(u,v) in zip(dest,corners):matrix.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);values.extend([u,v])
 coefficients=np.linalg.solve(np.asarray(matrix),np.asarray(values))
 return sprite.transform(sprite.size,Image.Transform.PERSPECTIVE,coefficients,Image.Resampling.BICUBIC)

def draw_controls(x,y,held=(),tilt=(0,0)):
 # Preserve the approved DMG palette; borrow only the site's pressed behavior.
 cx,cy=x+133,y+650
 ellipse((cx-82,cy-82,cx+82,cy+82),'#c7cbc0')
 directions=tuple(b for b in ['UP','DOWN','LEFT','RIGHT'] if b in held)
 sprite=dpad_sprite(*tilt,directions);art.alpha_composite(sprite,(round((cx-80)*S),round((cy-80)*S)))
 for label,bx,by in [('B',x+367,y+665),('A',x+447,y+617)]:
  ellipse((bx-43,by-40,bx+48,by+49),'#b8bbb0')
  pressed=label in held;by+=3 if pressed else 0
  ellipse((bx-36,by-36,bx+36,by+36),'#641436' if pressed else '#891949',INK,4)
  poly([(bx-27,by-12),(bx-19,by-26),(bx+8,by-30),(bx+25,by-14),(bx+15,by-9),(bx-13,by-14)],'#8e2852' if pressed else '#c0396c')
  line([(bx-21,by+25),(bx+6,by+30),(bx+27,by+15)],'#46132c' if pressed else '#541534',4)
  text(bx+2,by-(3 if pressed else 0)+48,label,21,BLUE)
 for label,bx,by in [('SELECT',x+218,y+767),('START',x+301,y+767)]:
  poly([(bx-26,by+8),(bx+16,by-13),(bx+25,by-9),(bx+29,by+1),(bx-15,by+24),(bx-24,by+19)],'#a2a99f')
  base=by;pressed=label in held;by+=3 if pressed else 0
  poly([(bx-27,by),(bx+14,by-20),(bx+22,by-17),(bx+24,by-9),(bx-19,by+12),(bx-25,by+8)],'#424e55' if pressed else '#606d73',INK,3)
  line([(bx-19,by+1),(bx+14,by-15)],'#718189' if pressed else '#a1aeb0',3)
  text(bx-31,base+29,label,12,BLUE)

def control_tile(base,held,tilt):
 global art,draw
 previous=art,draw;art=base.copy();draw=ImageDraw.Draw(art)
 draw_controls(-32,-550,held,tilt)
 result=art.resize((480,290),Image.Resampling.LANCZOS).convert('RGB');art,draw=previous
 return result

def shell(x,y):
 if not FLAT:
  side=[(x+520,y+5),(x+564,y+25),(x+564,y+756)]+cubic((x+564,y+756),(x+562,y+848),(x+520,y+882),(x+460,y+890))+[(x+450,y+861)]
  poly(side,'#969e99',INK,5)
  poly([(x+541,y+66),(x+555,y+74),(x+555,y+750),(x+541,y+776)],'#c2c6bb')
 front=[(x+28,y),(x+512,y)]+cubic((x+512,y),(x+540,y),(x+540,y+4),(x+540,y+28))+[(x+540,y+752)]+cubic((x+540,y+752),(x+540,y+842),(x+496,y+876),(x+426,y+876))+[(x+28,y+876)]+cubic((x+28,y+876),(x,y+876),(x,y+864),(x,y+846))+[(x,y+30)]+cubic((x,y+30),(x,y+9),(x+8,y),(x+28,y))
 poly(front,BODY,INK,6)
 poly([(x+10,y+26),(x+27,y+10),(x+510,y+10),(x+527,y+28),(x+526,y+50),(x+17,y+50),(x+17,y+830),(x+10,y+844)],LIGHT)
 poly([(x+520,y+63),(x+534,y+63),(x+534,y+753),(x+525,y+804),(x+495,y+843),(x+445,y+865),(x+32,y+865),(x+18,y+852),(x+430,y+852),(x+486,y+830),(x+513,y+789)],SHADE)
 line([(x+5,y+62),(x+536,y+62)],INK,3)
 line([(x+30,y+4),(x+30,y+61)],SHADE,2);line([(x+507,y+5),(x+507,y+61)],SHADE,2)
 # Power slider and molded top face detail.
 rect((x+63,y-5,x+130,y+5),INK,r=3)
 for i in range(6):line([(x+70+i*9,y-3),(x+70+i*9,y+3)],'#8e9692',2)
 text(x+145,y+20,'OFF   ON',10,'#737b78')
 # Dark screen bezel, with flat highlight and shadow facets.
 rect((x+35,y+102,x+505,y+496),'#666b77',INK,4,r=17)
 poly([(x+50,y+112),(x+488,y+112),(x+495,y+122),(x+495,y+134),(x+47,y+134)],'#858a94')
 poly([(x+492,y+139),(x+501,y+132),(x+501,y+479),(x+489,y+490),(x+50,y+490),(x+42,y+479),(x+487,y+479)],'#454c59')
 line([(x+55,y+140),(x+158,y+140)],'#a56484',3)
 line([(x+55,y+146),(x+158,y+146)],'#3c5476',3)
 text(x+173,y+124,'DOT MATRIX WITH STEREO SOUND',10,'#f0eddf')
 # Actual footage replaces this exact 320x288 rectangle.
 rect((x+104,y+156,x+430,y+450),'#111c24',width=0)
 rect((x+107,y+159,x+427,y+447),'#000000',width=0)
 ellipse((x+64,y+224,x+77,y+237),'#e04b58',INK,2)
 text(x+51,y+245,'BATTERY',8,'#edece2')
 text(x+36,y+521,'Nintendo',20,BLUE,'arial.ttf')
 text(x+139,y+515,'GAME BOY',32,BLUE,'arialbi.ttf')
 text(x+353,y+525,'TM',9,BLUE)
 if not ANIMATE:draw_controls(x,y)
 # Speaker grooves and their small specular lower edges.
 for i in range(6):
  sx=x+391+i*18;sy=y+756-i*8
  line([(sx,sy),(sx+33,sy+49)],'#9ea79f',12)
  line([(sx-2,sy-2),(sx+31,sy+47)],INK,7)
  line([(sx+5,sy),(sx+38,sy+48)],LIGHT,2)
 text(x+42,y+827,'DMG-01',11,'#7c877f')
 # A flat right-edge socket retains the correct upper-right cable attachment.
 if FLAT:rect((x+536,y+145,x+550,y+185),'#343e49',INK,2,r=2)
 else:
  poly([(x+540,y+143),(x+559,y+150),(x+559,y+190),(x+540,y+184)],'#343e49',INK,3)
  poly([(x+544,y+150),(x+555,y+154),(x+555,y+183),(x+544,y+179)],'#080f17')
 # Molded plug seats inside that socket and extends out to the right.
 poly([(x+550,y+151),(x+578,y+153),(x+578,y+183),(x+550,y+181)],'#9ca8ab',INK,3)
 rect((x+568,y+144,x+608,y+190),'#535f6d',INK,3,r=5)
 poly([(x+574,y+149),(x+602,y+149),(x+602,y+157),(x+574,y+157)],'#8495a0')
 for i in range(4):line([(x+576+i*7,y+163),(x+576+i*7,y+186)],'#283442',2)
 rect((x+606,y+155,x+619,y+180),'#44515e',INK,3,r=3)
 return dict(x=x+107,y=y+159,width=320,height=288)

def make_scene(folder):
 global art,draw
 art=Image.new('RGBA',(W*S,H*S));draw=ImageDraw.Draw(art)
 # Cable routes entirely above/outside the displays, ending at both right-side plugs.
 cable=cubic((839,307),(905,307),(842,72),(960,72))+cubic((960,72),(1150,72),(1540,72),(1759,72))+cubic((1759,72),(1850,72),(1850,307),(1739,307))
 line(cable,INK,18);line(cable,'#728591',11)
 highlight=[(x,y-3) for x,y in cable];line(highlight,'#afc1c8',3)
 screens=[shell(220,140),shell(1120,140)]
 if ANIMATE:
  for side,x in [('LEFT',252),('RIGHT',1152)]:art.crop((x*S,690*S,(x+480)*S,980*S)).save(folder/('controls-base-'+side+'.png'))
 rgba=art.resize((W,H),Image.Resampling.LANCZOS)
 rgba.save(folder/'shells-transparent.png')
 matte=rgba.getchannel('A');matte.save(folder/'luma-matte.png')
 scene=Image.new('RGB',(W,H),'black');scene.paste(rgba,mask=rgba.getchannel('A'));scene.save(folder/'shells-black.png')
 return screens

def main():
 global FLAT,ANIMATE
 parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--start',type=float,default=150);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--preview-only',action='store_true');parser.add_argument('--flat',action='store_true');parser.add_argument('--animate-buttons',action='store_true');parser.add_argument('--keys',type=Path);args=parser.parse_args()
 FLAT=args.flat;ANIMATE=args.animate_buttons
 folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=True)
 source=args.source.resolve();ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
 probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_format','-show_streams','-of','json',str(source)]))
 duration=float(probe['format']['duration'])-args.start
 if duration<=0:raise SystemExit('Source ends before the requested start time.')
 assert any(s['codec_type']=='audio' for s in probe['streams']),'Source must contain audio'
 screens=make_scene(folder)
 if ANIMATE:
  from dmg_button_timeline import render_controls
  keys=args.keys or source.with_name('keys-timed.json')
  video_stream=next(s for s in probe['streams'] if s['codec_type']=='video')
  frame_count=int(video_stream['nb_frames'])-round(args.start*30)
  render_controls(folder,keys,args.start,frame_count,control_tile)
 subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',str(args.start),'-i',str(source),'-frames:v','1',str(folder/'source-frame.png')],check=True)
 scene=Image.open(folder/'shells-black.png');frame=Image.open(folder/'source-frame.png');half=frame.width//2
 for i,screen in enumerate(screens):
  image=frame.crop((i*half,0,(i+1)*half,frame.height)).resize((320,288),Image.Resampling.NEAREST)
  scene.paste(image,(screen['x'],screen['y']))
 if ANIMATE:
  controls=Image.open(folder/'controls-preview.png')
  for i,x in enumerate([252,1152]):scene.paste(controls.crop((i*480,0,(i+1)*480,290)),(x,690))
 scene.save(folder/'preview.png')
 config=dict(flat_shells=FLAT,animated_buttons=ANIMATE,source=str(source),start_seconds=args.start,duration_seconds=duration,resolution=[W,H],fps=30,screens=screens,background='black',matte='luma-matte.mp4 (white foreground / black transparent)',audio=f'source audio, trimmed at the same {args.start}-second boundary')
 (folder/'composite.json').write_text(json.dumps(config,indent=2))
 if args.preview_only:print(folder/'preview.png');return
 left,right=screens
 filters=f"[0:v]split=2[l][r];[l]crop=iw/2:ih:0:0,scale=320:288:flags=neighbor[ls];[r]crop=iw/2:ih:iw/2:0,scale=320:288:flags=neighbor[rs];[1:v][ls]overlay={left['x']}:{left['y']}:shortest=1[a];[a][rs]overlay={right['x']}:{right['y']}:shortest=1,format=yuv420p[v]"
 if ANIMATE:
  filters=filters.replace(',format=yuv420p[v]', '[screened]')+";[2:v]split=2[cl][cr];[cl]crop=480:290:0:0[lc];[cr]crop=480:290:480:0[rc];[screened][lc]overlay=252:690:shortest=1[lcfull];[lcfull][rc]overlay=1152:690:shortest=1,format=yuv420p[v]"
 command=[ffmpeg,'-hide_banner','-y','-ss',str(args.start),'-i',str(source),'-loop','1','-framerate','30','-i',str(folder/'shells-black.png'),'-filter_complex',filters,'-map','[v]','-map','0:a:0','-c:v','libx264','-preset','fast','-crf','18','-r','30','-c:a','aac','-b:a','256k','-shortest','-movflags','+faststart',str(folder/'dmg-linked-composite.mp4')]
 if ANIMATE:
  insertion=command.index('-filter_complex');command[insertion:insertion]=['-i',str(folder/'button-controls.mkv')]
 with (folder/'render.log').open('w') as log:subprocess.run(command,stderr=log,stdout=log,check=True)
 frame_probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-select_streams','v:0','-show_entries','stream=nb_frames','-of','json',str(folder/'dmg-linked-composite.mp4')]))
 frame_count=int(frame_probe['streams'][0]['nb_frames'])
 command=[ffmpeg,'-hide_banner','-y','-loop','1','-framerate','30','-i',str(folder/'luma-matte.png'),'-frames:v',str(frame_count),'-an','-c:v','libx264','-preset','fast','-crf','0','-pix_fmt','yuv420p','-movflags','+faststart',str(folder/'luma-matte.mp4')]
 with (folder/'matte-render.log').open('w') as log:subprocess.run(command,stderr=log,stdout=log,check=True)
 print(folder/'dmg-linked-composite.mp4')
if __name__=='__main__':main()

"""Hand-drawn four-shade pixel cinematics, converted to native Game Boy tiles."""
import ast
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
tree = ast.parse((root / 'tools/make_ui_font.py').read_text())
glyphs = next(eval(compile(ast.Expression(n.value), '<local font>', 'eval'), {'__builtins__': {}})
              for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'glyphs' for t in n.targets))

# Compact lowercase lettering for the handheld's dialogue and footer.
small_letters = dict(zip('abcdefghijklmnopqrstuvwxyz', (
 '000/011/101/111/101','100/100/110/101/110','000/011/100/100/011',
 '001/001/011/101/011','000/010/101/110/011','011/010/111/010/010',
 '000/011/101/011/001','100/100/110/101/101','010/000/010/010/010',
 '001/000/001/101/010','100/101/110/101/101','110/010/010/010/011',
 '000/110/111/101/101','000/110/101/101/101','000/010/101/101/010',
 '000/110/101/110/100','000/011/101/011/001','000/101/110/100/100',
 '000/011/110/001/110','010/111/010/010/011','000/101/101/101/011',
 '000/101/101/101/010','000/101/101/111/101','000/101/010/010/101',
 '000/101/101/011/001','000/111/001/010/111')))
small_letters.update({'2':'110/001/010/100/111','.':'000/000/000/000/010',
                     '@':'010/101/111/100/011',' ':'000/000/000/000/000'})
def small_text(im, text, x, y, color):
    for i, char in enumerate(text):
        for yy, row in enumerate(small_letters[char].split('/')):
            for xx, bit in enumerate(row):
                if bit=='1': im.putpixel((x+i*4+xx,y+yy),color)

# Pillow's bundled Aileron font gives contacts familiar, unscaled letterforms.
credit_font = ImageFont.load_default(size=16)
footer_font = ImageFont.load_default(size=12)
def credit_text(im, text, x, y, font=credit_font):
    d=ImageDraw.Draw(im)
    d.fontmode='1'
    d.text((x,y),text,font=font,fill=0,anchor='lt')

def room(d):
    d.rectangle((0, 16, 159, 127), fill=2)
    # City lights through a studio window, with deliberate low-resolution bands.
    d.rectangle((7, 22, 101, 87), fill=3)
    d.rectangle((11, 26, 97, 83), fill=1)
    for x, h in ((12, 42), (28, 31), (46, 48), (65, 35), (83, 51)):
        d.rectangle((x, h, x+13, 83), fill=2)
        for yy in range(h+5, 80, 9):
            for xx in (x+3, x+9): d.rectangle((xx, yy, xx+1, yy+2), fill=0)
    d.rectangle((52, 24, 54, 84), fill=3)
    d.line((9, 66, 98, 66), fill=3, width=2)

def pads(d, x, y, size=10):
    for r in range(3):
        for c in range(4):
            px=x+c*(size+3);py=y+r*(size+3)
            d.rectangle((px, py, px+size, py+size), fill=3)
            d.rectangle((px+1, py+1, px+size-1, py+size-2), fill=2)

train_highlights=set()
def train_finish(im,variant):
    for y in range(24,72):
        for x in range(8,112):
            value=im.getpixel((x,y))
            if value==0 and variant in (0,9):train_highlights.add((x,y))
            im.putpixel((x,y),0 if value==4 else value)
    return im

def draw_scene(which, variant=0, emotion=0):
    im=Image.new('L',(160,144),3);d=ImageDraw.Draw(im)
    if which==0:
        # Frontal scene-girl portrait, centerline x=107 (right third).
        d.rectangle((0,16,159,127),fill=2)
        d.rectangle((4,24,57,84),fill=3);d.rectangle((8,28,53,80),fill=1)
        for x,h in ((9,43),(24,34),(39,48)):
            d.rectangle((x,h,x+11,80),fill=3)
            for y in range(h+5,78,9):d.line((x+3,y,x+6,y),fill=0)
        d.line((30,26,30,82),fill=3,width=2)
        d.line((6,63,55,63),fill=3,width=2)
        # Hair silhouette and shoulders reach the right edge of the frame.
        d.polygon([(76,43),(84,25),(105,19),(126,25),(139,43),(137,76),(147,99),(130,94),(125,106),(82,99),(73,82)],fill=3)
        d.polygon([(62,127),(70,100),(90,86),(123,86),(145,96),(159,107),(159,127)],fill=3)
        d.polygon([(74,124),(81,103),(94,94),(106,106),(120,94),(137,104),(159,117),(159,127)],fill=1)
        d.polygon([(98,78),(98,94),(107,102),(117,93),(116,78)],fill=2)
        d.polygon([(84,43),(96,30),(119,31),(131,44),(129,67),(120,83),(108,90),(95,84),(85,69)],fill=0)
        d.polygon([(123,45),(130,46),(127,67),(118,81),(109,86),(119,68)],fill=1)
        # Long, jagged side-swept fringe, with a light streak.
        d.polygon([(77,48),(82,29),(98,20),(119,21),(133,33),(139,51),(124,43),(117,52),(105,39),(95,51),(93,40),(85,60)],fill=3)
        d.polygon([(86,31),(100,25),(119,27),(128,33),(108,29),(98,34),(94,42)],fill=1)
        d.polygon([(82,53),(88,67),(91,93),(81,83),(77,92),(76,69)],fill=3)
        d.polygon([(129,48),(136,62),(135,91),(127,101),(127,82)],fill=3)
        # Heavy winged eyeliner, equal forward-facing pupils.
        lift=3 if emotion else 0
        d.line((88,54-lift,98,52-lift,102,55-lift),fill=3,width=2)
        d.line((113,55-lift,117,52-lift,127,54-lift),fill=3,width=2)
        if emotion==1:
            d.polygon([(89,56),(101,55),(100,63),(92,64)],fill=3)
            d.polygon([(114,55),(126,56),(123,64),(115,63)],fill=3)
            d.rectangle((92,56,99,62),fill=0);d.rectangle((116,56,123,62),fill=0)
            d.rectangle((95,57,97,62),fill=3);d.rectangle((118,57,120,62),fill=3)
        else:
            d.polygon([(89,57),(101,56),(99,61),(93,62)],fill=3)
            d.polygon([(114,56),(126,57),(122,62),(116,61)],fill=3)
            d.rectangle((92,57,99,59),fill=0);d.rectangle((116,57,123,59),fill=0)
            d.rectangle((95,57,97,61),fill=3);d.rectangle((118,57,120,61),fill=3)
        d.line((106,65,104,70,108,71),fill=2)
        if emotion==1:d.ellipse((105,76,109,80),fill=3)
        elif emotion==2:d.arc((100,71,114,81),0,165,fill=3,width=2)
        else:d.line((101,78,113,78),fill=3)
        d.point((107,83),fill=2)
        d.arc((72,20,142,88),175,360,fill=1,width=4)
        d.ellipse((74,46,89,73),fill=3);d.ellipse((77,50,86,69),fill=1)
        d.ellipse((129,46,143,73),fill=3);d.ellipse((132,50,140,69),fill=1)
        d.line((82,74,84,91,91,100),fill=3,width=2)
        # Sampling a record: platter/grooves and a complete balanced tonearm.
        d.polygon([(5,89),(110,85),(132,127),(0,127)],fill=3)
        d.polygon([(10,93),(106,89),(122,123),(3,124)],fill=1)
        d.ellipse((12,94,85,122),fill=3)
        d.ellipse((19,97,78,119),outline=2 if not variant&1 else 1)
        d.ellipse((25,100,72,116),outline=1 if not variant&1 else 2)
        d.ellipse((37,103,59,114),fill=0)
        d.ellipse((46,107,50,110),fill=3)
        if variant&1:d.line((43,107,45,105),fill=2)
        else:d.line((51,111,54,112),fill=2)
        wobble=(0,1,0,-1)[variant&3]
        # Thick silver arm with a dark outline, anchored at the bearing.
        d.line((103,91,96,97,92+wobble,110,77+wobble,114),fill=3,width=5)
        d.line((103,91,96,97,92+wobble,110,77+wobble,114),fill=0,width=3)
        d.ellipse((92,94,100,102),fill=3);d.ellipse((94,96,98,100),fill=2)
        # Cylindrical rear counterweight and adjustment ring.
        # Cartridge on the long end, with the stylus descending to the groove.
        d.polygon([(68+wobble,111),(79+wobble,111),(77+wobble,118),(70+wobble,118)],fill=3)
        d.line((70+wobble,112,77+wobble,112),fill=0,width=2)
        d.line((72+wobble,118,71+wobble,121),fill=0)
    elif which==1:
        d.rectangle((0,16,159,127),fill=2)
        for y in range(22,100,12):d.line((0,y,159,y-9),fill=1)
        # Low-angle pad machine and hands, with a waveform display.
        d.polygon([(14,43),(136,35),(159,115),(0,125)],fill=3)
        d.polygon([(18,47),(131,40),(150,109),(7,118)],fill=1)
        d.rectangle((26,49,85,66),fill=3)
        d.line((29,58,34,58,38,53,42,62,47,56,52,58,58,51,63,63,68,55,74,59,81,57),fill=0)
        for x in (99,113,127):
            d.ellipse((x-4,49,x+4,57),fill=3);d.line((x,50,x,53),fill=0)
        pads(d,29,75,10)
        d.rectangle((106,76,114,104),fill=3)
        d.rectangle((105,86,115,90),fill=0)
    elif which==2:
        # Train carriage, city outside, seated beatmaker and unmistakable handheld.
        d.rectangle((0,16,159,127),fill=1)
        d.rectangle((5,22,111,75),fill=3);d.rectangle((9,26,107,71),fill=0)
        # Sentinel marks exterior pixels; foreground remains opaque to sprites.
        d.rectangle((9,26,107,71),fill=4)
        d.rectangle((118,18,122,126),fill=3);d.rectangle((119,18,120,126),fill=0)
        for x in (19,94):
            d.line((x,16,x,28),fill=3,width=2);d.ellipse((x-5,26,x+5,37),outline=3,width=2)
        d.rounded_rectangle((2,89,112,113),radius=4,fill=3)
        d.rectangle((5,93,109,108),fill=2)
        d.line((19,114,17,127),fill=3,width=3);d.line((102,114,105,127),fill=3,width=3)
        # Single-ink vertical WERO handstyle with loose hooks and ink runs.
        tag=Image.new('L',(24,100),1);ink=ImageDraw.Draw(tag)
        strokes=[
            ([(1,3),(4,20),(11,8),(14,20),(22,1)],2),
            ([(0,7),(4,2),(5,10)],1),
            ([(22,26),(6,28),(2,45),(20,41)],2),
            ([(5,36),(18,32),(15,36)],2),
            ([(1,70),(6,51),(19,49),(22,53),(18,59),(6,61),(21,71)],2),
            ([(3,56),(11,52),(17,52)],1),
            ([(20,77),(12,74),(4,78),(1,88),(5,94),(15,93),(22,85),(21,79),(15,78)],2),
            ([(5,88),(7,81),(14,78)],1),
            ([(0,98),(21,94),(18,98)],1),
        ]
        for points,width in strokes:ink.line(points,fill=3,width=width,joint='curve')
        for x,y,end in ((4,19,25),(18,42,48),(20,69,76),(5,93,99)):
            ink.line((x,y,x,end),fill=3)
            ink.ellipse((x-1,end-1,x+1,end+1),fill=3)
        im.paste(tag,(128,24))
        # Frontal, rounded shoulders and a bowed head over a centered handheld.
        d.polygon([(44,98),(48,81),(56,73),(63,70),(77,70),(84,73),(92,81),(96,98),(85,108),(55,108)],fill=3)
        d.polygon([(49,96),(52,84),(60,78),(70,83),(80,78),(88,84),(91,96),(81,103),(59,103)],fill=2)
        d.polygon([(60,82),(70,87),(80,82),(81,102),(59,102)],fill=1)
        d.line((56,80,60,91),fill=0);d.line((84,80,80,91),fill=0)
        # Knees and feet face the camera rather than crossing sideways.
        d.polygon([(52,105),(65,104),(65,124),(61,127),(49,127),(51,116)],fill=3)
        d.polygon([(75,104),(88,105),(89,116),(91,127),(79,127),(75,124)],fill=3)
        d.rectangle((56,110,61,123),fill=2);d.rectangle((79,110,84,123),fill=2)
        h=8 if variant<3 else 0
        # Match the turntable portrait at the train shot's smaller scale.
        d.polygon([(48,46+h),(53,34+h),(67,30+h),(81,34+h),(90,46+h),(89,68+h),(95,83+h),(84,80+h),(81,88+h),(52,83+h),(46,71+h)],fill=3)
        d.polygon([(54,46+h),(62,37+h),(77,38+h),(85,47+h),(84,62+h),(78,73+h),(72,77+h),(68,77+h),(61,74+h),(55,64+h)],fill=0)
        # Asymmetric choppy fringe and the same muted light streak.
        d.polygon([(49,49+h),(52,36+h),(63,30+h),(77,31+h),(87,39+h),(91,51+h),(81,46+h),(76,52+h),(68,44+h),(61,52+h),(60,45+h),(54,58+h)],fill=3)
        d.polygon([(55,38+h),(65,34+h),(77,35+h),(83,39+h),(70,37+h),(63,40+h),(60,46+h)],fill=1)
        d.polygon([(52,53+h),(56,63+h),(58,80+h),(51,73+h),(48,79+h),(48,64+h)],fill=3)
        d.polygon([(84,50+h),(89,59+h),(88,79+h),(83,85+h),(83,72+h)],fill=3)
        # Keep her winged eyeliner when her eyes widen in surprise.
        surprised=variant>=3
        lift=2 if surprised else 0
        d.line((56,54+h-lift,63,53+h-lift,66,55+h-lift),fill=3,width=1)
        d.line((73,55+h-lift,76,53+h-lift,83,54+h-lift),fill=3,width=1)
        if surprised:
            d.polygon([(56,55+h),(65,54+h),(64,61+h),(58,62+h)],fill=3)
            d.polygon([(73,54+h),(83,55+h),(81,62+h),(74,61+h)],fill=3)
            d.rectangle((58,55+h,63,60+h),fill=0)
            d.rectangle((75,55+h,80,60+h),fill=0)
            d.rectangle((60,56+h,61,60+h),fill=3)
            d.rectangle((77,56+h,78,60+h),fill=3)
        else:
            d.polygon([(56,56+h),(65,55+h),(64,60+h),(59,61+h)],fill=3)
            d.polygon([(73,55+h),(83,56+h),(80,61+h),(75,60+h)],fill=3)
            d.rectangle((58,56+h,63,58+h),fill=0)
            d.rectangle((75,56+h,80,58+h),fill=0)
            left,right=(58,75) if variant in (1,2) else (60,77)
            d.rectangle((left,56+h,left+1,60+h),fill=3)
            d.rectangle((right,56+h,right+1,60+h),fill=3)
        d.line((69,62+h,68,65+h,71,66+h),fill=2)
        if surprised:d.ellipse((68,69+h,72,73+h),fill=3)
        else:d.line((65,70+h,73,70+h),fill=3)
        # Knit beanie sits behind the headphones; the jagged bangs stay exposed.
        d.polygon([(49,46+h),(51,37+h),(56,31+h),(65,27+h),(77,28+h),(86,33+h),(90,41+h),(91,47+h),(81,43+h),(74,40+h),(65,40+h),(56,43+h)],fill=2)
        d.line((52,37+h,57,32+h,65,29+h,76,30+h,84,34+h),fill=1)
        d.polygon([(49,43+h),(60,39+h),(73,38+h),(86,42+h),(91,47+h),(89,50+h),(78,45+h),(65,44+h),(53,48+h),(49,49+h)],fill=1)
        for x,y in ((53,44),(58,42),(63,41),(68,41),(73,41),(78,43),(83,44),(88,46)):
            d.line((x,y+h,x,y+2+h),fill=2)
        d.arc((46,30+h,93,77+h),175,360,fill=1,width=3)
        d.ellipse((47,48+h,57,66+h),fill=3);d.ellipse((49,51+h,55,63+h),fill=1)
        d.ellipse((84,48+h,94,66+h),fill=3);d.ellipse((86,51+h,92,63+h),fill=1)
        if variant<8:
            # Bored, hands resting in her lap until the handheld reaches her.
            d.polygon([(50,86),(55,87),(59,100),(62,105),(55,107),(50,101),(47,91)],fill=1)
            d.polygon([(90,86),(85,87),(81,100),(78,105),(85,107),(90,101),(93,91)],fill=1)
            d.line((49,91,56,93),fill=3,width=2);d.line((51,97,58,99),fill=3,width=2)
            d.line((91,91,84,93),fill=3,width=2);d.line((89,97,82,99),fill=3,width=2)
        else:
            d.polygon([(51,87),(55,87),(62,93),(65,97),(60,100),(54,96),(49,92)],fill=1)
            d.polygon([(89,87),(85,87),(78,93),(75,97),(80,100),(86,96),(91,92)],fill=1)
            d.line((52,88,56,93),fill=3,width=2);d.line((50,91,54,96),fill=3,width=2)
            d.line((88,88,84,93),fill=3,width=2);d.line((90,91,86,96),fill=3,width=2)
        # Exposed hands share the portrait's white skin tone.
        if variant<8:
            d.polygon([(55,101),(59,101),(62,105),(55,107)],fill=0)
            d.polygon([(81,101),(85,101),(85,107),(78,105)],fill=0)
        else:
            d.polygon([(60,93),(62,93),(65,97),(60,100),(58,97)],fill=0)
            d.polygon([(78,93),(80,93),(82,97),(80,100),(75,97)],fill=0)
        bx=-1 if variant==1 else 1 if variant==2 else 0;by=1 if variant==2 else 0
        d.arc((17+bx,72+by,30+bx,88+by),180,360,fill=3,width=3)
        d.rounded_rectangle((10+bx,78+by,37+bx,110+by),radius=5,fill=3)
        d.rounded_rectangle((13+bx,81+by,34+bx,107+by),radius=3,fill=2)
        d.rounded_rectangle((14+bx,94+by,33+bx,108+by),radius=2,fill=3)
        d.line((16+bx,98+by,31+bx,98+by),fill=1);d.line((29+bx,98+by,29+bx,101+by),fill=0)
        if variant>=3:
            d.ellipse((12,77,35,85),fill=3);d.line((16,80,30,80),fill=0,width=2)
        if variant<3:return train_finish(im,variant)
        dx,dy=((-46,-17),(-42,-29),(-32,-38),(-20,-40),(-9,-29),(0,-12),(0,0))[min(variant-3,6)]
        # Upper-left light: rear plane, right-side thickness and bottom shadow.
        d.polygon([(64+dx,79+dy),(75+dx,79+dy),(81+dx,84+dy),(81+dx,105+dy),(78+dx,109+dy),(65+dx,109+dy),(61+dx,105+dy),(61+dx,82+dy)],fill=3)
        d.polygon([(77+dx,82+dy),(80+dx,85+dy),(80+dx,104+dy),(77+dx,107+dy),(76+dx,103+dy)],fill=1)
        d.polygon([(64+dx,104+dy),(76+dx,104+dy),(79+dx,107+dy),(65+dx,107+dy),(63+dx,105+dy)],fill=2)
        d.rounded_rectangle((62+dx,80+dy,77+dx,104+dy),radius=3,fill=0)
        if variant>=3:
            d.line((56+dx,85+dy,59+dx,87+dy),fill=0)
            d.line((81+dx,96+dy,84+dx,98+dy),fill=0)
        if variant>=8:
            # The catch turns the front toward camera, revealing the living screen.
            d.rounded_rectangle((64+dx,83+dy,75+dx,94+dy),radius=2,fill=3)
            d.rectangle((65+dx,84+dy,74+dx,92+dy),fill=1)
            d.rectangle((66+dx,86+dy,67+dx,88+dy),fill=3)
            d.rectangle((71+dx,86+dy,72+dx,88+dy),fill=3)
            d.arc((67+dx,88+dy,72+dx,91+dy),0,180,fill=3)
            d.line((65+dx,98+dy,69+dx,98+dy),fill=3)
            d.line((67+dx,96+dy,67+dx,100+dy),fill=3)
            d.point((73+dx,98+dy),fill=3)
        return train_finish(im,variant)
    elif which==3:
        # Time dissolves: headphones and eyes behind a constellation of clocks.
        d.rectangle((0,16,159,127),fill=3)
        for x,y,r in ((17,39,15),(138,42,18),(27,104,19),(130,108,16),(81,29,10)):
            d.ellipse((x-r,y-r,x+r,y+r),fill=2,outline=0,width=2)
            d.line((x,y-r+3,x,y-r+5),fill=0)
            d.line((x+r-5,y,x+r-3,y),fill=0)
            d.line((x,y,x+5,y-7),fill=0,width=2);d.line((x,y,x-6,y-3),fill=0)
        d.polygon([(40,124),(49,91),(65,80),(99,82),(117,105),(125,127)],fill=1)
        d.polygon([(47,60),(58,40),(88,37),(108,57),(103,82),(88,96),(67,93),(52,79)],fill=2)
        d.polygon([(53,57),(61,45),(89,43),(101,59),(96,79),(83,89),(67,85),(58,74)],fill=0)
        d.polygon([(43,66),(49,42),(64,30),(90,31),(107,45),(113,69),(106,91),(99,98),(98,78),(91,51),(81,62),(73,48),(62,66),(60,52),(54,91),(43,96)],fill=3)
        d.line((56,42,67,35,88,36),fill=1,width=2)
        d.line((61,68,75,65),fill=3,width=2);d.line((86,65,97,68),fill=3,width=2)
        d.line((65,70,72,69),fill=3);d.line((88,69,94,70),fill=3)
        d.arc((41,33,113,100),170,290,fill=1,width=4)
        d.ellipse((43,61,57,85),fill=3);d.ellipse((46,65,54,81),fill=0)
        for x,y in ((7,76),(150,78),(109,25),(38,24),(56,113),(101,112)):
            d.line((x-2,y,x+2,y),fill=0);d.line((x,y-2,x,y+2),fill=0)
    elif which==4:
        # Fragments align into a beat: an illuminated sampler arrangement screen.
        d.rectangle((0,16,159,127),fill=2)
        d.polygon([(0,16),(159,16),(159,40),(0,48)],fill=3)
        d.line((20,34,45,28,58,35),fill=0,width=2)
        d.line((99,34,114,28,141,32),fill=0,width=2)
        d.rectangle((10,48,149,118),fill=3)
        d.rectangle((14,52,145,114),fill=0)
        for x in range(23,144,8):d.line((x,55,x,111),fill=1)
        for y in (65,81,97,112):d.line((17,y,142,y),fill=1)
        for row,starts in enumerate(((0,6,10,14),(4,12),(2,5,8,11,15))):
            for step in starts:
                x=17+step*8;y=55+row*16
                d.rectangle((x,y,x+6,y+8),fill=3)
                d.line((x+1,y+6,x+2,y+3,x+3,y+5,x+4,y+1,x+5,y+4),fill=0)
        d.rectangle((85,53,86,112),fill=2)
        d.polygon([(0,107),(15,103),(29,112),(33,119),(24,126),(0,127)],fill=3)
        d.polygon([(0,112),(14,108),(24,115),(26,120),(20,123),(0,123)],fill=1)
        d.polygon([(159,107),(145,103),(131,113),(128,121),(139,127),(159,127)],fill=3)
        d.polygon([(159,112),(146,108),(135,115),(134,121),(141,124),(159,123)],fill=1)
    else:
        # The handheld wakes up: BMO lives inside the Game Boy's actual screen.
        d.rectangle((0,16,159,127),fill=3)
        # The four stars are animated as sprites, independently of the face.
        d.polygon([(34,127),(28,104),(32,75),(43,68),(54,89),(48,127)],fill=2)
        d.polygon([(126,127),(133,103),(127,76),(117,69),(107,89),(111,127)],fill=2)
        d.rounded_rectangle((43,21,117,130),radius=7,fill=2)
        d.rounded_rectangle((46,23,114,128),radius=6,fill=0)
        d.rounded_rectangle((50,29,110,85),radius=4,fill=3)
        d.rectangle((55,34,105,78),fill=1)
        d.rectangle((57,36,103,76),fill=0)
        if variant&1:
            d.line((65,51,70,51),fill=3,width=2);d.line((90,51,95,51),fill=3,width=2)
        else:
            d.ellipse((65,46,70,55),fill=3);d.ellipse((90,46,95,55),fill=3)
        d.arc((70,48,91,66),0,180,fill=3,width=2)
        d.rectangle((59,94,65,111),fill=3);d.rectangle((53,100,71,105),fill=3)
        d.ellipse((94,95,102,103),fill=3);d.ellipse((83,103,91,111),fill=3)
        d.line((72,118,80,116),fill=2,width=2);d.line((86,118,94,116),fill=2,width=2)
        for x in (96,100,104):d.line((x,115,x,123),fill=2)
        if variant&2:
            # A pointed comic balloon connects directly to BMO's smile.
            d.polygon([(81,63),(102,72),(97,81)],fill=3)
            d.polygon([(83,65),(102,74),(99,78)],fill=0)
            d.rounded_rectangle((94,69,158,103),radius=6,fill=3)
            d.rounded_rectangle((96,71,156,101),radius=5,fill=0)
            for line,y in zip(('this version','is obsolete'),(78,89)):
                small_text(im,line,126-(len(line)*4-1)//2,y,3)
    # Widescreen crop and a subtle title-safe frame.
    d.rectangle((0,0,159,15),fill=3);d.rectangle((0,128,159,143),fill=3)
    if which==5:
        address='y2kcrisis.com'
        address_font=footer_font
        credit_text(im,address,(160-address_font.getbbox(address)[2])//2,3,address_font)
        credit_text(im,'@bestjonever',(160-footer_font.getbbox('@bestjonever')[2])//2,130,footer_font)
    return im

phrases=[['a processor running'],['is like an animal breathing'],['time is an illusion...','that helps things make sense'],[],[],['']]
array=lambda xs:','.join(map(str,xs))
for scene in (0,1,2,5):
    tiles=[];lookup={}
    def tile(im):
        data=[]
        for y in range(8):
            pixels=[im.getpixel((x,y)) for x in range(8)]
            data.extend((sum((v&1)<<(7-x) for x,v in enumerate(pixels)),
                         sum(((v>>1)&1)<<(7-x) for x,v in enumerate(pixels))))
        key=bytes(data)
        if key not in lookup:lookup[key]=len(tiles);tiles.append(key)
        return lookup[key]
    im=draw_scene(scene)
    if scene==0:ImageDraw.Draw(im).rectangle((0,0,159,15),fill=3)
    if scene==2:
        train_window_base=im.copy()
        # This area is fully covered by the animated window layer at runtime.
        pass
    screen=[]
    for y in range(0,144,8):
        for x in range(0,160,8):
            screen.append(0 if scene==2 and 8<=x<104 and 32<=y<112 else tile(im.crop((x,y,x+8,y+8))))
    texts=[]
    for phrase in phrases[scene]:
        prefixes=[]
        for count in range(29):
            line=Image.new('L',(160,8),3)
            if scene==5:
                pass # Handheld credits are already part of the static background.
            advance=5 if len(phrase)>26 else 6
            # Give the long MPC caption a blank pixel between every letter.
            # Narrow word spaces let its full 5x7 lettering fit without touching.
            advances=[3 if c==' ' else 6 for c in phrase] if len(phrase)>26 else [advance]*len(phrase)
            width=sum(advances)-1
            assert width<=160,(phrase,width)
            left=(160-width)//2
            printed=count if scene!=2 or phrase!='that helps things make sense' else (28 if count==28 else 0)
            cursor=left
            for i,c in enumerate(phrase[:printed]):
                for y,row in enumerate(glyphs.get(c.upper(),['00000']*7)):
                    for x,v in enumerate(row):
                        if v=='1':line.putpixel((cursor+x,y),0)
                cursor+=advances[i]
            prefixes.append([tile(line.crop((x,0,x+8,8))) for x in range(0,160,8)])
        texts.append(prefixes)
    motion=[]
    if scene in (0,5):
        bounds=(8,88,112,128) if scene==0 else (56,40,160,104)
        for variant in range(4):
            shot=draw_scene(scene,variant)
            motion.append([tile(shot.crop((x,y,x+8,y+8))) for y in range(bounds[1],bounds[3],8) for x in range(bounds[0],bounds[2],8)])
    if scene==2:
        motionbase=len(tiles);train_frames=[]
        for variant in range(10):
            shot=draw_scene(2,variant)
            pass
            pixels=[]
            for y in range(32,112,8):
                for x in range(8,104,8):
                    chunk=[]
                    for yy in range(8):
                        colors=[shot.getpixel((x+xx,y+yy)) for xx in range(8)]
                        chunk.extend((sum((v&1)<<(7-i) for i,v in enumerate(colors)),sum(((v>>1)&1)<<(7-i) for i,v in enumerate(colors))))
                    pixels.extend(chunk)
                    if variant==0:
                        screen[(y//8)*20+x//8]=len(tiles)
                        tiles.append(bytes(chunk))
            train_frames.append(pixels)
        for group in range(2):
            code=f'#pragma bank {25+group}\n#include "api.h"\n'
            code+='static const uint8_t frames[5][1920]={'+','.join('{'+array(p)+'}' for p in train_frames[group*5:group*5+5])+'};\n'
            # Only upload tiles changed by this pose's possible predecessors.
            code+=f'void train_motion{group}(uint8_t frame) BANKED {{switch(frame%5){{'
            for local in range(5):
                pose=group*5+local
                previous={0:[],1:[0,2],2:[0,1],3:[1,2]}.get(pose,[pose-1])
                changed=[i for i in range(120) if any(train_frames[pose][i*16:(i+1)*16]!=train_frames[p][i*16:(i+1)*16] for p in previous)]
                code+=f'case {local}:'
                while changed:
                    start=changed.pop(0);end=start+1
                    while changed and changed[0]==end:end=changed.pop(0)+1
                    code+=f'set_bkg_data({motionbase+start},{end-start},frames[{local}]+{start*16});'
                code+='break;'
            code+='}}\n'
            (root/f'src/train_motion{group}.c').write_text(code)
    assert len(tiles)<=256,(scene,len(tiles))
    if scene==1:assert len(tiles)<224
    out=f'#pragma bank {22+scene}\n#include "api.h"\n'
    out+='static const uint8_t tiles[]={'+array(b for t in tiles for b in t)+'};\n'
    out+='static const uint8_t screen[]={'+array(screen)+'};\n'
    out+=f'static const uint8_t text[{len(texts)}][29][20]={{'+','.join('{'+','.join('{'+array(p)+'}' for p in line)+'}' for line in texts)+'};\n'
    if motion:out+=f'static const uint8_t motion[{len(motion)}][{len(motion[0])}]={{'+','.join('{'+array(p)+'}' for p in motion)+'};\n'
    if scene==0:
        reactions=[]
        for emotion in range(3):
            portrait=draw_scene(0,emotion=emotion);sprite=[]
            for yy in range(48,88,8):
                for xx in range(88,128,8):
                    for y in range(8):
                        colors=[1 if portrait.getpixel((xx+x,yy+y))==0 else 3 if portrait.getpixel((xx+x,yy+y))==3 else 2 for x in range(8)]
                        sprite.extend((sum((c&1)<<(7-x) for x,c in enumerate(colors)),sum(((c>>1)&1)<<(7-x) for x,c in enumerate(colors))))
            reactions.append(sprite)
        out+='static const uint8_t reactions[3][400]={'+','.join('{'+array(p)+'}' for p in reactions)+'};\n'
    if scene==2:out+='static const uint8_t border[32]={0};\nstatic uint8_t train_window_pose;\n'
    clear='for(i=0;i<32;i++)set_bkg_tiles(0,i,32,1,border);' if scene==2 else ''
    out+=f'void cinema{scene}(uint8_t line,uint8_t count,uint8_t load) BANKED {{\n'
    out+=f' uint16_t i;if(load){{DISPLAY_OFF;HIDE_SPRITES;SPRITES_8x8;SCX_REG=SCY_REG=0;OBP0_REG=0xe4;for(i=0;i<40;i++)move_sprite(i,0,0);for(i=0;i<{len(tiles)};i++)set_bkg_data(i,1,tiles+i*16);{clear}set_bkg_tiles(0,0,20,18,screen);SHOW_BKG;DISPLAY_ON;}}\n'
    if scene==5:
        out+=' HIDE_WIN;\n}\n'
    else:
        out+=' if(count>28)count=28;LCDC_REG|=0x40;set_win_tiles(0,0,20,1,text[line][count]);set_win_tiles(0,1,20,1,text[0][0]);move_win(7,132);SHOW_WIN;\n}\n'
    if motion:
        x,y,right,bottom=bounds
        out+=f'void cinema{scene}_motion(uint8_t frame) BANKED {{set_bkg_tiles({x//8},{y//8},{(right-x)//8},{(bottom-y)//8},motion[frame%{len(motion)}]);}}\n'
    if scene==2:
        out+='void train_motion0(uint8_t frame) BANKED;\nvoid train_motion1(uint8_t frame) BANKED;\n'
        out+='void cinema2_motion(uint8_t frame) BANKED {train_window_pose=frame;if(frame<5)train_motion0(frame);else train_motion1(frame-5);}\n'
    if scene==0:
        out+='''void cinema0_react(uint8_t emotion) BANKED {
 uint8_t i;SPRITES_8x8;OBP0_REG=0xd0;
 for(i=0;i<25;i++){set_sprite_data(i,1,reactions[emotion%3]+(uint16_t)i*16);set_sprite_tile(i,i);set_sprite_prop(i,0);move_sprite(i,96+(i%5)*8,64+(i/5)*8);}
 SHOW_SPRITES;
}
'''
    if scene==2:
        window_frames=[]
        for phase in range(8):
            view=Image.new('L',(104,48),0);vd=ImageDraw.Draw(view)
            for j in range(-2,9):
                xx=j*24-phase*3
                vd.rectangle((xx,8+(j%3)*3,xx+16,47),fill=2)
            for j in range(-2,12):
                xx=j*24-phase*12;height=(25,18,30,22)[j%4]
                vd.rectangle((xx,height,xx+14,47),fill=3)
                for yy in range(height+4,47,7):
                    for wx in (xx+3,xx+9):vd.point((wx,yy),fill=1)
            # Preserve white foreground highlights without tinting the portrait.
            for xx,yy in train_highlights:
                view.putpixel((xx-8,yy-24),0)
            pixels=[]
            for ty in range(0,48,16):
                for tx in range(0,104,8):
                    for yy in range(16):
                        colors=[view.getpixel((tx+xx,ty+yy)) for xx in range(8)]
                        pixels.extend((sum((c&1)<<(7-x) for x,c in enumerate(colors)),sum(((c>>1)&1)<<(7-x) for x,c in enumerate(colors))))
            window_frames.append(pixels)
        # Stencil every flying pose into the exterior sprite data. BG shade zero
        # is white but does not block behind-BG sprites on DMG hardware.
        lookup_masks=[[255]*39 for _ in range(10)];patches=[[] for _ in range(8)]
        nextslot=0
        visible={(r,c) for r in range(3) for c in range(13)
                 if (c<7 if r==0 else c<5) or c>=10}
        for pose in range(3,8):
            shot=draw_scene(2,pose)
            dx,dy=((-46,-17),(-42,-29),(-32,-38),(-20,-40),(-9,-29))[pose-3]
            for row,col in sorted(visible):
                stencil=[]
                for yy in range(16):
                    y=24+row*16+yy;bits=0
                    for xx in range(8):
                        x=8+col*8+xx
                        if 62+dx<=x<=77+dx and 80+dy<=y<=104+dy and shot.getpixel((x,y))==0:
                            bits|=128>>xx
                    stencil.append(bits)
                if not any(stencil):continue
                cell=row*13+col;lookup_masks[pose][cell]=nextslot;nextslot+=1
                for phase in range(8):
                    tile=list(window_frames[phase][cell*32:cell*32+32])
                    for yy,bits in enumerate(stencil):
                        tile[yy*2]&=255^bits;tile[yy*2+1]&=255^bits
                    patches[phase].extend(tile)
        code='#pragma bank 28\n#include "api.h"\n'
        code+='static const uint8_t passing[8][1248]={'+','.join('{'+array(p)+'}' for p in window_frames)+'};\n'
        code+='static const uint8_t masks[10][39]={'+','.join('{'+array(p)+'}' for p in lookup_masks)+'};\n'
        code+=f'static const uint8_t solid[8][{nextslot*32}]={{'+','.join('{'+array(p)+'}' for p in patches)+'};\n'
        code+='''void train_window_draw(uint8_t phase,uint8_t pose) BANKED {
 uint8_t i,slot;if(pose>9)pose=9;phase&=7;
 set_sprite_data(0,78,passing[phase]);
 for(i=0;i<39;i++){slot=masks[pose][i];if(slot!=255)set_sprite_data(i*2,2,solid[phase]+(uint16_t)slot*32);}
}
'''
        (root/'src/train_window.c').write_text(code)
        out+='void train_window_draw(uint8_t phase,uint8_t pose) BANKED;\n'
        out+='''void cinema2_ride(uint16_t frame) BANKED {
 uint8_t i,j,col,row,phase=(frame>>3)&7;int8_t sx,sy;static uint8_t previous=255,previouspose=255;
 static const int8_t swayx[8]={0,0,1,1,0,0,-1,-1};
 static const int8_t swayy[8]={0,1,1,0,0,-1,-1,0};
 sx=swayx[(frame>>4)&7];sy=swayy[(frame>>4)&7];SCX_REG=sx;SCY_REG=sy;
 if(frame<3)previous=255;
 if(phase!=previous||train_window_pose!=previouspose){train_window_draw(phase,train_window_pose);previous=phase;previouspose=train_window_pose;}
 OBP0_REG=0xe4;SPRITES_8x16;
 for(i=0;i<26;i++){if(i<10){row=0;col=i<7?i:i+3;}else{j=i-10;row=1+j/8;col=j%8;if(col>=5)col+=5;}set_sprite_tile(i,(row*13+col)*2);set_sprite_prop(i,0x80);move_sprite(i,16+col*8-sx,40+row*16-sy);}
 SHOW_SPRITES;
}
'''
    if scene==5:
        stars=[]
        for phase in range(4):
            star=Image.new('L',(8,8),0);sd=ImageDraw.Draw(star)
            radius=(0,1,3,1)[phase];shade=2 if phase==0 else 1
            sd.line((3-radius,3,3+radius,3),fill=shade)
            sd.line((3,3-radius,3,3+radius),fill=shade)
            if phase==2:
                for xx,yy in ((1,1),(5,1),(1,5),(5,5)):sd.point((xx,yy),fill=2)
            pixels=[]
            for yy in range(8):
                colors=[star.getpixel((xx,yy)) for xx in range(8)]
                pixels.extend((sum((c&1)<<(7-x) for x,c in enumerate(colors)),sum(((c>>1)&1)<<(7-x) for x,c in enumerate(colors))))
            stars.append(pixels)
        out+='static const uint8_t stars[4][16]={'+','.join('{'+array(p)+'}' for p in stars)+'};\n'
        out+='''void cinema5_stars(uint8_t frame) BANKED {
 uint8_t i;static const uint8_t x[4]={14,152,24,142},y[4]={48,54,124,117};
 SPRITES_8x8;OBP0_REG=0xe0;
 for(i=0;i<4;i++){set_sprite_data(i,1,stars[((frame>>3)+i)&3]);set_sprite_tile(i,i);set_sprite_prop(i,0);move_sprite(i,x[i],y[i]);}
 SHOW_SPRITES;
}
'''
    if scene==1:
        import math
        padboxes=[];padpixels=[]
        for pad in range(12):
            px=29+(pad%4)*13;py=75+(pad//4)*13
            shot=im.copy();ImageDraw.Draw(shot).rectangle((px+1,py+1,px+9,py+8),fill=0)
            tx=px//8;ty=py//8;w=(px+10)//8-tx+1;h=(py+10)//8-ty+1
            padboxes.append([tx,ty,w,h]);pixels=[]
            for yy in range(ty,ty+h):
                for xx in range(tx,tx+w):
                    for dy in range(8):
                        row=[shot.getpixel((xx*8+dx,yy*8+dy)) for dx in range(8)]
                        pixels.extend((sum((v&1)<<(7-dx) for dx,v in enumerate(row)),sum(((v>>1)&1)<<(7-dx) for dx,v in enumerate(row))))
            padpixels.append(pixels+[0]*(144-len(pixels)))
        out+='static const uint8_t padboxes[12][4]={'+','.join('{'+array(p)+'}' for p in padboxes)+'};\n'
        out+='static const uint8_t padpixels[12][144]={'+','.join('{'+array(p)+'}' for p in padpixels)+'};\n'
        scope_frames=[]
        for phase in range(8):
            trace=Image.new('L',(64,16),3);td=ImageDraw.Draw(trace);points=[]
            for x in range(64):
                value=3*math.sin((x+phase*3)*math.pi/10)+2*math.sin((x-phase*2)*math.pi/5)
                points.append((x,max(1,min(14,round(8-value)))))
            td.line(points,fill=0)
            pixels=[]
            for ty in (0,8):
                for tx in range(0,64,8):
                    for y in range(8):
                        row=[trace.getpixel((tx+x,ty+y)) for x in range(8)]
                        pixels.extend((sum((v&1)<<(7-x) for x,v in enumerate(row)),sum(((v>>1)&1)<<(7-x) for x,v in enumerate(row))))
            scope_frames.append(pixels)
        out+='static const uint8_t scope_frames[8][256]={'+','.join('{'+array(p)+'}' for p in scope_frames)+'};\n'
        out+='''
void cinema1_motion(uint8_t step,uint8_t phase) BANKED {
 uint8_t x,y,row,col,tile,pad,w,h,p[20];static uint8_t ready,lastpad=255;
 /* Stored art only: no oscillators, sample analysis or drawing math at runtime. */
 for(tile=0;tile<16;tile++)set_bkg_data(224+tile,1,scope_frames[phase&7]+(uint16_t)tile*16);
 if(!ready){for(row=0;row<2;row++){for(col=0;col<8;col++)p[col]=224+row*8+col;set_bkg_tiles(3,6+row,8,1,p);}ready=1;}
 pad=step%12;if(pad==lastpad)return;lastpad=pad;
 /* Replace the entire pad face, preserving its border and surrounding art. */
 for(row=9;row<14;row++)set_bkg_tiles(3,row,8,1,screen+(uint16_t)row*20+3);
 x=padboxes[pad][0];y=padboxes[pad][1];w=padboxes[pad][2];h=padboxes[pad][3];
 for(tile=0;tile<w*h;tile++)set_bkg_data(240+tile,1,padpixels[pad]+(uint16_t)tile*16);
 for(row=0;row<h;row++){
  for(col=0;col<w;col++)p[col]=240+row*w+col;
  set_bkg_tiles(x,y+row,w,1,p);
 }
}
'''
    (root/f'src/cinema{scene}.c').write_text(out)
    print(f'Cinema {scene+1}: {len(tiles)} native tiles')

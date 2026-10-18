"""Native pixel-camera zoom from the handheld into the full-screen face."""
from pathlib import Path
from PIL import Image, ImageDraw

root=Path(__file__).resolve().parents[1]
# Read drawing definitions without running the cinematic file-generation loop.
namespace={'__file__':str(root/'tools/make_cinema.py')}
exec(compile((root/'tools/make_cinema.py').read_text().split('\nphrases=')[0], 'cinema drawings', 'exec'),namespace)
source=namespace['draw_scene'](5)
# Credits belong to the cutscene, not the camera zoom's two 128-tile buffers.
source_draw=ImageDraw.Draw(source)
source_draw.rectangle((0,0,159,15),fill=3)
source_draw.rectangle((0,128,159,143),fill=3)
array=lambda xs:','.join(map(str,xs))
frames=[]
for frame in range(18):
    t=frame/17
    eased=t*t*(3-2*t)
    scale=3.5**eased
    cy=56+16*eased
    im=source.transform((160,144),Image.Transform.AFFINE,
                        (1/scale,0,80-80/scale,0,1/scale,56-cy/scale),
                        Image.Resampling.NEAREST,fillcolor=3)
    d=ImageDraw.Draw(im)
    pad=round(3*eased)
    viewport=(round(80+(57-80)*scale)-pad,round(cy+(36-56)*scale)-pad,
              round(80+(103-80)*scale)+pad,round(cy+(76-56)*scale)+pad)
    if frame==17:viewport=(0,0,159,143)
    d.rectangle(viewport,fill=0)
    # Landmarks expand continuously into the exact final native proportions.
    def box(a,b):return tuple(round(x+(y-x)*eased) for x,y in zip(a,b))
    d.ellipse(box((65,46,70,55),(36,41,54,69)),fill=3)
    d.ellipse(box((90,46,95,55),(106,41,124,69)),fill=3)
    d.arc(box((70,48,91,66),(51,61,109,108)),0,180,fill=3,width=round(2+2*eased))
    tiles=[];lookup={};screen=[]
    for ty in range(0,144,8):
        for tx in range(0,160,8):
            data=[]
            for y in range(8):
                colors=[im.getpixel((tx+x,ty+y)) for x in range(8)]
                data.extend((sum((v&1)<<(7-x) for x,v in enumerate(colors)),sum(((v>>1)&1)<<(7-x) for x,v in enumerate(colors))))
            key=bytes(data)
            if key not in lookup:lookup[key]=len(tiles);tiles.append(key)
            screen.append(lookup[key])
    assert len(tiles)<=128,(frame,len(tiles))
    frames.append((tiles,screen))

for group in range(3):
    out=f'#pragma bank {29+group}\n#include "api.h"\n'
    total=0
    for local in range(6):
        tiles,screen=frames[group*6+local];total+=len(tiles)*16+360
        out+=f'static const uint8_t tiles{local}[]={{'+array(b for tile in tiles for b in tile)+'};\n'
        out+=f'static const uint8_t screen{local}[]={{'+array(screen)+'};\n'
    assert total<15000,(group,total)
    out+='extern uint8_t zoombuffer;\n'
    out+=f'void zoom{group}(uint8_t frame) BANKED {{uint16_t i,n;uint8_t row,col,buf[20];const uint8_t *pixels,*map;switch(frame%6){{\n'
    for local in range(6):
        out+=f'case {local}:pixels=tiles{local};map=screen{local};n={len(frames[group*6+local][0])};break;\n'
    out+='default:return;}'
    if group==0:out+='if(!frame){DISPLAY_OFF;}'
    out+='HIDE_SPRITES;SCX_REG=SCY_REG=0;BGP_REG=0xe4;zoombuffer^=128;for(i=0;i<n;i++)set_bkg_data(zoombuffer+i,1,pixels+i*16);for(row=0;row<18;row++){for(col=0;col<20;col++)buf[col]=map[(uint16_t)row*20+col]+zoombuffer;set_bkg_tiles(0,row,20,1,buf);}SHOW_BKG;'
    if group==0:out+='if(!frame){DISPLAY_ON;}'
    out+='}\n'
    (root/f'src/zoom{group}.c').write_text(out)
    print(f'Zoom bank {29+group}: six frames, {total} asset bytes')

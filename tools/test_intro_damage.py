"""Exercise ten intro glitches, lasting damage, and the two-pulse prompt."""
from pathlib import Path
from pyboy import PyBoy

symbols={line.split()[1]:int(line.split()[2],16) for line in Path('build/GAYBOY.noi').read_text().splitlines() if line.startswith('DEF ')}

def run(cgb):
    p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,cgb=cgb)
    p.set_emulation_speed(0)
    val=lambda name:p.memory[symbols['_'+name]]
    runs=[];on=None;length=0;glitches=[];recoveries=[];active=False;final_frame=None;first_face=None;capture=None;sounds=[];music_end=None
    try:
        for frame in range(16500):
            p.tick(1)
            if capture is not None and frame>=capture[0]:
                p.screen.image.save(f'build/cracks-{capture[1]:02d}.png');capture=None
            if val('intro_audio_scene')!=4:continue
            a=symbols['_intro_scene_ticks'];time=(p.memory[a]|p.memory[a+1]<<8)*15//64
            if time<=75:continue
            if val('introfade')==4 and music_end is None:music_end=frame
            if first_face is None:first_face=frame
            fault=p.memory[0xff43]!=0 or p.memory[0xff42]!=0
            if fault and not active:
                glitches.append(frame);sounds.append(set())
            if fault:sounds[-1].add(tuple(p.memory[a] for a in (0xff10,0xff11,0xff13,0xff14,0xff16,0xff18,0xff19,0xff22)))
            if active and not fault:
                recoveries.append(frame)
                if len(recoveries) in (1,3,5,7,9,10) and not cgb:
                    capture=(frame+30,len(recoveries))
                if len(recoveries)==10:final_frame=frame
            active=fault
            if len(glitches)==0:
                base=val('zoombuffer')^128
                address=0x9000+((base+60+128)%256-128)*16
                mapped=list(p.memory[0x9a00:0x9a14])==[(base+60+i)&255 for i in range(20)]
                visible=mapped and any(p.memory[address:address+320])
                if visible==on:length+=1
                else:
                    if on is not None:runs.append((on,length))
                    on=visible;length=1
            if len(glitches)>=1 and not active and time>750:
                assert p.memory[0xff21]==0,'Glitch noise persisted during calm interval'
                if val('introfade')==4:assert p.memory[0xff12]==0 and p.memory[0xff17]==0,'Glitch pulses persisted during calm interval'
            if final_frame is not None and frame>final_frame+120:
                ids=[p.memory[0x9800+row*32+col] for row in range(18) for col in range(20)]
                assert len(set(ids))>20,'Final damage disappeared or became a blank screen'
                pixels=[]
                for y in range(144):
                    for x in range(160):
                        tile=p.memory[0x9800+(y//8)*32+x//8]
                        tile=tile if tile<128 else tile-256
                        addr=0x9000+tile*16+(y%8)*2
                        bit=7-x%8
                        pixels.append(((p.memory[addr]>>bit)&1)|(((p.memory[addr+1]>>bit)&1)<<1))
                scope={'__file__':str(Path('tools/make_intro.py').resolve())}
                exec(Path('tools/make_intro.py').read_text().split('assert len(tiles) < 256')[0],scope)
                assert min(sum(a!=b for a,b in zip(pixels,image.getdata())) for image in scope['face_images'])>1000,'Final emote recovered instead of retaining hardware damage'
                break
        else:raise AssertionError('Did not reach ten damage cycles')
        pulses=[n for state,n in runs if state]
        assert len(pulses)==2 and all(55<=n<=65 for n in pulses),('Prompt did not stop after two pulses',runs)
        assert len(recoveries)>=10
        assert music_end is not None and 295<=glitches[0]-music_end<=310,('Damage did not wait five seconds after music',music_end,glitches[0])
        assert len({frozenset(sound) for sound in sounds[:10]})==10,'Glitch sounds repeated'
        assert all(592<=b-a<=625 for a,b in zip(recoveries,glitches[1:])),('Calm interval changed',recoveries,glitches)
        assert all(8<=b-a<=45 for a,b in zip(glitches,recoveries)),('Glitch duration changed',glitches,recoveries)
        p.button_press('start');p.tick(120)
        assert not val('introactive') and not val('intro_audio_running'),'Start did not leave damaged intro'
        print('PASS', 'CGB' if cgb else 'DMG',': two prompt pulses, ten glitches, quiet recoveries, persistent final damage, Start exit')
    finally:p.stop(save=False)

run(False)
run(True)

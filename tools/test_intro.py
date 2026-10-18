"""Check musical scene boundaries, uninterrupted timer and one-way intro."""
from pathlib import Path
import re
import numpy as np
from pyboy import PyBoy
symbols={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
texts={}
for scene,file in enumerate(('cinema0','cinema1','cinema2','cinema5')):
    source=Path('src/'+file+'.c').read_text()
    block=re.search(r'static const uint8_t text.*?=\{(.*?)\};',source,re.S)[1]
    texts[scene]=list(map(int,re.findall(r'\d+',block)))
assert 'scope_frames' in Path('src/cinema1.c').read_text()
def run(cgb):
    p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,cgb=cgb);p.set_emulation_speed(0)
    val=lambda name:p.memory[symbols['_'+name]]
    word=lambda name:val(name)|(p.memory[symbols['_'+name]+1]<<8)
    ticks=[];drums=[];drumsteps=[];steps=[];entries={};pictures=set();window=set();caption_state=None;caption_since=0;fades=set();starframes=set();rasterframes=set();promptframes=set()
    def hook(name,cb):
        addr=symbols['_'+name];p.hook_register(addr>>16,addr&65535,cb,None)
    hook('intro_audio_tick',lambda _:ticks.append(p._cycles()))
    hook('intro_audio_step',lambda _:steps.append((p._cycles(),val('intro_audio_scene'),val('introbar'),val('introstep'))))
    hook('intro_drum',lambda _:(drums.append(val('intro_audio_scene')),drumsteps.append((val('intro_audio_scene'),val('introstep')))))
    for frame in range(2400):
        p.tick(1)
        if not val('intro_audio_running'):continue
        scene=val('intro_audio_scene');local=word('intro_scene_ticks');entries.setdefault(scene,p._cycles());fades.add(val('introfade'))
        time=(local>>2 if scene==2 else local>>1) if scene<4 else local*15//64
        if scene==0:assert p.memory[0xff26]&14==0,'Opening must be melody alone'
        if scene<4:
            line=1 if scene==2 and val('introbar')>=6 else 0
            count=28 if line else (19,27,22,0)[scene]
            if caption_state!=(scene,line):caption_state=(scene,line);caption_since=frame
            stable=(time>145 if scene<3 else time>10) and frame-caption_since>10
            if stable:
                expected=texts[scene][(line*29+count)*20:(line*29+count+1)*20]
                assert list(p.memory[0x9a20:0x9a34])==expected,(scene,time,'caption changed or doubled')
                assert len(set(p.memory[0x9a00:0x9a14]))==1,'Duplicate caption row'
        if scene==2:
            window.add(bytes(p.memory[0x8000:0x84e0]))
            for target in (100,300,420,470,530):
                if time>=target and target not in pictures:
                    pictures.add(target)
                    if not cgb:p.screen.image.save(f'build/train-{target}.png')
        if scene==3 and time>10:starframes.add(p.screen.image.crop((5,31,14,40)).tobytes())
        if scene==4:
            if time>200:
                rasterframes.add(p.screen.image.crop((0,0,160,24)).tobytes())
                promptframes.add(p.screen.image.crop((0,128,160,136)).tobytes())
            if 100<time<125:
                assert len(set(p.memory[0x9800:0x9814]))==1,'Logo appeared before one second'
                assert len(set(p.memory[0x9a00:0x9a14]))==1,'Prompt appeared before its delay'
            for target in (120,136,148,158,168,180,200):
                mark=1000+target
                if time>=target and mark not in pictures:
                    pictures.add(mark)
                    if not cgb:p.screen.image.save(f'build/final-{target}.png')
            if time>540:break
    assert set(entries)==set(range(5)),entries
    durations=[(entries[i+1]-entries[i])/4194304 for i in range(4)]
    train_seconds=sum((15360+(1 if i%2==0 else -1)*(3072*(63-i)//63))/(380+132*i//63) for i in range(64))/256
    expected=[8*60/95]*2+[train_seconds,8*60/128]
    quarters=[cycle for cycle,scene,bar,step in steps if (scene==2 and step%4==0) or (scene==1 and bar==4 and step==0)]
    gaps=np.diff(quarters)/4194304
    assert len(gaps)>=15 and all(a>b for a,b in zip(gaps,gaps[1:])),('Train tempo did not ramp',gaps)
    assert abs(gaps[-1]-60/128)<0.025,('Train did not reach second-cue tempo',gaps)
    assert all(abs(a-b)<0.06 for a,b in zip(durations,expected)),durations
    delta=np.diff(ticks);error=max(abs(delta-16384))
    assert error<4096,('Audio timer delayed',error)
    assert drums.count(0)==0 and drums.count(2)==32,drums
    assert [step for scene,step in drumsteps if scene==2]==list(range(0,16,2))*4,'Train drums drifted off-grid'
    assert len(window)>=8 and val('introready')
    assert len(starframes)>=3 and len(rasterframes)>=8 and len(promptframes)>=4,('Demo effects stalled',len(starframes),len(rasterframes),len(promptframes))
    # Muting progresses once per two-bar end-screen loop and survives score wrap.
    lastbar=val('introbar');wrapped=False
    for _ in range(2600):
        p.tick(1);fade=val('introfade');fades.add(fade)
        if fade>=1:assert p.memory[0xff21]==0,'Drums returned after mute'
        if fade>=2:assert p.memory[0xff1c]&0x60==0,'Bass returned after mute'
        if fade>=3:assert p.memory[0xff17]==0,'Countermelody returned after mute'
        if fade==4:assert p.memory[0xff12]==0,'Lead returned after mute'
        bar=val('introbar')
        if bar<lastbar and fade==4:wrapped=True
        lastbar=bar
        if wrapped and bar>=2:break
    assert fades=={0,1,2,3,4} and wrapped and val('introfade')==4,'End-screen fade did not reach persistent silence'
    addr=symbols['_intro_scene_ticks'];p.memory[addr]=250;p.memory[addr+1]=255
    p.tick(60)
    assert 49000<word('intro_scene_ticks')<65000 and val('introready'),'Final demo clock froze or replayed intro'
    base=val('zoombuffer')^128
    assert list(p.memory[0x9a00:0x9a14])==[(base+60+i)&255 for i in range(20)],'Final press play prompt incorrect'
    for row in range(3):
        assert list(p.memory[0x9800+32*row:0x9800+32*row+20])==[(base+row*20+i)&255 for i in range(20)],'Final GAYBOY logo missing'
    p.button_press('start')
    for _ in range(120):
        p.tick(1)
        if not val('introactive') and val('page')==8 and val('seqtrack')==6 and not val('navopen'):break
    assert not val('introactive') and not val('intro_audio_running') and not val('navopen') and val('page')==8 and val('seqtrack')==6
    p.button_release('start');p.tick(60)
    assert val('page')==8 and val('seqtrack')==6 and not val('navopen')
    assert val('drumkit')==1
    p.button_press('start')
    for _ in range(120):
        p.tick(1)
        if val('navopen'):break
    assert val('navopen') and val('navchoice')==8
    p.button_release('start');p.tick(60)
    assert val('page')==8 and val('seqtrack')==6 and not val('navopen')
    p.stop(save=False)
    print('PASS', 'CGB' if cgb else 'DMG', 'scene seconds',durations,'timer error cycles',error,'MPC/train hits',drums.count(1),drums.count(2))
run(False)
run(True)

# Start skips immediately from every cinematic, with timer teardown.
for target in range(4):
    p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True);p.set_emulation_speed(0)
    for _ in range(1800):
        p.tick(1)
        if p.memory[symbols['_intro_audio_running']] and p.memory[symbols['_intro_audio_scene']]==target:break
    else:raise AssertionError(('Missing skip scene',target))
    p.tick(5);p.button_press('start')
    for _ in range(120):
        p.tick(1)
        if not p.memory[symbols['_introactive']] and p.memory[symbols['_page']]==8 and p.memory[symbols['_seqtrack']]==6 and not p.memory[symbols['_navopen']]:break
    assert not p.memory[symbols['_introactive']] and not p.memory[symbols['_intro_audio_running']] and not p.memory[symbols['_navopen']] and p.memory[symbols['_page']]==8 and p.memory[symbols['_seqtrack']]==6,target
    p.tick(90);assert not p.memory[symbols['_navopen']], 'Held intro Start reopened menu'
    p.button_release('start');p.tick(60)
    assert not p.memory[symbols['_navopen']]
    p.stop(save=False)
print('PASS: Start skips all four cutscenes and stops intro audio')

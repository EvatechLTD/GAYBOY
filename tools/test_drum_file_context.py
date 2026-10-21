"""Real File menu, per-row PCM routing and battery-backed whole drum kits."""
from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])

def file_menu(item=None):
    p.button_press('start');p.tick(30)
    assert v('navopen')
    press('left');p.tick(20)
    assert v('navcategory')==4
    choices=[]
    for _ in range(12):
        n=v('navchoice')
        if n in choices:break
        choices.append(n);press('down')
    if item is None:
        press('select');p.button_release('start');p.tick(50)
        return choices
    assert item in choices,(item,choices,text(0))
    for _ in range(12):
        if v('navchoice')==item:break
        press('down')
    p.screen.image.save('build/drum-file-menu-'+('sample' if item==50 else 'kit')+'.png')
    p.button_release('start');p.tick(100)
    assert v('page')==23 and not v('navopen'),(item,v('page'),text(0))
    return choices

def pick_kit(kit):
    file_menu(48)
    for _ in range(16):
        if v('kitchoice')==kit:break
        press('down')
    assert v('kitchoice')==kit
    press('a');p.tick(100)
    assert v('page')==8 and v('drumkit')==(kit if kit<8 else v('drumkit'))

def state():
    fields={'drumsourcekit':10,'drumsourceslot':10,'drumsourcebank':10,
            'drumsourceoffset':20,'drumsourcelength':20,'noisepatch':10,
            'pulsekickpatch':8,'drummutemask':2,'drumsolomask':2,'globalmod':10}
    out={n:bytes(v(n,i) for i in range(size)) for n,size in fields.items()}
    out['eval']=bytes(v('evalpatch',64+i) for i in range(64))
    out['coarse']=bytes(v('coarsepitch',12+i) for i in range(12))
    out['mix']=bytes((v('mx',18),v('mx',25)))
    return out

def battery():
    data=bytearray()
    for bank in range(4):
        p.memory[0x4000]=bank;data.extend(p.memory[0xa000:0xc000])
    p.memory[0x4000]=0
    return data

try:
    enter_app(p,S)
    assert v('seqtrack')==6
    assert 48 in file_menu() and 49 in file_menu() and 50 not in file_menu()
    # KITS is absent from the Instruments group.
    p.button_press('start');p.tick(30)
    for _ in range(3):press('right')
    seen=set()
    for _ in range(20):seen.add(v('navchoice'));press('down')
    assert 23 not in seen
    press('select');p.button_release('start');p.tick(60)
    pick_kit(6)
    put('drumrow',3);put('seqhead',0);put('seqcursor',0,6);put('dirty',1);p.tick(50)
    press('left');assert v('seqhead')==6
    assert 50 in file_menu() and 48 not in file_menu() and 49 not in file_menu()
    file_menu(50)
    assert 'LOAD SAMPLE' in line(0) and 'KIK' in line(2),text(0)
    press('down');assert v('kitchoice')==7
    press('right');assert v('kitslot')==1
    before=bytes(v('drumsourcekit',i) for i in range(10))
    audition=[]
    a=S['_drum_pack']
    p.hook_register(a>>16,a&65535,lambda _:audition.append((v('drumbankvoice'),v('drumbankvoice',1))),None)
    press('b');p.tick(10)
    assert any(62 in banks for banks in audition),audition
    assert bytes(v('drumsourcekit',i) for i in range(10))==before,'Audition changed assignments'
    p.screen.image.save('build/drum-file-load-sample.png')
    press('a');p.tick(100)
    assert v('page')==8 and v('seqhead')==6
    assert v('drumsourcekit')==7 and v('drumsourceslot')==1
    assert bytes(v('drumsourcekit',i) for i in range(1,10))==before[1:]
    # Assign a second source to a different destination channel.
    press('down');assert v('drumrow')==4
    file_menu(50);assert v('kitchoice')==6 and v('kitslot')==1
    press('right');press('a');p.tick(80)
    assert v('drumsourceslot',1)==2 and v('drumsourcekit',1)==6
    # A real plotted destination-channel note plays its assigned source.
    press('up');press('right');assert v('seqhead')==0
    press('b');p.tick(80)
    audition.clear()
    p.button_press('select');p.tick(3);press('a');p.button_release('select');p.tick(45)
    assert v('seqplaying') and any(62 in banks for banks in audition),audition
    p.button_press('select');p.tick(3);press('a');p.button_release('select');p.tick(30)
    assert not v('seqplaying')
    # Custom patches and modulation values must survive whole-kit save/load.
    for i,x in enumerate((9,2,3,1,2,13,3,4,0,2)):put('noisepatch',x,i)
    put('pulsekickpatch',67,1);put('pulsekickpatch',3,3)
    put('evalpatch',85,64);put('evalpatch',94,65);put('evalpatch',103,66)
    put('evalpatch',12,5*16+9);put('evalpatch',255,6*16+9)
    put('coarsepitch',7,15);put('coarsepitch',254,18)
    put('globalmod',2,4);put('drummutemask',4);put('drumsolomask',0)
    put('mx',111,18);put('mx',1,25)
    assert v('seqhead')==0
    expected=state()
    file_menu(49);p.screen.image.save('build/drum-file-save-kit.png');press('a');p.tick(100)
    assert v('page')==8
    pick_kit(1);assert state()!=expected
    file_menu(48);press('right');assert v('kitchoice')==8
    p.screen.image.save('build/drum-file-load-kit.png')
    press('a');p.tick(100)
    assert state()==expected,{k:(expected[k],state()[k]) for k in expected if state()[k]!=expected[k]}
    menu(18);put('mx',31,4);put('dirty',1);p.tick(20);press('b');p.tick(100)
    assert v('mx',1)==1 and state()!=expected
    menu(18);put('mx',30,4);put('dirty',1);p.tick(20);press('b');p.tick(100)
    assert v('mx',1)==0 and state()==expected,'Pattern switch lost custom assignments'
    menu(34);put('seqhead',0)
    file_menu(48);press('right');press('down');press('a');p.tick(40)
    assert v('page')==23 and state()==expected,'Empty kit changed the engine'
    press('select');p.tick(60)
    # Save cancellation must leave the battery record unchanged.
    saved=battery()[2*8192+0x800:2*8192+0x800+160]
    file_menu(49);press('a');assert 'REPLACE USER KIT' in text(0)
    press('b');press('select');p.tick(80)
    assert battery()[2*8192+0x800:2*8192+0x800+160]==saved
    # Current pattern persistence and a battery reboot retain assignments.
    p.tick(100)
    data=battery();p.stop(save=False)
    p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(data));p.set_emulation_speed(0)
    enter_app(p,S)
    assert state()==expected,{k:(expected[k],state()[k]) for k in expected if state()[k]!=expected[k]}
    pick_kit(2);file_menu(48);press('right');press('a');p.tick(80)
    assert state()==expected
    p.screen.image.save('build/drum-file-custom-kit.png')
    # Pre-extension patterns retain their original kit rather than stale routing.
    p.tick(100);legacy=battery();legacy[8192+128+320:8192+128+342]=bytes(22)
    p.stop(save=False)
    p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(legacy));p.set_emulation_speed(0)
    enter_app(p,S)
    assert all(v('drumsourcekit',i)==v('drumkit') and v('drumsourceslot',i)==i for i in range(10))
    file_menu(48);press('right');press('a');p.tick(80)
    assert state()==expected
    print('PASS: contextual File actions, source audition, independent assignments, full DrumSynth/mix kit restore, overwrite cancellation and battery reboot')
finally:
    p.stop(save=False)

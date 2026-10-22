"""Evaluation controls, real button input, static previews and DSP navigation."""
from io import BytesIO
from pathlib import Path
from pyboy import PyBoy
from boot_helpers import enter_app

S = {line.split()[1]: int(line.split()[2], 16)
     for line in Path('build/GAYBOY.noi').read_text().splitlines() if line.startswith('DEF ')}
p = PyBoy('build/GAYBOY.gb', window='null', sound_emulated=True, cgb=False,
          ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)

def v(name, offset=0):
    address=S['_' + name]+offset
    return p.memory[0,address] if 0xa000<=address<0xc000 else p.memory[address]

def put(name, value, offset=0):
    address=S['_' + name]+offset
    if 0xa000<=address<0xc000:p.memory[0,address]=value&255
    else:p.memory[address]=value&255

def press(key, frames=5):
    p.button_press(key)
    p.tick(frames)
    p.button_release(key)
    p.tick(frames)

def adjust(key):
    p.button_press('b')
    p.tick(3)
    press(key)
    p.button_release('b')
    p.tick(80)

def menu(item, button='a'):
    if v('sticky_start'):
        press('start')
    else:
        p.button_press('start');p.tick(20)
    for _ in range(120):
        if v('navopen'):break
        p.tick(1)
    assert v('navopen')
    put('navchoice',item)
    if v('sticky_start'):press(button)
    else:p.button_release('start');p.tick(20)
    p.tick(180)
    assert not v('navopen')


def row(tab, value):
    put('eval_tab', tab)
    put('eval_row', value)
    put('eval_col', 0)
    put('dirty', 1)
    p.tick(20)

def text(start=100):
    return ''.join(chr(p.memory[S['_canvas']+i] % 96+32) for i in range(start, 360))

def line(row):return text(row*20)[:20]

try:
    enter_app(p,S)
    assert v('sparse_enabled')==1
    assert sum(v('seqeventcounts',i) for i in range(14))==0
    assert bytes(v('pool_root',i) for i in range(4))==b'GSR1'
    menu(2);assert 'MOD' in line(0)
    row(1,5);adjust('up');assert v('globalmod',5)==1
    # All tempo divisions use Up/Right = faster and Down/Left = slower.
    row(1,6)
    for key,expected in [('up',7),('right',6),('down',7),('left',8)]:
        adjust(key);assert v('globalmod',6)==expected,(key,v('globalmod',6))
    for initial,key,expected in [(0,'up',0),(0,'right',0),(16,'down',16),(16,'left',16)]:
        put('globalmod',initial,6);adjust(key);assert v('globalmod',6)==expected
    menu(11);row(3,1);put('evalpatch',0,1);put('evalpatch',8,2)
    for key,expected in [('up',7),('right',6),('down',7),('left',8)]:
        adjust(key);assert v('evalpatch',2)==expected,(key,v('evalpatch',2))
    for initial,key,expected in [(0,'up',0),(0,'right',0),(16,'down',16),(16,'left',16)]:
        put('evalpatch',initial,2);adjust(key);assert v('evalpatch',2)==expected
    row(0,5);put('eval_col',1);put('dirty',1);p.tick(40)
    adjust('down');assert v('evalpatch',9)==255
    assert 'FINE' in text(40) and 'LFO WAVE' not in text(40)
    p.screen.image.save('build/stripped-tone.png')
    menu(2);p.screen.image.save('build/stripped-mod.png')
    menu(8);assert v('seqtrack') not in (4,5)
    # Plot through actual A input and preserve a fresh battery image.
    put('seqhead',0);press('b');p.tick(120)
    assert sum(v('seqeventcounts',i) for i in range(14))>0,[(name,v(name)) for name in ('seqtrack','seqhead','seqapending','page','navopen')]
    menu(18);p.tick(120)
    p.screen.image.save('build/stripped-mixer.png')
    assert line(2).strip()=='P1 P2 WV  N DR NHH',line(2)
    assert line(5)[0]=='V' and 'VOL' not in line(5),line(5)
    assert '5 PATTERNS' in line(14),line(14)
    assert v('sparse_patterns')==5
    print('PASS: fresh blank project, global MOD page, inline fine controls, note plotting, and reduced mixer')
finally:
    p.stop(save=False)

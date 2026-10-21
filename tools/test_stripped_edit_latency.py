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
    return p.memory[S['_' + name]+offset]

def put(name, value, offset=0):
    p.memory[S['_' + name]+offset] = value & 255

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
    p.tick(20)
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

import json
try:
    enter_app(p,S);menu(28);put('seqhead',0);p.tick(80)
    events=[[i,11,127,1] for i in range(255)]
    p.memory[0x4000]=1
    for i,e in enumerate(events):p.memory[0xa000+768+i*4:0xa000+772+i*4]=e
    p.memory[0x4000]=0
    for c in range(7):put('seqeventcounts',255 if c==6 else 0,c*2);put('seqeventcounts',0,c*2+1);put('seqeventoffsets',0,c*2);put('seqeventoffsets',0,c*2+1)
    p.tick(10)
    publications=[]
    expected=[1]
    ptr=S['_ui_flush']
    p.hook_register(ptr>>16,ptr&65535,lambda _:publications.append(p._cycles()) if (v('seqeventcounts')|v('seqeventcounts',1)<<8)==expected[0] and v('seqdrawvalid') and not v('dirty') else None,None)
    results={}
    for action in ('plot','delete'):
        p.tick(30)
        expected[0]=1 if action=='plot' else 0
        publications.clear()
        start=p._cycles();p.button_press('b');p.tick(1);p.button_release('b')
        for frame in range(120):
            p.tick(1)
            if publications and (v('seqeventcounts')|v('seqeventcounts',1)<<8)==(1 if action=='plot' else 0) and v('seqdrawvalid') and not v('dirty') and list(p.memory[S['_canvas']:S['_canvas']+360])==list(p.memory[S['_visible']:S['_visible']+360]):break
        elapsed=(p._cycles()-start)*1000/4194304;results[action+'_visible_ms']=elapsed
        assert (v('seqeventcounts')|v('seqeventcounts',1)<<8)==(1 if action=='plot' else 0),(action,elapsed,v('seqeventcounts'),v('seqhead'),v('seqapending'))
    assert max(results.values())<200,results
    Path('build/stripped-edit-latency.json').write_text(json.dumps(results,indent=2));print('Visible cell latency',results)
finally:p.stop(save=False)

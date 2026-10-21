"""Measure live DMG onset intervals and DSP refills while navigating the roll."""
from io import BytesIO
from pathlib import Path
import sys
import json
import numpy as np
from pyboy import PyBoy
from boot_helpers import enter_app

S = {line.split()[1]: int(line.split()[2], 16)
     for line in Path('build/GAYBOY.noi').read_text().splitlines() if line.startswith('DEF ')}
p = PyBoy('build/GAYBOY.gb', window='null', sound_emulated=True, cgb=False,
          ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)

def get(name, offset=0):
    return p.memory[S['_' + name]+offset]

def put(name, value, offset=0):
    p.memory[S['_' + name]+offset] = value & 255

def word(name):
    return get(name) | get(name, 1) << 8

def press(key):
    p.button_press(key)
    p.tick(5)
    p.button_release(key)
    p.tick(5)

def send(data):
    for byte in data:
        write = get('wr')
        put('rx', byte, write)
        put('wr', write+1)
    p.tick(12)

try:
    enter_app(p,S)
    mode=1 if '--arp' in sys.argv else 0
    put('evalpatch',mode);put('evalpatch',bool(mode),13);put('evalpatch',4,2);put('evalpatch',1,4)
    put('evalpatch',8,9);put('evalpatch',1,8);put('globalmod',128,5)
    pulses=[[step,n,127,4 if mode else 1] for step in (0,4,8,12) for n in ((61,65,68) if mode else (70,))]
    events=pulses+[[0,49,127,16]]+[[step,11 if step%4==0 else 12,100,1] for step in range(0,16,2)]+[[0,1,100,1],[8,2,100,1],[0,13,100,1],[8,13,100,1]]
    offset=0
    for c in range(7):
        n=len(pulses) if c==0 else 1 if c==2 else 12 if c==6 else 0
        put('seqeventoffsets',offset,c*2);put('seqeventoffsets',0,c*2+1);put('seqeventcounts',n,c*2);put('seqeventcounts',0,c*2+1);offset+=n
    p.memory[0x4000]=1
    for i,e in enumerate(events):p.memory[0xa000+768+i*4:0xa000+772+i*4]=e
    p.memory[0x4000]=0
    put('page',8);put('selected',0);put('seqtrack',0);put('seqhead',0);put('dirty',1);p.tick(60)
    hits=[];p.hook_register(0,S['_play'],lambda _:hits.append(p._cycles()) if p.register_file.A==0 else None,None)
    p.button_press('select');press('a');p.button_release('select');p.tick(30);assert get('seqplaying')
    reports={}
    for phase in ('idle','navigation'):
        hits.clear()
        for i in range(240):
            if phase=='navigation':
                if i%12==0:p.button_press('right')
                if i%12==2:p.button_release('right')
                if i%24==4:p.button_press('up')
                if i%24==6:p.button_release('up')
            p.tick(1)
        intervals=np.diff(hits)/4194304*1000;assert len(intervals)>=6,intervals
        expected=125 if mode else 500
        reports[phase+'_max_error_ms']=float(abs(intervals-expected).max())
        reports[phase+'_intervals_ms']=intervals.tolist()
    reports['mode']='arp' if mode else 'mono';reports['pcm_underruns']=word('mixunderruns')
    Path('build/stripped-timing-'+reports['mode']+'.json').write_text(json.dumps(reports,indent=2))
    print('PASS: native, fine LFO, Wave, drums and PCM playback timing',reports)
    assert reports['navigation_max_error_ms']<25 and reports['pcm_underruns']<5
finally:p.stop(save=False)

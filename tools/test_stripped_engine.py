"""Exercise the evaluation engine in the real DMG CPU, without UI timing noise."""
from io import BytesIO
from pathlib import Path
import binascii
from pyboy import PyBoy

S = {line.split()[1]: int(line.split()[2], 16)
     for line in Path('build/GAYBOY.noi').read_text().splitlines() if line.startswith('DEF ')}
p = PyBoy('build/GAYBOY.gb', window='null', sound_emulated=True, cgb=False,
          ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
p.memory[0] = 10
p.memory[0x4000] = 0
p.memory[0xffff] = p.memory[0xff0f] = p.memory[0xff40] = 0
p.memory[0xff50] = 1
p.memory[0xc000:0xe000] = [0] * 8192
p.memory[0xc000:0xc004] = [0x18, 0, 0x18, 0xfe]
returns = []
p.hook_register(0, 0xc000, lambda _: returns.append((p.register_file.A, p._cycles())), None)

def put(name, value, offset=0):
    p.memory[S['_' + name] + offset] = value & 255

def get(name, offset=0):
    return p.memory[S['_' + name] + offset]

def word(name, offset=0):
    return get(name, offset) | get(name, offset+1) << 8

def call(name, *args):
    pointer = S['_' + name]
    bank = pointer >> 16
    p.memory[0x2000] = bank
    p.memory[0x3000] = 0
    p.memory[0xff90] = bank
    frame = [0, 0xc0, 0, 0, 0, 0, *args]
    p.memory[0xdfe0:0xdfe0+len(frame)] = frame
    p.register_file.SP = 0xdfe0
    p.register_file.PC = pointer & 65535
    returns.clear()
    started = p._cycles()
    for _ in range(600):
        p.tick(1)
        if returns:
            break
    assert returns, (name, hex(p.register_file.PC))
    return returns[-1][0], (returns[-1][1]-started)*1000/4194304

def tracks(mapping):
    flat = []
    for c in range(7):
        values = mapping.get(c, [])
        put('seqeventoffsets', len(flat), c*2)
        put('seqeventoffsets', len(flat) >> 8, c*2+1)
        put('seqeventcounts', len(values), c*2)
        put('seqeventcounts', len(values) >> 8, c*2+1)
        flat.extend(values)
        put('seqposition', 0, c)
    for i, event in enumerate(flat):
        address = S['_seqevents_lo']+i*4 if i < 256 else 0xa800+(i-256)*4
        p.memory[address:address+4] = event
    put('seqeventcache', 0)
    call('eval_drum_dirty')

def object_fixture(data, head=4):
    header = bytes((ord('T'), 1)) + len(data).to_bytes(2, 'little')
    content = header + binascii.crc_hqx(header+data, 65535).to_bytes(2, 'little') + data
    chunks = [content[i:i+62] for i in range(0, len(content), 62)]
    for i, chunk in enumerate(chunks):
        page = head+i
        block = (page+1 if i+1 < len(chunks) else 65535).to_bytes(2, 'little') + chunk.ljust(62, b'\0')
        p.memory[0x4000] = 1
        p.memory[0xa000+page*64:0xa000+page*64+64] = list(block)
    p.memory[0x4000] = 0
    return head

def tracks(mapping):
    flat=[]
    put('mx',0,1)
    for c in range(7):
        values=mapping.get(c,[]);put('seqeventoffsets',len(flat),c*2);put('seqeventoffsets',len(flat)>>8,c*2+1);put('seqeventcounts',len(values),c*2);put('seqeventcounts',len(values)>>8,c*2+1);flat.extend(values)
    p.memory[0x4000]=1
    for i,e in enumerate(flat):p.memory[0xa000+768+i*4:0xa000+772+i*4]=e
    p.memory[0x4000]=0
    call('eval_drum_dirty')

try:
    put('experimental_mode',1);put('power',1);put('frameadvance',1)
    call('eval_defaults')
    assert all(get('evalpatch',c*16+10)==0 for c in range(8))
    # One phase and envelope serve all instruments.
    put('globalmod',8,5)
    put('evalpatch',64,9);put('evalpatch',1,8)
    put('evalpatch',64,16+9);put('evalpatch',1,16+8)
    call('eval_frame')
    assert call('eval_amount',0,0)[0]==call('eval_amount',1,0)[0]
    for dest in range(1,8):assert call('eval_amount',0,dest)[0]==0
    put('globalmod',2,0);put('globalmod',2,3)
    put('evalpatch',128,10);put('evalpatch',128,26)
    call('eval_note',0,1);call('eval_frame');assert call('eval_signal',0,0)[0]==32
    call('eval_note',1,1);call('eval_frame');call('eval_frame')
    call('eval_note',0,0);call('eval_frame');assert call('eval_signal',1,0)[0]==64
    call('eval_note',1,0);call('eval_frame');assert call('eval_signal',0,0)[0]==32
    call('eval_frame');assert call('eval_signal',0,0)[0]==0
    # Current-format round trip includes shared generators and compact channel settings.
    put('globalmod',47,5);put('param',13,1)
    call('tones_capture');put('param',0,1);put('globalmod',0,5)
    call('tones_apply');assert get('param',1)==13 and get('globalmod',5)==47
    # Overlapping hat and snare are both admitted, including the launch cache.
    tracks({6:[[0,11,127,8],[0,12,127,8]]})
    assert call('eval_drum_allowed',0,0)[0] and call('eval_drum_allowed',1,0)[0]
    for i,value in enumerate([15,2,1,0,0,15,10,5,0,0]):put('noisepatch',value,i)
    put('noiseleft',100);put('noiseleft',100,4)
    put('noiselevel',127);put('noiselevel',127,1)
    call('drum_noise');assert p.memory[0xff22]==0x63,hex(p.memory[0xff22])
    assert '_expalpha' not in S and '_monoset' not in S and '_noiseset' not in S
    print('PASS: shared generators, hardware defaults, fine-only modulation, current tone round trip, overlapping NSH/NSN mean and removed DSP/Mono state')
finally:
    p.stop(save=False)

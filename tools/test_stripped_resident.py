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

import json
try:
    put('experimental_mode',1);put('power',1);put('frameadvance',1)
    call('eval_defaults');call('drum_init');call('startup');call('sparse_boot');call('mixer_init')
    timings=[]
    for slot in range(5):
        call('sparse_restore',slot);call('seq_storage_clear')
        for i in range(256):
            p.memory[0xb100:0xb104]=[i,40+slot,127,1]
            result,ms=call('seq_event_put',0,255,255,0,0xb1)
            assert result,(slot,i)
        assert call('seq_event_total')[0]==0  # uint16 result low byte of256
        p.memory[0xb100:0xb104]=[0,60,127,1]
        assert not call('seq_event_put',0,255,255,0,0xb1)[0]
        call('sparse_snapshot',slot)
    writes=[]
    pointer=S['_resident_write'];p.hook_register(pointer>>16,pointer&65535,lambda _:writes.append(p._cycles()),None)
    for slot in range(5):
        writes.clear();result,ms=call('sparse_restore',slot)
        assert result and not writes,(slot,ms,writes)
        p.memory[0xb100:0xb104]=[0]*4
        assert call('seq_event_get',0,0,0,0,0xb1)[0]
        assert list(p.memory[0xb100:0xb104])==[0,40+slot,127,1],(slot,list(p.memory[0xb100:0xb104]),get('mx',1))
        timings.append(ms)
    assert not call('sparse_restore',5)[0]
    assert not call('sparse_clear_slot',5)[0]
    # Reinitialize descriptors from the battery records and inspect every pool.
    call('sparse_boot')
    for slot in range(5):
        assert call('sparse_restore',slot)[0]
        assert call('seq_event_get',0,255,0,0,0xb1)[0]
        assert list(p.memory[0xb100:0xb104])==[255,40+slot,127,1]
    call('seq_storage_clear')
    for i in range(255):
        p.memory[0xb100:0xb104]=[i,11,127,1];call('seq_event_put',6,255,255,0,0xb1)
    p.memory[0xb100:0xb104]=[0,60,127,1]
    result,plot=call('seq_event_put',0,255,255,0,0xb1);assert result
    _,erase=call('seq_event_erase',0,0,0)
    assert plot<30 and erase<30,(plot,erase)
    assert '_seqevents_lo' not in S and '_seqnativestep' not in S and '_eval_chords' not in S
    data={'patterns':5,'notes_each':256,'resident_notes_total':1280,'worst_shift_plot_ms':plot,'worst_shift_delete_ms':erase,'restore_settings_ms':timings,'note_writes_on_switch':0}
    Path('build/stripped-resident-timing.json').write_text(json.dumps(data,indent=2))
    print('PASS: all five resident pools at256 notes, bounded edits, no note copies on switch',data)
finally:p.stop(save=False)

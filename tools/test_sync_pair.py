"""Run two ROM instances, forwarding the master's emulated serial bytes each frame."""
from pathlib import Path
from io import BytesIO
from pyboy import PyBoy

env = {}
exec(Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0], env)
master, S, choose, press, word, v = (env[k] for k in ('p','S','choose','press','word','v'))
slave = None

def value(machine, name):
    return machine.memory[S['_' + name]]

def store_word(machine, name, n):
    at = S['_' + name]
    machine.memory[at:at+2] = [n & 255, n >> 8]

def forward():
    data = master._serial()
    w = value(slave, 'wr')
    for b in data:
        slave.memory[S['_rx'] + w] = ord(b)
        w = (w + 1) & 255
    slave.memory[S['_wr']] = w
    return len(data)

def run(frames):
    for _ in range(frames):
        master.tick(1)
        forward()
        slave.tick(1)
        a, b = value(master, 'seqposition'), value(slave, 'seqposition')
        at = S['_seqlength']
        length = master.memory[at] | master.memory[at+1] << 8
        assert (a - b) % length in (0, 1, length - 1), (a, b, length)

try:
    choose(27); press('right')
    state = BytesIO()
    master.save_state(state)
    state.seek(0)
    slave = PyBoy('build/GAYBOY.gb', window='null', sound_emulated=False, ram_file=BytesIO(bytes(32768)))
    slave.set_emulation_speed(0)
    slave.load_state(state)
    slave.memory[S['_syncslave']] = 1
    slave.memory[0xFF01] = 0
    slave.memory[0xFF02] = 0x80
    store_word(master, 'seqbpm', 200)
    store_word(master, 'seqglobalbpm', 200)
    master._serial()
    master.button_press('a')
    run(12)
    master.button_release('a')
    run(180)
    assert value(slave, 'seqplaying')
    at = S['_seqglobalbpm']
    assert slave.memory[at] | slave.memory[at+1] << 8 == 200
    store_word(master, 'seqbpm', 157)
    store_word(master, 'seqglobalbpm', 157)
    run(120)
    assert slave.memory[at] | slave.memory[at+1] << 8 == 157
    press('a'); forward(); slave.tick(4)
    assert not value(slave, 'seqplaying')
    print('Two ROM instances stayed within one step through start, 200->157 BPM, and stop')
finally:
    master.stop(save=False)
    if slave:
        slave.stop(save=False)

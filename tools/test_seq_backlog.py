"""Overdue ordinary steps catch up within one scheduler invocation."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import write_tracks, write_word

services = [0]
boundaries = []

def hook(name, callback):
    address = S['_' + name]
    p.hook_register(address >> 16, address & 65535, callback, None)

def entered(_):
    services[0] += 1

try:
    choose(18)
    p.memory[S['_seqservicing']] = 1
    p.tick(2)
    write_tracks(p, S, [[] for _ in range(7)])
    write_word(p, S['_seqbpm'], 300)
    write_word(p, S['_seqclock'], 0)
    write_word(p, S['_seqticks'], 220)
    write_word(p, S['_seqdeadline'], 1)
    p.memory[S['_mx'] + 2] = 255
    p.memory[S['_seqplaying']] = 1
    hook('seq_frame', entered)
    hook('mixer_boundary', lambda _: boundaries.append(services[0]))
    p.memory[S['_seqservicing']] = 0
    for _ in range(10):
        p.tick(1)
        if len(boundaries) >= 4:
            break
    assert len(boundaries) >= 4, boundaries
    assert boundaries[:4] == [1] * 4, ('Catch-up deferred ordinary steps', boundaries)
    print('PASS: four overdue steps processed in one scheduler invocation')
finally:
    p.stop(save=False)

"""Exercise both routing destinations, real consumers, releases and sleeping arps."""
import json
from pathlib import Path
from mod_port_harness import Engine

E = Engine('build/GAYBOY.gb')
p = E.p
calls = []
for name in ('eval_mod_frame', 'eval_audio_frame'):
    a = E.S['_' + name]
    p.hook_register(a >> 16, a & 65535,
                    lambda name: calls.append((name, p.memory[p.register_file.SP+6])), name)


def fresh():
    E.reset()
    for c in range(4):
        E.put('active', 1, c)
        E.put('keycount', 1, c)
    E.word('seqbpm', 240)
    E.put('globalmod', 1, 7)
    E.put('globalmod', 8, 6)
    E.put('globalmod', 32, 2)
    E.put('globalmod', 6, 3)
    calls.clear()


def changed():
    E.word('pattern_generation', E.get('pattern_generation') +
           (E.get('pattern_generation', 1) << 8) + 1)


def frame(n=1):
    cost = 0
    for _ in range(n):
        E.word('sys_time', E.get('lastframe') + (E.get('lastframe', 1) << 8) + 1)
        cost += E.call('service_frame')[1]
    return cost / n


def flags():
    return [x[1] for x in calls if x[0] == 'eval_mod_frame']


try:
    fresh()
    frame()
    calls.clear()
    idle_cycles = frame(32)
    assert not calls
    phase = E.S['_evalpatch'] + 137
    clock = E.S['_evalpatch'] + 140
    # Negative fine/coarse depths, either source, on every supported voice.
    cases = 0
    for c in (0, 1, 2, 3, 5, 6, 7):
        for dest in (0, 1):
            for source in (0, 1):
                fresh()
                if c == 7:
                    E.word('pulsekickleft', 256)
                elif c in (5, 6):
                    E.put('drumnoiseowned', 1)
                    E.word('noiseleft', 256, (c-5)*4)
                if dest:
                    E.put('coarsepitch', -8, c*3+1)
                    E.put('coarsepitch', source, c*3+2)
                else:
                    E.put('evalpatch', -8, c*16+9)
                    E.put('evalpatch', source, c*16+8)
                frame(2)
                assert flags() and set(flags()) == {1 if source else 2}, (c, dest, source, calls)
                cases += 1
    # Independent fine/coarse sources can require both shared engines.
    fresh()
    E.put('evalpatch', 8, 9)
    E.put('evalpatch', 1, 8)
    E.put('coarsepitch', 8, 1)
    frame(2)
    assert set(flags()) == {3}
    # Removing one destination retains the other's phase; last route resets.
    before = bytes(p.memory[clock:clock+4])
    E.put('coarsepitch', 0, 1)
    changed()
    frame()
    assert bytes(p.memory[clock:clock+4]) != before
    E.put('evalpatch', 0, 9)
    changed()
    calls.clear()
    frame(3)
    assert not calls and not p.memory[phase] and bytes(p.memory[clock:clock+4]) == bytes(4)
    E.put('evalpatch', 8, 9)
    changed()
    frame()
    assert int.from_bytes(bytes(p.memory[clock:clock+4]), 'little') == 240
    # Inactive configured voices pause without catch-up, including free phase.
    E.put('globalmod', 1, 9)
    E.put('active', 0)
    before = bytes(p.memory[clock:clock+4])
    calls.clear()
    frame(20)
    assert not calls and bytes(p.memory[clock:clock+4]) == before
    E.put('active', 1)
    frame()
    assert int.from_bytes(bytes(p.memory[clock:clock+4]), 'little') == 480
    # LFO-only note starts must not create an envelope or held-envelope user.
    E.call('eval_note', (0, 1))
    assert E.call('eval_signal', (0, 0))[0] == 0
    # Source change during a held note starts ADSR; release remains audible.
    E.put('evalpatch', 0, 8)
    E.put('evalpatch', 128, 10)
    changed()
    frame()
    assert E.call('eval_signal', (0, 0))[0] == 32
    E.call('eval_note', (0, 0))
    E.put('keycount', 0)
    calls.clear()
    frame(6)
    assert flags() and not E.get('active')
    calls.clear()
    frame(3)
    assert not calls
    # Two held envelope voices: releasing one must retain shared sustain.
    fresh()
    for c in (0, 1):
        E.put('evalpatch', 128, c*16+10)
    frame()
    E.call('eval_note', (0, 0))
    E.put('keycount', 0)
    frame(8)
    assert E.call('eval_signal', (0, 0))[0] == 32
    E.call('eval_note', (1, 0))
    E.put('keycount', 0, 1)
    frame(6)
    assert E.call('eval_signal', (0, 0))[0] == 0
    # Removing the final held route releases another voice's existing tail.
    fresh()
    for c in (0, 1):
        E.put('evalpatch', 128, c*16+10)
    frame()
    E.call('eval_note', (1, 0))
    E.put('keycount', 0, 1)
    E.put('evalpatch', 0, 10)
    changed()
    frame(6)
    assert E.call('eval_signal', (0, 0))[0] == 0
    # Restore/default paths invalidate independently of a pattern generation.
    fresh()
    E.put('evalpatch', 8, 9)
    E.put('evalpatch', 1, 8)
    E.put('coarsepitch', 8, 4)
    frame()
    E.call('tones_capture')
    E.call('eval_defaults')
    frame()
    assert not E.get('eval_lfousers') and not E.get('eval_envusers')
    E.call('tones_apply')
    frame()
    assert E.get('eval_lfousers') == 1 and E.get('eval_envusers') == 2
    # User-preset restore rebuilds both destinations without manual dirtying.
    E.call('user_preset_save', (0, 0))
    E.put('evalpatch', 0, 9)
    changed()
    frame()
    assert not E.get('eval_lfousers')
    assert E.call('user_preset_load', (0, 0))[0]
    frame()
    assert E.get('eval_lfousers') == 1
    # Actual MIDI note stack: releasing the top key resumes the older held key;
    # the shared envelope releases only after the final key is released.
    fresh()
    E.put('active', 0)
    E.put('keycount', 0)
    E.put('evalpatch', 128, 10)
    E.call('event', (0x90, 60, 127))
    E.call('event', (0x90, 64, 127))
    frame()
    assert E.get('keycount') == 2
    E.call('event', (0x80, 64, 0))
    frame(8)
    assert E.get('keycount') == 1 and E.call('eval_signal', (0, 0))[0] == 32
    E.call('event', (0x80, 60, 0))
    frame(6)
    assert not E.get('keycount') and not E.get('active')
    # Ownership excludes native routes while their channel is taken over.
    for c, owner in ((0, 'pulsekickleft'), (2, 'waveengine'), (3, 'drumnoiseowned')):
        fresh()
        E.put('evalpatch', 8, c*16+9)
        E.put('evalpatch', 1, c*16+8)
        E.put(owner, 3 if c == 2 else 1)
        frame(2)
        assert not calls, (c, calls)
    # Empty arp clocks and deadlines sleep; retained phase resumes unchanged.
    fresh()
    E.put('evalpatch', 1)
    E.word('arpclock', 321)
    old = bytes(p.memory[E.S['_arpclock']:E.S['_arpclock']+12])
    assert E.call('eval_arp_wait')[0] == 255
    E.call('eval_seq_tick', (64, 0))
    assert bytes(p.memory[E.S['_arpclock']:E.S['_arpclock']+12]) == old
    E.put('arpcount', 1)
    E.put('evalpatch', 0, 4)
    E.call('eval_seq_tick', (1, 0))
    assert E.get('arpclock') | E.get('arpclock', 1) << 8 == 561
    report = {'routing_cases': cases, 'idle_frame_cycles': idle_cycles}
    Path('build/mod-port-idle.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS:', report)
finally:
    p.stop(save=False)

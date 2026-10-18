"""Cancel snapshots and interrupt commits without losing saves or clipboards."""
from pathlib import Path
from io import BytesIO
import argparse
import json
from pyboy import PyBoy

ap = argparse.ArgumentParser()
ap.add_argument('--rom', default='build/GAYBOY.gb')
ap.add_argument('--dirty-edge', action='store_true', help='Check edits after a launch was prepared')
args = ap.parse_args()
S = {l.split()[1]: int(l.split()[2], 16)
     for l in Path(args.rom).with_suffix('.noi').read_text().splitlines()
     if l.startswith('DEF ')}


def boot(machine):
    for _ in range(2800):
        machine.tick(1)
        if machine.memory[S['_introready']]:
            break
    assert machine.memory[S['_introready']]
    machine.button_press('start')
    for _ in range(120):
        machine.tick(1)
        if not machine.memory[S['_introactive']] and machine.memory[S['_page']] == 8:
            break
    assert not machine.memory[S['_introactive']]
    machine.button_release('start')
    machine.tick(50)


def machine(battery=None):
    result = PyBoy(args.rom, window='null', cgb=False, sound_emulated=False,
                   ram_file=BytesIO(battery if battery is not None else bytes(32768)))
    result.set_emulation_speed(0)
    boot(result)
    return result


p = machine()
from seq_storage_helpers import write_tracks


def record(machine, slot):
    machine.memory[0x4000] = 1 + slot // 3
    at = 0xa000 + slot % 3 * 2560
    result = bytes(machine.memory[at:at + 2560])
    machine.memory[0x4000] = 0
    return result


def active(data):
    return data[:20] + data[32:2449]


def clipboard(machine):
    machine.memory[0x4000] = 3
    result = bytes(machine.memory[0xb400:0xbc10])
    machine.memory[0x4000] = 0
    return result


def battery(machine):
    result = bytearray()
    for bank in range(4):
        machine.memory[0x4000] = bank
        result.extend(machine.memory[0xa000:0xc000])
    machine.memory[0x4000] = 0
    return result


# Direct calls avoid introducing real user edits while placing reset points.
p.memory[0, 0x3ff0:0x3ff3] = [0, 0x18, 0xfe]
p.memory[0xffff] = p.memory[0xff07] = p.memory[0xff0f] = 0
p.memory[0] = 0x0a
end = [None]
p.hook_register(0, 0x3ff0, lambda _: end.__setitem__(0, p._cycles()), None)


def call(name, arguments=()):
    target = S['_' + name]
    bank = target >> 16
    p.memory[0x2000] = p.memory[0xff90] = bank
    p.memory[0x3000] = 0
    sp = 0xdf00
    p.memory[sp:sp + 6 + len(arguments)] = [0xf0, 0x3f, 0, 0, 0, 0] + list(arguments)
    p.register_file.SP = sp
    p.register_file.PC = target & 65535
    end[0] = None
    begin = p._cycles()
    for _ in range(600):
        p.tick(1)
        if end[0] is not None:
            break
    assert end[0] is not None, name
    assert p.register_file.SP == sp + 2, name
    return (end[0] - begin) * 1000 / 4194304


def phase():
    return p.memory[S['_prep']]


def start():
    p.memory[S['_page']] = 18
    p.memory[S['_seqplaying']] = 1
    p.memory[S['_seqticks']:S['_seqticks'] + 2] = [0, 0]
    p.memory[S['_mx'] + 3] = 2
    call('mixer_launch_request', [1, 0])


def until(wanted):
    for _ in range(1200):
        if phase() == wanted:
            return
        call('mixer_prepare_service')
    raise AssertionError(('Preparation stuck', wanted, phase()))


reports = []
try:
    p.memory[S['_page']] = 18
    p.memory[S['_seqplaying']] = 0
    tracks = [[] for _ in range(7)]
    tracks[0] = [[0, 61, 100, 8]]
    write_tracks(p, S, tracks)
    call('snapshot', [0])
    previous = record(p, 0)
    # Exercise the complete maximum-size clipboard reservation.
    clip = bytes((i * 31 + 7) & 255 for i in range(2064))
    p.memory[0x4000] = 3
    p.memory[0xb400:0xbc10] = clip
    p.memory[0x4000] = 0
    tracks[0] = [[s, 65 + s % 4, 97, 1] for s in range(64)]
    write_tracks(p, S, tracks)
    p.memory[S['_param']] = 2
    call('mixer_pattern_changed')
    call('snapshot', [1])
    expected = record(p, 1)
    for canceled_phase in range(1, 7):
        start()
        until(canceled_phase)
        elapsed = call('mixer_prepare_cancel')
        assert not phase()
        assert active(record(p, 0)) == active(previous), canceled_phase
        assert clipboard(p) == clip
        reports.append(dict(cancel_phase=canceled_phase, cpu_ms=elapsed))

    start()
    until(18)
    assert active(record(p, 0)) == active(previous), 'Source changed before journal commit'
    # Reset before invalidation and at multiple partial-copy positions.
    advanced = 0
    for point in (0, 1, 17, 73, 151):
        while advanced < point:
            call('mixer_prepare_service')
            advanced += 1
        q = machine(battery(p))
        try:
            assert active(record(q, 0)) == active(expected), ('Reset lost snapshot', point)
            assert record(q, 0)[2500:2504] == b'GBM2'
            assert clipboard(q) == clip
        finally:
            q.stop(save=False)
    elapsed = call('mixer_prepare_cancel')
    p.memory[S['_page']] = 8
    p.memory[0xb000:0xc000] = bytes([0xa7]) * 4096
    until(0)
    assert active(record(p, 0)) == active(expected), 'Renderer clobbered deferred commit'
    assert clipboard(p) == clip
    reports.append(dict(cancel_commit_cpu_ms=elapsed))
    # A tone edit during capture must invalidate the mixed-generation
    # snapshot, then preserve the final edit after the retry commits.
    p.memory[S['_page']] = 18
    p.memory[S['_param']] = 1
    call('mixer_pattern_changed')
    call('snapshot', [2])
    latest = record(p, 2)
    start()
    until(4)
    p.memory[S['_param']] = 0
    call('mixer_pattern_changed')
    until(6)
    call('mixer_prepare_service')
    assert phase() == 1, 'Concurrent edit did not restart snapshot capture'
    # Return to the known expected value while the retried capture is pending.
    p.memory[S['_param']] = 1
    call('mixer_pattern_changed')
    until(18)
    call('mixer_prepare_cancel')
    p.memory[S['_page']] = 8
    until(0)
    assert active(record(p, 0)) == active(latest), 'Finite concurrent tone edit was lost'
    assert clipboard(p) == clip
    reports.append(dict(concurrent_edit_retry='preserved'))
    if args.dirty_edge:
        # An edit arriving after preparation but before quantization must
        # revoke the presaved flag and block handoff until it is saved.
        p.memory[S['_page']] = 18
        p.memory[S['_mx'] + 2] = 1
        p.memory[S['_mx'] + 46] = 1  # presaved
        call('mixer_pattern_changed')
        assert not p.memory[S['_mx'] + 46], 'Late edit retained a stale saved-generation flag'
        call('mixer_prepare_busy')
        assert p.register_file.A, 'Late edit was allowed to leave without a snapshot'
        call('mixer_prepare_service')
        assert phase() == 2, ('Late edit did not start capture', phase())
        call('mixer_prepare_cancel')
        reports.append(dict(edit_after_preparation='handoff_deferred'))
    Path('build/pattern-journal.json').write_text(json.dumps(reports, indent=2))
    print('PASS: capture cancellation, partial-commit power loss, deferred off-page commit, clipboard and boot magic', json.dumps(reports))
finally:
    p.stop(save=False)

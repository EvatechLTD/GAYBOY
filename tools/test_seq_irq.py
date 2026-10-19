"""Observe standalone APU attacks, including short gates, navigation and mute."""
from pathlib import Path
import json
import statistics
import test_pcm_timing as pcm
from seq_storage_helpers import write_tracks, write_word

env = {}
exec(Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0].replace('sound_emulated=True,','sound_emulated=True,cgb=False,'), env)
p, S, v, press, choose = (env[k] for k in ('p', 'S', 'v', 'press', 'choose'))
checking_pitch = False
attacks = [[], []]
irq = [0, 0]
frequency_low = [0, 0]
pitch_errors = []
CPU = 4194304


def written(site):
    op, extra, cost = site
    r = p.register_file
    at = ((r.B << 8) | r.C) if op == 2 else ((r.D << 8) | r.E) if op == 0x12 else r.HL if op in (0x22, 0x32, 0x36, 0x77) else 0xff00 + extra if op == 0xe0 else 0xff00 + r.C if op == 0xe2 else extra
    value = extra if op == 0x36 else r.A
    if at in (0xff13, 0xff18):
        frequency_low[int(at == 0xff18)] = value
        return
    if at not in (0xff14, 0xff19) or not value & 128:
        return
    c = int(at == 0xff19)
    step = pcm.pulse_position(p, S, c)
    attacks[c].append((p._cycles() + cost, step))
    if not checking_pitch:return
    note = 60 + c * 7 + step % 4
    at_note = S['_notes'] + note * 2
    f = p.memory[at_note] | p.memory[at_note + 1] << 8
    if c:
        following = p.memory[at_note + 2] | p.memory[at_note + 3] << 8
        f += (following - f) // 2
    else:
        f += 10
    actual = frequency_low[c] | (value & 7) << 8
    if actual != f and len(pitch_errors) < 10:pitch_errors.append((c, step, actual, f))
    begin = S['_seq_irq_tick']
    end = min(x for name, x in S.items() if name.startswith('_') and begin < x < 0x4000)
    irq[c] += begin <= r.PC < end


for pc, op, extra, cost in pcm.pulse_write_sites(S):
    p.hook_register(0, pc, written, (op, extra, cost))

try:
    choose(8)
    tracks = [[] for _ in range(7)]
    for c in (0, 1):
        tracks[c] = [[s, 61 + c * 7 + s % 4, 100, 1] for s in range(16)]
    write_tracks(p, S, tracks)
    for c in range(7):
        write_word(p, S['_seqlength'] + c * 2, 16)
    write_word(p, S['_seqbpm'], 300)
    write_word(p, S['_seqcachedbpm'], 0)
    p.memory[S['_seqeventcache']] = 0
    # Short gates exercise old-note releases while the following attack is
    # independently committed by the timer.
    p.memory[S['_seqgate']] = 50
    p.memory[S['_seqgate'] + 1] = 80
    write_word(p, S['_finepitch'], 10)
    write_word(p, S['_bend'] + 2, 64)
    p.button_press('select')
    p.tick(3)
    press('a')
    p.button_release('select')
    p.tick(60)
    assert v('seqplaying') and not v('syncmode') and v('waveengine') == 0
    for a in attacks:
        a.clear()
    checking_pitch = True
    irq[:] = [0, 0]
    p.button_press('right')
    p.tick(240)
    p.button_release('right')
    assert not pitch_errors, ('Hardware pitch differs', pitch_errors)
    report = []
    for c in (0, 1):
        a = attacks[c]
        assert len(a) > 60
        assert all(b[1] == (a0[1] + 1) % 16 for a0, b in zip(a, a[1:])), (c, a)
        residual = [(t - a[0][0] - i * CPU / 20) * 1000 / CPU for i, (t, _) in enumerate(a)]
        jitter = max(residual) - min(residual)
        report.append(dict(channel=c, attacks=len(a), irq_attacks=irq[c], phase_jitter_ms=jitter, phase_rms_ms=statistics.pstdev(residual)))
        assert irq[c] >= len(a) - 1, report
        assert jitter < 5, report

    choose(18)
    mx = S['_mx']
    p.memory[mx + 4] = 2  # P1 mute, real Mixer input.
    press('a')
    attacks[0].clear()
    p.tick(90)
    assert not attacks[0], 'A prepared P1 attack survived muting'
    press('a')
    attacks[0].clear()
    p.tick(90)
    assert len(attacks[0]) > 20, 'P1 did not recover after unmuting'
    p.memory[mx + 4] = 0
    press('a')
    for a in attacks:
        a.clear()
    p.tick(60)
    assert not any(attacks), 'A prepared attack survived transport stop'
    press('a')
    p.tick(60)
    assert all(len(a) > 10 for a in attacks), 'Restart did not restore both voices'
    Path('build/standalone-irq-no-pcm.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    print('Standalone short gates, scrolling, mute/unmute and stop/restart passed')
except Exception:
    print('Failure state', {n:v(n) for n in ('page','lastpad','padsampled','seqplaying','seqservicing','seqirqready','seqirqfired','seqirqdirty','seqposition','navopen')}, 'PC',hex(p.register_file.PC),'SP',hex(p.register_file.SP),'bank',p.memory[0xff90])
    raise
finally:
    p.stop(save=False)

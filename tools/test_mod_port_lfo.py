"""Compare exact active phase and clock against an archived pre-port main ROM."""
import argparse
import json
from pathlib import Path
from mod_port_harness import Engine

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--before', default='build/mod-port-baseline/GAYBOY.gb')
ap.add_argument('--after', default='build/GAYBOY.gb')
ap.add_argument('--phase-only', action='store_true', help='Compare an already optimized baseline without requiring another CPU reduction')
args = ap.parse_args()
engines = [Engine(args.before), Engine(args.after)]
try:
    checks = 0
    costs = []
    gap_costs = []
    # These offsets describe the unchanged leading private fields of main's
    # evaluation object, checked against the compiler .sym before this port.
    for timing in range(3):
        for div in range(17):
            traces = []
            for E in engines:
                E.reset()
                phase = E.S['_evalpatch'] + 137
                clock = E.S['_evalpatch'] + 140
                E.p.memory[clock:clock+4] = list((22118000).to_bytes(4, 'little'))
                E.put('globalmod', 1, 7)
                E.put('globalmod', div, 6)
                E.put('globalmod', timing, 8)
                trace = []
                gaps = (0, 1, 2, 5, 7, 8, 9, 16, 31, 127, 128, 255)
                for i in range(36):
                    E.word('seqbpm', (120, 150, 240, 999)[(i // 6) % 4])
                    E.put('frameadvance', gaps[i % len(gaps)])
                    if i == 9:
                        E.put('globalmod', 0, 7)
                        E.put('globalmod', 4, 5)
                    if i == 11:
                        E.put('globalmod', 1, 7)
                    if i in (4, 13):
                        E.p.memory[phase] = 0
                    E.call('eval_frame')
                    trace.append((E.p.memory[phase], bytes(E.p.memory[clock:clock+4])))
                traces.append(trace)
            assert traces[0] == traces[1], (div, timing, next(
                (i, a, b) for i, (a, b) in enumerate(zip(*traces)) if a != b))
            checks += len(traces[0])
    for E in engines:
        E.reset()
        E.word('seqbpm', 240)
        E.put('globalmod', 1, 7)
        E.put('globalmod', 8, 6)
        E.call('eval_frame')
        costs.append(sum(E.call('eval_frame')[1] for _ in range(32)) / 32)
        E.put('frameadvance', 255)
        gap_costs.append(E.call('eval_frame')[1])
    if not args.phase_only:
        assert costs[1] < costs[0]
    # Catch-up is infrequent but must remain bounded, rather than looping 255
    # times. Allow the extra quotient/remainder work compared to old main.
    assert gap_costs[1] < 32768, gap_costs
    report = {'exact_comparisons': checks, 'warmed_frame_cycles': costs,
              'gap_255_frame_cycles': gap_costs}
    Path('build/mod-port-lfo.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS:', report)
finally:
    for E in engines:
        E.p.stop(save=False)

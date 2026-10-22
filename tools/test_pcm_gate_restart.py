"""A gated PCM tail must release both slots for the next pair of attacks."""
import argparse
from io import BytesIO
import json
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--rom', default='build/GAYBOY.gb')
ap.add_argument('--out', default='build/pcm-gate-restart.json')
ap.add_argument('--cgb', action='store_true')
args = ap.parse_args()
prefix = Path('tools/test_seq_gen.py').read_text().split('\ntry:\n')[0]
prefix = prefix.replace("Path('build/GAYBOY.noi')", "Path(args.rom).with_suffix('.noi')")
prefix = prefix.replace("PyBoy('build/GAYBOY.gb',", "PyBoy(args.rom,cgb=args.cgb,")
exec(prefix)
results = []
try:
    enter_app(p)
    put('sticky_start', 1)
    initial = BytesIO()
    p.save_state(initial)
    heard = set()
    first_kick = []

    def fetch(_):
        slot = p.register_file.A
        sample = p.memory[S['_drumsamplevoice']+slot]
        heard.add(sample)
        if sample == 0 and not first_kick:
            first_kick.append((word('drumpos', slot), word('drumend', slot)))

    a = S['_drum_fetch_fast']
    p.hook_register(a >> 16, a & 65535, fetch, None)
    lengths = (816, 3584, 1632, 480, 1168, 816)
    for kit in range(6):
        for bpm in (120, 150, 240, 300):
            for duration in (1, 4):
                initial.seek(0)
                p.load_state(initial)
                heard.clear()
                first_kick.clear()
                write_tracks([[], [], [], [], [], [],
                              [[0, 1, 127, duration],
                               [duration, 2, 127, 1], [duration, 3, 127, 1]]])
                put('seqtrack', 6)
                put('drumkit', kit)
                setword('seqbpm', bpm)
                setword('seqglobalbpm', bpm)
                for c in range(7):
                    setword('seqlength', 16, c)
                put('seqmuted', 63)
                put('seqsolo', 0)
                p.button_press('select')
                p.tick(3)
                press('a')
                p.button_release('select')
                p.tick(95)
                capped = min(lengths[kit], (171900//bpm)*duration//2)
                actual = first_kick[0][1]-first_kick[0][0] if first_kick else None
                results.append({'kit': kit, 'bpm': bpm, 'duration': duration,
                                'heard': sorted(heard), 'source_bytes': actual,
                                'expected_source_bytes': capped,
                                'pass': heard == {0, 1, 2} and actual == capped})
    failures = [row for row in results if not row['pass']]
    assert not failures, failures
    print('PASS:', len(results), 'PCM gate/restart cases: all kits, one/four-step '
          'gates, 120/150/240/300 BPM and both following sample attacks')
finally:
    Path(args.out).write_text(json.dumps({'rom': args.rom, 'cgb': args.cgb,
                                        'cases': results}, indent=2)+'\n')
    p.stop(save=False)

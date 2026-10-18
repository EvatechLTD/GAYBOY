"""Forced-DMG edge-scroll render budgets, with PCM and large event pools."""
from pathlib import Path
import json
from seq_storage_helpers import write_tracks
env = {}
source = Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0].replace('range(60)', 'range(600)')
exec(source.replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file='), env)
p, S, v, choose, press = (env[k] for k in ('p', 'S', 'v', 'choose', 'press'))
clock, renders, results = {}, [], []
def hook(name, fn):
    a = S['_' + name]
    p.hook_register(a >> 16, a & 65535, fn, None)
def flush(_):
    if 'start' in clock:
        renders.append((p._cycles() - clock.pop('start')) * 1000 / 4194304)
hook('ui_render', lambda _: clock.update(start=p._cycles()))
hook('ui_flush', flush)
def put(n, x): p.memory[S['_' + n]] = x
try:
    choose(8)
    # Keep the original workload fixed when the application's startup kit
    # changes: 808's longer kick keeps two PCM voices active more often.
    put('drumkit', 0)
    # Preserve the original envelope/gate workload for timing comparisons.
    put('seqgate', 80)
    for running in (False, True):
        for events in (0, 256):
            tracks = [[] for _ in range(7)]
            tracks[0] = [[step, 1 + step % 128, 100, 1] for step in range(events)]
            if running: tracks[6] = [[step, 1 + (step & 1), 100, 1] for step in range(16)]
            write_tracks(p, S, tracks)
            if running and not v('seqplaying'):
                p.button_press('select'); p.tick(5); press('a')
                p.button_release('select'); p.tick(30)
            for hidden in (0, 1):
                for key, pitch in (('up', 71), ('down', 58 if not hidden else 55)):
                    put('seqvelocityhidden', hidden); put('seqtop', 71); put('seqpitch', pitch)
                    put('seqhead', 1 if key == 'up' else 5 if not hidden else 0)
                    put('seqdrawvalid', 0); put('dirty', 1); p.tick(180)
                    renders.clear(); clock.clear()
                    press(key); p.tick(90)
                    assert len(renders) == 1, renders
                    assert v('seqtop') == (72 if key == 'up' else 70), 'Viewport did not scroll'
                    results.append(dict(kit='AMEN ORIGINAL', pcm=running, events=events, velocity_hidden=bool(hidden), direction=key, render_ms=round(renders[0], 2)))
    # Also measure the production 808 kit and full-duration pulse gate.
    put('seqgate', 100); put('drumkit', 1); put('seqvelocityhidden', 0)
    put('seqtop', 71); put('seqpitch', 58); put('seqhead', 5)
    put('seqdrawvalid', 0); put('dirty', 1); p.tick(180)
    renders.clear(); clock.clear()
    press('down'); p.tick(90)
    assert len(renders) == 1 and v('seqtop') == 70
    results.append(dict(kit='TR-808', pcm=True, events=256, velocity_hidden=False, direction='down', render_ms=round(renders[0], 2)))
    assert not env['word']('mixunderruns'), 'PCM underruns during edge scrolling'
    for result in results:
        budget = 110 if result['kit'] == 'TR-808' else 100 if result['pcm'] else 50
        assert result['render_ms'] < budget, result
    print(json.dumps(results, indent=2))
finally:
    p.stop(save=False)

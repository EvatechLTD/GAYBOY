"""Release check: real standalone attacks stay tight under redraw/control load."""
from pathlib import Path
import hashlib
import json
import test_pcm_timing as pcm

results = []
for scroll, view, control in ((False, 'sequencer', None), (True, 'sequencer', None),
                              (False, 'mixer', None), (False, 'mixer', 'volume'),
                              (False, 'mixer', 'pan')):
    r = pcm.run(scroll, 360, view, control)
    results.append(r)
    print(json.dumps({k:r[k] for k in ('ui', 'first_p1_to_p2_step1_ms',
          'pulse1_phase_jitter_ms_peak_to_peak', 'pulse1_phase_jitter_ms_rms',
          'irq_pulse1_onsets', 'pulse1_onsets', 'audio_underruns')}), flush=True)

Path('build/standalone-final.json').write_text(json.dumps(dict(
    rom_sha256=hashlib.sha256(pcm.ROM.read_bytes()).hexdigest(),
    limitations='DMG emulation, actual APU writes; physical hardware remains to be tested.',
    results=results), indent=2) + '\n')
for r in results:
    assert all(r[k] for k in ('meets_first_step_target', 'meets_irq_budget',
                             'meets_audio_delivery', 'meets_note_rate')), r
    assert r['pulse1_phase_jitter_ms_peak_to_peak'] < 5, r
    assert r['pulse1_phase_jitter_ms_rms'] < 1.5, r
    assert r['irq_pulse1_onsets'] >= r['pulse1_onsets'] - 1, r
print('Standalone attack timing and audio delivery passed all five loads')

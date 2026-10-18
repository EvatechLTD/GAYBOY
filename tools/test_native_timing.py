"""DMG cycle-budget comparison, not a claim of electrical hardware validation.

Run python tools/test_native_timing.py after build.ps1. Host emulation speed is
unlimited, but the emulated CPU is a forced DMG with 70,224 cycles per frame.
Hook timestamps count emulated cycles, never wall-clock execution time.
"""
from pathlib import Path
from io import BytesIO
from boot_helpers import enter_app
from seq_storage_helpers import write_tracks,write_word
import json
import math
import statistics
from pyboy import PyBoy

SYMS = {l.split()[1]: int(l.split()[2], 16)
        for l in Path('build/GAYBOY.noi').read_text().splitlines()
        if l.startswith('DEF ')}
CPU_HZ, FRAME_CYCLES = 4194304, 70224
HIGH_RES_CLOCK = "_seqticks" in SYMS
FRAMES, BPM = 720, 240


def run(native, software, scroll):
    p = PyBoy('build/GAYBOY.gb', window='null', sound_emulated=True, cgb=False, ram_file=BytesIO(bytes(32768)))
    p.set_emulation_speed(0)
    enter_app(p)
    def get(name, i=0): return p.memory[SYMS['_' + name] + i]
    def put(name, i, value): p.memory[SYMS['_' + name] + i] = value
    def word(name): return get(name) | (get(name, 1) << 8)
    def press(key):
        mask = {'right': 1, 'left': 2, 'up': 4, 'down': 8,
                'a': 16, 'b': 32, 'select': 64}[key]
        p.button_press(key)
        for _ in range(90):
            p.tick(1)
            if get('lastpad') & mask: break
        assert get('lastpad') & mask, key
        p.button_release(key)
        for _ in range(90):
            p.tick(1)
            if not get('lastpad') & mask: break
        assert not get('lastpad') & mask, key
        p.tick(4)
    def choose(target):
        p.button_press('start')
        for _ in range(100):
            p.tick(1)
            if get('navopen'): break
        assert get('navopen')
        for _ in range(24):
            if get('navchoice') == target: break
            press('down')
        assert get('navchoice') == target, (target, get('navchoice'))
        p.button_release('start')
        p.tick(40)
        assert get('page') == target, (get('page'), target, get('navopen'), get('lastpad'))
    try:
        assert p.memory[0x143] & 0x80 == 0, 'ROM unexpectedly requests CGB'
        assert p.memory[0xff4d] == 0xff, 'DMG has no CGB KEY1 speed switch'
        before = p._cycles()
        p.tick(10)
        assert abs(p._cycles() - before - FRAME_CYCLES * 10) <= 32
        if bool(get('experimental_mode')) == native:
            choose(16)
            press('a')
        assert bool(get('experimental_mode')) == (not native)
        # The same native four-track arrangement is used in both baseline cases.
        # Software load additionally enables the two DDS wave voices: this is a
        # separate stress comparison, not an identical arrangement comparison.
        if software:
            # Selecting W2 and auditioning it activates the shared two-voice DDS
            # engine through its normal MIDI path, without touching timer state.
            for byte in (0x95, 36, 100):
                w = get('wr'); put('rx', w, byte); put('wr', 0, (w + 1) & 255)
                p.tick(8)
            assert get('waveengine') == 2
        choose(8)
        put('seqbpm', 0, BPM & 255); put('seqbpm', 1, BPM >> 8)
        tracks=[[] for _ in range(7)]
        for c in range(6):
            write_word(p,SYMS['_seqlength']+c*2,64)
            if c<4 or (software and c==5):
                tracks[c]=[[step,1+(36 if c==5 else 60+step%12),100,1] for step in range(64)]
        write_tracks(p,SYMS,tracks)
        fires, onsets, frames, pending = [], [], [], []
        def fire(_):
            if p.register_file.A == 0:
                fires.append((p._cycles(), get('seqposition')))
        def onset(_):
            if p.register_file.A == 0:
                onsets.append(p._cycles())
        def frame(_):
            frames.append(get('frameadvance'))
            if HIGH_RES_CLOCK: pending.append(word('seqticks'))
        for name, callback in [('seq_fire', fire), ('play', onset), ('seq_frame', frame)]:
            a = SYMS['_' + name]
            p.hook_register(a >> 16 if a >= 65536 else 0, a & 65535, callback, None)
        p.button_press('select'); p.tick(5); press('a')
        p.button_release('select'); p.tick(20)
        assert get('seqplaying')
        fires.clear(); onsets.clear(); frames.clear(); pending.clear()
        pending_start = word('seqticks') if HIGH_RES_CLOCK else 0
        blocks0, drops0 = word('engineblocks'), word('mixunderruns')
        start = p._cycles()
        if scroll: p.button_press('right')
        p.tick(FRAMES)
        if scroll: p.button_release('right')
        elapsed = p._cycles() - start
        assert abs(elapsed - FRAME_CYCLES * FRAMES) <= 32, (elapsed, FRAME_CYCLES * FRAMES)
        assert len(fires) > 30 and abs(len(onsets) - len(fires)) <= 1, (len(fires), len(onsets))
        onsets[:] = [c for c in onsets if c >= fires[0][0]]
        matched = min(len(fires), len(onsets))
        fires[:] = fires[:matched]; onsets[:] = onsets[:matched]
        # Sequencer itself quantizes sixteenths to vblank, with 896 BPM units
        # per step. Compare hook time against that exact implemented schedule.
        first_cycle, first_pos = fires[0]
        reference_frame = first_cycle // FRAME_CYCLES
        nominal_cycles = CPU_HZ * 60 / (BPM * 4) if HIGH_RES_CLOCK else FRAME_CYCLES * 896 / BPM
        residuals = []
        for i, (cycles, pos) in enumerate(fires):
            assert pos == (first_pos + i) % 64, 'Skipped/reordered sequencer step'
            residuals.append(cycles - (reference_frame * FRAME_CYCLES + i * nominal_cycles))
        centered = [x - statistics.mean(residuals) for x in residuals]
        onset_residuals = [cycles - (onsets[0] + i * nominal_cycles) for i, cycles in enumerate(onsets)]
        onset_centered = [x - statistics.mean(onset_residuals) for x in onset_residuals]
        intervals = [b - a for a, b in zip(onsets, onsets[1:])]
        frame_gaps = [b[0] // FRAME_CYCLES - a[0] // FRAME_CYCLES for a, b in zip(fires, fires[1:])]
        result = {
            'experimental': not native, 'software_wave_load': software,
            'ui': 'held right / viewport redraws' if scroll else 'idle sequencer',
            'frames': FRAMES, 'bpm': BPM, 'clock': 'timer1024Hz' if HIGH_RES_CLOCK else 'vblank',
            'expected_onsets': elapsed / nominal_cycles, 'pulse1_onsets': len(onsets),
            'interval_ms_min': min(intervals) * 1000 / CPU_HZ,
            'interval_ms_max': max(intervals) * 1000 / CPU_HZ,
            'schedule_jitter_ms_peak_to_peak': (max(centered) - min(centered)) * 1000 / CPU_HZ,
            'schedule_jitter_ms_rms': math.sqrt(statistics.mean(x*x for x in centered)) * 1000 / CPU_HZ,
            'onset_jitter_ms_peak_to_peak': (max(onset_centered) - min(onset_centered)) * 1000 / CPU_HZ,
            'onset_jitter_ms_rms': math.sqrt(statistics.mean(x*x for x in onset_centered)) * 1000 / CPU_HZ,
            'step_frame_gap_min': min(frame_gaps), 'step_frame_gap_max': max(frame_gaps),
            'sequencer_service_calls': len(frames),
            'service_frameadvance_max': max(frames),
            'clock_pending_units_start': pending_start,
            'clock_pending_units_end': word('seqticks') if HIGH_RES_CLOCK else 0,
            'clock_pending_units_max': max(pending) if pending else 0,
            'audio_blocks': (word('engineblocks') - blocks0) & 65535,
            'audio_underruns': (word('mixunderruns') - drops0) & 65535,
        }
        if native:
            assert bool(p.memory[0xff07] & 4) == HIGH_RES_CLOCK, 'Unexpected native sequencer timer state'
            assert not get('mixrunning') and not get('expactive')
            assert result['audio_blocks'] == 0
        # No step may be delayed for two additional vblanks beyond the normal
        # three/four-frame sixteenth quantization at 240 BPM.
        result['meets_step_latency_target'] = max(frame_gaps) <= math.ceil(896 / BPM) + 1
        result['meets_frame_service_target'] = max(frames) <= 2
        result['meets_5ms_jitter_target'] = result['onset_jitter_ms_peak_to_peak'] <= 5
        result['meets_audio_delivery_target'] = result['audio_underruns'] == 0
        return result
    finally:
        p.stop(save=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bpm', type=int, default=240)
    parser.add_argument('--frames', type=int, default=720)
    parser.add_argument('--output', default='build/native-timing.json')
    parser.add_argument('--native-only', action='store_true', help='Run only the experimental-off native hardware cases')
    options = parser.parse_args()
    BPM, FRAMES = options.bpm, options.frames
    results, failures = [], []
    for native, software in ([(True, False)] if options.native_only else [(True, False), (False, False), (False, True)]):
        for scroll in (False, True):
            try:
                result = run(native, software, scroll)
            except AssertionError as error:
                result = {'experimental': not native, 'software_wave_load': software,
                          'ui': 'held right / viewport redraws' if scroll else 'idle sequencer',
                          'bpm': BPM, 'failure': str(error)}
                failures.append(result)
            results.append(result)
    report = {
        'clock_hz': CPU_HZ, 'cycles_per_frame': FRAME_CYCLES,
        'model': 'DMG forced with cgb=False',
        'limitations': 'Cycle-budget emulation; not electrical/analog, cartridge latency, MIDI serial transport, or physical hardware validation.',
        'results': results,
    }
    Path(options.output).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('COMPLETE: DMG cycle-budget comparison; consult timing target flags and underrun counts for failures')
    if failures:
        raise SystemExit(1)

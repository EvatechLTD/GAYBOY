"""Duplicate resident pads preserve PCM tails and unchanged patch runtime."""
from io import BytesIO
from pathlib import Path
import argparse
import statistics
from pyboy import PyBoy
from boot_helpers import enter_app

ap = argparse.ArgumentParser()
ap.add_argument('--rom', default='build/GAYBOY.gb')
ap.add_argument('--wave-noise', action='store_true')
ap.add_argument('--bpm', type=int, default=120)
args = ap.parse_args()
rom = args.rom
S = {l.split()[1]: int(l.split()[2], 16) for l in Path(rom).with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
p = PyBoy(rom, window='null', sound_emulated=True, cgb=False, ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
def get(n, i=0):
    a = S['_' + n] + i
    return p.memory[0, a] if 0xa000 <= a < 0xc000 else p.memory[a]
def put(n, value, i=0):
    a = S['_' + n] + i
    if 0xa000 <= a < 0xc000: p.memory[0, a] = value
    else: p.memory[a] = value
def word(n, value, i=0):
    put(n, value & 255, i); put(n, value >> 8, i+1)
def press(key):
    mask = {'a':16, 'start':128}[key]
    p.button_press(key)
    for _ in range(600):
        p.tick(1)
        if get('lastpad') & mask: break
    assert get('lastpad') & mask
    p.button_release(key)
    for _ in range(600):
        p.tick(1)
        if not get('lastpad') & mask: break
    assert not get('lastpad') & mask
    p.tick(3)
def launch(slot):
    put('mx', 30+slot, 4); press('a')
    for _ in range(600):
        p.tick(1)
        if get('mx', 1) == slot and get('mx', 2) == 255 and not get('seqservicing'): return
    raise AssertionError(('launch timeout', slot))

try:
    enter_app(p, S)
    put('page', 18); put('dirty', 1); put('mx', 0, 3)
    word('seqglobalbpm', args.bpm); word('seqbpm', args.bpm)
    # Resident events live directly in the selected pad's SRAM bank.
    offset = 0
    for c in range(7):
        if args.wave_noise:
            events = [[0, 49, 100, 16]] if c == 2 else [[s, 11, 100, 1] for s in range(16)] if c == 6 else []
        else:
            events = [[0, 61, 100, 16]] if c == 0 else [[0, 1, 127, 1]] if c == 6 else []
        word('seqeventoffsets', offset, c*2); word('seqeventcounts', len(events), c*2)
        for e in events:
            p.memory[1, 0xa000+768+offset*4:0xa000+772+offset*4] = e
            offset += 1
    put('pattern_dirty', 1)
    # Raw fixture writes bypass the editor's drum cache invalidation.
    a=S['_eval_drum_dirty'];code=list(p.memory[a>>16,a&65535:(a&65535)+5])
    assert code[0]==0x21 and code[3:]==[0x36,1],code
    drum_dirty_at=code[1]|code[2]<<8
    p.memory[drum_dirty_at]=1
    launch(1)  # Autosnapshot pad zero through the real launch request.
    p.memory[1, 0xa800:0xb000] = list(p.memory[1, 0xa000:0xa800])
    launch(0)
    assert get('seqplaying')
    timing = []
    wave_attacks = []
    reads = []
    a = S['_resident_read']; p.hook_register(a >> 16, a & 65535, lambda _: reads.append(p._cycles()), None)
    for name in ('sparse_activate', 'seq_pattern_handoff', 'play', 'tones_apply', 'tones_apply_buffer', 'seq_fire', 'seq_off'):
        def stamp(_, name=name):
            if name == 'play' and p.register_file.A == 2:
                wave_attacks.append(p._cycles())
            if name != 'play' or p.register_file.A == (3 if args.wave_noise else 0):
                timing.append((name+str(p.register_file.A) if name in ('seq_fire', 'seq_off') else name, p._cycles()))
        a = S['_' + name]; p.hook_register(a >> 16, a & 65535, stamp, None)
    counts = {}
    for name in ('eval_audio_reset', 'drum_stop', 'drum_map_factory', 'globals', 'seq_gates'):
        counts[name] = 0
        def count(_, name=name): counts[name] += 1
        a = S['_' + name]; p.hook_register(a >> 16, a & 65535, count, None)
    if args.wave_noise:
        p.memory[drum_dirty_at]=1
        a=S['_drum_noise'];p.hook_register(a>>16,a&65535,lambda _:timing.append(('play',p._cycles())),None)
        p.tick(180)
        idle = [t for n,t in timing if n == 'play']
        intervals = [(b-a)*1000/4194304 for a,b in zip(idle,idle[1:])]
        print('Idle hi-hat intervals ms (min/median/max):', tuple(round(f(intervals),3) for f in (min,statistics.median,max)))
    for quant in (0, 1, 4):
        put('mx', quant, 3)
        launch(1); launch(0)
        if args.wave_noise and quant:
            switches = [t for n,t in timing if n == 'sparse_activate'][-2:]
            for start in switches:
                noise = next(t for n,t in timing if n == 'play' and t > start)
                assert not any(start <= t <= noise for t in wave_attacks), ('Wave retriggered at duplicate-pad boundary', quant)
                assert not any(start <= t <= noise for t in reads), ('Storage read during prepared launch', quant)
        assert not any(counts.values()), (quant, counts)
        assert get('seqowned', 2) == 49 if args.wave_noise else get('seqowned') == 61
        assert get('seqplaying')
    put('mx', 0, 3)
    print('PASS identical pad: no runtime reset, PCM stop, map rebuild, global write or gate rebuild', counts)
    windows = []
    for i, (name, start) in enumerate(timing):
        if name == 'sparse_activate':
            handoff = next(t for n, t in timing[i+1:] if n == 'seq_pattern_handoff')
            attack = next(t for n, t in timing[i+1:] if n == 'play')
            windows.append(tuple(round((t-start)*1000/4194304, 3) for t in (handoff, attack)))
    print('Duplicate pad activation -> (handoff, onset dispatch) ms:', windows)
    if args.wave_noise:
        first = next(t for n, t in timing if n == 'sparse_activate')
        last = next(t for n,t in reversed(timing) if n == 'sparse_activate')
        print('Last launch stages:', [(n, round((t-last)*1000/4194304, 3)) for n,t in timing if last <= t < last+419430])
        print('PASS quantized duplicate pads preserve wave oscillator without retrigger')
        noises = [t for n,t in timing if n == 'play']
        switches = [t for n,t in timing if n == 'sparse_activate'][2:]
        spans = [(b-a)*1000/4194304 for a,b in zip(noises,noises[1:]) if any(a<s<b for s in switches)]
        print('Quantized switch hi-hat intervals ms:', [round(t,3) for t in spans])
        # Compare switch timing with this same ROM's steady playback jitter.
        # Dispatch is foreground work; do not confuse its baseline variation
        # with the additional storage stalls this regression targets.
        nominal = 60000/args.bpm/4
        idle_error = max(abs(t-nominal) for t in intervals)
        assert max(abs(t-nominal) for t in spans) <= idle_error+2, (spans, idle_error)
        # A newer pad request must replace the candidate already being prepared.
        p.memory[1, 0xb000:0xb800] = list(p.memory[1, 0xa800:0xb000])
        p.memory[1, 0xb000+768+1] = 50
        put('mx', 31, 4); press('a')
        launch(2)
        assert get('seqowned', 2) == 50, 'Cancelled candidate installed instead of latest request'
        # A changed wave instrument must trigger the incoming wave normally.
        shape = (p.memory[1, 0xa000+128+64+14]+1) % 32
        p.memory[1, 0xa000+128+64+14] = shape
        attacks_before = len(wave_attacks)
        launch(0)
        assert get('seqowned', 2) == 49 and get('param', 2*26+14) == shape
        assert len(wave_attacks) > attacks_before
        print('PASS replacement request, changed wave pitch and changed wave instrument')
        raise SystemExit(0)
    # A real patch change must still install, without resetting identical FX.
    p.memory[1, 0xa800+128] = 2
    launch(0); launch(1)
    assert get('param') == 2
    assert counts['eval_audio_reset'] == 0 and counts['drum_stop'] == 0, counts
    print('PASS changed pulse tone installed; unchanged FX and PCM preserved')
    # Incoming rests must release outgoing melodic ownership.
    p.memory[1, 0xa000+32] = 0
    p.memory[1, 0xa000+33] = 0
    launch(0)
    assert get('seqowned') == 0
    print('PASS incoming rest releases outgoing pulse')
    # Changed FX and tempo must invalidate the state that depends on them.
    word('seqglobalbpm', 0)
    p.memory[1, 0xa800+128+176+130+2] = 63
    p.memory[1, 0xa800+32+75] = 180
    p.memory[1, 0xa800+32+76] = 0
    launch(1)
    assert counts['eval_audio_reset'] > 0 and counts['seq_gates'] > 0, counts
    assert get('seqbpm') == 180 and get('seqbpm', 1) == 0
    print('PASS changed FX reset and changed tempo gate rebuild')
finally:
    p.stop(save=False)

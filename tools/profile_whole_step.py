"""Trace built-in demo dispatch, elapsed time and navigation/launch disturbances.

Records logical dispatch and actual APU writes, not detected audible onset.
Uses the built-in demo unless an aligned-note fixture is requested.
"""
import argparse
import ast
import hashlib
import json
from io import BytesIO
from pathlib import Path
from pyboy import PyBoy
from boot_helpers import enter_app

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--rom', default='build/GAYBOY.gb')
ap.add_argument('--output', default='build/whole-step-profile.json')
ap.add_argument('--slave', action='store_true', help='Diagnostic 120 BPM pulse injection at timer service; not a cable test')
ap.add_argument('--no-pulse-irq', action='store_true', help='Suppress advance pulse packets at timer entry for diagnosis')
ap.add_argument('--bpm', type=int)
ap.add_argument('--fixture', choices=('native-four','pcm'), help='Additional aligned-note fixture; omitted uses untouched built-in demo')
args = ap.parse_args()
rom = Path(args.rom)
symbols = {l.split()[1]: int(l.split()[2], 16)
           for l in rom.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
p = PyBoy(str(rom), window='null', sound_emulated=True, cgb=False,
          ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
events = []
timers = []
phase = 'boot'
completed = False
pcm_buffers = {}
phase_watch = [None,0]
epoch = 0

def value(name, i=0):
    return p.memory[symbols['_'+name]+i]

def word(name):
    return value(name) | value(name, 1) << 8

def record(name):
    global epoch
    if name in ('mixer_boundary','seq_pattern_start'):epoch+=1
    events.append(dict(event=name, cycle=p._cycles(), phase=phase,
        epoch=epoch,
        channel=p.register_file.A, positions=[value('seqposition', i) for i in range(7)],
        clock=word('seqclock'), ticks=word('seqticks'), deadline=word('seqdeadline'),
        fraction=value('seqfraction'), bpm=word('seqbpm'), engine=value('waveengine'),
        page=value('page'), slot=value('mx',1), pending=value('mx',2)))
    if '_seqnativehits' in symbols and name in ('seq_frame','seq_fire','mixer_boundary','seq_pattern_start'):
        events[-1].update(native_hits=word('seqnativehits'),native_misses=word('seqnativemisses'),
            native_fallback=value('seqnativefallback'),keys=[value('keycount',i) for i in range(4)],
            owned=[value('seqowned',i) for i in range(4)])

def press(key):
    mask={'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'select':64,'start':128}[key]
    p.button_press(key)
    for _ in range(180):
        p.tick(1)
        if value('lastpad') & mask: break
    assert value('lastpad') & mask, (key, phase)
    p.button_release(key)
    for _ in range(180):
        p.tick(1)
        if not value('lastpad') & mask: break
    assert not value('lastpad') & mask
    p.tick(4)

def run_frames(count):
    for _ in range(count):p.tick(1)

def choose(page):
    p.button_press('start')
    for _ in range(180):
        p.tick(1)
        if value('navopen'): break
    assert value('navopen')
    for _ in range(40):
        if value('navchoice') == page: break
        press('down')
    assert value('navchoice') == page
    p.button_release('start')
    p.tick(40)
    assert value('page') == (1 if 11 <= page <= 15 else page)

try:
    enter_app(p, symbols)
    for name in ('seq_frame','mixer_boundary','seq_fire','seq_pattern_start',
                 'seq_pattern_release','drum_enable','seq_transport','drum_fire','drum_noise','kick_start','play'):
        addr=symbols['_'+name]
        p.hook_register(addr >> 16, addr & 65535, record, name)
    choose(18)
    if args.fixture:
        from seq_storage_helpers import write_tracks, write_word
        def fixture(variant):
            tracks=[[] for _ in range(7)]
            for c in range(4):
                tracks[c]=[[s,49+c*7+variant+s%3,100,1] for s in range(16)]
            if args.fixture=='pcm':
                tracks[6]=[[s,4,100,4] for s in range(0,16,4)]
            write_tracks(p,symbols,tracks)
            for c in range(7):
                write_word(p,symbols['_seqlength']+c*2,16)
                p.memory[symbols['_seqgate']+c]=100
            p.memory[symbols['_param']+2*26+15]=1
            p.memory[symbols['_param']+3*26+1]=12
            p.memory[symbols['_seqcachedbpm']]=0
        for slot in (0,1):
            if slot:
                p.memory[symbols['_mx']+4]=31
                press('a');p.tick(60);choose(18)
            fixture(slot)
            choose(20);p.memory[symbols['_mx']+6]=slot;press('b');choose(18)
        p.memory[symbols['_mx']+4]=30;press('a');p.tick(60)
    if args.bpm:
        for name in ('seqbpm','seqglobalbpm'):
            p.memory[symbols['_'+name]]=args.bpm&255
            p.memory[symbols['_'+name]+1]=args.bpm>>8
    if args.slave:
        choose(27)
        press('right'); press('right')
        press('down'); press('right')
        assert value('syncmode') == 2 and value('syncslave')
        choose(18)
    next_pulse = [None]
    def timer(_):
        now = p._cycles()
        if phase_watch[0]!=phase:phase_watch[:]=[phase,now]
        if now-phase_watch[1]>4194304*(8 if phase=='start' else 60):
            raise RuntimeError(('Phase exceeded emulated CPU budget',phase,
                word('seqticks'),word('seqclock'),value('waveengine'),
                value('seqnativepending') if '_seqnativepending' in symbols else None,
                p.memory[0xffff],p.memory[0xff07]))
        if value('seqplaying'):
            timers.append((now,phase,word('seqticks'),value('seqfraction'),value('waveengine')))
            if args.no_pulse_irq and not value('syncmode'):
                p.memory[symbols['_seqirqready']]=0
            if args.slave:
                if next_pulse[0] is None: next_pulse[0]=now+4194304/48
                while now >= next_pulse[0]:
                    at=value('wr');p.memory[symbols['_rx']+at]=0xf8
                    p.memory[symbols['_wr']]=(at+1)&255
                    next_pulse[0]+=4194304/48
    p.hook_register(0,symbols['_engine_timer'],timer,None)
    import test_pcm_timing as pcm
    import pyboy
    pcm.ROM=rom
    irq_start=symbols.get('_seq_irq_tick',0)
    irq_end=min((v for k,v in symbols.items() if k.startswith('_') and irq_start<v<0x4000),default=irq_start)
    def drum_mix(_):
        voices=[]
        for c in range(2):
            if not value('drumon',c):continue
            sample=value('drumsamplevoice',c)
            kit=value('drumkit')
            offset_at=(symbols['_kitoffset']+(kit-1)*20 if kit else symbols['_amenoffset'])+sample*2
            bank=offset_at>>16;at=offset_at&65535
            offset=(p.memory[bank,at]|p.memory[bank,at+1]<<8) if bank else (p.memory[at]|p.memory[at+1]<<8)
            pos=value('drumpos',c*2)|value('drumpos',c*2+1)<<8
            if pos==offset:voices.append(dict(voice=c,sample=sample,step=value('seqposition',6),epoch=epoch))
        pcm_buffers[value('mixwrite')]=voices
    addr=symbols['_drum_mix'];p.hook_register(addr>>16,addr&65535,drum_mix,None)
    def apu_write(site):
        op,extra,cost,source=site;r=p.register_file
        at=(r.B<<8)|r.C if op==0x02 else (r.D<<8)|r.E if op==0x12 else r.HL if op in (0x22,0x32,0x36,0x77) else 0xff00+extra if op==0xe0 else 0xff00+r.C if op==0xe2 else extra
        data=extra if op==0x36 else r.A
        if at in (0xff14,0xff19,0xff1e,0xff23) and data&128:
            record('PCM-block-upload' if source=='drum_timer' else 'APU-trigger')
            c=(0xff14,0xff19,0xff1e,0xff23).index(at)
            events[-1].update(channel=c,register=at,cycle=p._cycles()+cost,source=source,
                target_step=value('seqirqstep',c) if c<2 and irq_start<=r.PC<irq_end else value('seqposition',6 if source in ('drum_noise','kick_start','kick_stop') else c))
            if source=='seq_irq_tick' and events[-1]['target_step']!=value('seqposition',c):events[-1]['epoch']+=1
            if source=='seq_native_hardware':
                target=p.memory[0xa428+c]
                if target!=value('seqposition',c):events[-1]['epoch']-=1
                events[-1]['target_step']=target
            if source=='drum_timer':
                voices=pcm_buffers.pop(value('mixread'),[])
                events[-1]['starting_voices']=voices
                if voices:events[-1]['event']='PCM-source-first-upload'
    sites=[]
    for site in pcm.pulse_write_sites(symbols):
        sites.append((0,site[0],site[1:]+('seq_irq_tick' if irq_start<=site[0]<irq_end else 'play',)))
    rom_bytes=rom.read_bytes()
    tree=ast.parse((Path(pyboy.__file__).parent/'core/opcodes.py').read_text())
    lengths=next(ast.literal_eval(n.value.args[1]) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OPCODE_LENGTHS' for t in n.targets))
    for name in ('kick_start','kick_stop','drum_noise','drum_timer','seq_native_hardware'):
        if '_'+name not in symbols:continue
        start=symbols['_'+name];bank=start>>16;pc=start&65535
        end=min(v for k,v in symbols.items() if k.startswith('_') and start<v<((bank<<16)|0x8000))&65535
        while pc<end:
            physical=bank*0x4000+(pc-0x4000 if bank else pc)
            op=rom_bytes[physical];size=2 if op==0xcb else lengths[op]
            if op in (0x02,0x12,0x22,0x32,0x36,0x77,0xe0,0xe2,0xea):
                extra=rom_bytes[physical+1] if size>1 else 0
                if op==0xea:extra|=rom_bytes[physical+2]<<8
                cost=16 if op==0xea else 12 if op in (0x36,0xe0) else 8
                sites.append((bank,pc,(op,extra,cost,name)))
            assert size>0
            pc+=size
    for bank,pc,site in sites:p.hook_register(bank,pc,apu_write,site)
    print('Demo', dict(bpm=word('seqbpm'), lengths=[value('seqlength',i*2)|value('seqlength',i*2+1)<<8 for i in range(7)],
                       counts=[value('seqeventcounts',i*2)|value('seqeventcounts',i*2+1)<<8 for i in range(7)]), flush=True)
    phase='start'
    p.memory[symbols['_mx']+4]=0
    press('a')
    assert value('seqplaying')
    phase='idle'
    run_frames(240)
    phase='navigate'
    for page in (11,12,13,15,8,10,17,18): choose(page)
    for quant in (4,2,1):
        for slot in ((1,0) if args.fixture else (1,2,3,0)):
            phase=f'launch-q{quant}-pad{slot}'
            p.memory[symbols['_mx']+3]=quant
            p.memory[symbols['_mx']+4]=30+slot
            press('a')
            run_frames(240)
    phase='recovery'
    run_frames(240)
    report=dict(rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
                measurement='Logical function entry, not audible onset',
                fixture=args.fixture or 'built-in demo',
                apu_measurement='Actual melodic, drum noise and kick NRx4 writes; PCM first upload carrying a newly started source (not detected audible onset)',
                synthetic_slave=args.slave,suppress_pulse_irq=args.no_pulse_irq,events=events,timers=timers)
    Path(args.output).write_text(json.dumps(report, indent=2)+'\n')
    completed = True
    for label in dict.fromkeys(e['phase'] for e in events):
        entries=[e for e in events if e['phase']==label and e['event']=='mixer_boundary']
        gaps=[(b['cycle']-a['cycle'])*1000/4194304 for a,b in zip(entries,entries[1:])]
        print(label, dict(boundaries=len(entries),min_ms=round(min(gaps,default=0),3),
                         max_ms=round(max(gaps,default=0),3),
                         max_pending=max((e['ticks'] for e in events if e['phase']==label),default=0)),flush=True)
finally:
    if not completed:
        Path(args.output).write_text(json.dumps(dict(incomplete=True,phase=phase,
            rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
            fixture=args.fixture or 'built-in demo',
            pc=p.register_file.PC,state={n:value(n) for n in ('lastpad','padsampled','padread','padwrite','navopen','navblocked','rollbuilding','seqservicing','seqnativepending') if '_'+n in symbols},events=events,timers=timers),indent=2)+'\n')
    p.stop(save=False)

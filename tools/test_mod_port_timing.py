"""DMG hardware-write timing under real navigation and interruptible CPU load.

The stall changes only this emulator instance: a register-preserving delay is
inserted ahead of ui_render. It keeps interrupts enabled and does not yield to
mixfill, so this checks deadline ownership rather than cooperative UI servicing.
"""
import argparse
from collections import defaultdict
from io import BytesIO
import json
from pathlib import Path
import statistics

from pyboy import PyBoy
from boot_helpers import enter_app

ap=argparse.ArgumentParser()
ap.add_argument('--rom',default='build/GAYBOY.gb')
ap.add_argument('--bpm',type=int,default=300)
ap.add_argument('--arp-div',type=int,default=2)
ap.add_argument('--synclfo',action='store_true')
ap.add_argument('--measure',action='store_true')
ap.add_argument('--foreground',action='store_true')
ap.add_argument('--pcm',action='store_true')
ap.add_argument('--native-sync',action='store_true')
ap.add_argument('--arp',action='store_true')
ap.add_argument('--arp-only',action='store_true')
ap.add_argument('--out',default='build/mod-port-timing.json')
args=ap.parse_args()
rom=Path(args.rom);raw=rom.read_bytes()
S={l.split()[1]:int(l.split()[2],16) for l in rom.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
def v(n,i=0):return p.memory[S['_'+n]+i]
def put(n,x,i=0):p.memory[S['_'+n]+i]=x&255
def word(n,i=0):return v(n,i)|v(n,i+1)<<8
def setword(n,x,i=0):put(n,x,i);put(n,x>>8,i+1)
def tap(k):p.button_press(k);p.tick(5);p.button_release(k);p.tick(5)
lengths=[1]*256
for op in (6,14,22,30,38,46,54,62,16,24,32,40,48,56,198,206,214,222,224,230,232,238,240,246,248,254,203):lengths[op]=2
for op in (1,8,17,33,49,194,195,196,202,204,205,210,212,218,220,234,250):lengths[op]=3
hits=defaultdict(list);entries=defaultdict(int);minsp=[0xe000];timer_calls=[0];drained=[0];units=[0];boundaries=[0];stalls=[0]
def timer_hook(_):
    timer_calls[0]+=1;units[0]+=(v("seqfraction")+183)>>6
def drain_hook(_):
    if not v("seqservicing"):drained[0]+=word("seqticks")
def boundary_hook(_):boundaries[0]+=1
def write_hook(info):
    op,imm=info;r=p.register_file
    address=r.HL if op in (0x22,0x32,0x36,0x70,0x71,0x72,0x73,0x74,0x75,0x77) else (r.D<<8)|r.E if op==0x12 else (r.B<<8)|r.C if op==2 else 0xff00+r.C if op==0xe2 else imm
    data=(r.B,r.C,r.D,r.E,r.HL>>8,r.HL&255,0,r.A)[op&7] if 0x70<=op<=0x77 else imm if op==0x36 else r.A
    if address in (0xff14,0xff19,0xff1e,0xff23) and data&128:
        c=(0xff14,0xff19,0xff1e,0xff23).index(address)
        hits[c].append(p._cycles())
        minsp[0]=min(minsp[0],r.SP)
def hooks_for(name):
    start=S['_'+name];bank=start>>16;start&=65535
    end=min(a&65535 for n,a in S.items() if n.startswith('_') and a>>16==bank and start<(a&65535)<(0x8000 if bank else 0x4000))
    pc=start
    while pc<end:
        off=bank*16384+pc-(0x4000 if bank else 0);op=raw[off]
        # Current main emits pulse trigger writes through BC and wave/noise
        # triggers through LDH. Hooking every stack/local write in this large
        # function makes PyBoy hang in some navigation paths. Validate trigger
        # coverage against function-entry counts below rather than assume it.
        if op in (2,0xe0,0xe2,0xea):
            imm=0xff00+raw[off+1] if op==0xe0 else int.from_bytes(raw[off+1:off+3],'little') if op==0xea else raw[off+1] if op==0x36 else 0
            p.hook_register(bank,pc,write_hook,(op,imm))
        pc+=lengths[op]
        if name=="seq_attack" and op==0xe9:pc+=8 # four-entry switch pointer table

def stall_hook(_):stalls[0]+=1

def stall_renderer():
    addr=S['_ui_render'];bank=addr>>16;pc=addr&65535;off=bank*16384+pc-(0x4000 if bank else 0)
    n=0
    while n<3:n+=lengths[raw[off+n]]
    stall=0x7f80
    target=bank*16384+stall-0x4000
    assert all(b==255 for b in raw[target:target+64]),'Stall trampoline must occupy unused ROM padding'
    code=bytes([0xf5,0xc5,0x01,0x88,0x13,0x0b,0x78,0xb1,0x20,0xfb,0xc1,0xf1])+raw[off:off+n]+bytes([0xc3,(pc+n)&255,(pc+n)>>8])
    for i,b in enumerate(code):p.memory[bank,stall+i]=b
    for i,b in enumerate([0xc3,stall&255,stall>>8]):p.memory[bank,pc+i]=b
    p.hook_register(bank,stall,stall_hook,None)

report={}
try:
    enter_app(p,S)
    if '_dispatch_enabled' in S:put('dispatch_enabled',not args.foreground)
    if not args.native_sync:put('syncmode',0);put('syncslave',0)
    tracks=[[] for _ in range(7)]
    for c in range(4):
        if c==2 and args.pcm or args.arp_only and c>=2:continue
        tracks[c]=[[s,49+c*7+s%3,127,1] for s in range(16)]
        if args.arp and c<2:tracks[c]=[[s,n+c*7,127,4] for s in range(0,16,4) for n in (49,53,56)]
    if args.pcm:tracks[6]=[[s,1+(s//4)%2,127,1] for s in range(0,16,4)]
    at=0
    p.memory[0x4000]=1
    for c,events in enumerate(tracks):
        setword('seqeventoffsets',at,c*2);setword('seqeventcounts',len(events),c*2);setword('seqlength',16,c*2)
        for e in events:p.memory[0xa300+at*4:0xa304+at*4]=e;at+=1
    p.memory[0x4000]=0
    setword('seqbpm',args.bpm);setword('seqglobalbpm',args.bpm)
    put('seqmuted',0);put('seqsolo',0);setword('drummutemask',0);setword('drumsolomask',0)
    for c in range(4):
        put('evalpatch',int(args.arp and c<2),c*16)
        put('evalpatch',1,c*16+4);put('evalpatch',args.arp_div,c*16+2);put('evalpatch',0,c*16+1);put('evalpatch',0,c*16+3)
        put('evalpatch',0,c*16+9);put('evalpatch',0,c*16+10)
        put('param',15,c*26+1);put('param',0,c*26+9);put('param',0,c*26+22)
        put('mx',127,12+c);put('mx',3,19+c)
    put('globalmod',0,5)
    put('globalmod',int(args.synclfo),7);put('globalmod',8,6);put('globalmod',0,8)
    if args.synclfo:
        for c in range(3):put('evalpatch',1,c*16+8);put('evalpatch',8,c*16+9)
    setword('pattern_generation',(word('pattern_generation')+1)&65535)
    put('seqtrack',0);put('selected',0);put('seqhead',0);put('page',8);put('dirty',1)
    p.tick(60)
    hooks_for('play')
    address=S['_play'];p.hook_register(address>>16,address&65535,lambda _:entries.__setitem__(p.register_file.A,entries[p.register_file.A]+1),None)
    if '_seq_attack' in S:hooks_for('seq_attack')
    p.hook_register(0,S['_engine_timer'],timer_hook,None)
    for name,hook in [('seq_frame',drain_hook),('mixer_boundary',boundary_hook)]:
        addr=S['_'+name];p.hook_register(addr>>16,addr&65535,hook,None)
    p.button_press('select');tap('a');p.button_release('select');p.tick(30)
    assert v('seqplaying'),'Transport did not start'
    for phase in ('idle','navigation','stall'):
        if phase=='stall':stall_renderer()
        hits.clear();entries.clear();timer_calls[0]=drained[0]=units[0]=boundaries[0]=0;start_cycle=p._cycles()
        for frame in range(240):
            if phase=='navigation':
                if frame%12==0:p.button_press('right')
                if frame%12==2:p.button_release('right')
                if frame%24==4:p.button_press('up')
                if frame%24==6:p.button_release('up')
            if phase=='stall':put('dirty',1)
            p.tick(1)
        summary={}
        expected=(960*(2**args.arp_div)/args.bpm/1024*1000) if args.arp else 15000/args.bpm
        for c,times in sorted(hits.items()):
            gaps=[(b-a)/4194.304 for a,b in zip(times,times[1:])]
            assert len(gaps)>10,(phase,c,len(gaps))
            target=expected if args.arp and c<2 else 15000/args.bpm
            summary[c]={'attacks':len(times),'min_ms':min(gaps),'max_ms':max(gaps),'mean_ms':statistics.mean(gaps),'max_error_ms':max(abs(t-target) for t in gaps)}
        assert 0 in summary and 1 in summary,(phase,summary)
        if '_seq_attack' not in S:
            assert all(abs(len(hits[c])-n)<=2 for c,n in entries.items()),('Incomplete APU trigger coverage',dict(entries),{c:len(h) for c,h in hits.items()})
        report[phase]=summary
        print(phase,json.dumps(summary),'bpm',word('seqbpm'),'timer_hz',timer_calls[0]*4194304/(p._cycles()-start_cycle),'TMA',p.memory[0xff06],'units',units[0],'drained',drained[0],'boundaries',boundaries[0],'pending',word('seqticks'),'threshold',word('seqthreshold'),flush=True)
    report['stall_calls']=stalls[0]
    report['foreground_load_exercised']=stalls[0]>=5
    report['pcm_underruns']=word('mixunderruns');report['lowest_observed_sp']=hex(minsp[0])
    report['bpm']=args.bpm;report['arp_div']=args.arp_div;report['synclfo']=args.synclfo
    if '_eval_prepared_hits' in S:report['prepared_hits']=word('eval_prepared_hits');report['prepared_misses']=word('eval_prepared_misses')
    if not args.measure:assert stalls[0]>=5,('Foreground load was not exercised',stalls[0])
    report['rom']=str(rom);report['pcm']=args.pcm;report['arp']=args.arp;report['foreground']=args.foreground
    if not args.measure:
        limit=7 if args.pcm else 4
        assert all(s['max_error_ms']<limit for phase in ('idle','navigation','stall') for s in report[phase].values()),report
        assert report['pcm_underruns']==0,report
        assert minsp[0]>=0xde00,report
    print('Measured' if args.measure else 'PASS',json.dumps(report),flush=True)
finally:
    Path(args.out).write_text(json.dumps(report,indent=2)+'\n')
    p.stop(save=False)

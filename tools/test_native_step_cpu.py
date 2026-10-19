"""Run the actual complete-step preparation/commit on a DMG CPU.

Checks all four note states, durations, wave data, PCM handoff and cancellation.
Reports CPU budgets rather than substituting host execution time.
"""
import json
from io import BytesIO
from pathlib import Path
from pyboy import PyBoy
from seq_storage_helpers import write_tracks,write_word

S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
def v(name,i=0):return p.memory[S['_'+name]+i]
def put(name,x,i=0):p.memory[S['_'+name]+i]=x
def word(name):return v(name)|v(name,1)<<8
returned=[]
budgets=[]
apu_cycles=[]
def call(name,arg=0,banked=True,extra=()):
    addr=S['_'+name];bank=addr>>16
    p.memory[0x2000]=bank;p.memory[0x3000]=0;p.memory[0xff90]=bank
    frame=[0,0xc0]+([0,0,0,0,arg,*extra] if banked else [])
    p.memory[0xdfe0:0xdfe0+len(frame)]=frame
    p.register_file.SP=0xdfe0;p.register_file.A=arg;p.register_file.PC=addr&65535
    returned.clear();start=p._cycles()
    for _ in range(60):
        p.tick(1)
        if returned:break
    assert returned,(name,hex(p.register_file.PC))
    cycles=returned[0]-start;budgets.append((name,cycles));return cycles

try:
    # Start from a CPU that has never entered HALT; application state below
    # is explicit, as in the existing isolated onset/gate CPU harness.
    p.memory[0x0000]=10;p.memory[0x4000]=0;p.memory[0xff50]=1
    p.memory[0xffff]=0;p.memory[0xff0f]=0;p.memory[0xff07]=0;p.memory[0xff40]=0
    p.memory[0xff26]=0x80;p.memory[0xff24]=0x77;p.memory[0xff25]=0xff
    p.memory[0xc000:0xc004]=[0x18,0,0x18,0xfe]
    p.hook_register(0,0xc000,lambda _:returned.append(p._cycles()),None)
    rom=Path('build/GAYBOY.gb').read_bytes()
    hw=S['_seq_native_hardware'];hw_end=min(a for k,a in S.items() if k.startswith('_') and hw<a<0x4000)
    def attack(channel):
        if p.register_file.A&128 and p.memory[0xa400]&(1<<channel):apu_cycles.append((channel,p._cycles()+12))
    for pc in range(hw,hw_end-1):
        if rom[pc]==0xe0 and rom[pc+1] in (0x14,0x19,0x1e,0x23):
            p.hook_register(0,pc,attack,(0x14,0x19,0x1e,0x23).index(rom[pc+1]))
    for name in ('experimental_mode','monomode','polymode','w2enabled','seqmuted','seqsolo','syncmode','syncslave','waveengine','drumnoiseowned'):
        put(name,0)
    put('power',1);put('seqplaying',1);put('seqrecordtrack',255);put('mx',0xd3);put('mx',0,1)
    for c in range(7):put('mx',127,12+c);put('mx',3,19+c);write_word(p,S['_seqlength']+c*2,16)
    write_word(p,S['_drummutemask'],0);write_word(p,S['_drumsolomask'],0)
    put('custom',0)
    tracks=[[] for _ in range(7)]
    for c in range(4):tracks[c]=[[s,49+c*7+s%3,100,1] for s in range(16)]
    write_tracks(p,S,tracks)
    for c in range(4):
        for i in range(26):put('param',0,c*26+i)
        put('param',12,c*26+1);put('param',3,c*26+21);put('seqgate',100,c)
        put('seqposition',0,c);put('keycount',0,c);put('seqowned',0,c)
    put('param',1,2*26+15)
    for bpm in (120,300):
        write_word(p,S['_seqbpm'],bpm);write_word(p,S['_seqclock'],0)
        write_word(p,S['_seqthreshold'],15360);put('seqposition',0,6)
        for c in range(4):put('seqposition',0,c)
        call('seq_native_reset')
        preparation=[call('seq_native_prepare') for _ in range(8)]
        before=word('seqnativehits')
        for c in range(4):put('seqposition',1,c)
        put('seqposition',1,6)
        apu_cycles.clear();commit=call('seq_native_fire')
        assert [c for c,_ in apu_cycles]==[0,1,2,3],apu_cycles
        assert apu_cycles[-1][1]-apu_cycles[0][1]<=400,apu_cycles
        assert word('seqnativehits')==before+1,('Prepared step not consumed',bpm)
        for c in range(4):
            assert v('seqowned',c)==50+c*7,(bpm,c,v('seqowned',c))
            assert v('keycount',c)==1 and v('held',c)==49+c*7
            at=S['_seqgateleft']+4*c
            assert int.from_bytes(bytes(p.memory[at:at+4]),'little')==15360//bpm
        # All shapes are zero: triangle data, packed two samples per byte.
        p.memory[0xff1a]=0
        expected=bytes(((i*2 if i<8 else 31-i*2)<<4)|((i*2+1) if i<8 else 30-i*2) for i in range(16))
        assert bytes(p.memory[0xff30:0xff40])==expected,('Wave RAM differs',bpm)
        warm=[call('seq_native_prepare') for _ in range(8)]
        for c in range(4):put('seqposition',2,c)
        put('seqposition',2,6)
        call('seq_native_fire')
        assert all(v('seqowned',c)==51+c*7 for c in range(4))
        # A control edit must invalidate a completed future packet rather
        # than leave the optimized configuration snapshot frozen.
        for _ in range(8):call('seq_native_prepare')
        put('param',3,1);call('seq_native_touch',banked=False)
        for c in range(4):put('seqposition',3,c)
        put('seqposition',3,6)
        call('seq_native_fire')
        assert p.memory[0xff12]>>4==2,('Stale volume after edit',bpm,p.memory[0xff12])
        put('param',12,1);call('seq_native_touch',banked=False)
        print(json.dumps(dict(bpm=bpm,prepare_cycles=sum(preparation),commit_cycles=commit,
                              prepare_ms=sum(preparation)/4194.304,commit_ms=commit/4194.304,
                              warm_prepare_ms=sum(warm)/4194.304)),flush=True)
    # A new PCM source takes CH3 from a held native wave without leaving a
    # phantom MIDI key that would force every later step onto the slow path.
    tracks[6]=[[1,4,100,4]];write_tracks(p,S,tracks)
    for c in (0,1,2,3,6):put('seqposition',1,c)
    put('waveengine',3);put('drumon',0);put('drumon',0,1)
    put('seqowned',64,2);put('keycount',1,2);put('keystack',63,16)
    call('seq_native_reset');call('seq_native_fire')
    assert v('seqnativepending')==2 and v('seqowned',2)==0 and v('keycount',2)==0
    assert v('drumon') or v('drumon',1)
    call('seq_native_pcm_tick',banked=False);assert v('seqnativepending')==1
    call('seq_native_pcm_tick',banked=False);assert v('seqnativepending')==0
    assert v('seqnativefallback')==0
    # Transport cancellation must make a delayed commit inert.
    put('seqnativepending',2);put('seqplaying',0)
    call('seq_native_pcm_tick',banked=False);assert v('seqnativepending')==0
    put('waveengine',0);put('drumon',0);put('drumon',0,1);put('mixrunning',0)
    for duration in (0,1,3,4):
        for gate in (80,100):
            tracks=[[[0,49+c*7,100,duration]] if c<4 else [] for c in range(7)]
            write_tracks(p,S,tracks)
            for c in range(7):put('seqposition',0,c)
            for c in range(4):put('seqgate',gate,c)
            call('seq_native_reset');call('seq_native_fire')
            expected=(15360//300)*(duration or 256)*gate//100
            for c in range(4):
                at=S['_seqgateleft']+4*c
                assert int.from_bytes(bytes(p.memory[at:at+4]),'little')==expected,(duration,gate,c)
    # Cold calculations must finish before the transport clock starts.
    put('seqplaying',0);call('seq_native_reset');call('seq_native_prime')
    hits=word('seqnativehits');put('seqplaying',1);call('seq_native_fire')
    assert word('seqnativehits')==hits+1
    # Build a different pad without applying its settings or disturbing the
    # live lookahead/held voices. The launch path must consume this packet.
    put('page',18);write_word(p,S['_sparse_slots']+2,123)
    p.memory[0xb5a0:0xb5f1]=[0]*81
    p.memory[0xb5a0+49:0xb5a0+53]=[100]*4
    p.memory[0xb5a0+56:0xb5a0+63]=[127]*7
    p.memory[0xb5a0+63:0xb5a0+70]=[3]*7
    write_word(p,0xb5a0+75,300)
    p.memory[0xb600:0xb600+450]=[0]*450
    for c in range(4):
        p.memory[0xb600+c*60:0xb600+c*60+26]=p.memory[S['_param']+c*26:S['_param']+c*26+26]
        p.memory[0xb600+c*60+1]=3
        p.memory[(0xb590+c*4) if c<2 else (0xb7d0+(c-2)*4):
                 ((0xb590+c*4) if c<2 else (0xb7d0+(c-2)*4))+4]=[0,65+c,100,1]
    for c in range(3):write_word(p,0xb600+257+c*2,7)
    segments=[(0xa000,512),(S['_param'],104),(S['_finepitch'],10),(S['_seqowned'],7),
              (S['_seqgateleft'],28),(S['_keycount'],4),(S['_drumon'],2)]
    before=[bytes(p.memory[a:a+n]) for a,n in segments]
    call('seq_native_launch_begin',1,extra=(0,0))
    for _ in range(8):call('seq_native_launch_service')
    assert p.memory[0xa600]==7,'Incoming packet did not complete'
    assert before==[bytes(p.memory[a:a+n]) for a,n in segments],'Preparation mutated live playback'
    # Simulate the existing validated metadata/tone installation.
    put('mx',1,1)
    for c in range(4):
        put('param',3,c*26+1);put('seqposition',0,c);put('seqgate',100,c)
    for c in range(3):write_word(p,S['_finepitch']+c*2,7)
    write_word(p,S['_seqbpm'],300)
    call('seq_native_launch_installed',1);call('seq_native_reset');call('seq_native_launch')
    hits=word('seqnativehits');apu_cycles.clear();call('seq_native_fire')
    assert word('seqnativehits')==hits+1,'Launch discarded its prepared packet'
    assert [v('seqowned',c) for c in range(4)]==[65,66,67,68]
    assert [c for c,_ in apu_cycles]==[0,1,2,3]
    for c in range(3):
        base=word('finebase') if c==0 else int.from_bytes(bytes(p.memory[S['_finebase']+c*2:S['_finebase']+c*2+2]),'little')
        low,high=((0xa407,0xa408),(0xa40b,0xa40c),(0xa410,0xa411))[c]
        assert (p.memory[low]|((p.memory[high]&7)<<8))==base+7,('Incoming fine pitch',c)
    # A changed pattern object invalidates an otherwise completed packet.
    call('seq_native_launch_begin',1,extra=(0,0))
    for _ in range(8):call('seq_native_launch_service')
    call('seq_native_launch_installed',1)
    write_word(p,S['_sparse_slots']+2,124)
    call('seq_native_reset');call('seq_native_launch')
    misses=word('seqnativemisses');call('seq_native_fire')
    assert word('seqnativemisses')==misses+1,'Stale launch identity accepted'
    # Incoming PCM uses its own kit; combined drum noise and kick share
    # their APUs without leaving held native wave/noise keys behind.
    p.memory[0xb600+435]=2
    p.memory[0xb600+425:0xb600+435]=[10,4,3,0,2,12,5,2,1,1]
    p.memory[0xb600+442:0xb600+450]=[15,48,2,1,1,2,24,1]
    for i,note in enumerate((1,11,12,13)):p.memory[0xb7e0+i*4:0xb7e0+i*4+4]=[0,note,100,1]
    call('seq_native_launch_begin',1,extra=(4,0))
    for _ in range(12):call('seq_native_launch_service')
    assert p.memory[0xa600]==7
    put('drumkit',2)
    p.memory[S['_noisepatch']:S['_noisepatch']+10]=p.memory[0xb600+425:0xb600+435]
    p.memory[S['_pulsekickpatch']:S['_pulsekickpatch']+8]=p.memory[0xb600+442:0xb600+450]
    call('seq_native_launch_installed',1);call('seq_native_reset');call('seq_native_launch')
    hits=word('seqnativehits');call('seq_native_fire')
    assert word('seqnativehits')==hits+1
    assert v('seqnativepending')==2 and v('drumnoiseowned')==1
    assert v('seqowned',2)==v('seqowned',3)==v('keycount',2)==v('keycount',3)==0
    assert v('drumbankvoice')==33 or v('drumbankvoice',1)==33
    call('seq_native_pcm_tick',banked=False);call('seq_native_pcm_tick',banked=False)
    assert v('seqnativepending')==0
    # Native notes between sample hits use the same block pipeline; a
    # sample step must not insert an extra per-voice phase shift.
    write_tracks(p,S,[[[0,60+c,100,1]] if c<4 else [] for c in range(7)])
    for c in range(2):
        at=S['_noiseleft']+c*4;p.memory[at:at+4]=[0]*4
    p.memory[S['_pulsekickleft']:S['_pulsekickleft']+4]=[0]*4
    put('drumnoiseowned',0);apu_cycles.clear()
    call('seq_native_reset');call('seq_native_fire')
    assert v('seqnativepending')==2 and not apu_cycles
    call('seq_native_pcm_tick',banked=False);assert not apu_cycles
    call('seq_native_pcm_tick',banked=False)
    assert [c for c,_ in apu_cycles]==[0,1,3],apu_cycles
    # Unsupported drum batches never leave an installable partial packet.
    call('seq_native_launch_begin',1,extra=(16,1))
    call('seq_native_launch_service');assert p.memory[0xa600]==255
    Path('build/native-step-cpu.json').write_text(json.dumps(budgets,indent=2)+'\n')
    print('PASS: four native voice states/gates/waveform, PCM ownership and pending-stop cancellation',flush=True)
finally:
    Path('build/native-step-cpu.json').write_text(json.dumps(budgets,indent=2)+'\n')
    p.stop(save=False)

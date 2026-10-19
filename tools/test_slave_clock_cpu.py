"""Actual DMG CPU: slave launches preserve clock/grid in every sync mode."""
from pathlib import Path
bootstrap=Path("tools/test_native_step_cpu.py").read_text().split("    for bpm in (120,300):")[0]
tests = r'''
    reports=[]
    for mode in range(1,6):
        for bpm in (120,300):
            put('syncmode',mode);put('syncslave',1);put('seqplaying',1);put('seqservicing',0)
            write_word(p,S['_seqbpm'],bpm);write_word(p,S['_seqglobalbpm'],bpm)
            write_word(p,S['_seqclock'],0);write_word(p,S['_seqticks'],0);write_word(p,S['_seqthreshold'],15360)
            write_word(p,S['_sys_time'],0);put('seqswing',50);put('seqswingphase',0);put('mx',0,10);put('mx',255,2)
            call('sync_transport',1)
            unit=30720 if mode==4 else 15360 if mode==5 else 2560
            pulses=16*15360*4//unit
            for n in range(1,pulses+1):
                call('sync_receive',(0x80|(n&63)) if mode==1 else 0)
                call('seq_frame')
                expected=(n*unit)//15360%16
                assert v('mx',10)==expected,(mode,bpm,n,v('mx',10),expected)
                # Repeated local launches must leave both integer clock phase
                # and the receiver's fractional conversion state untouched.
                if n%7==0:
                    before=(word('seqclock'),word('seqticks'),v('mx',10),v('seqswingphase'),v('syncpending'),bytes(p.memory[0xffe2:0xffe6]))
                    call('seq_pattern_handoff')
                    after=(word('seqclock'),word('seqticks'),v('mx',10),v('seqswingphase'),v('syncpending'),bytes(p.memory[0xffe2:0xffe6]))
                    assert before==after,(mode,bpm,n,before,after)
                    assert v('seqplaying')==1
            if mode>1:
                # Raw tempo estimates fluctuate with frame timestamps. Deliver
                # clock bursts before servicing notes, so old converted ticks
                # are still pending when a new estimate is measured.
                put('mx',255,2);put('mx',0,10);put('seqswingphase',0)
                write_word(p,S['_seqclock'],0);write_word(p,S['_seqticks'],0)
                write_word(p,S['_seqthreshold'],15360);write_word(p,S['_sys_time'],0)
                write_word(p,S['_seqbpm'],bpm);write_word(p,S['_seqglobalbpm'],bpm)
                call('sync_transport',1)
                ppqn=2 if mode==4 else 4 if mode==5 else 24
                for n in range(1,pulses+1):
                    frame=int(n*3584/(bpm*ppqn))+(n//ppqn)%2
                    write_word(p,S['_sys_time'],frame)
                    call('sync_receive',0)
                    if n%7==0 or n==pulses:
                        call('seq_frame')
                        actual=v('mx',10)*15360+word('seqclock')
                        expected=n*unit%(16*15360)
                        error=(actual-expected+8*15360)%(16*15360)-8*15360
                        assert abs(error)<=600,('Tempo estimate lost clock phase',mode,bpm,n,error)
            # Specifically exercise pending clock time and an odd swing half.
            write_word(p,S['_seqticks'],11);put('seqswingphase',1);put('mx',5,10)
            before=(word('seqclock'),word('seqticks'),v('mx',10),v('seqswingphase'))
            call('seq_pattern_handoff')
            assert before==(word('seqclock'),word('seqticks'),v('mx',10),v('seqswingphase'))
            # Engine changes used to stop/restart transport as well. Exercise
            # both directions with clock time already pending at the handoff.
            put('experimental_mode',1)
            for synth in (1,0):
                put('seqmode',synth);write_word(p,S['_seqticks'],11)
                before=(word('seqclock'),v('mx',10),v('seqswingphase'))
                call('seq_pattern_handoff')
                assert v('seqplaying')==1 and word('seqticks')==11,(mode,bpm,synth,word('seqticks'))
                assert before==(word('seqclock'),v('mx',10),v('seqswingphase'))
                assert bool(v('monomode'))==bool(synth)
            put('experimental_mode',0)
            reports.append(dict(mode=mode,bpm=bpm,pulses=pulses))
    print('PASS slave clock/handoff phase invariants:',json.dumps(reports))
finally:
    p.stop(save=False)
'''
exec(bootstrap + tests)

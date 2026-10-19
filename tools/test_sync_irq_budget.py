"""Reuse the two-PCM/P1/P2 hardware-write fixture with the master clock enabled."""
from pathlib import Path
import argparse,json

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom',type=Path,default=Path('build/GAYBOY.gb'))
parser.add_argument('--output',type=Path,default=Path('build/sync-irq-budget.json'))
args=parser.parse_args()

source=Path('tools/test_pcm_timing.py').read_text()
source=source.replace('exec(source,env)',"exec(source,env);env['choose'](27)\n while env['v']('syncmode')!=1:env['press']('right')\n if '_syncrole' in env['S']:\n  env['press']('down');env['press']('right')\n env['choose'](0)")
source=source.replace("put('seqbpm',1,300>>8)","put('seqbpm',1,300>>8);write_word(p,S['_seqglobalbpm'],300)")
# Fast subdivisions do not upload PCM; count delivery eligibility only on the
# subdivision which actually enters drum_timer. Still measure every full IRQ.
source=source.replace("if v('power') and v('mixrunning'):","if v('power') and v('mixrunning') and (not v('syncarmed') or v('syncsub')+1==v('syncdivider')):")
source=source.replace('choose(8);p.tick(90)',"print('Preparing fixture',flush=True);choose(8);p.tick(90)")
source=source.replace('measurement[0]=p._cycles()',"measurement[0]=p._cycles();print('Measuring audio',flush=True)")
env={'__name__':'sync_irq_budget'}
exec(compile(source,'tools/test_pcm_timing.py','exec'),env)
env['ROM']=args.rom
results=[]
for scroll,view,control in ((False,'sequencer',None),(True,'sequencer',None),(False,'mixer','volume')):
    print('Running',view,control,scroll,flush=True)
    result=env['run'](scroll,60,view,control)
    print('Measured',result['full_irq_count'],flush=True)
    # PCM clocks run at the original block period; the entire IRQ must
    # finish before the next block deadline.
    result['meets_subdivision_budget']=result['full_irq_cycles_max']<11712
    result['expected_fast_irqs']=result['elapsed_timer_periods']
    # The original ROM also misses the historical 58 ms cold-onset target.
    # Record it unchanged; separately bound added clock overhead to 5 ms
    # against the measured pre-refactor 61.36 ms mixer result.
    result['meets_startup_regression_budget']=result['first_p1_to_p2_step1_ms']<=66.36
    results.append(result)
args.output.write_text(json.dumps(results,indent=2)+'\n')
for r in results:
    print(json.dumps({k:r[k] for k in ('ui','full_irq_cpu_percent','full_irq_cycles_max','audio_underruns','meets_audio_delivery','meets_note_rate','meets_startup_regression_budget','meets_subdivision_budget')}))
assert all(all(r[k] for k in ('meets_audio_delivery','meets_note_rate','meets_startup_regression_budget','meets_subdivision_budget')) for r in results)

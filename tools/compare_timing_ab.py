"""Bounded, matched whole-engine traces of the preserved IRQ-on/off ROMs."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

OUT = Path('build/timing-ab')
OUT.mkdir(exist_ok=True)
CASES = [('demo', 120), ('demo', 300), ('native-four', 120),
         ('native-four', 300), ('pcm', 120), ('pcm', 300)]

def stats(values):
    if not values:return None
    values=sorted(values)
    return dict(count=len(values),min_ms=round(values[0],3),
                median_ms=round(statistics.median(values),3),
                p95_ms=round(values[int((len(values)-1)*.95)],3),max_ms=round(values[-1],3))

def summarize(report):
    events=report['events'];phases={}
    for phase in dict.fromkeys(e['phase'] for e in events):
        es=[e for e in events if e['phase']==phase]
        groups={};due={};fires={};counts={}
        for e in es:
            epoch=e['epoch']
            if e['event'] in ('mixer_boundary','seq_pattern_start'):
                # Boundary publishes the unconsumed snapshot tail globally.
                # Estimate its deadline from accumulated musical time; local
                # timer quantization limits accuracy to one timer period.
                due[epoch]=e['cycle']-(e['ticks']+e['clock']/e['bpm'])*4096
            if e['event']=='seq_fire':fires.setdefault(epoch,{})[e['channel']]=e['cycle']
            if e['event']=='APU-trigger' and e.get('source')!='kick_stop':
                key=e.get('source','unknown')+':'+str(e['channel'])
                counts[key]=counts.get(key,0)+1
                groups.setdefault(epoch,[]).append(e['cycle'])
            if e['event']=='PCM-source-first-upload':
                counts['PCM-source-first-upload']=counts.get('PCM-source-first-upload',0)+1
                for voice in e['starting_voices']:
                    groups.setdefault(voice['epoch'],[]).append(e['cycle'])
        spreads=[(max(g)-min(g))/4194.304 for g in groups.values() if len(g)>1]
        late=[(max(g)-due[k])/4194.304 for k,g in groups.items() if k in due]
        bs=[e['cycle'] for e in es if e['event']=='mixer_boundary']
        segments={}
        for a,b,label in ((6,0,'drum-dispatch'),(0,1,'P1-dispatch'),
                          (1,2,'P2-dispatch'),(2,3,'wave-dispatch')):
            segments[label]=stats([(f[b]-f[a])/4194.304 for f in fires.values() if a in f and b in f])
        phases[phase]=dict(attacks=counts,same_step_trigger_spread=stats(spreads),
            last_attack_after_estimated_deadline=stats(late),
            boundary_intervals=stats([(b-a)/4194.304 for a,b in zip(bs,bs[1:])]),
            dispatch_segments=segments)
    return phases

def run(case):
    mode,fixture,bpm=case;name=f'{mode}-{fixture}-{bpm}'
    output=OUT/(name+'.json');rom=Path(f'build/timing-ab-irq-{mode}.gb')
    cmd=[sys.executable,'tools/profile_whole_step.py','--rom',str(rom),
         '--bpm',str(bpm),'--output',str(output)]
    if fixture!='demo':cmd+=['--fixture',fixture]
    result=dict(mode=mode,fixture=fixture,bpm=bpm,
                rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest())
    with (OUT/(name+'.log')).open('w') as stdout,(OUT/(name+'.err')).open('w') as stderr:
        try:
            process=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=25)
            result['exit_code']=process.returncode
        except subprocess.TimeoutExpired:
            result['status']='timeout';return result
    if output.exists():
        report=json.loads(output.read_text())
        result['status']='incomplete' if report.get('incomplete') else 'complete'
        result['failed_phase']=report.get('phase')
        result['phases']=summarize(report)
        result['irq_attacks']=sum(e.get('source')=='seq_irq_tick' for e in report['events'])
        if mode=='off':assert result['irq_attacks']==0,result
    else:result['status']='no report'
    assert 'Exception ignored in' not in (OUT/(name+'.err')).read_text(),f'Invalid hook trace: {name}'
    return result

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(run,(mode,fixture,bpm)) for fixture,bpm in CASES for mode in ('on','off')]
    for future in concurrent.futures.as_completed(futures):
        result=future.result();results.append(result)
        print(json.dumps({k:v for k,v in result.items() if k!='phases'}),flush=True)
        (OUT/'summary.json').write_text(json.dumps(dict(
            limitations='Hardware trigger/delivery timing in DMG emulation, not detected audible onset. Deadline estimates have timer-period uncertainty. Native-four/PCM are additional aligned fixtures; demo is unedited.',
            results=results),indent=2)+'\n')
print('Matched A/B traces saved to',OUT/'summary.json',flush=True)

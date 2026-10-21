"""Record paired main timing measurements; timing/coverage failures stay explicit."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--before', default='build/mod-port-baseline/GAYBOY.gb')
ap.add_argument('--after', default='build/GAYBOY.gb')
args = ap.parse_args()
cases = [('native', []),
         ('arp', ['--arp', '--bpm', '240', '--arp-div', '3']),
         ('lfo', ['--arp', '--synclfo', '--bpm', '240', '--arp-div', '3']),
         ('pcm', ['--arp', '--synclfo', '--pcm', '--bpm', '150', '--arp-div', '2']),
         ('drawing', ['--bpm', '60'])]


def run(job):
    version, rom, name, flags = job
    output = Path('build/mod-' + version + '-' + name + '.json')
    with output.with_suffix('.log').open('w') as log:
        try:
            result = subprocess.run(
                [sys.executable, 'tools/test_mod_port_timing.py', '--rom', rom,
                 '--measure', '--out', str(output), *flags],
                stdout=log, stderr=subprocess.STDOUT, timeout=20)
        except subprocess.TimeoutExpired:
            return {'version': version, 'case': name, 'timeout': True}
    row = {'version': version, 'case': name, 'exit_code': result.returncode,
           'rom_sha256': hashlib.sha256(Path(rom).read_bytes()).hexdigest(),
           'details': str(output)}
    if result.returncode:
        return row
    data = json.loads(output.read_text())
    row.update(worst_interval_error_ms=max(
        x['max_error_ms'] for phase in ('idle', 'navigation', 'stall')
        for x in data[phase].values()),
        foreground_load_exercised=data['foreground_load_exercised'],
        stall_calls=data['stall_calls'], pcm_underruns=data['pcm_underruns'],
        lowest_observed_sp=data['lowest_observed_sp'])
    row['timing_target_met'] = row['worst_interval_error_ms'] < 4
    return row


jobs = [(version, rom, name, flags)
        for version, rom in (('before', args.before), ('after', args.after))
        for name, flags in cases]
with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(run, jobs))
Path('build/mod-port-comparison.json').write_text(json.dumps(results, indent=2) + '\n')
for row in results:
    print(json.dumps(row))
if any(row.get('exit_code', 1) for row in results):
    raise SystemExit(1)

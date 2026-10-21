"""Separate idle savings from active sync, free-rate and envelope overhead."""
import json
from pathlib import Path
from mod_port_harness import Engine

results = {}
for version, rom in (('before', 'build/mod-port-baseline/GAYBOY.gb'),
                     ('after', 'build/GAYBOY.gb')):
    E = Engine(rom)
    try:
        for case in ('idle_sync', 'active_sync', 'active_free', 'active_envelope'):
            E.reset()
            E.word('seqbpm', 240)
            E.put('globalmod', case != 'active_free', 7)
            E.put('globalmod', 8, 5)
            E.put('globalmod', 8, 6)
            for c in range(4):
                E.put('active', 1, c)
                E.put('keycount', 1, c)
                E.put('evalpatch', 0 if case == 'idle_sync' else 8, c*16+9)
                E.put('evalpatch', case != 'active_envelope', c*16+8)
            costs = []
            for i in range(33):
                E.word('sys_time', i+1)
                cost = E.call('service_frame')[1]
                if i:
                    costs.append(cost)
            results.setdefault(case, {})[version] = sum(costs)/len(costs)
    finally:
        E.p.stop(save=False)
assert results['idle_sync']['after'] < results['idle_sync']['before']
assert results['active_sync']['after'] < results['active_sync']['before']
Path('build/mod-port-cost.json').write_text(json.dumps(results, indent=2) + '\n')
print('PASS:', results)

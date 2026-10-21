"""Compare preserved baseline measurements with the current stripped build."""
import hashlib,json
from pathlib import Path
from check_memory import audit
b=Path('build/stripped-baseline');out=Path('briefs/stripped-cpu-comparison.json')
def read(p):return json.loads(p.read_text())
base=read(b/'validation.json');now=audit(Path('build/GAYBOY.gb'))
bcpu=read(b/'cpu.json');ncpu=read(Path('build/stripped-cpu.json'))
report={'baseline_tag':'stripped-baseline-20261020','baseline_commit':'e7a66e6','baseline_rom_sha256':base['rom_sha256'],'current_rom_sha256':hashlib.sha256(Path('build/GAYBOY.gb').read_bytes()).hexdigest(),'measurements':{}}
def pair(name,old,new):report['measurements'][name]={'baseline':old,'optimized':new}
for key in ('event_lookup_mean_ms','unchanged_wave_mean_ms','first_wave_upload_ms','index_prepare_ms'):pair(key,bcpu[key],ncpu[key])
for key,value in read(b/'navigation.json').items():pair(key,value,read(Path('build/stripped-navigation.json'))[key])
for key,value in base['edit-latency'].items():pair(key,value,read(Path('build/stripped-edit-latency.json'))[key])
for mode in ('mono','arp'):
 for dense in (False,True):
  key='stripped-timing-'+mode+('-dense' if dense else '')+'.json'
  old=read(b/key) if dense else base['timing-'+mode]
  new=read(Path('build')/key)
  pair(('dense_' if dense else 'mixed_pcm_')+mode+'_worst_error_ms',max(old['idle_max_error_ms'],old['navigation_max_error_ms']),max(new['idle_max_error_ms'],new['navigation_max_error_ms']))
  pair(('dense_' if dense else 'mixed_pcm_')+mode+'_pcm_underruns',old['pcm_underruns'],new['pcm_underruns'])
pair('wram_ordinary_bytes',base['wram_ordinary_bytes'],now['wram_ordinary_bytes'])
pair('event_index_and_wave_shadow_cartridge_ram_bytes',0,now['event_address_index_bytes']+now['wave_upload_shadow_bytes'])
report['notes']=['Microbenchmarks measure individual paths, not overall CPU utilization.','A full 256-note address index is built once at transport start or after note edits/pattern switches; stopped editing uses direct reads.','Projects below32 events skip index construction.','Dense fixture includes256 events with pulse, wave and noise drums; mixed fixture also includes PCM samples and pulse kick.','Wave upload is skipped only while content matches; custom edits and PCM takeover force a refresh.','No active PCM attack busy-wait existed in the baseline. The inactive legacy launch wait was removed.','Required envelope/trigger/length writes remain to preserve hardware behavior.','All measurements use DMG emulation; physical hardware testing remains outstanding.']
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

"""Package the validated stripped ROM with a fresh project battery."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile
from check_memory import audit
root=Path(__file__).resolve().parents[1]
build=root/'build';out=build/'stripped';out.mkdir(exist_ok=True)
for ext in ('gb','noi','map'):
 shutil.copy2(build/('GAYBOY.'+ext),out/('stripped.'+ext))
(out/'stripped.srm').write_bytes(bytes(32768))
report=audit(build/'GAYBOY.gb')
report['wram_saved_vs_gatefix_bytes']=report['wram_unused_total_bytes']-386
report['wram_saved_percent_of_8k']=round(report['wram_saved_vs_gatefix_bytes']/8192*100,1)
report['cartridge_ram_saved_vs_six_patterns_bytes']=2048
for kind in ('resident-timing','edit-latency','timing-mono','timing-arp'):
 p=build/('stripped-'+kind+'.json')
 if p.exists():report[kind]=json.loads(p.read_text())
def used(p):
 return sum(int(n,16) for n in re.findall(r'^_CODE(?:_\d+)?\s+[0-9A-F]+\s+([0-9A-F]+)\s+=',p.read_text(),re.M))
report['linked_code_bytes']=used(build/'GAYBOY.map')
report['gatefix_linked_code_bytes']=used(build/'gatefix.map')
report['linked_code_saved_bytes']=report['gatefix_linked_code_bytes']-report['linked_code_bytes']
report['rom_sha256']=hashlib.sha256((out/'stripped.gb').read_bytes()).hexdigest()
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'README.txt').write_text('STRIPPED experimental build\nBranch: stripped\n\nFive resident patterns; 256 notes per pattern shared across tracks.\nSix mixer strips and all five pattern pads visible. M/S/V legends; WV/N/DR names.\nOne shared ADSR and LFO on MOD. Only fine pitch has modulation amount/source.\nLevel selects hardware or ADSR; defaults to hardware. Mono/arp sequencers.\nMonosynth, poly, Noise Lab and experimental DSP effects removed.\nNSH and NSN overlap by averaging their settings.\n\nUse stripped.gb with the supplied blank stripped.srm for a fresh project.\nOld saves are unsupported. Do not overwrite a save you want to keep.\n\nSee validation.json for measured memory and emulator results.\nPhysical Game Boy performance still needs user evaluation.\n')
with zipfile.ZipFile(build/'stripped.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()):z.write(p,'stripped/'+p.name)
print(json.dumps(report,indent=2))

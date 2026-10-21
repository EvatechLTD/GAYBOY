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
for kind in ('resident-timing','edit-latency','timing-mono','timing-arp','timing-mono-dense','timing-arp-dense','cpu','navigation','fast-edits','resize','groups','timing-mono-editing','timing-mono-groups','timing-mono-velocity','locked-velocity','velocity-dense','group-comparison'):
 p=build/('stripped-'+kind+'.json')
 if p.exists():report[kind]=json.loads(p.read_text())
def used(p):
 return sum(int(n,16) for n in re.findall(r'^_CODE(?:_\d+)?\s+[0-9A-F]+\s+([0-9A-F]+)\s+=',p.read_text(),re.M))
report['linked_code_bytes']=used(build/'GAYBOY.map')
report['gatefix_linked_code_bytes']=used(build/'gatefix.map')
report['linked_code_saved_bytes']=report['gatefix_linked_code_bytes']-report['linked_code_bytes']
comparison=root/'briefs/stripped-cpu-comparison.json'
if comparison.exists():
 report['baseline_comparison']=json.loads(comparison.read_text())
 shutil.copy2(comparison,out/'baseline-comparison.json')
report['validation_warnings']=[{'test':key,'navigation_max_error_ms':value['navigation_max_error_ms'],'limit_ms':25} for key,value in report.items() if key.startswith('timing-') and isinstance(value,dict) and value.get('navigation_max_error_ms',0)>=25]
report['rom_sha256']=hashlib.sha256((out/'stripped.gb').read_bytes()).hexdigest()
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'README.txt').write_text('STRIPPED experimental build\nBranch: stripped\n\nFive resident patterns; 256 notes per pattern shared across tracks.\nSix mixer strips and all five pattern pads visible. M/S/V legends; WV/N/DR names.\nOne shared ADSR and LFO on MOD. Fine and coarse pitch have modulation amount/source.\nLevel selects hardware or ADSR; defaults to hardware. Mono/arp sequencers.\nMonosynth, poly, Noise Lab and experimental DSP effects removed.\nNSH and NSN overlap by averaging their settings.\n\nUse stripped.gb with the supplied blank stripped.srm for a fresh project.\nOld saves are unsupported. Do not overwrite a save you want to keep.\n\nSee validation.json for measured memory and emulator results.\nPhysical Game Boy performance still needs user evaluation.\n\nFast drum plot/delete, resizing and note dragging; A+B cursor painting.\nSticky Start defaults OFF: hold Start, navigate, release to select.\nSelect cancels menus; tap Select in sequencer opens Seq Settings.\nKits publishing fixed. Ghost notes retained. Complex overlaps may still redraw.\nDuplicate is available in Edit and Selection menus.\nSequencer header shows first visible step / pattern length.\nPulse levels default 8; waveform displays OFF; LFO tempo 1/1.\nSelect+Left/Right changes instrument; plain Left/Right at column edges changes its page.\nSettings contains Mixer Settings, Quick Menu, Sync and Seq Pages.\nDuplicate shortcuts are repaired; assigning an existing item moves it to the new slot.\nSettings remains a fixed menu entry. Seq Pages controls visibility only.\nDrum synth voices come first in the drum grid and after DR in the mixer.\nTaller mixer faders update after pattern audio has settled.\nGroup edits retain ghost notes and update changed columns and note tails.\nOne blank row separates drum synth voices from the ten sample rows.\nSample grid top edge restored. A+B waits for horizontal movement: Right paints, Left erases, locked until release. Both starting and entered cells are edited; B taps delete notes under the cursor.\nMixer BPM formatting supports the full 300 BPM range.\nSelect+Start restarts stopped playback or panics/stops active playback on every screen.\nDrum velocity: Left onto a channel name, A/B selects its sliders; Up returns to the name.\nThe selected velocity channel stays pinned while navigating notes. All zoom sizes supported.\nHold A/B with Up/Down for single velocity steps, Left/Right for ten. Only changed bar pixels redraw.\nPainted hits keep tiny separators, including overlapping sample notes.\n')
with zipfile.ZipFile(build/'stripped.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()):z.write(p,'stripped/'+p.name)
print(json.dumps(report,indent=2))

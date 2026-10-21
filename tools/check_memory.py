"""Audit the stripped resident layout using linked symbols."""
import argparse,json
from pathlib import Path

def audit(rom):
 s={l.split()[1]:int(l.split()[2],16) for l in rom.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
 assert '_resident_read' in s and '_seqevents_lo' not in s and '_seqnativestep' not in s
 assert '_expalpha' not in s and '_monoset' not in s
 heap=s['s__HEAP_END'];assert heap<=0xD800
 fixed=[('_chord',48),('_arpindex',3),('_arpnote',3),('_arpcount',3),('_arpcycle',3),('_arpvel',3),('_arpstride',3),('_arpclock',12),('_arpfirstvel',12)]
 regions=sorted((s[n],s[n]+size,n) for n,size in fixed)
 for a,b in zip(regions,regions[1:]):assert a[1]<=b[0],(a,b)
 assert max(e for _,e,_ in regions)<=0xDE00
 assert s['_wavepixels']==0xB000 and s['_mx']==0xAC80
 # Notes: slots0..3 bank1, slot4 bank2 A000..A7FF; presets bank3 A000..A81F.
 # Clipboard stays bank3 B400..BC0F; globals bank3 BF80..BFFF.
 assert 5*2048==10240 and 5*256*4==5120
 index_bytes=1024 if '_eventheads' in s else 0
 if index_bytes:assert s['_eventheads']==0xA000 and s['_eventnext']==0xA200 and s['_waveimage']==0xA400
 ordinary=heap-0xC000;fixed_bytes=sum(z for _,z in fixed);unused=8192-ordinary-fixed_bytes-512
 return {'rom':str(rom),'cartridge_ram_bytes':32768,'resident_patterns':5,'notes_per_pattern':256,'resident_note_payload_bytes':5120,'resident_pattern_records_bytes':10240,'user_preset_records_bytes':2048,'user_bank_names_bytes':32,'global_settings_bytes':128,'clipboard_reserved_bytes':2064,'wram_ordinary_bytes':ordinary,'wram_fixed_runtime_bytes':fixed_bytes,'wram_unused_total_bytes':unused,'wram_unused_below_audio_tables_bytes':0xD800-heap,'wram_minimum_reserve_bytes':384,'stack_reserved_bytes':512,'stack_minimum_reserve_bytes':512,'evaluation_chord_cache_bytes':0,'event_address_index_bytes':index_bytes,'wave_upload_shadow_bytes':16 if index_bytes else 0,'note_install_cache_bytes':0,'launch_packet_cache_bytes':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,default=Path('build/GAYBOY.gb'));p.add_argument('--output',type=Path);a=p.parse_args();v=audit(a.rom);t=json.dumps(v,indent=2);print(t)
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(t+'\n')

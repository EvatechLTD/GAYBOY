"""Publish one validated build to both web packages, preserving beat cartridges."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
rom=(ROOT/'build/GAYBOY.gb').read_bytes()
symbols={line.split()[1][1:]:int(line.split()[2],16)
         for line in (ROOT/'build/GAYBOY.noi').read_text().splitlines() if line.startswith('DEF _')}
digest=hashlib.sha256(rom).hexdigest()
assert len(rom)==1048576 and rom[0x147]==0x1B and rom[0x149]==3
assert (sum(rom)-rom[0x14e]-rom[0x14f])&65535==int.from_bytes(rom[0x14e:0x150],'big')
names=('page navopen navchoice seqplaying seqtrack seqcursor seqpitch seqhead seqfocus '
       'seqedit seqapending seqposition seqevents_lo seqevents_hi seqeventcounts '
       'seqeventoffsets seqmuted seqsolo seqlength lastpad').split()
metadata={'rom':'emulator/roms/GAYBOY.gb','sha256':digest,
          'symbols':{name:symbols[name] for name in names},'mixer':symbols['mx']}
snapshot=ROOT/'build/web-rom-releases'/digest
snapshot.mkdir(parents=True,exist_ok=True)
for name in ['GAYBOY.gb','GAYBOY.noi','GAYBOY.map']:
    shutil.copy2(ROOT/'build'/name,snapshot/name)
for folder in [ROOT/'website',ROOT/'network/apps/gayboy']:
    (folder/'emulator/roms').mkdir(parents=True,exist_ok=True)
    registry_path=folder/'emulator/rom-versions.json'
    registry=json.loads(registry_path.read_text()) if registry_path.exists() else {'versions':{}}
    old=json.loads((folder/'emulator/tutorial-rom.json').read_text())
    old_rom=(folder/old['rom']).read_bytes()
    assert hashlib.sha256(old_rom).hexdigest()==old['sha256']
    if old['sha256']!=digest:
        archived='emulator/roms/GAYBOY-'+old['sha256'][:12]+'.gb'
        (folder/archived).write_bytes(old_rom)
        registry['versions'][old['sha256']]={**old,'rom':archived}
    # Keep every shared-beat cartridge outside the public download namespace.
    for version in registry['versions'].values():
        previous=folder/version['rom']
        target='emulator/roms/'+previous.name
        data=previous.read_bytes()
        assert hashlib.sha256(data).hexdigest()==version['sha256']
        (folder/target).write_bytes(data)
        version['rom']=target
    (folder/'emulator/roms/GAYBOY.gb').write_bytes(rom)
    registry['current']=digest
    registry['versions'][digest]=metadata
    registry_path.write_text(json.dumps(registry,indent=2)+'\n')
    for name in ['GAYBOY.gb','GAYBOY-0.3.gb','GAYBOY-tutorial.gb']:
        (folder/'downloads'/name).write_bytes(rom)
    (folder/'emulator/tutorial-rom.json').write_text(json.dumps(metadata,indent=2)+'\n')
    checksums=''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n'
                      for f in sorted((folder/'downloads').glob('*.gb')))
    (folder/'downloads/SHA256SUMS.txt').write_text(checksums)
assert hashlib.sha256((ROOT/'build/GAYBOY.gb').read_bytes()).hexdigest()==digest,'Build changed during packaging; package again.'
(snapshot/'release.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('Both web ROM packages pinned to:',digest)

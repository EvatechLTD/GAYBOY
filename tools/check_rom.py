from pathlib import Path
from check_memory import audit
s={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
assert s['s__HRAM']+s['l__HRAM']<=0xFF98,'Library HRAM overlaps serial sync state'
assert 0xC000<=s['_twinktx'] and s['_twinktx']+32<=0xD800,'TWINK queue must not alias native HRAM flags'
assert s['_synctx']==0xFF98 and s['_syncbusy']==0xFFDD,'Unexpected sync HRAM layout'
assert s['_sync_clock_isr']<0x4000,'Clock IRQ must stay in fixed ROM'
assert s['_syncirqphase']==0xFFB8 and s['_syncdue']==0xFFC4,'Clock state overlaps reserved HRAM'
assert s['_pad_names']==0xAE40 and s['_mixer_image']>=0xAE68 and s['_mixer_image']+28<=0xAE90,'Five-character pad cache overlaps mixer renderer state'
assert s['s__GSFINAL']+s['l__GSFINAL']<=0x4000,'Fixed ROM bank overflow'
for n,v in s.items():
 if n.startswith('l__CODE_'):assert v<=0x4000,(n,v)
assert s['s__HEAP_END']<=0xD800,'Shared state overlaps audio lookup tables'
# DSP tables must leave a real stack window above the final fixed table.
regions=[(s[n],s[n]+size,n) for n,size in [('_softlut',64),('_explut',32),('_expwet',256),('_expalpha',256),('_expreslut',256),('_expinterp',256),('_expfeedback',256)] if n in s]
if '_evalpatch' in s:
 for name,size in [('_chord',48 if '_globalmod' in s else 80),('_arpindex',5),('_arpnote',5),('_arpcount',5),('_arpcycle',5),('_arpvel',5),('_arpstride',5),('_arpclock',20),('_arpfirstvel',20),('_releaseleft',8)]:
  if name not in s:continue
  assert 0xD860 <= s[name] and s[name]+size <= 0xD900, ('Evaluation runtime outside reserved DSP gap',name)
  regions.append((s[name],s[name]+size,name))
regions.sort()
for a,b in zip(regions,regions[1:]):assert a[1]<=b[0],('DSP lookup overlap',a,b)
assert max(end for _,end,_ in regions)<=0xDE00,'DSP tables leave less than512bytes for stack'
r=Path('build/GAYBOY.gb').read_bytes()
assert len(r)==1024*1024 and r[0x147]==0x1B and r[0x149]==3,'Expected MBC5 + 32 KiB RAM'
assert (sum(r)-r[0x14e]-r[0x14f])&65535==int.from_bytes(r[0x14e:0x150],'big')
print('ROM layout verified: 1 MiB MBC5 + battery, 32 KiB cartridge RAM, bounded ROM banks and work RAM')
memory = audit(Path('build/GAYBOY.gb'))
print('Engine reserves verified: %d bytes WRAM, %d bytes stack; bank zero excluded from song storage' %
      (memory['wram_unused_below_audio_tables_bytes'], memory['stack_reserved_bytes']))

for bank in [32,33,34,35,36,39,62]:
 assert (s['_drumdata'+str(bank)]&65535)==(s['_drumdata32']&65535), 'PCM fast fetch requires bank-aligned kit data'

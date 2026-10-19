"""Build a local Node/SameBoy cable test core, without changing website assets."""
from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[1]
source=root/'build/web-audio/SameBoy'
generated=root/'build/web-audio/generated'
generated.mkdir(parents=True,exist_ok=True)
boot=(root/'tools/sameboy/dmg_boot.bin').read_bytes()
(generated/'browser_bootrom.h').write_text('static const unsigned char browser_bootrom[] = {'+','.join(map(str,boot))+'};\n')
excluded={'debugger.c','sm83_disassembler.c','symbol_hash.c','rewind.c','cheats.c','cheat_search.c'}
sources=[str(p) for p in sorted((source/'Core').glob('*.c')) if p.name not in excluded]
subprocess.run([sys.executable,str(root/'build/web-audio/emsdk/upstream/emscripten/emcc.py'),
 *sources,str(root/'tools/sync_link_core.c'),'-o',str(root/'build/sync_link_core.cjs'),
 '-I'+str(source),'-I'+str(generated),'-std=gnu11','-O3','-flto',
 '-D_GNU_SOURCE','-DGB_INTERNAL','-DGB_DISABLE_DEBUGGER','-DGB_DISABLE_REWIND',
 '-DGB_DISABLE_CHEATS','-DGB_DISABLE_CHEAT_SEARCH','-DGB_DISABLE_TIMEKEEPING',
 '-DGB_VERSION="1.0.4"','-DGB_COPYRIGHT_YEAR="2026"',
 '-sMODULARIZE=1','-sENVIRONMENT=node','-sALLOW_MEMORY_GROWTH=1',
 '-sEXPORTED_RUNTIME_METHODS=["HEAPU8"]','-sEXPORTED_FUNCTIONS=["_malloc","_free"]','--no-entry','-lm'],cwd=root,check=True)

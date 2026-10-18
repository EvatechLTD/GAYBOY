"""Build SameBoy with checkout-local Emscripten 4.0.10; no system installation.

Source: official SameBoy v1.0.4 in build/web-audio/SameBoy. Install/activate
Emscripten 4.0.10 under build/web-audio/emsdk before running this script.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'build/web-audio/SameBoy'
SDK=ROOT/'build/web-audio/emsdk'
GENERATED=ROOT/'build/web-audio/generated'
GENERATED.mkdir(parents=True,exist_ok=True)
boot=(ROOT/'tools/sameboy/dmg_boot.bin').read_bytes()
(GENERATED/'browser_bootrom.h').write_text('static const unsigned char browser_bootrom[] = {'+','.join(map(str,boot))+'};\n')
excluded={'debugger.c','sm83_disassembler.c','symbol_hash.c','rewind.c','cheats.c','cheat_search.c'}
sources=[str(p) for p in sorted((SOURCE/'Core').glob('*.c')) if p.name not in excluded]
command=[sys.executable,str(SDK/'upstream/emscripten/emcc.py'),*sources,str(ROOT/'tools/browser_sameboy.c'),
 '-o',str(ROOT/'website/emulator/sameboy.js'),'-I'+str(SOURCE),'-I'+str(GENERATED),
 '-std=gnu11','-O3','-flto','-D_GNU_SOURCE','-DGB_INTERNAL','-DGB_DISABLE_DEBUGGER','-DGB_DISABLE_REWIND',
 '-DGB_DISABLE_CHEATS','-DGB_DISABLE_CHEAT_SEARCH','-DGB_DISABLE_TIMEKEEPING',
 '-DGB_VERSION="1.0.4"','-DGB_COPYRIGHT_YEAR="2026"','-Wno-pass-failed',
 '-sMODULARIZE=1','-sEXPORT_NAME=SameBoyCore','-sENVIRONMENT=web','-sALLOW_MEMORY_GROWTH=1',
 '-sINITIAL_MEMORY=33554432','-sFILESYSTEM=0','-sEXPORTED_FUNCTIONS=["_malloc","_free"]',
 '-sEXPORTED_RUNTIME_METHODS=["HEAPU8"]',
 '-sDYNAMIC_EXECUTION=0','--no-entry','-lm']
subprocess.run(command,cwd=ROOT,check=True)
out=ROOT/'website/emulator'
(out/'SAMEBOY-LICENSE.txt').write_bytes((SOURCE/'LICENSE').read_bytes())
(out/'SAMEBOY-UPSTREAM.txt').write_text('SameBoy 1.0.4 by Lior Halphon (Expat/MIT license).\n'
 'Source: https://github.com/LIJI32/SameBoy/tree/v1.0.4\n'
 'Built locally with Emscripten 4.0.10 and tools/browser_sameboy.c.\n'
 'No audio-core patches; GB_MODEL_DMG_B with accurate hardware high-pass.\n'
 'Hardware boot runs off-screen; logo frames and boot audio are discarded before cartridge LCD handoff.\n'
 'Boot ROM SHA256: '+hashlib.sha256(boot).hexdigest()+'\n',encoding='utf-8')
print(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [out/'sameboy.js',out/'sameboy.wasm']},indent=2))

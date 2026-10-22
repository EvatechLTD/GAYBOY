from pathlib import Path
import argparse, concurrent.futures, hashlib, re, subprocess, sys, time
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--demo-seed',type=Path);options=parser.parse_args()
# Concurrent sessions share object names; serialize compilation and linking.
(root/'build').mkdir(exist_ok=True)
build_lock=(root/'build/build.lock').open('a+b')
if sys.platform=='win32':
 import msvcrt
 if not build_lock.tell():build_lock.write(b'0');build_lock.flush()
 while True:
  try:
   build_lock.seek(0);msvcrt.locking(build_lock.fileno(),msvcrt.LK_NBLCK,1);break
  except OSError:time.sleep(.1)
else:
 import fcntl
 fcntl.flock(build_lock,fcntl.LOCK_EX)
compiler=root/'tools/gbdk/bin/lcc.exe'; out=root/'build/objects';out.mkdir(exist_ok=True)
names='seq_support twink native_feedback drum_velocity coarse_pitch fast_feedback drum_grid evaluation_sequencer evaluation_controls user_presets evaluation evaluation_audio evaluation_ui evaluation_mono resident control seq_pulse sync_clock link_serial link_control sync clear_pattern pattern_io kits drum_samples32 drum_samples33 drum_samples34 drum_samples35 drum_samples36 drum_samples39 drum_samples62 main ui legacy stripped_compat storage sequencer seq_gen seq_clipboard tones tone_presets instruments seq_pixels finepitch global drum drum_samples drum_samples19 drum_samples20 mixer mixer_layout mixer_pads mixer_link intro intro_demo cinema cinema0 cinema1 cinema2 cinema5 train_motion0 train_motion1 train_window zoom0 zoom1 zoom2'.split()
names += ['intro_damage'+str(stage) for stage in range(1,11)]
if options.demo_seed:
 from make_sparse_seed import generate
 generate(options.demo_seed,root/'build/sparse_seed.c')
from generate_startup_font import generate as generate_startup_font
generate_startup_font(root/'src/ui_tiles.h',root/'src/ui_startup_font.h')
headers=b''.join(p.read_bytes() for p in sorted((root/'src').glob('*.h')))
flags=['-Wf--opt-code-size','-Wa-l']

def source_dependencies(source):
 # Include every local header transitively, including inactive branches. This
 # keeps cache invalidation conservative without recompiling unrelated pages.
 pending=[source];seen=set();parts=[]
 while pending:
  path=pending.pop().resolve()
  if path in seen:continue
  seen.add(path);data=path.read_bytes()
  parts.append((path.relative_to(root).as_posix(),data))
  for name in re.findall(rb'^\s*#\s*include\s*"([^"\r\n]+)"',data,re.M):
   child=path.parent/name.decode()
   if not child.exists():child=root/'src'/name.decode()
   if child.exists():pending.append(child)
 return b''.join(name.encode()+b'\0'+data+b'\0' for name,data in sorted(parts))
def compile_one(name):
 src=root/('build/sparse_seed.c' if name=='sparse_seed' and options.demo_seed else 'src/'+name+'.c');obj=out/(name+'.o');stamp=out/(name+'.sha256')
 toolchain=str(compiler.stat().st_mtime_ns).encode()+str(flags).encode()
 digest=hashlib.sha256(b'deps-v1\0'+source_dependencies(src)+toolchain).hexdigest()
 # Migrate a verified old cache entry without changing its object code.
 legacy=hashlib.sha256(src.read_bytes()+headers+toolchain).hexdigest()
 if obj.exists() and stamp.exists() and stamp.read_text()==legacy:stamp.write_text(digest)
 if obj.exists() and stamp.exists() and stamp.read_text()==digest:return
 r=subprocess.run([str(compiler),*flags,'-c','-o',str(obj),str(src)],cwd=root,capture_output=True,text=True)
 if r.stdout:print(r.stdout,end='',flush=True)
 if r.stderr:print(r.stderr,end='',file=sys.stderr,flush=True)
 if r.returncode:raise RuntimeError('Compilation failed: '+name)
 stamp.write_text(digest)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(compile_one,names))
r=subprocess.run([str(compiler),'-Wl-m','-Wl-j','-Wm-ynGAYBOY','-Wm-yt0x1B','-Wm-yo64','-Wm-ya4','-o','build/GAYBOY.gb',*[str(out/(n+'.o')) for n in names]],cwd=root)
if r.returncode:sys.exit(r.returncode)
# The linker can return success even when a bank overlaps the next one.
sys.exit(subprocess.run([sys.executable,str(root/'tools/check_rom.py')],cwd=root).returncode)

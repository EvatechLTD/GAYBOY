from pathlib import Path
import argparse, concurrent.futures, hashlib, subprocess, sys, time
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
names='sparse_seed clear_pattern sparse_pool sparse_store sparse_journal pattern_io kits drum_samples32 drum_samples33 drum_samples34 drum_samples35 drum_samples36 main ui legacy experimental exp_waves5 exp_waves6 exp_waves7 exp_waves8 exp_coefficients exp_maps storage sequencer seq_gen seq_clipboard tones tones_native tone_presets noiselab instruments seq_pixels finepitch global drum drum_samples drum_samples19 drum_samples20 mixer intro intro_demo cinema cinema0 cinema1 cinema2 cinema5 train_motion0 train_motion1 train_window zoom0 zoom1 zoom2'.split()
names += ['intro_damage'+str(stage) for stage in range(1,11)]
if options.demo_seed:
 from make_sparse_seed import generate
 generate(options.demo_seed,root/'build/sparse_seed.c')
from generate_native_scatter import generate as generate_native_scatter
generate_native_scatter()
from generate_startup_font import generate as generate_startup_font
generate_startup_font(root/'src/ui_tiles.h',root/'src/ui_startup_font.h')
headers=b''.join(p.read_bytes() for p in sorted((root/'src').glob('*.h')))
flags=['-Wf--opt-code-size','-Wa-l']
def compile_one(name):
 src=root/('build/sparse_seed.c' if name=='sparse_seed' and options.demo_seed else 'src/'+name+'.c');obj=out/(name+'.o');stamp=out/(name+'.sha256')
 digest=hashlib.sha256(src.read_bytes()+headers+str(compiler.stat().st_mtime_ns).encode()+str(flags).encode()).hexdigest()
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

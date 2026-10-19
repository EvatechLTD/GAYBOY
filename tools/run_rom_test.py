"""Run an existing fixture-based regression against an immutable ROM copy."""
from pathlib import Path
import argparse,builtins,io,runpy,sys
import pyboy
ap=argparse.ArgumentParser();ap.add_argument('--rom',required=True);ap.add_argument('--legacy',action='store_true',help='Start fresh batteries in the legacy fixed-record format');ap.add_argument('test');ap.add_argument('test_args',nargs=argparse.REMAINDER);args=ap.parse_args()
test_path=Path(args.test)
if not test_path.exists():test_path=Path('tools')/args.test
if not test_path.exists():ap.error('Test file not found: '+args.test)
original_open=builtins.open;original_read_text=Path.read_text;original_read_bytes=Path.read_bytes;original_pyboy=pyboy.PyBoy
rom=Path(args.rom).as_posix();noi=Path(args.rom).with_suffix('.noi').as_posix()
def is_fixture(path):return str(path).replace('\\','/').endswith('tools/test_monosynth.py')
def canonical(path,suffix):
 try:return Path(path).resolve()==Path('build/GAYBOY'+suffix).resolve()
 except (TypeError,ValueError):return False
def fixture():return original_read_text(Path('tools/test_monosynth.py')).replace('build/GAYBOY.gb',rom).replace('build/GAYBOY.noi',noi)
def redirected_open(file,mode='r',*a,**kw):
 if is_fixture(file) and 'r' in mode and 'b' not in mode:return io.StringIO(fixture())
 if 'r' in mode and canonical(file,'.noi'):file=noi
 elif 'r' in mode and canonical(file,'.gb'):file=rom
 return original_open(file,mode,*a,**kw)
def redirected_read_text(path,*a,**kw):
 if is_fixture(path):return fixture()
 if canonical(path,'.noi'):path=Path(noi)
 return original_read_text(path,*a,**kw)
def redirected_read_bytes(path,*a,**kw):return original_read_bytes(Path(rom) if canonical(path,'.gb') else path,*a,**kw)
def redirected_pyboy(*a,**kw):
 a=list(a)
 if a and canonical(a[0],'.gb'):a[0]=rom
 for key in ('gamerom','rom_path'):
  if key in kw and canonical(kw[key],'.gb'):kw[key]=rom
 target=a[0] if a else kw.get('gamerom',kw.get('rom_path'))
 try:isolated=canonical(target,'.gb') or Path(target).resolve()==Path(rom).resolve()
 except (TypeError,ValueError):isolated=False
 if isolated and 'ram_file' not in kw:kw['ram_file']=io.BytesIO(bytes(32768))
 if isolated and args.legacy and isinstance(kw.get('ram_file'),io.BytesIO):
  battery=kw['ram_file'].getvalue()
  if len(battery)==32768 and not any(battery):
   battery=bytearray(battery);battery[8192+2500:8192+2504]=b'GBM2';kw['ram_file']=io.BytesIO(battery)
 return original_pyboy(*a,**kw)
builtins.open=redirected_open;Path.read_text=redirected_read_text;Path.read_bytes=redirected_read_bytes;pyboy.PyBoy=redirected_pyboy
sys.argv=[str(test_path)]+args.test_args
try:runpy.run_path(str(test_path),run_name='__main__')
finally:builtins.open=original_open;Path.read_text=original_read_text;Path.read_bytes=original_read_bytes;pyboy.PyBoy=original_pyboy

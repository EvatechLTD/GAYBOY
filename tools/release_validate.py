"""Run a named emulator regression set and preserve per-test release evidence."""
from pathlib import Path
import argparse,subprocess,sys,time,json
ap=argparse.ArgumentParser();ap.add_argument('--name',default='stability');ap.add_argument('--rom',help='Immutable ROM copy with matching .noi');ap.add_argument('tests',nargs='+');a=ap.parse_args()
out=Path('build/alpha1-validation')/a.name;out.mkdir(parents=True,exist_ok=True)
results=[]
for test in a.tests:
 start=time.monotonic()
 try:
  command=[sys.executable,'tools/run_rom_test.py','--rom',a.rom,test] if a.rom else [sys.executable,'tools/'+test]
  r=subprocess.run(command,capture_output=True,text=True,timeout=180)
  status='PASS' if r.returncode==0 else 'FAIL';output=r.stdout+r.stderr;code=r.returncode
 except subprocess.TimeoutExpired as e:
  status='TIMEOUT';output=str(e);code=-1
 result={'test':test,'status':status,'seconds':round(time.monotonic()-start,2),'exit_code':code}
 results.append(result);(out/(Path(test).stem+'.log')).write_text(output,encoding='utf-8')
 (out/'results.json').write_text(json.dumps(results,indent=2))
 print(status,test,result['seconds'],flush=True)
sys.exit(any(r['status']!='PASS' for r in results))

"""Launch a fresh, recorded BGB link-cable take. Run from Record-Linked-Take.cmd."""
from pathlib import Path
import argparse,ctypes as C,ctypes.wintypes as W,datetime,hashlib,json,shutil,socket,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[1]

def launch(args):
 u=C.windll.user32;u.SetProcessDPIAware()
 u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
 rom=(args.rom or next((p for p in [ROOT/'build/GAYBOYMIXER-FIX.gb',ROOT/'build/GAYBOY.gb'] if p.is_file()),ROOT/'build/GAYBOYMIXER-FIX.gb')).resolve()
 # Linked worktrees can move into an archive; resolve shared saves through
 # Git's common directory instead of assuming a sibling checkout location.
 common=subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip()
 shared_root=(ROOT/common).resolve().parent
 candidates=[ROOT/'saves/reggae.srm',shared_root/'saves/reggae.srm',ROOT.parent/'GAYBOY/saves/reggae.srm']
 battery=args.battery or next((p for p in candidates if p.is_file()),candidates[0])
 battery=battery.resolve();emulator=ROOT/'tools/bgb/bgb64.exe'
 ffmpeg=shutil.which('ffmpeg')
 for item in [rom,battery,emulator]:
  if not item.is_file():raise RuntimeError('Missing file: '+str(item))
 if battery.stat().st_size!=32768:raise RuntimeError('Expected a 32768-byte battery: '+str(battery))
 if not ffmpeg:raise RuntimeError('ffmpeg is not on PATH.')
 pythonw=Path(sys.executable).with_name('pythonw.exe')
 if not pythonw.is_file():raise RuntimeError('Missing Python background executable: '+str(pythonw))
 from loopback_audio import LoopbackAudio
 import pyaudiowpatch as pa
 with pa.PyAudio() as audio:
  device=audio.get_default_wasapi_loopback()
  if not device.get('isLoopbackDevice'):raise RuntimeError('Output-loopback audio is unavailable.')
 if args.check:
  print('Ready: ROM, reggae battery, BGB, ffmpeg, Python and output audio verified: '+device['name']);return
 current=ROOT/'build/linked-test/current-recording.json'
 if current.exists():
  last=json.loads(current.read_text());config=Path(last['session'])
  if config.exists():
   previous=json.loads(config.read_text())
   if any(u.IsWindow(w['hwnd']) for w in previous['windows']):
    raise RuntimeError('A take is already open. Close both emulator windows before starting another take.\n'+last['folder'])
   status=config.with_name('recording.json')
   if status.exists() and json.loads(status.read_text()).get('status')=='finalizing':
    raise RuntimeError('The previous take is still saving. Try again in a few seconds.')
 folder=ROOT/'build/linked-test'/('reggae-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
 folder.mkdir(parents=True)
 probe=socket.socket();probe.bind(('127.0.0.1',0));port=probe.getsockname()[1];probe.close()
 windows=[];processes=[]
 try:
  for i,side in enumerate(['LEFT','RIGHT']):
   directory=folder/side;directory.mkdir();dest=directory/(side+'.gb')
   shutil.copy2(rom,dest);shutil.copy2(battery,directory/(side+'.sav'))
   command=[str(emulator),'-rom',str(dest),'-listen' if i==0 else '-connect',f'127.0.0.1:{port}','-nowriteini']
   settings=['Joypad0=27252628585A2010FFFF6B73716A6D1BFFFFFF09FF','SaveRamDir='+str(directory),'PauseOnDefocus=0','WinX='+str(40+i*700),'WinY=80','Width=640','Height=576']
   for setting in settings:command.extend(['-setting',setting])
   proc=subprocess.Popen(command,cwd=emulator.parent);processes.append(proc);windows.append(dict(side=side,pid=proc.pid));time.sleep(.5)
  callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
  for window in windows:
   for _ in range(100):
    found=[]
    @callback
    def enum(hwnd,_):
     pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid))
     if pid.value==window['pid'] and u.IsWindowVisible(hwnd):
      title=C.create_unicode_buffer(512);u.GetWindowTextW(hwnd,title,512)
      if title.value.lower().startswith('bgb'):found.append((hwnd,title.value))
     return True
    u.EnumWindows(enum,0)
    if found:window.update(hwnd=found[0][0],title=found[0][1]);break
    time.sleep(.1)
   if 'hwnd' not in window:raise RuntimeError('Emulator window did not open: '+window['side'])
  work=W.RECT();u.SystemParametersInfoW(48,0,C.byref(work),0)
  scale=max(1,min(6,(work.right-work.left-64)//320,(work.bottom-work.top-80)//144))
  rect=W.RECT(0,0,160*scale,144*scale)
  u.AdjustWindowRectEx(C.byref(rect),u.GetWindowLongW(windows[0]['hwnd'],-16),False,u.GetWindowLongW(windows[0]['hwnd'],-20))
  width,height=rect.right-rect.left,rect.bottom-rect.top;gap=16
  x=work.left+((work.right-work.left)-(width*2+gap))//2;y=work.top+((work.bottom-work.top)-height)//2
  for i,window in enumerate(windows):u.SetWindowPos(window['hwnd'],W.HWND(-1),x+i*(width+gap),y,width,height,0x0040)
  time.sleep(.5)
  for window in windows:
   bounds=W.RECT();u.GetWindowRect(window['hwnd'],C.byref(bounds));window['rect']=[bounds.left,bounds.top,bounds.right,bounds.bottom]
  if windows[0]['rect'][2]>windows[1]['rect'][0] or windows[0]['rect'][1]!=windows[1]['rect'][1]:raise RuntimeError('Could not align emulator windows side by side.')
  cfg=dict(folder=str(folder),windows=windows,port=port,ffmpeg=ffmpeg,rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),battery_source=str(battery),battery_sha256=hashlib.sha256(battery.read_bytes()).hexdigest(),stop_when='either emulator closes',mapping={'Shift':'Start','Space':'Select','Z':'B','X':'A','arrows':'D-pad'})
  config=folder/'session.json';config.write_text(json.dumps(cfg,indent=2))
  recorder=subprocess.Popen([str(pythonw),str(ROOT/'tools/record_linked_windows.py'),str(config)],creationflags=subprocess.CREATE_NO_WINDOW)
  current.write_text(json.dumps({'session':str(config),'folder':str(folder),'recorder_pid':recorder.pid},indent=2))
  for _ in range(150):
   error=folder/'recorder-error.log';status=folder/'recording.json'
   if error.exists():raise RuntimeError(error.read_text())
   if status.exists():
    try:state=json.loads(status.read_text())
    except json.JSONDecodeError:state={}
    if state.get('status')=='recording':
     print('Recording started at 30 fps with stereo output audio and timed LEFT/RIGHT button logs.\nClose either emulator to save the take.\n'+str(folder));return
   if recorder.poll() is not None:raise RuntimeError('Recorder exited before capture started. See '+str(folder))
   time.sleep(.1)
  raise RuntimeError('Recording did not start within 15 seconds. See '+str(folder))
 except Exception:
  # Close only the windows this invocation created; preserve all other takes.
  for window in windows:
   if 'hwnd' in window:u.PostMessageW(window['hwnd'],0x10,0,0)
  raise

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--rom',type=Path);parser.add_argument('--battery',type=Path);parser.add_argument('--check',action='store_true')
 try:launch(parser.parse_args())
 except Exception as error:print('Could not start take:\n'+str(error),file=sys.stderr);sys.exit(1)

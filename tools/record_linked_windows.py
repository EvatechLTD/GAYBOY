"""Record a bounded pair of emulator clients and their focused joypad input.
Video is 30 fps; closing either supplied emulator finalizes the recording.
Only keys sent while one of the supplied windows is foreground are logged.
"""
import argparse, ctypes as C, ctypes.wintypes as W, json, os, re, subprocess, threading, time
from pathlib import Path
from decimal import Decimal
from loopback_audio import LoopbackAudio

u=C.windll.user32;k=C.windll.kernel32
u.SetProcessDPIAware()
u.GetForegroundWindow.restype=W.HWND
u.CallNextHookEx.restype=C.c_ssize_t
u.SetWindowsHookExW.restype=W.HANDLE
u.SetWindowsHookExW.argtypes=[C.c_int,C.c_void_p,W.HINSTANCE,W.DWORD]
u.CallNextHookEx.argtypes=[W.HANDLE,C.c_int,W.WPARAM,W.LPARAM]
k.GetModuleHandleW.restype=W.HMODULE

def client(hwnd):
 r=W.RECT();pt=W.POINT(0,0);u.GetClientRect(hwnd,C.byref(r));u.ClientToScreen(hwnd,C.byref(pt))
 return dict(x=pt.x,y=pt.y,width=r.right,height=r.bottom)

def record(config):
 cfg=json.loads(Path(config).read_text());folder=Path(cfg['folder']);windows=cfg['windows']
 output=folder/'linked-30fps.mkv';keys=folder/'keys.jsonl';meta=folder/'recording.json'
 left,right=[client(w['hwnd']) for w in windows]
 x=min(left['x'],right['x']);y=min(left['y'],right['y'])
 width=max(r['x']+r['width'] for r in [left,right])-x
 height=max(r['y']+r['height'] for r in [left,right])-y
 size=(min(left['width'],right['width'])//2*2,min(left['height'],right['height'])//2*2)
 filters='[0:v]split=2[l][r];[l]crop=%d:%d:%d:%d[a];[r]crop=%d:%d:%d:%d[b];[a][b]hstack=inputs=2[v]'%(*size,left['x']-x,left['y']-y,*size,right['x']-x,right['y']-y)
 state={**cfg,'status':'starting','recorder_pid':os.getpid(),'fps':30,'video':str(output),'keys':str(keys),'client_rects':[left,right],'video_size':[size[0]*2,size[1]],'clock':'key unix_ns minus video_start_unix_ns gives video-relative time; monotonic_ns also retained','video_start_unix_ns':None}
 def publish():meta.write_text(json.dumps(state,indent=2))
 publish()
 audio=LoopbackAudio(folder/'loopback.wav').start()
 state['audio']=audio.summary();publish()
 cmd=[cfg['ffmpeg'],'-hide_banner','-y','-f','gdigrab','-framerate','30','-draw_mouse','0','-offset_x',str(x),'-offset_y',str(y),'-video_size',f'{width}x{height}','-i','desktop','-filter_complex',filters,'-map','[v]','-an','-c:v','libx264','-preset','ultrafast','-crf','18','-pix_fmt','yuv420p','-r','30','-fps_mode','cfr','-progress',str(folder/'progress.txt'),str(output)]
 start_mono=time.perf_counter_ns();start_wall=time.time_ns();state.update(start_monotonic_ns=start_mono,start_unix_ns=start_wall)
 encoder=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 state['ffmpeg_pid']=encoder.pid;publish()
 def errors():
  with (folder/'ffmpeg.log').open('w',encoding='utf8') as log:
   for line in iter(encoder.stderr.readline,b''):
    line=line.decode(errors='replace');log.write(line);log.flush()
    found=re.search(r'Duration: N/A, start: ([0-9.]+)',line)
    if found:
     state['video_start_unix_ns']=int(Decimal(found.group(1))*1_000_000_000);state['status']='recording';publish()
 threading.Thread(target=errors,daemon=True).start()
 buttons={0x25:'LEFT',0x27:'RIGHT',0x26:'UP',0x28:'DOWN',0x58:'A',0x5A:'B',0x20:'SELECT',0x10:'START',0xA0:'START',0xA1:'START'}
 class KEY(C.Structure):_fields_=[('vk',W.DWORD),('scan',W.DWORD),('flags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
 pressed={};event_count=0
 log=keys.open('w',encoding='utf8',buffering=1)
 def write_event(side,vk,scan,down,repeat=False,synthetic=False):
  nonlocal event_count
  now=time.perf_counter_ns();wall=start_wall+(now-start_mono)
  event={'monotonic_ns':now,'unix_ns':wall,'recorder_seconds':(now-start_mono)/1e9,'side':side,'button':buttons.get(vk),'vk':vk,'scan':scan,'event':'down' if down else 'up','repeat':repeat,'synthetic':synthetic}
  log.write(json.dumps(event)+'\n');event_count+=1
 @C.WINFUNCTYPE(C.c_ssize_t,C.c_int,W.WPARAM,W.LPARAM)
 def keyboard(code,message,data):
  if code>=0 and message in (0x100,0x101,0x104,0x105):
   e=C.cast(data,C.POINTER(KEY)).contents;down=message in (0x100,0x104)
   hwnd=u.GetForegroundWindow();side=next((w['side'] for w in windows if w['hwnd']==hwnd),None)
   if e.vk in buttons:
    if down and side:
     repeat=e.vk in pressed;pressed[e.vk]=(side,e.scan);write_event(side,e.vk,e.scan,True,repeat)
    elif not down and e.vk in pressed:
     old,scan=pressed.pop(e.vk);write_event(old,e.vk,scan,False)
  return u.CallNextHookEx(None,code,message,data)
 hook=u.SetWindowsHookExW(13,keyboard,k.GetModuleHandleW(None),0)
 if not hook:raise C.WinError()
 message=W.MSG()
 try:
  while encoder.poll() is None and all(u.IsWindow(w['hwnd']) for w in windows):
   while u.PeekMessageW(C.byref(message),None,0,0,1):u.TranslateMessage(C.byref(message));u.DispatchMessageW(C.byref(message))
   # Release the shell animation when focus leaves the originating emulator.
   foreground=u.GetForegroundWindow()
   for vk,(side,scan) in list(pressed.items()):
    own=next(w['hwnd'] for w in windows if w['side']==side)
    if foreground!=own:write_event(side,vk,scan,False,synthetic=True);pressed.pop(vk)
   time.sleep(.005)
 finally:
  u.UnhookWindowsHookEx(hook)
  for vk,(side,scan) in pressed.items():write_event(side,vk,scan,False,synthetic=True)
  log.close()
  audio.stop();state['audio']=audio.summary()
  if encoder.poll() is None:
   encoder.stdin.write(b'q\n');encoder.stdin.flush()
   try:encoder.wait(timeout=20)
   except subprocess.TimeoutExpired:encoder.terminate();encoder.wait(timeout=5)
  state.update(status='finalizing',encoder_exit=encoder.returncode,key_event_count=event_count);publish()
  final=folder/'linked-30fps.mp4'
  epoch=state.get('video_start_unix_ns')
  audio_epoch=audio.first_sample_unix_ns
  if encoder.returncode==0 and epoch and audio_epoch and audio.frames and not audio.error:
   # WAV begins before the first video frame. Trim that lead-in, or pad a
   # later audio start, using the actual capture timestamps rather than launch time.
   offset=(audio_epoch-epoch)/1e9
   audio_args=['-ss',str(-offset)] if offset<0 else ['-itsoffset',str(offset)]
   state['audio_video_offset_seconds']=offset
   mux=[cfg['ffmpeg'],'-hide_banner','-y','-i',str(output),*audio_args,'-i',str(audio.path),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-af','aresample=async=1:first_pts=0','-shortest','-movflags','+faststart',str(final)]
   r=subprocess.run(mux,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
   (folder/'mux.log').write_bytes(r.stderr)
   if r.returncode==0:state['final_video']=str(final)
   else:state['finalization_error']='Audio/video mux failed; original WAV and MKV retained.'
  else:state['finalization_error']='Audio capture or video capture failed; raw files retained.'
  state['status']='finished' if state.get('final_video') else 'failed';state['stopped_unix_ns']=time.time_ns();publish()
  epoch=state.get('video_start_unix_ns')
  if epoch:
   events=[json.loads(line) for line in keys.read_text().splitlines()]
   for event in events:event['video_seconds']=(event['unix_ns']-epoch)/1e9;event['frame_30fps']=round(event['video_seconds']*30)
   (folder/'keys-timed.json').write_text(json.dumps({'fps':30,'video_start_unix_ns':epoch,'events':events},indent=2))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('config');args=ap.parse_args()
 try:record(args.config)
 except Exception:
  import traceback
  Path(args.config).with_name('recorder-error.log').write_text(traceback.format_exc());raise

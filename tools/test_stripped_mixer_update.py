"""Mixer layout, synth gain faders and deferred graphics after pattern launch."""
from pathlib import Path
import json
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
try:
 enter_app(p,S);menu(18);p.tick(120)
 assert line(0)[8:12]=='PLAY' and line(1).startswith('BPM') and line(1).rstrip().endswith('LAUNCH 1/1'),(line(0),line(1))
 assert line(2).strip()=='P1 P2 WV  N DR NHH',line(2)
 assert [v('canvas',r*20) for r in (3,4,5)]==[ord(c)-32 for c in 'MSV']
 assert all(v('fader_image_knob',i)!=255 for i in range(6)),'Deferred initial faders did not finish'
 # DR level, then three synth faders, then sample M/S.
 put('mx',28,4);put('dirty',1);p.tick(20)
 for focus in (65,66,67):press('right');assert v('mx',4)==focus,(focus,v('mx',4))
 press('right');assert v('mx',4)==39
 # Independent gain editing leaves Tone hardware level/ADSR selection intact.
 put('mx',65,4);put('dirty',1);p.tick(20)
 original=v('noisepatch');mode=v('evalpatch',5*16+10)
 p.button_press('b');p.tick(3);press('down');p.button_release('b');p.tick(30)
 assert v('evalpatch',4*16)==126 and v('noisepatch')==original and v('evalpatch',5*16+10)==mode
 p.button_press('a');p.tick(3);press('left');p.button_release('a');p.tick(30);assert v('evalpatch',4*16)==116
 p.screen.image.save('build/stripped-mixer-tall.png')
 # The destination pattern has different P1 mixer volume.
 p.memory[0x4000]=1;p.memory[0xa800+32+56]=32;p.memory[0x4000]=0
 put('mx',31,4);put('dirty',1);p.tick(20)
 uploads=[];restores=[];slot=S['_sparse_restore'];p.hook_register(slot>>16,slot&65535,lambda _:restores.append(p._cycles()),None)
 def upload(_):
  tile=p.memory[p.register_file.SP+6]
  if 192<=tile<=203 or 220<=tile<=249:uploads.append(p._cycles())
 ptr=S['_ui_upload_tile'];p.hook_register(ptr>>16,ptr&65535,upload,None)
 press('a');p.tick(120);assert v('mx',1)==1 and restores and uploads
 delay=(uploads[0]-restores[-1])*1000/4194304;assert delay>=33,delay
 assert v('mx',12)==32
 p.button_press('start');p.tick(20);press('select');p.button_release('start');p.tick(120)
 assert line(0).startswith('MIXER') and line(1).startswith('BPM'),'Menu cancellation left stale mixer text'
 Path('build/stripped-mixer-update.json').write_text(json.dumps({'first_fader_after_restore_start_ms':delay,'pcm_underruns':v('mixunderruns')|v('mixunderruns',1)<<8},indent=2)+'\n')
 print('PASS: tall mixer, synth ordering/gains, clean pads, deferred faders',delay)
finally:p.stop(save=False)

"""Incremental mixer pad/fader bitmaps equal independent full regenerations."""
from pathlib import Path
import argparse,json,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--output',default='build/mixer-pixel-cache.json');args=ap.parse_args()
env={};source=Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0].replace('range(60)','range(600)').replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file=')
source=source.replace('build/GAYBOY.gb',args.rom).replace('build/GAYBOY.noi',str(Path(args.rom).with_suffix('.noi')));exec(source,env)
p,S,choose=env['p'],env['S'],env['choose'];mx=S['_mx'];flushes=[];results=[]
def v(n,i=0):return p.memory[S['_'+n]+i]
def put(n,x,i=0):p.memory[S['_'+n]+i]=x
def sm(i,x):p.memory[mx+i]=x
def name(slot):return ('P%02d'%(slot+1)).encode()
def live_name(slot):p.memory[mx+26:mx+43]=list(name(slot)+bytes(14))
def ptile(tile,bank):return (168+tile if tile<24 else 180+tile) if bank else (64+tile if tile<32 else 128+tile)
def bitmap(tile):
 at=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16
 return bytes(p.memory[at:at+16])
def render(force_pads=False,force_faders=False,invalidate_pads=True):
 if (force_pads or force_faders) and '_mixer_image' in S:put('mixer_image',0)
 if force_pads:put('pad_names_valid',0)
 if force_faders:
  for i in range(5):put('fader_image_knob',255,i)
 if invalidate_pads:sm(9,0)
 put('dirty',1);before=len(flushes)
 for _ in range(600):
  p.tick(1)
  if len(flushes)>before:break
 assert len(flushes)>before,'Mixer did not publish its render'
 p.tick(2)
def capture(queued):
 bank=v('padbank');active=[bitmap(ptile(i,bank)) for i in range(40)]
 opposite=[]
 if queued<8:
  col=queued*2+queued//2
  opposite=[bitmap(ptile(row*20+col+x,bank^1)) for row in range(2) for x in range(3)]
 return active,opposite
try:
 assert '_pad_names_valid' in S and '_fader_image_knob' in S,'Requires mixer pixel-cache candidate'
 choose(18)
 # Persisted names make every pad distinct. No musical data is loaded by this
 # renderer-only test; each temporary RAM bank is restored before emulation.
 for slot in range(8):
  p.memory[0x4000]=1+slot//3;at=0xa000+(slot%3)*2560
  p.memory[at]=0xb9;p.memory[at+1:at+18]=list(name(slot)+bytes(14))
 p.memory[0x4000]=0
 a=S['_ui_flush'];p.hook_register(a>>16,a&65535,lambda _:flushes.append(p._cycles()),None)
 # Adjacent pads share half a tile: all ordered transitions include those
 # neighbors, far slots, no queue, and queued==playing.
 for playing in range(8):
  for queued in (255,playing,(playing+1)%8,(playing-1)%8,7-playing):
   sm(1,playing);sm(2,queued);sm(4,30+playing);live_name(playing)
   render();incremental=capture(queued)
   render(force_pads=True);full=capture(queued)
   active_diff=[i for i,(a,b) in enumerate(zip(incremental[0],full[0])) if a!=b]
   opposite_diff=[i for i,(a,b) in enumerate(zip(incremental[1],full[1])) if a!=b]
   result={'playing':playing,'queued':queued,'active_tiles_compared':40,'queued_opposite_tiles_compared':len(full[1]),'active_differences':active_diff,'queued_differences':opposite_diff};results.append(result)
   assert not active_diff and not opposite_diff,result
 # Focus and value changes must leave identical fader tiles and numeric cells
 # whether or not the knob-image cache is reused.
 faders=[]
 for focus in (4,8,12,16,28,38,39,4):
  for value in (0,1,12,63,64,126,127):
   sm(4,focus)
   for c in range(7):sm(12+c,(value+c*19)%128)
   render();before=[bitmap(243+i) for i in range(10)];numbers=bytes(p.memory[S['_canvas']+140:S['_canvas']+160])
   render(force_faders=True);after=[bitmap(243+i) for i in range(10)];newnumbers=bytes(p.memory[S['_canvas']+140:S['_canvas']+160])
   differences=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
   result={'focus':focus,'value':value,'tile_differences':differences,'numbers_equal':numbers==newnumbers};faders.append(result)
   assert not differences and numbers==newnumbers,result
 # Retained pad-focus drawing must preserve every background cell and font/
 # graphics byte across all state changes that invalidate the strip template.
 whole=[]
 def screen_state():
  # Normalize the queued blink phase; its intentional animation is unrelated
  # to cache equivalence. Let production mixer_tick publish the active bank.
  now=v('sys_time')|(v('sys_time',1)<<8)
  put('padflash_started',now&255);put('padflash_started',now>>8,1);p.tick(2)
  return bytes(p.memory[0x8000:0x9800]),bytes(p.memory[0x9800:0x9c00])
 states=[{'focus':f} for f in (30,31,32,33,32,37,30)]+[{'quant':q} for q in (0,1,2)]+[{'edit':1},{'edit':0},{'muted':1},{'muted':0},{'solo':2},{'solo':0},{'drummute':1},{'drummute':0},{'slot':1,'pending':1},{'slot':2,'pending':3},{'slot':7,'pending':6},{'slot':0,'pending':255},{'page':19},{'page':20},{'page':18}]
 sm(1,0);sm(2,255);sm(4,30);live_name(0);render(force_pads=True,force_faders=True)
 for changes in states:
  for field,value in changes.items():
   if field in ('focus','quant','edit','slot','pending'):sm({'focus':4,'quant':3,'edit':5,'slot':1,'pending':2}[field],value)
   else:put({'muted':'seqmuted','solo':'seqsolo','drummute':'drummutemask','page':'page'}[field],value)
  if 'slot' in changes:live_name(changes['slot'])
  invalidate='slot' in changes or 'pending' in changes
  render(invalidate_pads=invalidate);incremental=screen_state()
  render(force_pads=True,force_faders=True);full=screen_state()
  result={'changes':changes,'vram_differing_bytes':sum(a!=b for a,b in zip(incremental[0],full[0])),'background_map_differing_bytes':sum(a!=b for a,b in zip(incremental[1],full[1]))};whole.append(result)
  assert not result['vram_differing_bytes'] and not result['background_map_differing_bytes'],result
 # Exercise actual START menu opening/return, whose overlay reuses canvas.
 p.button_press('start')
 for _ in range(600):
  p.tick(1)
  if v('navopen'):break
 assert v('navopen')
 render();incremental=screen_state();render(force_pads=True,force_faders=True);full=screen_state()
 assert incremental==full,'START menu overlay differs after full regeneration'
 p.button_release('start');p.tick(120);assert v('page')==18 and not v('navopen')
 render(invalidate_pads=False);incremental=screen_state();render(force_pads=True,force_faders=True);full=screen_state()
 assert incremental==full,'Returning from START menu leaves stale mixer pixels'
 report={'rom_sha256':hashlib.sha256(Path(args.rom).read_bytes()).hexdigest(),'model':'DMG','pad_cases':results,'fader_cases':faders,'whole_background_cases':whole,'retained_mixer_image_exercised':'_mixer_image' in S,'menu_open_and_return_equal':True,'passes':True};Path(args.output).write_text(json.dumps(report,indent=2));print('PASS: %d pad transitions compare all40 active tiles + queued6 opposite tiles; %d fader cases and %d whole-map/VRAM transitions match full regeneration'%(len(results),len(faders),len(whole)))
finally:p.stop(save=False)

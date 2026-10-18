"""Dense melodic-to-drum transitions retain every displayed VRAM tile."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
import json

def put(n,i,x):fixture_put(p,S,n,i,x)

state={'rendering':False,'completed':False,'clearing':False};returns=set()
def entered(_):
 state['rendering']=True;state['completed']=False;state['clearing']=False
 sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;bank=p.memory[0xff90] if 0x4000<=ret<0x8000 else 0
 key=(bank,ret,sp+2)
 if key not in returns:
  returns.add(key)
  def returned(k):
   if state['rendering'] and p.register_file.SP==k[2]:state['rendering']=False;state['completed']=True
  p.hook_register(bank,ret,returned,key)
a=S['_drum_render'];p.hook_register(a>>16,a&65535,entered,None)
a=S['_roll_clear_transition'];p.hook_register(a>>16,a&65535,lambda _:state.update(clearing=True),None)

def tiles():
 # Signed GB background addressing: tile0 at9000, IDs128..255 at8800..8ff0.
 out={}
 for ident in set(p.memory[S['_visible']:S['_visible']+360]):
  if 64<=ident<96 or 160<=ident<244 or ident>=252:
   addr=0x9000+(ident if ident<128 else ident-256)*16
   out[addr]=bytes(p.memory[addr:addr+16])
 return out
try:
 choose(8);results=[]
 for zoom in range(4):
  put('seqtrack',0,0);put('seqzoom',0,zoom)
  for c in range(7):put('seqlength',c,64)
  for i in range(64):
   put('seqnotes',i,49+(i*7)%25);put('seqvelocity',i,1+(i*19)%127);put('seqduration',i,1)
  for i in range(128):
   put('drumhits',i,1+(i//2)%10 if i%4<2 else 0);put('drumvel',i,1+(i*17)%127);put('drumdur',i,1)
   put('noisehits',i,1 if i%3==0 else 0);put('noisevel',i,1+(i*11)%127);put('noisedur',i,1)
  put('seqdrawvalid',0,0);put('dirty',0,1);p.tick(180)
  assert not v('seqtileoverflow'),('melodic fixture overflow',zoom)
  old=tiles();p.screen.image.save('build/ui-drum-transition-'+str(zoom)+'-before.png')
  state['completed']=False;p.button_press('select');p.tick(4);p.button_press('left')
  checked=0
  for frame in range(300):
   p.tick(1)
   if state['rendering']:
    neutral=state['clearing'] and not any(p.memory[S['_visible']+20:S['_visible']+360])
    for addr,data in ([] if neutral else old.items()):assert bytes(p.memory[addr:addr+16])==data,('visible tile overwritten during drum build',zoom,hex(addr),frame)
    if checked==5:p.screen.image.save('build/ui-drum-transition-'+str(zoom)+'-during.png')
    checked+=1
   if state['completed'] and v('lastpad')&2:break
  p.button_release('left');p.button_release('select');p.tick(30)
  assert v('seqtrack')==6 and state['completed']
  assert not v('seqtileoverflow'),('old/new tile union overflow',zoom,v('seqtilecount'))
  p.screen.image.save('build/ui-drum-transition-'+str(zoom)+'-after.png')
  results.append({'columns':(zoom+1)*8,'transition_frames':checked,'old_unique_tiles':len(old),'union_tiles':v('seqtilecount'),'neutral_fallback':state['clearing']})
 print(json.dumps(results,indent=2));print('PASS: dense DRUM transitions preserve displayed tiles with no pool overflow')
finally:p.stop(save=False)

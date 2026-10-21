"""Instrument/menu partial composition stays identical to a forced full draw."""
from pathlib import Path
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
exec(prefix)
try:
 enter_app(p,S)
 def canvas():return bytes(v('canvas',i) for i in range(360))
 def compare(cache):
  p.tick(30);before=canvas();p.memory[0,cache]=0;put('dirty',1);p.tick(100);assert canvas()==before,('full rendering differs',cache,[(i%20,i//20,a,b) for i,(a,b) in enumerate(zip(before,canvas())) if a!=b][:25])
 calls=[];ptr=S['_eval_value_named'];p.hook_register(ptr>>16,ptr&65535,lambda _:calls.append(p._cycles()),None)
 for selected in (0,1,2,3):
  put('page',1);put('selected',selected);put('eval_tab',0);put('eval_row',0);put('eval_col',0);put('dirty',1);p.tick(100);calls.clear()
  press('down');p.tick(30);assert len(calls)<=2,('rebuilt all tone rows',selected,len(calls));compare(0xa475);calls.clear()
  put('dirty',1);p.tick(40);assert not calls,('unchanged rows composed',selected,len(calls))
  # An external edit must also refresh a row that is not selected.
  put('param',(v('param',selected*26)&3)^1,selected*26);put('dirty',1);p.tick(40);compare(0xa475)
 # A change by256 must not collide in the fine-pitch signature.
 put('selected',0);put('finepitch',0);put('finepitch',1,1);put('dirty',1);p.tick(40);compare(0xa475)
 put('page',2);put('eval_row',0);put('dirty',1);p.tick(80);press('down');p.tick(30);compare(0xa475)
 # Start menu selection and category changes keep identical maps.
 p.button_press('start');p.tick(30)
 for key in ('down','down','right','down','left','up'):
  press(key);p.tick(30);compare(0xa4d0)
 press('select');p.button_release('start');p.tick(60);compare(0xa475)
finally:p.stop(save=False)
print('PASS: changed instrument rows only, external edits, fine pitch, MOD, menu categories and cancel return')

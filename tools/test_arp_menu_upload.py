"""Interruptible menu/settings uploads finish with the correct visible tile map."""
from pathlib import Path
exec(Path('tools/test_arp_stress.py').read_text().split('reports=[]')[0])
try:
 enter_app(p,S);put('seqtrack',1);put('selected',1);put('seqhead',1);put('seqfocus',0);put('dirty',1);p.tick(180)
 key('select',True);key('a',True);key('a',False);key('select',False)
 for bpm in (120,240):
  word('seqbpm',bpm);word('seqglobalbpm',bpm);word('seqcachedbpm',0)
  for page,menu in ((1,0),(2,0),(17,0),(1,1)):
   put('page',page);put('navopen',menu);put('eval_tab',0);put('eval_row',0);put('navcategory',0);put('navchoice',1);put('dirty',1);p.tick(120)
   for k in ('down','down','up','up'):
    assert key(k,True) is not None and key(k,False) is not None
   p.tick(240)
   canvas=bytes(get('canvas',i) for i in range(360));visible=bytes(get('visible',i) for i in range(360))
   vram=bytes(p.memory[0x9800+r*32+x] for r in range(18) for x in range(20))
   assert canvas==visible==vram,(bpm,page,menu,'unfinished or incorrect upload')
   assert not get('ui_transition_hidden') and p.memory[0xff40]&1
   print('PASS settled map after live navigation',bpm,page,menu,flush=True)
finally:p.stop(save=False)

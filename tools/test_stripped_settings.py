"""Duplicate shortcut recovery and the Settings hierarchy."""
from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
try:
 enter_app(p,S)
 for i,value in enumerate((11,11,16,13,255,255,255,255)):put('pool_root',value,100+i)
 put('pool_root',ord('P'),108);put('pool_root',1,109)
 p.button_press('start');p.tick(30)
 assert v('pool_root',101)==255 and v('pool_root',102)==255
 choices=[]
 for _ in range(7):choices.append(v('navchoice'));press('down')
 assert 16 in choices and set(choices)=={18,8,16,11,13},choices
 put('navchoice',16);p.button_release('start');p.tick(180)
 assert line(0).strip()=='SETTINGS',(line(0),v('page'),v('navopen'),v('pageconfig'))
 for label in ('MIXER SETTINGS','QUICK MENU','SYNC','SEQ PAGES'):assert label in text(0)
 # Seq page visibility lives on its own page and returns to Settings.
 put('eval_row',3);put('dirty',1);p.tick(10);press('a');assert v('pageconfig')==3
 assert line(0).strip()=='SEQ PAGES';press('a');assert v('eval_hidden')&1
 press('select');assert v('pageconfig')==0 and v('eval_row')==3
 # Reassigning an existing shortcut moves it instead of making a duplicate.
 put('eval_row',1);put('dirty',1);p.tick(10);press('a');assert v('pageconfig')==1 and line(0).strip()=='QUICK MENU'
 for slot in (0,1):
  if slot:press('down')
  press('a');assert v('pageconfig')==2
  put('navchoice',13);press('a');assert v('pageconfig')==1
 assert sum(v('pool_root',100+i)==13 for i in range(8))==1
 press('select');assert v('pageconfig')==0
 print('PASS: duplicate repair, reachable Settings, hierarchy, Seq Pages and unique shortcut assignment')
finally:p.stop(save=False)


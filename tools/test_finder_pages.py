"""Configurable PAGE entries keep fixed endpoints and persist across boots."""
exec(open('tools/test_finder.py').read().split('try:\n')[0])

def action(n,cat=0):
 tap('start');category(cat);item(n);tap('start')
def settings():
 action(16)
 if not p.memory[S['_cursor']]:tap('down')
 tap('a');assert v('pageconfig')==1
 for _ in range(8):
  if p.memory[S['_canvas']+3*20]==ord('>')-32:break
  tap('up')

def assign(n,cat):
 tap('a');assert v('pageconfig')==2;category(cat);item(n);tap('a');assert v('pageconfig')==1

def slots():return bytes(p.memory[S['_pool_root']+100:S['_pool_root']+108])
def menu():
 tap('start');assert v('navcategory')==0
 result=[]
 for _ in range(20):
  if v('navchoice') in result:break
  result.append(v('navchoice'));tap('down')
 return result

def battery():
 data=bytearray()
 for bank in range(4):
  p.memory[0x4000]=bank;data.extend(p.memory[0xa000:0xc000])
 p.memory[0x4000]=0
 return bytes(data)
try:
 enter_app(p);assert menu()==[18,8,16,27];tap('select')
 # Start+Up behaves as normal menu navigation; release never dispatches.
 p.button_press('start');p.tick(30);tap('up');assert v('navchoice')==27
 p.button_release('start');p.tick(30);assert v('navopen') and v('page')==8;tap('select')
 settings();assign(34,2);tap('down');assign(11,3)
 p.screen.image.save('build/finder-page-settings.png')
 tap('select');assert menu()==[18,8,34,11,16,27]
 p.screen.image.save('build/finder-page-custom.png');tap('select')
 # Custom entries dispatch through the normal page paths.
 action(11);assert v('page')==1 and v('selected')==0
 action(34);assert v('page')==8 and v('seqtrack')==6
 # Reorder/remove only the middle slots; fixed pages stay at the ends.
 settings();tap('right');assert slots()[:2]==bytes([11,34]);tap('b');assert slots()[1]==255
 tap('select');assert menu()==[18,8,11,16,27];tap('select')
 # Saved page assignments survive reboot, with the same fixed ordering.
 expected=slots();saved=battery();p.stop(save=False)
 p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,ram_file=BytesIO(saved));p.set_emulation_speed(0);enter_app(p)
 assert slots()==expected;assert menu()==[18,8,11,16,27];tap('select')
 # Old default Quick entries do not populate the new PAGE menu with edit actions.
 root=S['_pool_root'];p.memory[root+100:root+108]=[18,8,38,21,22,35,16,255];p.memory[root+108:root+110]=[ord('Q'),1]
 assert menu()==[18,8,16,27];tap('select')
 # An explicitly customized old menu keeps its nonfixed shortcuts.
 p.memory[root+100:root+108]=[18,8,34,11,16,27,255,255];p.memory[root+108:root+110]=[ord('Q'),1]
 assert menu()==[18,8,34,11,16,27];tap('select')
 print('PASS: fixed PAGE order, configurable middle entries, reorder/remove, shortcut dispatch, restart persistence, old Quick migration and removal of hold/release gesture')
finally:p.stop(save=False)

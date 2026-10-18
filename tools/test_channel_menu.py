exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def alias(item,channel):
 p.button_press('start')
 for _ in range(100):
  p.tick(1)
  if v('navopen'):break
 for _ in range(16):
  if v('navchoice')==item:break
  press('down')
 assert v('navchoice')==item
 p.button_release('start');p.tick(60)
 assert v('page')==1 and v('selected')==channel

def menu_items():
 p.button_press('start');p.tick(40);items=[]
 for _ in range(16):items.append(v('navchoice'));press('down')
 p.button_release('start');p.tick(60)
 return items
# Direct instrument entries preserve contextual selection across all pages.
for item,channel in ((11,0),(12,1),(13,2),(15,3),(14,4)):
 alias(item,channel)
 for target in (1,2,3,4,5,6):
  choose(target);assert v('selected')==channel
 p.screen.image.save('build/ui-channel-'+str(channel)+'-table.png')
# Hardware tables edit only the selected channel.
alias(13,2);choose(5);old=v('tables',0);press('right')
assert v('tables',48)==1 and v('tables',0)==old
choose(1);old=v('param',0);press('right');assert v('param',0)==old
choose(4);assert v('selected')==2
# W2 table and modulation have their own state and leave W1 untouched.
alias(14,4);choose(5);press('right');assert v('w2tables')==1
assert v('tables',48)==1
choose(2);press('right');assert v('w2tablemode')==1
choose(4);p.screen.image.save('build/ui-wave2-cc.png')
p.memory[S['_w2settings']+2]=120;p.memory[S['_w2settings']+3]=0
p.memory[S['_w2tables']]=12;p.memory[S['_w2tablelen']]=2
send([0x95,60,127]);steps=[]
for _ in range(45):
 steps.append(v('softstep',2)|(v('softstep',3)<<8));p.tick(1)
assert 523 in steps and 1047 in steps,steps
send([0x85,60,0])
# Global screens expose instrument entries, not instrument settings or LIVE.
choose(7);assert v('monomode')
items=menu_items();assert not set((0,1,2,3,4,5,6))&set(items)
assert set((11,12,13,14,15))<=set(items)
alias(12,1);assert not v('monomode') and not v('polymode')
items=menu_items();assert 4 in items and 0 not in items
alias(11,0);p.button_press('start');p.tick(30);p.screen.image.save('build/ui-channel-menu.png');p.button_release('start');p.tick(30)
p.stop(save=False)
print('PASS: direct channel entries, persistent Tone/Mod/Bank/CC/Table context, isolated W2 tables, contextual menu, no LIVE entry and Mono exit')

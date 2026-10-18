"""Enter and persist pattern names using the real on-screen keyboard."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from collections import deque
mx=S['_mx']
def key(target):
 start=p.memory[mx+4];todo=deque([(start,[]) ]);seen={start}
 while todo:
  at,path=todo.popleft()
  if at==target:
   for k in path:press(k)
   press('a');return
  row,col=divmod(at,6) if at<36 else (6,at-36)
  for k in ('left','right','up','down'):
   r,c=row,col
   if k=='left':c=(c-1)%(4 if r==6 else 6)
   if k=='right':c=(c+1)%(4 if r==6 else 6)
   if k=='up':r=(r-1)%7;c=min(c,3) if r==6 else c
   if k=='down':r=(r+1)%7;c=min(c,3) if r==6 else c
   nxt=36+c if r==6 else r*6+c
   if nxt not in seen:seen.add(nxt);todo.append((nxt,path+[k]))
 raise AssertionError(target)
def saved():
 p.memory[0x4000]=1
 try:return bytes(p.memory[0xa001:0xa012]).split(b'\0')[0]
 finally:p.memory[0x4000]=0
try:
 choose(20);press('a');assert v('page')==20 and p.memory[mx+7]
 key(38) # Clear an existing name.
 for k in (0,1,35,36,2):key(k)
 press('b');key(3)
 p.tick(12);p.screen.image.save('build/ui-name-keyboard.png')
 key(39);assert v('page')==18 and saved()==b'AB9 D',saved()
 # Entering the screen again retains the name; B edits rather than saves.
 choose(20);press('a');press('b');assert v('page')==20
 key(38)
 for _ in range(17):key(0)
 assert p.memory[mx+8]==16
 key(39);assert saved()==b'A'*16,saved()
 # SELECT returns to the destination picker without committing the edit.
 choose(20);press('a');key(38);press('select')
 assert v('page')==20 and not p.memory[mx+7] and saved()==b'A'*16
 print('PASS: D-pad keyboard, letters, numbers, spaces, delete, clear, 16-character bound, save and back')
finally:p.stop(save=False)

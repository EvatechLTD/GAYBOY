"""Native screenshots of the current ROM, with DEMO SONG loaded via real input."""
from pathlib import Path
from io import BytesIO
import hashlib,json,shutil
from pyboy import PyBoy
from boot_helpers import enter_app
from sameboy_palette import website_palette

ROOT=Path(__file__).resolve().parents[1]
rom=ROOT/'build/GAYBOY.gb'
symbols={l.split()[1]:int(l.split()[2],16) for l in rom.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
palette=website_palette()
colors=[((c&255)<<16)|(c&0xff00)|((c>>16)&255) for c in palette]
p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)),color_palette=colors)
p.set_emulation_speed(0)
out=ROOT/'build/current-site-captures';out.mkdir(exist_ok=True)
def value(name):return p.memory[symbols['_'+name]]
def press(key):
    mask={'down':8,'a':16}[key];p.button_press(key)
    for _ in range(600):
        p.tick(1)
        if value('lastpad')&mask:break
    assert value('lastpad')&mask
    p.button_release(key)
    for _ in range(600):
        p.tick(1)
        if not value('lastpad')&mask:break
    p.tick(8)
def choose(target):
    p.button_press('start')
    for _ in range(600):
        p.tick(1)
        if value('navopen'):break
    assert value('navopen')
    for _ in range(32):
        if value('navchoice')==target:break
        press('down')
    assert value('navchoice')==target
    p.button_release('start')
    for _ in range(600):
        p.tick(1)
        if value('page')==target and not value('navopen') and not(value('lastpad')&128):break
    assert value('page')==target
    p.tick(30)
try:
    for _ in range(2400):
        p.tick(1)
        ticks=value('intro_scene_ticks')|(p.memory[symbols['_intro_scene_ticks']+1]<<8)
        if value('intro_audio_scene')==2 and ticks>>2>=300:break
    assert value('intro_audio_scene')==2
    p.screen.image.save(out/'train.png')
    enter_app(p,symbols);choose(24);press('a')
    for _ in range(1800):
        p.tick(1)
        if value('page')==18 and value('sparse_song')==0:break
    song=bytes(p.memory[symbols['_sparse_song_name']:symbols['_sparse_song_name']+17]).split(b'\0')[0].decode()
    assert song=='DEMO SONG',song
    p.tick(45);press('a');assert value('seqplaying');p.tick(30);p.screen.image.save(out/'mixer.png')
    choose(8);p.tick(30);p.screen.image.save(out/'sequencer.png')
finally:p.stop(save=False)
report={'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'song':song,'palette':[hex(c) for c in palette],'resolution':[160,144],'capture':'Unmodified ROM; actual joypad navigation'}
for root in [ROOT/'website/images',ROOT/'network/apps/gayboy/images']:
    for name in ['train.png','mixer.png','sequencer.png']:
        target=root/name;old=target.read_bytes()
        backup=ROOT/'build/image-backups'/hashlib.sha256(old).hexdigest()/name
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(old)
        shutil.copyfile(out/name,target)
(out/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))

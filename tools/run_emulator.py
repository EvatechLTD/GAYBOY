"""Project PyBoy launcher: arrows, X/Z, Space=Select, Shift=Start, F5=restart."""
from pathlib import Path
import argparse
import sys
import sdl2
import pyboy.plugins.window_sdl2 as window
from pyboy.utils import WindowEvent
from pyboy import PyBoy
from demo_style import DMG_PALETTE

def configure_keys():
 for key in (sdl2.SDLK_a,sdl2.SDLK_s):
  window.KEY_DOWN.pop(key,None);window.KEY_UP.pop(key,None)
 window.KEY_DOWN[sdl2.SDLK_x]=WindowEvent.PRESS_BUTTON_A
 window.KEY_UP[sdl2.SDLK_x]=WindowEvent.RELEASE_BUTTON_A
 window.KEY_DOWN[sdl2.SDLK_z]=WindowEvent.PRESS_BUTTON_B
 window.KEY_UP[sdl2.SDLK_z]=WindowEvent.RELEASE_BUTTON_B
 window.KEY_DOWN[sdl2.SDLK_SPACE]=WindowEvent.PRESS_BUTTON_SELECT
 window.KEY_UP[sdl2.SDLK_SPACE]=WindowEvent.RELEASE_BUTTON_SELECT
 for key in (sdl2.SDLK_LSHIFT,sdl2.SDLK_RSHIFT):
  window.KEY_DOWN[key]=WindowEvent.PRESS_BUTTON_START
  window.KEY_UP[key]=WindowEvent.RELEASE_BUTTON_START

def run(rom, **options):
 options.setdefault('color_palette', DMG_PALETTE)
 restart = [False]
 @sdl2.SDL_EventFilter
 def watch(_userdata, event):
  if event.contents.type == sdl2.SDL_KEYDOWN and event.contents.key.keysym.sym == sdl2.SDLK_F5:
   restart[0] = True
  return 1
 while True:
  restart[0] = False
  emulator = PyBoy(rom, **options)
  sdl2.SDL_AddEventWatch(watch, None)
  try:
   while emulator.tick():
    if restart[0]: break
  finally:
   sdl2.SDL_DelEventWatch(watch, None)
   emulator.stop(save=True)
  if not restart[0]: break

if __name__=='__main__':
 configure_keys()
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('rom',nargs='?',default=str(Path(__file__).resolve().parents[1]/'build'/'GAYBOY.gb'))
 parser.add_argument('--scale',type=int,default=4)
 parser.add_argument('--sound-volume',type=int,default=70)
 parser.add_argument('--window',default='SDL2')
 parser.add_argument('--dmg',action='store_true')
 args=parser.parse_args()
 run(args.rom,window=args.window,scale=args.scale,sound_volume=args.sound_volume,cgb=False)

"""Retained sequencer tiles: only changed note/velocity pixels are uploaded."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
import random


def put(name, i, x): fixture_put(p,S,name,i,x)

def settle(): p.tick(90)

def background():
    # Decode hardware background pixels directly, excluding cursor/playhead
    # sprites so an edit can be compared with a complete render of the same data.
    out = np.zeros((144, 160), dtype=np.uint8)
    unsigned = bool(p.memory[0xff40] & 16)
    for row in range(18):
        for col in range(20):
            tile = p.memory[0x9800 + row * 32 + col]
            address = 0x8000 + tile * 16 if unsigned else 0x9000 + (tile if tile < 128 else tile - 256) * 16
            for y in range(8):
                lo, hi = p.memory[address + y * 2], p.memory[address + y * 2 + 1]
                for x in range(8):
                    out[row * 8 + y, col * 8 + x] = ((lo >> (7-x)) & 1) | (((hi >> (7-x)) & 1) << 1)
    return out

def invalidate(full=False):
    if full: put('seqviewtrack', 0, 255)
    put('seqdrawvalid', 0, 0); put('dirty', 0, 1); settle()

choose(8); settle()
uploads=[]
a=S['_ui_upload_tile'];p.hook_register(a>>16,a&65535,lambda _:uploads.append(p.frame_count),None)
base=background(); uploads.clear()
press('b'); settle()
assert v('seqnotes') == 61
note=background(); inserted=len(uploads)
assert 0 < inserted <= 12, ('note tile uploads', inserted)
assert np.array_equal(base[8:96],note[8:96]), 'Unrelated piano/grid rows changed'
# Rendering the exact same pattern afresh must give identical pixel output.
invalidate(True); assert np.array_equal(note, background())
uploads.clear(); press('b'); settle()
assert not v('seqnotes')
assert np.array_equal(base,background()), 'Deleting a note left stale pixels'
assert len(uploads) == 0, ('cached blank tiles were uploaded again',len(uploads))
# A velocity edit must leave every pixel of the note grid untouched.
press('b');settle();before=background();uploads.clear()
put('seqvelocity',0,20);invalidate();after=background()
velocity=len(uploads)
assert np.array_equal(before[8:120],after[8:120]), 'Velocity edit touched note grid'
assert not np.array_equal(before[120:],after[120:]), 'Velocity slider did not change'
assert 0 < velocity <= 6, ('velocity tile uploads',velocity)
invalidate(True);assert np.array_equal(after,background())
# Exercise cache eviction and moved/extended notes, checking every retained
# result against a full reference render, including neighboring body edges.
rng=random.Random(812)
for iteration in range(24):
    step=rng.randrange(16)
    put('seqnotes',step,0 if iteration%5==0 else 59+rng.randrange(13))
    put('seqduration',step,1+rng.randrange(4));put('seqvelocity',step,1+rng.randrange(127))
    invalidate();retained=background()
    assert not v('seqtileoverflow'),('retained cache overflow',iteration,v('seqtilecount'))
    invalidate(True)
    assert np.array_equal(retained,background()), ('Retained/full mismatch',iteration)
# Repeated edits without forcing a full rebuild must recycle unused tiles.
for iteration in range(100):
    step=rng.randrange(16);put('seqnotes',step,59+rng.randrange(13));put('seqvelocity',step,1+rng.randrange(127))
    invalidate()
    assert not v('seqtileoverflow'), ('eviction overflow',iteration,v('seqtilecount'))
retained=background();invalidate(True);assert np.array_equal(retained,background())
p.stop(save=False)
print('PASS: immutable retained tiles, row-only note edits, velocity-only edits, deletion, safe cache eviction; inserted/velocity uploads',inserted,velocity)

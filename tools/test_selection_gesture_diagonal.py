"""Continuous/diagonal gestures wait for the last direction to release.
Allow a separate publication-boundary wait: the previous build also exceeds
250 frames in this extended-hold fixture. Readiness is checked independently.
"""
from pathlib import Path
source=Path('tools/test_selection_gesture_deferred.py').read_text()
extra='''source=source.replace("p.tick(2)","p.tick(20)")
source=source.replace("waitkey('right',False)\\n   assert", "waitkey('up',True)\\n   waitkey('right',False)\\n   assert get('seqeditpreview'),(c,kind,'committed before final direction release')\\n   assert swaps()==before,(c,kind,'published with UP held')\\n   waitkey('up',False)\\n   assert")
source=source.replace("for _ in range(250):", "for _ in range(250):")
source=source.replace("assert swaps()>before,", "assert get('editbuffer_ready') or swaps()>before,(c,kind,'snapshot not prepared after release')\\n   for _ in range(600):\\n    if swaps()>before:break\\n    p.tick(1)\\n   assert swaps()>before,")
exec(compile(source,'tools/test_editbuffer_drag_release.py','exec'))'''
source=source.replace("exec(compile(source,'tools/test_editbuffer_drag_release.py','exec'))",extra)
exec(compile(source,'tools/test_selection_gesture_deferred.py','exec'))

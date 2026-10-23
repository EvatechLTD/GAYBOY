"""Attribute real group tap gestures, counting nested interrupt time separately."""
from pathlib import Path
profile=Path('tools/audit_prep_work.py').read_text().split('class Profile:',1)[1].split("source=Path('tools/test_editbuffer_timing.py')",1)[0]
profile='class Profile:'+profile
start=profile.index('  # Count actual table-rebuild')
end=profile.index(' def rebuilt',start)
profile=profile[:start]+profile[end:]
profile=profile.replace("'native_edit_flush')", "'native_edit_flush','eval_seq_group_move','eval_seq_group_resize','seq_event_count','seq_event_get','seq_event_put','seq_group_contains','native_edit_mark','roll_preview_finish','seq_note_get','seq_pixels')")
exec(profile)
source=Path('tools/test_editbuffer_timing.py').read_text()
source=source.replace(' fixture=BytesIO();p.save_state(fixture)',' profiler=Profile()\n fixture=BytesIO();p.save_state(fixture)',1)
source=source.replace('  start_count=event_total();','  profiler.begin()\n  start_count=event_total();',1)
source=source.replace('  intervals=[','  profile=profiler.end()\n  intervals=[',1)
source=source.replace('  if rolling_before:',"  reports[phase]['profile']=profile\n  if rolling_before:",1)
exec(compile(source,'tools/test_editbuffer_timing.py','exec'))

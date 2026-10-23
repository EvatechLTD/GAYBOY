"""One-bar released Wave edits publish promptly and sound by the next occurrence."""
from pathlib import Path
s=Path('tools/test_wave_edit_latency_matrix.py').read_text()
s=s.replace("exec(compile(s,'tools/test_wave_edit_audible_latency.py','exec'))", "s=s.replace(\"assert 'changed_attack_ms' in times,(phase,times)\",\"assert 'changed_attack_ms' in times,(phase,times)\\n  assert times['published_ms']<500,(target,phase,'publication exceeded500ms',times)\\n  assert times['changed_attack_ms']<2250,(target,phase,'missed an extra one-bar loop',times)\")\nexec(compile(s,'tools/test_wave_edit_audible_latency.py','exec'))")
exec(compile(s,'tools/test_wave_edit_latency_matrix.py','exec'))

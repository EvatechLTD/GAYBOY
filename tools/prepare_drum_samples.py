"""Antialias the existing mastered drum chops to LSDj's recommended kit rate.

Keep the 22,050 Hz masters unchanged. Compression/normalization have already
been applied by LSBATCH; do not apply them a second time here.
"""
from pathlib import Path
import shutil
import subprocess
import wave

root = Path(__file__).resolve().parents[1]
source = root / 'BREAKS/AMEN172chop/processed'
destination = source.parent / 'processed-lsdj'
rate = 11468
ffmpeg = shutil.which('ffmpeg')
if not ffmpeg:
    raise SystemExit('ffmpeg is required to prepare the drum samples')
destination.mkdir(exist_ok=True)
for path in sorted(source.glob('*.wav')):
    output = destination / path.name
    subprocess.run([
        ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(path),
        '-af', f'aresample={rate}:filter_size=64:cutoff=0.95',
        '-ar', str(rate), '-ac', '1', '-c:a', 'pcm_s16le', str(output),
    ], check=True)
    with wave.open(str(path), 'rb') as before, wave.open(str(output), 'rb') as after:
        assert after.getframerate() == rate
        assert after.getnchannels() == 1 and after.getsampwidth() == 2
        assert abs(before.getnframes() / before.getframerate()
                   - after.getnframes() / rate) <= 1 / rate
        print(f'{path.name}: {before.getnframes()} -> {after.getnframes()} samples, {rate} Hz')

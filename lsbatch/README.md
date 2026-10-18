# Drum preparation

LSBATCH now outputs mono, 16-bit **11,468 Hz** WAVs, using a 5 kHz low-pass,
antialiased resampling, and final peak normalization to -1 dBFS. The existing
compression, high-pass and soft clipping remain part of the mastering chain.
The installed right-click script at `C:/Scripts/lsbatch.ps1` was updated after
verifying it matched the workspace's previous version; its backup is alongside it.

For this ROM's existing kit, the mastered 22,050 Hz WAVs remain untouched in
`BREAKS/AMEN172chop/processed`. Run:

```powershell
python tools/prepare_drum_samples.py
./build.ps1
```

The first command performs antialiased resampling into `processed-lsdj`, without
applying compression or normalization again. Duration differences stay below one
output sample. The ROM generator reads these prepared WAVs and quantizes them to
packed 4-bit samples. Hardware playback is 11,459.846995 Hz, 0.071% below the
prepared file rate, with 11,712 CPU cycles available for each 32-sample block.

Reference: [LSDPatcher sample preparation](https://www.littlesounddj.com/lsd/latest/lsd-patcher/documentation.html).

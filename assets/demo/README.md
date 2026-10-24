KILLING demo project: five completed patterns and nine arrangement clips.

This sanitized 32 KiB GSR1 source includes only the resident patterns/song, user kits, presets and global root. Renderer/audio scratch and editing clipboards are zeroed. The ROM installer only seeds a blank battery and never replaces an existing GSR1 project.

Rebuild the published demo with:

```powershell
python tools/build_rom.py --demo-seed assets/demo/KILLING.srm
```

Project model: five working pads and one arrangement per SRM. Reuse the existing external project tool for cross-project pattern management. No on-cartridge pattern/song archive or 128 KiB requirement.

Original user source SHA256: 49f36b747e14bd6b6f7433984767c3f0781eb90fdc4ab77806ef57869bf4ac28

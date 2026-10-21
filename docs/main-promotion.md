# Main promotion ? 2026-10-21

The tested stripped implementation is now the main ROM baseline. Website work
was committed independently, then merged with the ROM branch without conflicts.
The promotion does not deploy or modify the running website.

## Archived references

- Previous experimental main: `experimental/archived-main-2026-10-21`
- Previous-main tag: `experimental-main-2026-10-21`
- Retired stripped branch: `archive/stripped-2026-10-21`
- Retired local worktree: `archived/stripped`
- Local snapshots and tested ROM reference: `archived/promotion-2026-10-21`
- Stripped local-file stash: `0849646003e673a4d47b7b715256883f9325d0e9`

The snapshots preserve tracked modifications and untracked files from both
worktrees, including the two distinct mixer-proposal drafts. They are local
archives, excluded from Git; unrelated main-folder work remains untouched.

## Reproduce the promoted ROM

Run `./build.ps1` from the main folder. It compiles the committed generated
assets and checks the cartridge layout without regenerating experimental data.
The complete regression suite remains available as `./build-stripped.ps1`.

Tested ROM SHA-256:
`c879747148ae66000ed902507f44d6e7ff3c7a09005b067fc8123d3f85cd7684`

A clean main-folder rebuild matched this hash byte for byte. Main-folder smoke
checks passed for PCM/Wave handoff, Theory, viewport snapping and partial UI
rendering. The retired worktree is Git-clean and was moved using Git worktree
management, preserving its metadata and historical build outputs.

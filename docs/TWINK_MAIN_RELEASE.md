# Live-link and TWINK song promotion

The user approved merging TWINK_SONG into main and updating the web emulator
and download after hardware testing. Merge commit: a46e3ea.

Main rebuilds to the exact hardware-tested ROM SHA-256:
`adf25cd8612d51cbc12b15e040f9c37edb5a2aaad4d5e3c819493d8a1c65f98e`.
There are no additional audio changes in the integration/release. Main's root
GAYBOY.gb, both web packages and their symbol manifests use that image. Version
remains stable 1.0. The unchanged Monosimp receiver is main 0a512be, SHA-256
`de079e296852a5cf7c2b6bb047cd6a9a46999c53f8ed372cf0c9e31f01440012`.

## Verification and limits

- ROM-bank, fixed-ROM, WRAM, stack-window, cartridge and checksum checks pass.
- Merged-main TWINK song stress passes at240 BPM with local1/32 ARP, active
  pitch LFO and an eight-note MS chord; source/pitch counts match the reference,
  with no underruns or wire faults.
- Both-machine linked Smooth start/stop passes with blank screens and no
  prepared-song underruns.
- Live linked functional checks confirm master panic stops and disarms the
  slave, with no receive overflow, queue underrun, abort or unarmed edge.
- Local browser verification checks normal/download ROM hashes, the separate
  tutorial cartridge, lesson entry/exit, preservation of normal-machine SRAM
  and execution time, and zero browser errors. The offline shared-beat stub now
  matches cache-busting script URLs; the production PHP shelf is not stubbed.

Do not call every strict live-link timing case passing. Additional linked-ARP
fixtures at120 BPM and137 BPM/+1000ppm exceed the old1.3ms per-device grid gate.
The137 BPM report is numerically identical on merged main and the frozen
hardware-test image. This is a pre-existing stress limit, not a merge change;
it is preserved for follow-up rather than hidden or fixed in an untested ROM.
Functional panic checks are separate measurement-only runs and are not proof
that this stricter timing gate passed.

Reports and failed traces are preserved under
`build/release-twink-song-20261026/`. Historical chord/sparse reports and the
full song test matrix remain indexed in TWINK_SONG_TEST_EVIDENCE.md.

## Publication scope

Use package_web_rom.py and publish_web_rom.py. They preserve all existing
shared-beat ROM versions, the live player shell, browser save keys and the
separate practice cartridge. Publish only the GAYBOY application assets and
download aliases on Y2KCRISIS, with remote backups and public hash verification.
Main's unrelated uncommitted launcher/palette/share work remains unchanged;
its exact premerge patch was retained and compared after integration.

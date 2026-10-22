GAYBOY retro homepage

Live destination: https://buttholechopper.com/gayboy/
Remote mount: /home/centered/buttholechopper.com/gayboy

Buildless HTML/CSS/JavaScript. No external assets or dependencies.
The parent site's existing HTTPS redirect and security headers apply.
All scripts and styles are separate files to respect its content security policy.

Publish from the GAYBOY repository:
G:\DEVELOPMENT\VIBECHOPPER\.venv\Scripts\python.exe tools\publish_website.py

The publisher reuses the sibling VIBECHOPPER encrypted connection helper.
It never copies or prints credentials. It checks mount ownership, backs up
existing files beneath build/website-publish/, uploads assets before index.html,
and verifies every deployed file over public HTTPS against its SHA256 hash.
It only publishes the explicit file list, not this README or project files.

Download and browser play use the October 18, 2026 build/GAYBOY.gb,
published as downloads/GAYBOY.gb (with the older filenames kept as aliases). To update it, validate the new ROM with
tools/check_rom.py, copy it to the website download path, update SHA256SUMS.txt,
and adjust the page's date/version/size if needed before publishing.
Never upload .sav files or cartridge RAM backups.

Screenshots are original captures, copied without visual modification:
train.png: screenshots/GAYBOY-2026.10.17-15.00.56.png
turntable.png: screenshots/GAYBOY-2026.10.17-14.36.45.png
drum-machine.png: screenshots/GAYBOY-2026.10.17-15.25.08.png
sequencer.png: build/ui-sequencer.png
mixer.png: build/ui-mixer.png

Local QA: Chrome desktop/mobile at 1440, 768, 390, 320px; loaded images,
no horizontal overflow, no console errors, motion toggle, and ROM download.

Live demo (added October 17, 2026):
Self-hosted SameBoy 1.0.4 WebAssembly core, built from official unpatched sources
with the same DMG model and accurate high-pass mode as the local listening app.
Expat/MIT license and provenance are under emulator/SAMEBOY-*.
Build instructions and adapter: tools/build_browser_sameboy.py and
tools/browser_sameboy.c. The checkout-local SDK/source live in build/web-audio/.
Only sameboy.js, sameboy.wasm, player.js, player.css and attribution files are
published. Prior binjgb files remain local for the comparative PCM regression.
Custom player loads the core and ROM after Power On. No external service.
The /gayboy/.htaccess permits wasm-unsafe-eval for WebAssembly compilation;
ordinary JavaScript eval and inline scripts remain disallowed.

Keyboard: arrows = D-pad, Z = B, X = A, Shift = Start, Space = Select.
Escape pauses. Touch uses independent pointer capture for multi-button holds,
with minimum 100ms input duration so very quick taps reach the ROM's input poll.
Small screens automatically expand to the handheld UI; Back to page exits it.
Portrait and landscape layouts are supported. No browser fullscreen API needed.
Leaving the window/tab pauses audio and emulation and releases held buttons.
Saved cartridge SRAM is namespaced in localStorage for this ROM snapshot.
Pattern saving must be performed in-game; unsaved edits are not a save state.
The download-save action exports 32 KiB cartridge RAM; storage failures are
handled without stopping the demo.

The initial checksum-valid ROM snapshot failed to boot in binjgb and PyBoy.
It was replaced with the boot-tested current build, SHA256:
73d49395dc63e68c60db0bcc28aef87a18feb900e68cb386bdcea8a7e7efa2ab

Verify served local or live site:
G:\DEVELOPMENT\VIBECHOPPER\.venv\Scripts\python.exe tools\verify_browser_demo.py URL
This drives the real core, ROM pixels and audio, all eight keyboard controls,
pause/resume/restart/mute, save download and mobile multi-touch B+Left.
It checks phone, tablet and landscape widths. Phone testing uses Chrome touch
emulation; physical iOS/Android device testing remains separate.

PCM and focus fix (October 17, 2026):
The binjgb core generated a strong ~358 Hz refresh carrier with a constant
0x88 PCM waveform. In an identical timed-register probe, SameBoy reduced
constant-value noise RMS from 0.02361 to 0.001936 (21.72 dB) and preserved
real ROM sample output. See tools/measure_browser_pcm.py and generated
build/web-audio/measurements/ WAVs/report.json for the comparison.

The player consumes SameBoy's signed 16-bit stereo output, retains its native
hardware DAC/high-pass modeling, and paces emulation against the sound-device
clock with a short lookahead buffer. It does not apply binjgb's unsigned-sample
conversion or the previous additional browser high-pass filter.
tools/verify_browser_pcm.py drives the real ROM UI to enter the drum roll,
add samples and run transport, captures audio, and checks continuous buffer
scheduling, non-silent/unclipped output, real-time speed and the PCM frequency.
The same test verifies that focus outlines the bezel by +5px and never the canvas.

Shade and phone recovery fixes:
SameBoy's GB_palette_t stores colors black-to-white plus LCD-off color. The
adapter's white-to-black input is reversed into a persistent Player.palette;
GB_set_palette retains that pointer, so a temporary stack object is invalid.
tools/verify_browser_palette_recovery.py renders hardware shades 0,1,2,3 with
an identity BGP register and asserts exact RGBA pixel values in ascending darkness.

Screen sleep, browser page hiding and interrupted audio show a Tap to Resume
button directly on the display. Resume awaits an actually running AudioContext
before re-anchoring the sound/emulation clocks. After sleep or a stuck interrupted
context, the user's tap creates a fresh sound device while retaining the same
GB instance, sequencer and RAM. A changed device sample rate is applied to the
core's output resampler without resetting it. Failed/timed-out resume leaves
the recovery button available for retry. Tests simulate hidden-page lifecycle,
iOS-style interruption and a rejected resume, checking frozen/continuing ticks
and preserved emulator identity. Real phone lock/unlock still requires device QA.

Interactive ROM tutorial (October 17, 2026):
Play tutorial under Power On starts a separate, unmodified practice cartridge.
Instructions sit directly above the handheld in an expanded layout that fits
portrait phone screens. The molded D-pad keeps 44px hit areas and tilts with
actual directional presses; tutorial targets have no yellow outlines.

Each lesson demonstrates real joypad input, checks the resulting ROM state,
restores a full SameBoy checkpoint, and asks the learner to try it. The Next
button unlocks only after a stable ROM success result with controls released.
Open goals accept the learner's pitches, rhythm, instrument, note lengths and
mixer channels/values. The learner's pattern carries between tasks; only the
teacher's changes are rolled back. The sequence starts with plotting any note,
starting playback, adding four notes, and another instrument with two notes.
It continues through note editing, mixer navigation, mute, solo, volume and pan.

Score: 100 per lesson; practice resets cost 10, extra demonstrations cost 15,
with a 40 point floor per lesson and no speed penalty. Best score uses a separate
localStorage key. Normal emulator and SRAM stay parked intact during practice;
exit restores them. Practice RAM never overwrites the normal browser save.
Pause/visibility interruption cancels and safely restarts a demonstration.

emulator/tutorial-rom.json pins downloads/GAYBOY-tutorial.gb by SHA256 and
contains the symbol addresses used for read-only outcome checks. The player
rejects a mismatched cartridge. Build the normal ROM, run check_rom.py, then
package_browser_tutorial.py to regenerate this pair deliberately. The normal
ROM download and browser cartridge contain the same build. The publisher verifies the pair before upload.
Full checkpoint API exports are built with build_browser_sameboy.py.

QA: verify_browser_tutorial.py runs all 12 demonstrations and learner tasks
against actual WASM, with a deliberately different pattern/instrument/mixer
settings. It checks incomplete-task gating, reset/replay score, preservation of
learner notes, and restoration of the original emulator and all SRAM bytes.
The normal verify_browser_demo.py regression also covers the redesigned D-pad.

Both the normal web player and tutorial use the pinned browser cartridge at
downloads/GAYBOY-tutorial.gb, so learned controls match normal web play. The
standalone 0.3 download is an alias of the current build. The new web cartridge has
a separate SRAM key and imports the previous key when empty; the old browser
save is retained as a backup. Lesson practice never writes to either key.
Tutorial observations use side-effect-free RAM access, bypassing DMA bus
contention and reading known SRAM symbols from bank zero. Demonstrations wait
for the ROM's lastpad acknowledgement for both edges of every scripted tap.
verify_browser_tutorial_layout.py checks the instructions above the handheld,
visible portrait controls down to 320x667, desktop/tablet/landscape layout,
44px D-pad targets, actual directional tilt, replay, and interrupted demos.


Myspace-style visitor comments:
Public UI: comments/style.css, wall.js, default-avatar.svg; API: comments/api.php.
PHP 8.3 + SQLite3 + GD + mbstring required; verified on the hosting account.
Private application/data: /home/centered/gayboy-comments-private, outside web roots.
The publisher installs hosting/comments/app.php, admin.php and audio clips there,
with directory mode 0700 and file mode 0600. It creates a private 32-byte HMAC
key once, preserves it and all data across deployments, and takes SQLite backup
snapshots before subsequent deployments. The database, key, session files and
uploaded thumbnails are never copied into the public document root.

Thumbnail images are stored as 128px re-encoded PNG BLOBs inside SQLite and
served by numeric comment ID. Source uploads never become executable files.
Accept JPEG/PNG/WebP <=2 MiB, <=2048px each dimension; crop, orient and remove
metadata. Text is rendered with DOM textContent; no visitor HTML or link markup.
The API only returns public comment fields. Lists paginate 20 per request.

Human check: six randomly generated digits in a noisy image, with spoken audio
alternative. Challenge is session-bound, one-use, expires after 20 minutes,
and has a minimum form age. Strict/HttpOnly/Secure session cookie, CSRF + Origin
checks, honeypot, request/post throttles, duplicate checks and bounded content.
Rate keys use HMAC-hashed peer addresses; raw IPs are not stored in the database.
Human-check audio digits were generated locally with Windows speech synthesis.
No external CAPTCHA account, analytics or tracking service is used.

Own-comment deletion uses a random capability kept in the posting browser;
only its hash is stored on the server. Owner moderation runs privately over SSH:
G:/DEVELOPMENT/VIBECHOPPER/.venv/Scripts/python.exe tools/moderate_comments.py list
G:/DEVELOPMENT/VIBECHOPPER/.venv/Scripts/python.exe tools/moderate_comments.py delete ID
There is no public admin route. Normal wall comments appear immediately.

Local QA: tools/verify_comments.py against checkout-local PHP 8.3.35 and isolated
build/comments-private storage. It covers valid posting/deletion/reload,
CSRF and challenge failures/replay, honeypot, request throttling, upload format
and dimension checks, metadata removal, escaped text/XSS, visual/audio checks
and desktop/tablet/phone widths. Tests do not post anything on the live wall.
Local development only: set GAYBOY_COMMENTS_HOME to isolated storage containing
app.php, audio/ and a fresh secret.bin; set GAYBOY_COMMENTS_LOCAL_TEST=1 and use
PHP's localhost development server. The local cookie exception applies only to
cli-server + loopback. Production ignores that exception.

October 18, 2026 ROM update:
Both sites now use build/GAYBOY.gb for normal play, tutorial practice and all
current download aliases. downloads/GAYBOY.gb is the canonical download.
Run check_rom.py then package_web_rom.py to copy a validated build and its
matching symbols into both packages. rom-versions.json retains the original
cartridge/symbol map for shared beats; archived ROMs are used only for those
versioned snapshots. New saves use a separate browser key and retain old keys.

October 19, 2026: legacy /gayboy/ redirects to https://y2kcrisis.com/gayboy.
Legacy asset links redirect to /apps/gayboy/ on Y2KCRISIS. Browser cartridges
now live under emulator/roms/; downloads/GAYBOY.gb is for explicit downloads.
Count those URL namespaces separately; cached older players may still use old URLs.

October 21, 2026 MOD/NEWGEN update:
Normal play and the canonical download now use the current main ROM, including
the GEN cursor fix and gated-PCM restart fix. Package with package_web_rom.py;
publish this narrow update with the VIBECHOPPER Python interpreter running
tools/publish_web_rom.py. This targets the live Y2KCRISIS app, not the retired
standalone mount, and backs up/rechecks changed files before HTTPS verification.
The older publish_website.py is for the retired standalone package.

emulator/tutorial-rom.json continues to identify the normal-play ROM and symbol
map used for beat capture/server validation. emulator/practice-rom.json separately
pins the existing lesson-compatible cartridge: main's resident event storage no
longer has the lesson reader's old seqevents_lo/hi layout. The player loads that
practice map only for lessons. Archived ROMs/maps remain available for shared
beats. Old browser-save keys remain recoverable; current main uses a separate
save key rather than loading the old storage format automatically.

Release QA: verify_browser_demo.py passed desktop/mobile controls, audio, render,
pause/restart, save export and multitouch. verify_web_rom_release.py checks the
current ROM/download hashes, the pinned practice ROM, first-lesson startup and
preservation of the paused normal machine and every SRAM byte on tutorial exit.
The full older tutorial suite reached lesson 8, then failed its lesson-9 mute
demonstration on the retained legacy cartridge; a full twelve-lesson pass is not
claimed for this update.

October 22, 2026 smooth pattern launches and DJ retriggers:
The released main cartridge buffers incoming pad metadata, instruments and
first notes before quantized launches. Matching instruments retain their runtime;
matching held wave notes preserve oscillator continuity across pad switches.
Hold A on a pad to repeat launches. While holding A, Up selects faster repeats
and Down selects slower repeats. Launch quantization extends through 1/32.
Normal-play browser ROM and both main downloads have SHA256:
f3ff8d7fee1864c3d430b6993d568b91a452dbf808b32c964cc4d85fd6de65ce
Tutorial lessons retain the separate compatible practice cartridge. Existing
shared-beat cartridges remain pinned to their original symbol maps.

The same cartridge is designated stable 1.0 (Git tag v1.0). VERSION controls
package labels; GAYBOY-1.0.gb is the versioned stable download. Browser save
keys remain unchanged so this release retains existing resident-format saves.

Held-pad slide update: A+Left/Right launches the adjacent pattern while A stays
held, retaining the current launch interval. Arp/LFO tempo divisions and the
launch header use Up/Right for faster and Down/Left for slower. Same-pad repeats
reuse unchanged pad graphics. See briefspatternlaunch.md for the launch design.

# GAYBOY 0.3

## Boot intro

After the system boot logo/chime, a boot-only cinematic follows a scene-girl
beatmaker with choppy hair, eyeliner, headphones and striped sleeves. The first
shot faces the camera, with her centerline on the right third, shoulders filling
the right edge, a window on the left, and a turntable across the foreground.

Four native four-shade pixel shots cover record sampling, a finger-free MPC
close-up, a train ride, and a handheld that has come alive. The turntable cuts
after its first three expressions (neutral, curious, interested smile) to the MPC;
only the fourth expression is omitted. MPC pads follow the score step counter;
its scope uses prebuilt animation frames with no audio analysis.
On the train, she sits bored with her hands in her lap and a backpack on the
seat beside her. The backpack shakes, then the Game Boy jumps out in an arc.
She reacts in shock and catches it, turning its front and BMO screen toward us. The carriage sways and the window has
two-speed parallax. A large vertical WERO handstyle tag with drips fills the right wall.
The rounded, rectangular Game Boy has a plain white back, a lighter side
and a darker bottom, lit from the upper left. A close-up reveals BMO inside
its screen, then an 18-step camera zoom expands that face to fill the display.
Four stars twinkle independently around the living Game Boy.
Alternating tile buffers keep the image visible throughout the zoom.

One compact caption appears at a time: "a processor running", then
"is like an animal breathing". The four-bar train scene shows "time is an
illusion..." in its first half, then the complete "that helps things make sense"
all at once in its second half. The living Game Boy close-up is caption-free.
After the face zoom, a striped C64-style GAYBOY block logo fades in above the
eyes at one second, then runs looping raster bands and a scanline wave. The bold
"press play" prompt starts fading in half a second later and pulses forever.
Visual effects continue after the soundtrack falls silent. Start skips the intro at
any point and opens the DRUM sequencer directly. Subsequent Start presses open the page menu. F5 in the emulator restarts the ROM.

Turntable, MPC and living Game Boy close-up each last two bars; the train lasts
four. Original leads repeat over two-bar harmonic reductions: C / F / Am / Am
for Basement Tape, then F / C / Bb / F C for Little Clock / Big Sky.
The turntable has melody alone at 95 BPM with 60/40 swing. MPC adds hip-hop
drums. Train switches to four-on-the-floor house drums, ramping from 95 to
128 BPM across four bars and easing swing into straight timing. The second
cue continues at 128 BPM with no tempo jump. A 256 Hz timer drives audio
separately from drawing. On the final face, each two-bar loop mutes another
channel: drums, bass, secondary melody, then lead. It stays silent afterward.
Entering the DRUM sequencer stops intro audio and restores workstation operation.

Chord references: [District](https://www.cifraclub.com/the-postal-service/the-district-sleeps-alone-tonight/zthpgs.html), [Heights](https://www.guitartabsexplorer.com/postal-service/such-great-heights-chords). Leads are original.

Build with `./build.ps1`. Cinematic assets come from `tools/make_cinema.py`,
face/prompt assets from `tools/make_intro.py`, and zoom from `tools/make_zoom.py`.
`python tools/test_intro.py` checks DMG/CGB scene lengths, timer deadlines,
melody-only opening, drum arrangement, stable captions and menu handoff.

Hardware-test build: `build/GAYBOY.gb` (512 KiB, MBC5 with battery-backed 32 KiB cartridge RAM, DMG/GBC).
Build with `./build.ps1` using the local GBDK 4.5.0 toolchain. Test with
`python tools/smoke_test.py` (requires PyBoy). Experimental table generation also requires NumPy. The software delay uses cartridge RAM; use an MBC5/RAM-capable flash cartridge or emulator.

Connect a normal Game Boy link cable to Arduinoboy and select **mGB mode**.
Default MIDI channels 1/2/3/4 address pulse 1/pulse 2/wave/noise.
Arduinoboy can remap incoming channels. Its fifth logical channel is now a
three-note poly synth on MIDI channel 5 by default. Notes, note-offs, velocity,
program change, sustain and full 14-bit pitch bend work. Direct mono channels 1?4 track up to eight held keys and restore the previous key and velocity when the newest key is released.

## Live sequencer controls

Hold Start, choose a page with Up/Down, and release Start. The menu includes individual instruments, Sequencer, Mixer, Drumsynth, Global Settings, Load and Save. Channel Tone/Mod/CC/Table/FX entries follow the selected instrument.

- **Global Settings:** Experimental Mode defaults OFF. A toggles optional DSP, macros and software synths; their pages stay hidden while off, and Tone/CC expose native controls. All ten PCM sample rows and both noise-drum rows remain available in either mode. Changing this mode stops transport.
- **Sequencer:** Select+A starts/stops; Select+Left/Right changes track; Select+Up/Down changes zoom (8/16/24/32 steps); Select alone opens settings. A plots/deletes a note; hold A and move to drag it. Hold B to change duration with Left/Right or velocity with Up/Down.
- The first PULSE1 grid view starts at C2 and PULSE2 at C3 (lowest visible pitch). Each track then retains its viewport and cursor when you leave and return.
- Move left from the first visible grid cell to select the **piano**. Up/Down selects pitches and scrolls both views at their edges; A auditions the selected note while held. Right returns to the grid. The piano cannot enter the top bar.
- At 16-step zoom, move below the bottom grid row to select the **velocity strip**. Left/Right selects a slider; A toggles editing and Up/Down changes its value. B+Up/Down edits directly. With editing off, Up returns to the grid.
- The header **V** switch beside M/S shows or hides the velocity strip (A or B toggles). At 16-step zoom, hiding it expands the piano roll from 14 to 17 pitch rows. Notes and their velocities are preserved.
- From the top grid row, Up enters the header. Further Up presses scroll one pitch row while keeping header focus; Down returns to the grid. Pulse1/2 start with flat envelopes and 100% gates, so drawn notes sustain for their full duration. Its far-right number is loop length: hold A and press Left to halve or Right to double it, within 1?64 steps. Shortening never deletes notes; inactive notes remain visible in gray.
- **Mixer:** Five vertical channel strips are visible at once; Left/Right scrolls through channels and drum voices, and Up/Down selects mute, solo, volume and pan. Play/Stop, per-track Mute/Solo, volume and pan. Scroll right past DRM for individual Mute/Solo switches on samples S01-S10 and Drumsynth noise voices N1/N2. Up/Down chooses M/S; A or B toggles it. Multiple solos combine, mute takes priority, and DRM bus controls still apply. These switches save with each pattern; older saves enable all voices. Hold A or B on volume or pan to edit (Up/Down by one, Left/Right by ten); holding Up/Down accelerates. Eight numbered pads select complete multi-track patterns. The active pad is inverted; queued changes are marked. Quantization is Off, Beat or Bar. Selecting an empty pad opens the sequencer to program it; B also opens the selected pattern for editing.
- **Save:** choose one of the eight slots, A edits its name (Up/Down changes characters, Left/Right moves, A finishes), and B saves. **Load** copies the chosen saved arrangement into the current pad. Names can contain sixteen characters; pads and the sequencer header show the first three. Notes, lengths, velocities, durations, drum data, mixer levels/pans and timing settings persist in cartridge save RAM. Instrument Tone patches remain global. Records have a checksum and bounds validation; invalid records open as empty patterns.
- **DRUM track:** TR-808 is the startup kit; the Kits page offers the other kits and Amen original. Ten samples from `breaks/AMEN172chop/processed-lsdj` are baked into the ROM; no companion WAV files are required. `tools/prepare_drum_samples.py` antialiases the preserved 22,050 Hz masters into mono 16-bit 11,468 Hz WAVs. Two sample voices mix directly as 4-bit PCM. The matching hardware clock plays about 11,459.85 samples/sec (-0.071%). The player applies no wave oscillator, pitch or envelope settings. Samples play to their ends unless a third hit steals the oldest voice. Plotting a third overlapping sample replaces the oldest plotted overlap. Sample drums take priority over WAVE1/WAVE2 while playing.
- **Performance status:** PCM buffering runs on the audio timer and uses about 43% CPU with two sample voices. Mixer rendering yields between rows, internal pulse notes avoid MIDI dispatch overhead, and prepared same-mode pattern handoffs preserve elapsed clock time. Live-control tests deliver every scheduled note with zero audio underruns and about 1.5 ms accumulated drift across three switches. Brief timing outliers remain (a 61.7 ms interval at 300 BPM, versus 50 ms ideal); strict live-timing acceptance is still failing. These are emulator cycle measurements, pending physical hardware validation.
- **Drumsynth:** two native noise patches, initially a bright closed hi-hat and a short, fuller snare, with level, clock shift, divisor, metallic character and fall rate. Select switches patches; B auditions. Their N1/N2 drum rows share the one physical noise channel. Overlapping patches blend their rounded settings; a mixed metallic switch uses the short LFSR. These patches take priority over the regular noise track.

The hardware wave output has four amplitude states and shared stereo routing. WAVE1/WAVE2 share that physical output; their pan cannot be independent. The DRUM mixer fader therefore uses native attenuation steps for PCM, while its noise hits use velocity scaling.

The sequencer clock is independent of drawing. Pitch scrolling reuses complete tile rows and renders only the newly exposed pitch row (two tile rows at 8-step zoom), preserving the velocity strip. Note edits retain unchanged VRAM tiles; velocity-only edits update the affected slider. Performance checks use a forced DMG emulator at 4,194,304 CPU cycles/sec, not host wall-clock speed. Hardware audio behavior still needs listening on the original DMG.

## Monosynth experimental effects

Hold Select and press Right from MOD to reach **EXP** (Pulse1 ? Pulse2 ? Wave ? MOD ? EXP). The existing B editing, A toggle, accelerated Up/Down and B+Left/Right ?10 controls work here. The list scrolls through 27 settings. All effects start bypassed; normal native synthesis remains the default.

| EXP setting | Meaning |
|---|---|
| ENGINE | 0 native; 1 software oscillator/filter/delay through the wave channel. The software engine mutes the hardware pulses and uses the selected wave oscillator plus an optional detuned copy. It cannot filter the analog output of native pulse channels. |
| WAVE ADSR | 0 bypass; 1 software amplitude ADSR. A/D/R times are 0-255 frames (~16.7 ms each), Sustain is 0-64. Decay happens while held; Release starts on key-up. WAVE RELEASE also appears on the Wave page; each pulse has its own Release row. |
| BRIGHTNESS / RESONANCE | 0-15 darkness-to-brightness and 0-3 resonant wavetable shapes. Tables cover all 32 waves and all 32 custom pulse widths. These are coherent filtered versions of the same waveform, not unrelated waveform changes. Cutoff is relative to note pitch. |
| FILTER MOD / SOURCE | Depth 0-15; source 0 off, 1 wave envelope, 2 MOD LFO. Use WAVE ADSR for an evolving filter envelope; the MOD page supplies LFO shape/rate. |
| PHASE DEPTH / RATE | 0-31 sample offsets; rate 0 holds a fixed offset, 1-32 moves it (~0.23-7.5 Hz). Combines shifted waveform copies for phasing-like harmonic cancellations, rather than processing the native output through an all-pass phaser. |
| DETUNE CENTS / CHORUS DEPTH / RATE | Opposite pulse offsets, and a detuned second oscillator in software mode. Detune is 0-64 cents; chorus depth 0-32 cents; rate 0-32. Native divider resolution limits very small offsets. |
| NOTE DELAY / ECHO LEVEL / REPEATS / PAN | Native mode: delay in frames (0 off), echo amount 0-15, up to 8 repeats with falling levels, pan 0 oscillator pan or 1 alternating sides. This reserves Pulse2 for echoes, uses its waveform with an independent echo level, and keeps queued echoes after key-up. Set delay, level and repeats above zero to hear it. |
| ZOMBIE ADSR | 0 off; 1 uses the experimental pulse-volume increment trick for software ADSR without ordinary volume retriggers. It uses the wave A/D/S controls and each pulse's own Release. DMG hardware behavior needs testing; emulator results are not a hardware guarantee. |
| CONTROL RATE | 0 frame clock (~60 Hz), 1 128 Hz, 2 256 Hz for native experimental modulation. The software engine uses its audio-block clock. Faster controls cost more CPU and do not remove hardware parameter quantization. |
| DSP CUTOFF / RESONANCE | Software mode only: two-pole low-pass with bounded feedback. Cutoff 0 darkest through 7 bypass; resonance 0-7. |
| AUDIO DELAY / MIX / FEEDBACK | Software mode only: actual PCM delay, 0 off or 1-64 increments of 15.625 ms (up to 1 second). Mix is 0-15, feedback 0-12 (up to 75%). Delay tails may continue after key-up; Panic clears the delay memory and queued note echoes. |
| SLEW | 0 immediate; 1-7 progressively smooths wavetable brightness movement between filter frames. |

The software engine renders signed PCM in assembly at **2,048 samples/sec**, packed into the wave channel's 4-bit output. Its bandwidth is about 1 kHz; pitches above MIDI 83 clamp to that upper usable range. This is a deliberately lo-fi alternative to the full-range native path. The filter/resonance/feedback kernel, oscillator lookup, and interpolation/amplitude tables avoid expensive sample-by-sample C math. Heavy combinations can still reach DMG CPU limits; `expblocks`/`expdrops` expose stream timing for tests. Native wave-RAM edits, panning, and non-zombie pulse volume changes can click on an original DMG.

Validation: `python tools/test_experimental.py`, `python tools/test_experimental_fx.py`, `python tools/test_note_release.py`, and the existing mono/UI/poly engine checks. They exercise actual rendered audio spectra and block timing in PyBoy; physical DMG listening remains necessary for the volume hack and wave-update artifacts.

## Screen controls

The interface uses an original tile font, inverted selection strips, meters,
waveform/timbre previews, and a live sequencer playhead. Core screens:

| Screen | What it does |
|---|---|
| LIV | Four voice activity/velocity meters, MIDI note numbers after transposition, current duty/timbre preview, modulation summary |
| TON | Voice-specific sound controls, output routing and master levels |
| MOD | Macro speed, chord, duty sequence, vibrato, slide, gate, table mode and length |
| BNK | Seven-row scrolling stock browser with current patch and suggested voice |
| CC | Full scrollable CC-to-parameter reference, wave sample indices and last received CC/value |
| TBL | Eight-step transpose, shape and stereo routing editor with playback marker |
| MONOSYNTH | Isolated channel 5 native mono: two pulses, one wave, hardware attack/decay and no wave mixing |
| SEQUENCER | Per-channel piano roll with independent 1?64 step patterns |
| NOISE LAB | Independent DSP drone/performance patch, chaos and feedback |
| FX | Wave engine selection, fast-arp divider, mixer waveforms, audio-block and underrun counters |

- **Hold Start** opens the page menu. Up/Down highlights a page; releasing Start opens it. The title shows the current page. **Select** cycles voices.
- **MONOSYNTH:** Opening this page enables an isolated channel 5 instrument: two hardware pulses and one native wavetable play in unison. The D-pad selects value cells: Up/Down moves rows, Left/Right moves through value, depth and phase. Crossing the left/right edge opens the adjacent oscillator/MOD/EXP screen at the same row (or the last row if the destination is shorter). Hold B and press Up/Down to change by 1, or Left/Right to change by 10. The cursor stays locked to that cell while B is held, including with Select. A toggles one-handed edit mode: Up/Down edits, Left/Right moves between cells and wraps to the next/previous row within the current oscillator (wrapping top/bottom). A again restores normal navigation. Holding an edit direction accelerates changes. An asterisk marks edit mode; switching oscillator/MOD/EXP pages or opening the Start menu clears the toggle. Hold Select and press Left/Right to switch oscillator/MOD/EXP screens directly. Select+A exits to poly mode.
- The black control strip identifies PULSE1, PULSE2, WAVE, MOD or EXP. The Monosynth header is a native waveform preview: pulse previews reflect their effective duty; the wave preview follows its selected bank shape/PW; MOD previews the LFO type. Graphics are cached, and a dedicated renderer replaces the title/status rows.
- Pulse controls: octave (0 to 4, with 0 unshifted), peak level (0-15), attack (0-7), decay (0-7), PW (four hardware duties), and pan (left/center/right). Attack 0 starts immediately at the peak; decay 0 holds that level until note-off. Nonzero rates use the native 64 Hz envelope clock (one volume step per selected number of ticks). A timed, single retrigger switches attack to decay, so the transition may click and its timing is approximate. A RELEASE row adds a 0-255-frame key-up fade (0 stops immediately). The ordinary pulse release changes the 16 hardware volume levels and may retrigger; the optional EXP zombie mode avoids those volume retriggers. Sustain is available through EXP software ADSR. The separate MOD envelope drives whichever parameter depths you assign.
- Wave controls: octave (0 to 4, where 0 is one octave below the input and 1 is unshifted), fixed hardware level (mute, quarter, half, full), pulse width (1-32 high samples when PULSE is selected), 32 original waveforms (sine, triangle, saw, pulse, organs, formants, metallic, folded and sync-like shapes), and pan. It has no envelope. No DDS mixer, wave streaming, or audio timer runs in mono mode.
- Mono accepts only channel 5 notes, note-offs, pitch bend, sustain pedal and panic CCs. Other MIDI channels, program changes and unrelated CCs are ignored; nothing falls through to the poly or preset handlers. Held-key priority is retained. Noise and cartridge VIN remain disconnected. Pulse velocity scales peak level; the wave uses its fixed hardware level. Final note-off cuts sound immediately unless the pedal is held or a nonzero modulation release is active.
- Each oscillator setting has a MOD depth: 0 disables it; the maximum is its count of available values (pulse duty 4, wave PW 32, waveform 32, pan 3, pulse level 16, wave level 4, octave 5, pulse attack/decay 8). The displayed base value stays unchanged; the effective value is a legal range around the base value, limited by depth, when LFO is selected. This range shifts inward at hardware limits so the complete LFO cycle stays useful rather than clipping half the waveform. In ADSR mode, the envelope adds a unipolar offset to the base value.
- The MOD screen has ARP RATE (0 off, 1-32 notes per second): two or more held channel 5 notes cycle in the order played; a single held note plays normally without arp retriggers, with all three oscillators in unison. Arp steps retrigger oscillator attack/decay while keeping the modulation clock running. Bottom tips have been removed from all screens, and the mono divider has been removed to leave room for more controls. VELOCITY is 0 for full velocity and 1 for velocity-sensitive notes; it applies on the next note and defaults to 0. MIDI note-on velocity zero remains note-off. The MOD screen contains an ADSR modulation envelope (A/D/R 0-255 frames, S 0-64), LFO wave (triangle, saw, square, sample-and-hold, sine), LFO rate (0 paused, 1-32 phase steps per frame; approximately 0.23-7.5 Hz), shared pitch-bend range (0-24 semitones, default +/-2), and LFO mode (KEY resets on each note; FREE runs continuously across notes and idle time while mono mode is active). Select the [X] ADSR checkbox with the D-pad and press A to switch sources: checked uses ADSR alone; unchecked uses LFO alone and greys out/locks the ADSR fields. B+Up/Right checks it; B+Down/Left unchecks it. LFO depth is independent of ADSR settings. Sustain 64 gives full sustained depth; sustain 0 removes sustained modulation. The default sustain is 64. Modulation preserves each pulse oscillator's elapsed attack/decay time; PW updates do not retrigger its hardware envelope, and a completed decay stays silent until a fresh trigger. Square and sample-and-hold intentionally have plateaus; sine, triangle and saw sweep the full legal range with only native parameter quantization. In ADSR mode, use base level zero and positive level depth for an amplitude envelope.
- Monosynth B+Up/Down holds (and Left/Right holds in the other value editors) repeat after about 0.3 seconds, initially every 8 frames, then every 3 frames after 1 second, and every frame after 2 seconds. Releasing, reversing direction, changing rows/columns or cycling oscillators resets acceleration. The Start menu and preset browser do not repeat edits.
- Each modulation target has its own LFO phase offset, shown as 0-359 degrees (internally quantized to 256 clock positions). ADSR remains note-triggered and is not phase-shifted. All targets share one LFO clock/rate; phase shifts apply to triangle, saw, square, sample-and-hold and sine. In the phase column, B+Down from 0 wraps to 359 and B+Up from 359 wraps to 0.
- Modulation changes discrete native register values; duty, wave selection and pan remain stepped. Live volume/envelope or wave shape changes can retrigger native channels and click. The default native path does not use DDS mixing or wave streaming; EXP ENGINE 1 enables the separate software path. B is the edit modifier on this page; audition with incoming channel-five MIDI.
- Pulse attack and decay default to zero for a constant-level hardware isolation test. These changes apply to mono mode; legacy poly and FX engines remain available after exiting it.
- **Select + A** toggles poly browser/audition mode (or returns from mono to poly) (and stops playing notes).
- **Select + Start** panics and clears the receive-overflow indicator.
- **B held** auditions C4 outside Monosynth; release stops the audition.
- **LIV and BNK:** Up/Down **instantly load** previous/next preset; Left/Right
  jump ten presets. A toggles between the live monitor and browser. Hold B while
  browsing to audition each new patch immediately.
- **TON and MOD:** Up/Down select a setting; Left/Right change it. A restores
  that setting from its stock preset. Values wrap at their limits.
- **CC:** Up/Down select an entry; Left/Right jump seven entries.
- **TBL:** Up/Down choose a step; A chooses transpose, shape or pan column;
  Left/Right edit it. Turn tables on and set their length in MOD.

An asterisk next to the patch name marks edits. Each voice retains its working
settings when switching screens/voices; loading a stock patch replaces them.
Edits are volatile: there are no save slots or battery persistence in this build.
Programs 0–99 correspond to displayed presets 001–100. CC102 uses literal 0–99.
Presets apply to the selected/MIDI voice; use the browser's suggested voice as
a starting point. Wave suits bass/bell/organ, noise suits kick/snare, and pulse
suits lead/pluck/arp/soft/zap.

The 100 stock sounds are original **game-inspired approximations**, grouped in
ten banks: Tetris, Super Mario Land, Link's Awakening, Pokemon Red/Blue, Kirby's
Dream Land, Metroid II, Mega Man, Castlevania, Wario Land, Donkey Kong Land.
These are not extracted or verified game patches. `src/presets.json` records
the generated bank; edit `tools/generate.py` to change the source definitions.
Each bank has ten roles voiced with envelopes, hardware sweep, frame macros,
and different duties/wave shapes. Names describe inspiration, not provenance.

## MIDI controls

Unless stated otherwise, CC values 0–127 scale evenly across the listed range.
Controls are per MIDI voice except hardware globals and shared wave RAM.
Unsupported hardware features on a given voice have no effect.

| CC | Parameter | Hardware range |
|---|---|---|
|41|Pulse duty|0–3 (12.5/25/50/75%)|
|42|Pulse/noise initial volume|0–15 (velocity scales it)|
|43|Envelope direction|0 down / 1 up|
|44|Envelope period|0–7|
|45|Pulse 1 sweep period|0–7|
|46|Pulse 1 sweep direction|0 up / 1 down|
|47|Pulse 1 sweep shift|0–7|
|48|Pulse/noise length load|0–63|
|49|Length enable|0/1|
|50|Voice mute|0/1|
|51|Master right level|0–7|
|52|VIN right enable|0/1|
|53|Master left level|0–7|
|54|VIN left enable|0/1|
|55|Wave shape|0–15|
|56|Wave level|0 mute / 1 full / 2 half / 3 quarter|
|57|Wave length load|0–255 (even values via 7-bit CC)|
|58|Wave DAC disable|0/1|
|59|Noise clock shift|0–15|
|60|Noise width|0 15-bit / 1 7-bit|
|61|Noise divisor|0–7|
|62|Voice routing|0 off / 1 right / 2 left / 3 both|
|63|Voice DAC disable|0/1|
|64|Standard MIDI sustain|below 64 off, otherwise on|
|65|Stop voice|64+ stops|
|66|Bend range|0–24 semitones|
|67|Raw tonal frequency low 7 bits|literal 0–127|
|68|Raw tonal frequency high 4 bits|0–15|
|69|Retrigger voice|64+ triggers|
|70–101|Wave samples 0–31|0–15 each|
|102|Load stock preset|literal 0–99|
|103|Panic|any value|
|104/105|Master right/left volume|0–7|
|106|VIN both|64+ enables|
|107|APU power|64+ on|
|108–111|Routing for voices 1–4|literal low two bits: right, left|
|112|Macro step interval|0–15 frames; 0 and 1 both one frame|
|113|Arpeggio|0 off, 1 major, 2 minor, 3 fifth/octave, 4 octave bounce|
|114|Duty sequencer|0 off, 1 cycle all, 2 square/thin, 3 thin accents|
|115|Vibrato depth|0–7 frequency-register units|
|116|Pitch slide|0 off; 1–7 down, 8 stationary, 9–16 up|
|117|Gate|0 hold, 1–63 frames|
|118|Table mode|0 off / 1 loop / 2 once / 3 advance on note|
|119|Table length|1–8 steps|
|122|Experimental wave engine|0?42 normal / 43?85 fast arp / 86?127 mixer|
|124|Fast arp clock divider|0?7; switching rate = 1024 / 2^value Hz|
|125/126|Mixer oscillator A/B shape|0 triangle / 1 saw / 2 square / 3 custom or hash|
|120/123|All sound/notes off|any value|

Live CC and pitch-wheel updates never call the note-trigger path. Duty, pan,
noise shape, wave output level, sweep registers, master level and tonal pitch
update without resetting note age, gate, arpeggio, envelope or table position.
The pitch wheel uses both MIDI data bytes; a released key held by sustain still
responds to it. CC69 remains an intentional retrigger; preset loads, panic,
DAC-off, gate and stop controls keep their explicit behavior.

On DMG, reliably changing a running hardware envelope or wave RAM requires
retriggering. To preserve the playing note, pulse/noise initial volume and
envelope direction/rate (CC42-44), wave shape (CC55), and wave samples (CC70-101)
are staged until the next note/explicit CC69. TON labels these settings LATCH
NEXT NOTE. Wave level (CC56) and master levels remain immediate volume controls.
Queued wave edits pause waveform-table replacements until the next note, so
there is no hidden wave restart while turning a knob. Explicit wave-table
shape steps still rebuild/retrigger the wave oscillator as part of that effect;
ordinary CC/wheel changes do not restart its table or note. Pulse 1 sweep has
the usual hardware constraints when changing direction or overflowing pitch.

Frame macros run at approximately 59.7 Hz. The renderer services MIDI and
audio between strings, then flushes changed tile spans in bounded batches.
Raw frequency changes are superseded by active pitch macros.

## Three-note poly patches

Send notes on MIDI channel **5** with Arduinoboy in mGB mode. The allocator
shares pulse 1, pulse 2 and wave: it uses free voices first and steals in
round-robin order once all three are occupied. Note-offs for a stolen note do
not release its replacement. Sustain releases only poly-owned notes that have
been lifted. Noise/channel 4 remains available independently.

Program Change or CC102 on channel 5 loads the patch into all three pitched
voices; channel 5 CC and bend messages control the group. Pulse-type patches
use a square waveform at full wave-channel level for their third voice.
Wave patches retain their wavetable setup. The oscillators have different
hardware envelopes, level resolution and sweep facilities, so their timbres
are related rather than identical. This is three-note polyphony, not three
additional oscillators: MIDI channels 1-3 and poly mode share that hardware.

Sending channel 5 MIDI activates the POLY 3 display/browser mode. Select+A also
toggles it locally. Up/Down in LIV/BNK loads the entire poly patch; holding B
auditions a C-major triad. Select chooses one of the three hardware voices for
TON/MOD/TBL editing, indicated by the highlighted activity dot. Local edits
still affect that selected hardware voice; channel 5 CCs affect the whole group.

## Experimental wave engines

Use **Start** to reach **FX**, select ENGINE with Up/Down, and change it with
Left/Right. Mode changes stop existing notes. NORMAL restores the original
three-note poly engine; FAST ARP and MIX 4 take exclusive ownership of wave
channel 3. Pulse channels 1/2 and noise channel 4 remain hardware voices.

| Engine | MIDI channel 3 | MIDI channel 5 |
|---|---|---|
| NORMAL | One hardware wave note | Original three-note pulse/pulse/wave polyphony |
| FAST ARP | Cycles up to eight held notes through one wave oscillator | Held-note fast arpeggiator on wave; pulses remain available on channels 1/2 |
| MIX 4 | Two independently pitched software wave voices | Four-note allocation: pulse 1, pulse 2, software wave A and software wave B |

You can also select the engine with **CC122**: 0 normal, 64 fast arp, 127 mix.
The setting is global and survives preset changes. In poly/browser mode, B
plays a four-note chord in MIX 4; release stops it. Channel 5 Program Change
and CC102 still load the shared patch. Channel 3 Program Change loads the wave
settings without changing the selected engine.

**FAST ARP:** Hold a chord on channel 3 or 5. A hardware timer cycles cached
pitches at 1024 Hz divided by 2^ARP DIV; dividers 0?7 span 1024 down to 8 pitch
changes per second. The default divider 2 gives 256 changes/second. This changes
frequency without retriggering the wave oscillator. More held notes means a
longer cycle, rather than independent simultaneous oscillators. Sustain holds
released pitches until the pedal lifts. CC124 and FX/ARP DIV change the divider.
The fast engine replaces the ordinary wave pitch/table macros while enabled.

**MIX 4:** Two 16-bit phase accumulators run independently at 8192 samples/sec.
Their gain-scaled single-cycle waveforms are summed and packed into four-bit
PCM. A short timer ISR uploads a 32-sample block 256 times/sec; two buffers keep
MIDI and screen work interruptible. Oscillator phases continue across blocks,
CC sweeps and bend changes; adding or stealing a note resets only that oscillator.
Voice stealing is round robin. Sustain, velocity, note-off and shared pitch bend
work for both software notes. Individual mixer shapes latch on each new note:
0 triangle, 1 saw, 2 square, 3 staged custom wave (or a hash shape if no custom
wave is selected). CC125 controls A and CC126 controls B. Master level, wave
output level and wave pan still apply to the combined wave output.

The stream clamps software pitch at MIDI note 107 (B7), below its Nyquist limit.
The two mixed notes share wave-channel pan and output level. Wave envelopes,
tables, hardware length and vibrato/slide are not applied to the software
oscillators in this prototype; velocity, software gate and pitch bend are.
Pulse voices retain their usual macros. The mixer prioritizes audio and MIDI. Control-rate macros coalesce overdue
frame updates under load while gates retain elapsed-frame ages; the screen
refresh can be slower. Pitch-wheel messages for the software voices are
coalesced at audio-block production, preserving oscillator phases. FX/DROP counts missing PCM blocks; BLOCK counts
successful uploads (both counters wrap at 65536).

This is intentionally experimental 4-bit block streaming. On DMG the upload
briefly disables/restarts the physical wave playback for safe RAM access;
software oscillator phases and note state remain continuous. Expect quantization,
block-boundary coloration and model-dependent artifacts. This is separate from
retriggering a musical note or restarting its envelope. Real Arduinoboy timing
and the quality of DMG/CGB output still need hardware tests.

`python tools/test_engines.py` checks block deadlines, two spectral pitch peaks,
4-note allocation/stealing/sustain, MIDI bursts, control sweeps, fast-arp sustain,
engine switching and the FX menu. The current emulator run delivered 514
blocks with zero underruns during two seconds of steady four-note playback,
and measured both requested software pitches at 261.48 and 329.83 Hz. An
adversarial 121-byte instantaneous queue burst produced three missed blocks;
that injection exceeds the arrival rate of a real DIN MIDI link. The regression
allows up to four misses for that overload case and requires bounded MIDI
latency; a subsequent pitch-wheel packet drained within one emulator frame.
These measurements are not a physical link or long-duration hardware guarantee.
The test exports emulator audio examples:
`build/mix4-chord.wav`, `build/mix2-wave.wav`, `build/fast-arp.wav`.

## Instrument tables

The table editor draws inspiration from LSDj instrument-table workflows, not
its code or graphics. Each preset carries eight editable steps, a mode and a
length. Rows execute at the macro speed from MOD; each note restarts the table,
except NOTE mode, which advances one row per note. ONCE runs to the final row
and holds its settings; LOOP wraps at the chosen length. The arrow in TBL marks
the last applied row. The four lights below show the repeating macro phase.

Each row has transpose (-24 to +24 semitones), shape and pan. On pulse voices,
shape is duty 0–3; on wave it selects shape 0–15; on noise it changes clock shift
0–15. Pan is off, right, left or both. Tables take priority over pulse duty
sequencing while enabled. Chord transpose, vibrato and slide still combine with
the table. Noise uses shape/pan automation rather than tonal transpose. Wave
shape tables rebuild/retrigger the wave channel; custom MIDI wave RAM disables
shape replacement. The displayed waveform is a timbre preview, not a sampled
audio oscilloscope. Meters show note velocity, not measured audio amplitude.

Stock arp/organ patches use looping pitch/duty tables, zaps use attack pitch
steps, and percussion uses noise-shape movement; snares alternate stereo pan.
For examples load 004 or 007 on pulse, 008 for a descending attack, or 010 on
noise. Tables and edits stay in RAM; reloading a preset restores its stock table.

Sources consulted: [Infu's LSDj tutorial, tables and drum design](https://learnlsdj.github.io/),
[LSDj advanced techniques](https://github.com/jkotlinski/lsdj-doc/blob/master/advanced.tex),
[LSDj command reference](https://github.com/jkotlinski/lsdj-doc/blob/master/commands.tex).
The implementations here are independent and simplified. Hardware timing references:
[Pan Docs audio registers](https://github.com/gbdev/pandocs/blob/master/src/Audio_Registers.md)
and [timer registers](https://github.com/gbdev/pandocs/blob/master/src/Timer_and_Divider_Registers.md).

## Validation and hardware check

Run `python tools/smoke_test.py`. Checks cover boot, ROM checksums, four-voice
note on/off, duty CC, program 100, custom wave RAM, gates, the six original UI screens,
instant browser loading, local tone/mod/table edits, table progression and
advance-per-note, panic, plus a queued MIDI burst during graphical updates, trigger-path instrumentation
for live CC/wheel sweeps, sustained pitch bend, deferred waveform edits, and
poly allocation/voice stealing/sustain/chord audition.
`build/ui-*.png` contains emulator captures from this ROM.

MIDI bytes are injected at the receive queue: PyBoy does not model the physical
Arduinoboy external clock. Real link timing, DMG readability and audible patch
matching remain hardware tests. Flash `build/GAYBOY.gb`, select mGB mode and
send notes on channels 1–4. While holding B, browse with Up/Down, visit MOD and
TBL, and edit parameters. Check fast MIDI traffic during page changes; the
receiver has a 255-byte queue and displays RX FULL after an overflow.

References: [Arduinoboy firmware](https://github.com/trash80/Arduinoboy),
[mGB](https://github.com/trash80/mGB),
[Pan Docs audio registers](https://gbdev.io/pandocs/Audio_Registers.html),
[GBDK](https://github.com/gbdk-2020/gbdk-2020/releases/tag/4.5.0).
The project uses a new C engine; upstream repositories in `reference/` are
research checkouts with their original licenses, not linked into the ROM.

Mixer implementation note: `softlut` reserves WRAM D800-D83F for two aligned
32-sample lookup tables used by the assembly producer. Keep that range free
and keep CGB WRAM bank 1 selected while these engines run.


## Piano-roll sequencer

Hold Start, highlight SEQUENCER with Up/Down, then release Start.
Each channel has an independent monophonic 1-256 step pattern, viewed in
16-step blocks with 12 pitches visible. Steps are sixteenth notes at a shared
30?300 BPM. Patterns and edits remain in RAM until power-off.

- D-pad: move through steps and pitches; A: insert/remove a note; tap B: erase.
- Hold B + Up/Down: note velocity; B + Left/Right: note duration in steps.
  Empty cells edit the defaults for new notes.
- Select + Left/Right: channel; Select + Up/Down: tempo.
- Select + A: play/stop; Select + B: mute the current track.
- Tap Select: switch between roll and the nine header settings. In the header,
  Left/Right selects a value, Up/Down changes rows, A toggles editing, and
  holding B edits with Up/Down (one) or Left/Right (ten). Held directions repeat
  with acceleration.

BPM is global. Length, default velocity, duration and mute are per track.
Each pulse TONE page has its own GATE % control (1?100, A resets to 100). Notes can span rests; a later note interrupts the previous note.
Playback continues on other pages. Select + Start stops everything.
Tracks 1?4 use the current pulse 1, pulse 2, wave and noise instruments together.
H is the default playback mode: all four hardware tracks run together, and
Select + Left/Right changes only the viewed track. The H/M field at the top
explicitly selects M for channel 5 Monosynth alone, using its current settings.
Tap Select then Left to select H/M; B + Up chooses M, B + Down chooses H.
These modes share the hardware voices. An explicit mode change during playback
restarts transport in the new group; merely paging never stops or restarts it.
The sequencer uses its internal tempo, without MIDI clock synchronization.

Run `python tools/test_sequencer.py` for sequencer editing and playback checks.

Native NOTE DELAY reserves pulse 2 for newly triggered note echoes. ECHO LEVEL
controls their gain independently of pulse 2?s dry LEVEL; successive repeats
lose one quarter of their level. NOTE DELAY, ECHO LEVEL and ECHO REPEATS must
all be above zero. ECHO PAN alternates the repeats left/right. AUDIO DELAY,
DELAY MIX and FEEDBACK instead belong to the software wave engine.


## Noise Lab

NOISE LAB is a separate Start-menu page built around DSP engine 1. It keeps
its own patch and restores the previous Monosynth settings when you leave.
Select + A latches/releases a drone without a keyboard; Select + B randomizes
the texture. Select + Start is panic. Drone release can leave an audio delay tail.
Up/Down selects a parameter, Left/Right changes it, A toggles editing with
Up/Down, and B + directions edits by one vertically or ten horizontally.
The parameter list scrolls between two blocks of eight.

Pitch, waveform and level feed brightness, sample-and-hold filter chaos,
phase scanning, detune/chorus, DSP cutoff/resonance, and audio delay/feedback.
Channel 5 MIDI also plays the lab patch. Leaving the lab stops its drone and
tail. These controls deliberately expose coarse, unstable DSP textures.

Heavy experimental waveform/phase scans update at up to 16 Hz in native mode or 8 Hz in DSP mode so the DMG can
keep producing DSP audio and servicing input. The audio sample rate is unchanged.

Sequencer/Noise Lab validation: `python tools/test_sequencer.py`,
`python tools/test_sequencer_dsp.py`, and `python tools/test_noiselab.py`.
These cover independent patterns, roll editing, gates/mute/transport, MIDI
engine isolation, DSP playback, drone/randomization and patch restoration.


Sequencer meter and note dragging: the signature at the top defaults to 4/4.
Tap Select for header selection; Left/Right also selects the numerator, denominator and H/M mode. Hold B + Up/Down, or toggle A editing, to change them. Numerators
are 1?12; denominators are 2, 4, 8 or 16. The roll remains a sixteenth-note grid:
thin vertical lines mark beats and two-pixel lines mark bars. Meter is global;
track length and quarter-note BPM remain independent.

In the roll, hold B + Left/Right to drag a note's end. Starting on an empty cell
creates a note when you first drag. Its onset and pitch stay fixed, and the
cursor follows the right edge. B + A can also place a note without releasing B.
Releasing B after a drag keeps the note. The most recently edited duration is
remembered separately on each track for the next note, including header DUR edits.
Dragging stops at the pattern end; a tap of B without dragging still erases a note.


## KY / original EDGB SD access test

`build/KY-SD-TEST.zip` contains a separate diagnostic ROM, three native `.GBW`
wave files, and an integer PCM WAV converter. Build it with `./build-ky.ps1`.
This is a hardware compatibility test; it is not yet a FILES page in GAYBOY.

The original EDGB interface is different from the EverDrive X series. The
independent driver in `src/ky/ky_sd.c` uses BE00 for SPI bytes, BF00 status bit
6 for completion, and indexed register 2 via BF00/BF80 for SPI control. These
interface facts were obtained by examining the original-series GBOS v4 from
Krikzz's download site (MD5 14763d546301eb45ecc74df85818571c). Manufacturer
firmware code is not linked into the diagnostic. Petit FatFs R0.03a by ChaN
was adapted from untoxa/VGM_player; notices remain in `src/ky`.

All loops have finite communication timeouts. The driver sends only SD init
and read commands, selects only the SPI control register, disables ordinary
cartridge SRAM before probing, and has no NOR-flash programming code. It
supports SDHC block addressing and older SD byte addressing, FAT16/FAT32,
short filenames, and the first MBR partition or a FAT volume without an MBR.
The cart's firmware is neither replaced nor updated.

Run the diagnostic from the existing KY menu. Report either a directory
listing or all displayed error fields: SD/FAT ERROR, STAGE, R1, PORT and WAIT.
A stage-2/R1-FF result means CMD0 got no valid response; it does not identify
the cause as a bad SD card. The KY menu may lock special registers when a ROM
is launched. Neither emulator tests nor the reported firmware version prove
that this physical-cart restriction can be bypassed. Integration with the
main synth is pending this real-cart access check.

A file is opened with A; another A previews exactly 16-byte native waves.
B stops preview and goes back. The included converter produces 32 samples
at four bits each, packed high nibble first into 16-byte `.GBW` files. It does
not convert complete recordings into LSDj drum kits or provide sample playback.

Checks: `python tools/test_ky_sd.py` injects simulated SPI replies into the
compiled ROM to exercise FAT16/FAT32, MBR/volume layouts, SDHC/SDSC, directory
navigation, file reads and actual wave-channel preview. It verifies that the
ROM emits no SD write command. `python tools/test_prepare_ky_waves.py` checks
PCM widths, stereo, cyclic resampling, normalization, cycle selection, batch
export, and preservation of existing output files. A simulated card verifies
the software protocol only; testing on a physical KY cart is still required.


Interactive testing: after ROM changes, launch the rebuilt ROM visibly with
`./launch-emulator.ps1` so it can be tested before copying it to a flash cart.
The project launcher maps arrows to the D-pad, X/Z to Game Boy A/B, Space to
Select, and either Shift to Start. Space no longer triggers fast-forward.
The standard Enter/Backspace aliases also remain available.


Startup channel settings use neutral APU instruments: Pulse 1 is a steady
50% square, Pulse 2 a steady 25% pulse (both level 10), Wave a triangle at
half hardware volume, and Noise a level-8 white-noise hit with hardware decay.
Sweep, arpeggios, vibrato, slides, duty sequencing, gates and table playback
start off. Channels are centered, with a two-semitone pitch-bend range.
The bank library remains available through browsing/program changes; the
startup instruments are marked as modified patches rather than changing the
100 stock presets.

Sequencer layout: the roll now uses 17 pitch rows and 19 steps across, with a one-column piano keyboard and octave numbers inside the C keys. Hold Start and choose SEQ SETTINGS for BPM, per-track length/gate/default velocity/default duration/mute, time signature and hardware/Mono mode. Tap Select to switch between the grid and settings; B plus directions edits, or A toggles editing. Select+A still starts/stops all enabled tracks.

The roll header contains a channel abbreviation, next-note velocity, and boxed M/S switches. Up at the top visible pitch selects the header; Left/Right selects velocity, M or S, and Down returns to the grid. Either A or B toggles M/S; enabled boxes are filled and the selected box has a bright border. For velocity, hold B+Up/Down (B+Left/Right changes by ten), or toggle editing with A. Velocity changes affect subsequently entered notes. Select+Up/Down changes zoom; tempo lives in SEQ SETTINGS. Solo is per track, allows multiple solo tracks, and applies within the active hardware/Mono playback group; mute takes precedence.

WAVE 2 is the fifth individual instrument (Select after Noise), received on MIDI channel 6; channel 5 keeps its existing Mono/poly role. Its default patch is an 808-style synthesized sine kick with pitch, level, decay, pitch-drop and waveform controls. A/B auditions it. W2 is available after Noise in the hardware sequencer group; Select+Left/Right selects tracks. It uses the second DDS voice and switches W1/W2 to the software mixer when first triggered. The two wave instruments share the hardware wave output and its routing. Monosynth remains a separate playback mode.

The final sequencer viewport overlaps the previous page so that patterns longer than the 19-column grid end at the right edge, without unused columns after the last step.

Sequencer zoom (SEQ SETTINGS > ZOOM STEPS) offers 8, 16 (default), 24, or 32 visible steps, coupled with approximately 9, 14, 17, or 17 visible pitches. The 16-step view includes a bottom velocity lane. The keyboard remains 16 pixels wide, with full-size octave numbers. Select+Up zooms in; Select+Down zooms out. The far-right two-digit header value is track length; highlight it and edit with B+directions or toggle editing with A. Beat boundaries use single dark-grey pixels and bars black pixels. Grid graphics use the upper cartridge-RAM scratch area, separately from the audio-delay buffer; cursor movement and playback use sprite overlays and does not rebuild the static grid.

With Select+Up/Down now assigned to zoom, pressing Up from a non-editing roll header raises the pitch view by an octave and returns to the grid. Down in the grid continues scrolling toward lower notes.

Sequencer editing update: zoom offers 8 / 16 / 24 / 32 steps, selected with Select+Up/Down. Tap B to plot or erase; hold B with Left/Right to set note length. Hold A and use the D-pad to move a note. A-drag from an empty cell selects a group; A-drag on a selected note moves the group, B-drag changes its lengths, and an empty A tap clears selection. The 16-step view has velocity sliders: B+Up/Down edits, released Up returns to cells, and released Down scrolls to lower notes. B on a highlighted piano key auditions while stopped and records at the playhead while playing. Start-menu Copy/Paste copies the current track.

Channel navigation: P1, P2, WAVE1, WAVE2 and NOISE are direct Start-menu entries; LIVE is no longer a menu entry. These open the corresponding instrument overview and retain that instrument when visiting Tone, Modulation, Bank, CC and Table. Those five pages appear only in an instrument context; global screens show global pages and instrument entries. The menu scrolls as needed. CC currently lists fixed MIDI mappings for the chosen instrument. WAVE2 has separate tone controls, a factory 808 patch, MIDI-6 mapping view and an eight-step pitch/wave/level table, enabled and timed from its own Modulation page.

Noise Lab is now named MASTURBATE. FX is contextual per instrument: each tonal instrument has independent FINE TICKS, while Noise exposes its native shift/divisor controls. Fine values are actual period-register steps (native) or DDS phase-increment steps (software waves), not fractional UI values rounded back to the same pitch. Limits follow the current/last note, stay strictly inside one semitone and are clipped again when the note or engine changes. Left/Right edits, B+Left/Right changes ten steps, A resets fine tuning. Monosynth keeps its own experimental tuning.


## Video demo capture

Run `python tools/record_demo.py` to capture the built ROM's entire intro and
musical fade into `recordings/GAYBOY-intro-reel.mp4`. Requires PyBoy, NumPy,
Pillow and FFmpeg on PATH. Exports 1080x1920 (9:16), 60 fps, H.264/AAC MP4
with stereo emulator audio and integer pixel scaling. Cartridge saves are
not modified. Audio sample timing drives video timing.

For scripted tutorials: `python tools/record_demo.py --seconds 30 --timeline demo.json
--output recordings/my-demo.mp4` (on one line). Timeline JSON example:
`[{"at":5,"button":"start","hold":0.15},{"at":6,"caption":"Choose an instrument"}]`.
Times are seconds from power-on; hold defaults to 0.15 seconds. Buttons:
start, select, a, b, up, down, left, right. Captions remain below the screen
until replaced; an empty caption clears them. Use JSON newline escapes for
line breaks. A JSON sidecar records settings and input events.
Automatic intro stopping requires the matching ROM .noi symbol file;
fixed-duration recording does not. See `python tools/record_demo.py --help`.


To reproduce the song performance, run `python tools/record_demo.py --song-demo
--output recordings/GAYBOY-song-demo.mp4` on one line. This drives real button
inputs against a fresh in-memory cartridge save, reads UI state for feedback,
and captures every frame and stereo sample. The completed build is accelerated
to 30 seconds with pitch-preserving audio tempo conversion and an on-screen
label. It includes all seven track types; MONO5 is shown separately because
it replaces the hardware arrangement while enabled. The final Save action
writes only the temporary emulator RAM; existing project saves are untouched.
The JSON sidecar contains the complete button event log and playback speed.
Story text for the intro lives in tools/intro-story.json; shared PyBoy colors
live in tools/demo_style.py.

For an unhurried performance with normal-speed audio, add `--realtime`:
`python tools/record_demo.py --song-demo --realtime --output recordings/GAYBOY-song-live.mp4`.
This leaves the completed arrangement playing for four bars after Save.


The revised musical demo is `python tools/record_demo.py --intro-song
--output recordings/GAYBOY-intro-theme-demo.mp4` (one line). This replaces the
short repetitive sketch with a prepared, intro-derived four-bar score at
95 BPM: C / F / Am / Am in two-beat harmonic changes, a varied 64-step lead,
quiet 64-step broken chords, and 32-step root bass and noise percussion.
It runs at normal speed and demonstrates live layer entrances and zoom through
real button inputs. The video explicitly labels the prepared score; note and
patch data are loaded before capture into isolated emulator RAM, not entered
on camera. No PCM layer steals the wave bass, and no exclusive MONO5 detour
interrupts the arrangement. Composition and stage data are in the JSON sidecar.
The score and performance are defined in tools/intro_song.py.


For the 30-second grayscale pattern performance, run:
`python tools/record_demo.py --quick-demo --output recordings/GAYBOY-30sec-pattern-demo.mp4`.
Intro is skipped. Prepared pad 1 has melody/bass, pad 2 adds percussion;
the live beat-quantized pattern launch occurs before the midpoint. The pad's
Edit shortcut opens the sequencer, then the drum roll is shown. Audio remains
at normal speed. Preparation and Save actions use isolated cartridge RAM.


## Display transitions

Sequencer graphics are staged in the existing cartridge-RAM tile cache and
published by ui_flush after construction. Incremental edits pin displayed tiles;
full replacements keep the outgoing VRAM intact until the final upload. Only
that upload/map publication temporarily hides the background. LCD power and
audio interrupts remain enabled, and uploads yield to the audio service after
each tile. The mixer alternates between two forty-tile preview sets so pad
selection and queued launches never rewrite the currently displayed bitmap.
Shared font restoration for mixer pages is staged in the existing preview RAM.

`python tools/test_display_transitions.py` checks the actual visible hardware
map against every tile-data upload during the 30-second performance, verifies
that the LCD stays enabled, and reports dispatch timing and blank-frame counts.
The JSON report is build/display-transitions.json. The saved pre-fix ROM and
baseline results are build/graphics-before.gb and build/display-before.json.
Use the retained-render, sprite-cache and drum regression checks alongside the
live mixer PCM timing test; emulator checks do not replace hardware validation.


The quick demo now follows a single live-edit workflow: a 16-step lead starts
with two missing notes, real B presses plot them before the next pass, then
pad 2 is queued in the Mixer for the 64-step backing arrangement's loop wrap.
The remaining footage stays on a 16-step drum roll with its moving playhead
continuously in view. The bass remains 32 steps and the accompaniment 64 steps.
Latest recording: recordings/GAYBOY-30sec-bass-queued-drums.mp4.


## Drum kit presets

Hold Start and choose **KITS**. Up/Down selects a preset; **A loads** it.
Left/Right selects an audition slot and **B plays that slot in the loaded kit**.
The star marks the loaded kit. New pattern saves also recall the kit choice.
Loading a kit from this screen preserves sequencer notes.
The original ten-sample Amen kit remains the startup default.

Five eight-sample kits: TR-808, TR-909, TR-707, LinnDrum and Oberheim DMX.
Slots 1?4 are kick, snare, closed hat and open hat; 5 is clap, 6/7 low/high
toms, and 8 cowbell (808/707), rim (909/DMX), or tambourine (Linn).
Legacy sample slots 9/10 are silent in these presets; noise rows N1/N2 remain.

Sources are from `G:/AUDIO/300 Drum Machines`; `assets/kits/manifest.json`
records each selection. Prepared WAVs build without the external library.
Preparation removes DC and excess silence, antialiases to mono 11,468 Hz,
uses the LSBATCH 20 Hz high-pass, -22 dB / 6:1 compressor (3 ms attack,
70 ms release), then drives the soft clipper by 18 dB for stronger body.
A 5 kHz low-pass precedes antialiased resampling. Final peaks normalize to
-1 dBFS; hits are limited to 650 ms with a final 7 ms fade.
Run `python tools/make_drum_samples.py --remaster` to rebuild from originals.
The versioned recipe lives in `assets/kits/mastering.json`; ordinary builds
reuse the prepared masters. Single hits retain full PCM amplitude; overlapping
voices use the existing averaging to avoid digital clipping.
The ROM player uses its existing packed four-bit PCM and two-voice limit.
ROM size is now 1 MiB (MBC5, same 32 KiB save RAM).
Run `python tools/test_kits.py` for menu/load/audition regression checks.


Queued pattern feedback: with Beat or Bar quantization, a requested pad flashes
inverted/normal while the previous pad stays solid. At the launch boundary,
the requested pad becomes solid and the old pad returns to its normal state.
Picking the active pad queues a restart at the next quantized boundary;
with quantization off it restarts immediately. Repeating a queued request leaves it queued. Flashing reuses uploaded graphics and changes only six map
cells from the foreground loop, with no animation work in the audio interrupt.
The off image includes neighboring half-tiles, so replacing adjacent queued
pads does not make an old selection flash. Display and flash bookkeeping use
reserved bank-zero cartridge RAM around ACC0 and ACE0-ACFD, outside audio
lookup tables at D800. Do not allocate that region to pattern or audio data.

`python tools/test_queued_flash.py` verifies actual rendered blinking, a stable
playing pad, solid launch state, adjacent queue replacement, cancellation and
zero tile-graphics uploads during blinking. The report is build/queued-flash.json.
The quick demo now completes two missing bass notes and queues the drums early
so the flashing wait and solid launch are visible before the drum roll view.


## Pattern tones and Load Preset

New pattern saves include edited hardware patches, preset identities, modulation,
instrument tables, fine tuning, custom wave RAM, W2 settings and tables,
Monosynth settings and effects, drum kit, and both drum noise patches.
Slots remain 2,560 bytes, with 256 steps per track and 512 shared note events.
Older B7/B8/B9 saves still load their notes and retain the current tone settings.
The new tone-aware format uses tag BA and includes the tone payload in its checksum.
Experimental mode remains a global setting; loading a pattern does not enable it.

Each P1/P2/Wave1/Noise/Wave2 Tone screen has a **LOAD PRESET** control at the
bottom of its parameter list. From the first parameter, Up wraps to this control.
A opens the picker; Up/Down browses all 100 sounds, Left/Right changes game banks,
A loads the highlighted preset, and B cancels. Browsing does not change the sound.
Wave2 adapts the shared library to its independent pitch/decay/wave/table engine.

Validation: `python tools/test_pattern_tones.py` and `python tools/test_tone_presets.py`.


Sequencer track navigation: hold Select and press Right to cycle only through
instrument rolls containing plotted notes. Left still visits every available roll,
including empty ones. Muted rolls remain eligible when they contain notes.
If all available rolls are empty, Right stays on the current roll.

PULSEKICK is the thirteenth drum sequencer row, labeled PK, and the third
DRUMSYNTH voice (Select cycles HiHat, Snare, PULSEKICK). It uses hardware
Pulse 1 with its own level, MIDI pitch, duty, envelope fall rate, downward sweep
time/shift/direction (DOWN or UP), and length (1/256-second units). The factory patch is a short,
Mario-style swept square kick. Left/Right edit, A restores the selected factory
value, and B auditions. PK has independent mute/solo strips in the mixer.
Kick notes take priority over P1 notes for their gate, capped by kick length.
P1 note and gate tracking continue during the kick. When PK ends, the current
P1 note resumes with the normal Pulse 1 Tone patch if its original gate is still
open. Notes that expired during PK stay silent. Kick controls do not change
that patch. Drum patterns and clipboard operations include PK.

Live pattern launches (OFF, BEAT and BAR) prepare the saved pattern and
snapshot outgoing edits while audio continues. Same-mode handoffs preserve
transport and accumulated clock time, install decoded tone settings before
releasing outgoing voices, and start incoming notes from the prepared event
cache before copying it into live storage. Validation:
`python tools/test_pattern_audio_handoff.py` checks a sustained P1 plus PCM
drums, continuing transport, and a release-to-P1 attack within one DMG frame.

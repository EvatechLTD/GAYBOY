#ifndef MIDI_INPUT_H
#define MIDI_INPUT_H
/* Performance mappings belong exclusively to decoded external MIDI. */
extern uint8_t midi_launch_enabled;
void midi_event(uint8_t status,uint8_t note,uint8_t value) BANKED;
void mixer_midi_launch_set(uint8_t enabled) BANKED;
#endif

#ifndef GAYBOY_VOICE_OWNERS_H
#define GAYBOY_VOICE_OWNERS_H
extern uint8_t mono_owned,mono_wave_owner,wave_track_down,voice_owner_busy;
uint8_t voice_mono_value(uint8_t c,uint8_t id) BANKED;
uint8_t voice_mono_key(uint8_t c,uint8_t note) BANKED;
uint16_t voice_mono_frequency(uint8_t c) BANKED;
void voice_mono_start(uint8_t note,uint8_t velocity) BANKED;
void voice_mono_release(void) BANKED;
void voice_mono_cut(void) BANKED;
void voice_mono_event(uint8_t type,uint8_t a,uint8_t b) BANKED;
void voice_mono_frame(void) BANKED;
void voice_route(void) BANKED;
void voice_reset(void) BANKED;
void voice_reclaim_wave(void) BANKED;
void eval_audio_resume_channel(uint8_t c) BANKED;
#endif

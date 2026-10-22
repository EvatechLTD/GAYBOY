#pragma bank 3
#include "api.h"
void eval_audio_resume_wave(void) BANKED;
/* Inert APU ownership entry points while shared native playback is retained. */
uint8_t expconfig[27],exprelease[3],expactive,expwaveon,expecho,exppan,expoutlevel;
int16_t expoffset[3]; volatile uint8_t exppending; volatile uint16_t expblocks,expdrops;
uint8_t expenv[3],expstage[3],expdirty,expzvolume[2],expampmap[16],expdelayenabled;
uint16_t exppcmstep[2];
void exp_changed(void) BANKED {} void exp_note(uint8_t n) BANKED {(void)n;}
uint8_t exp_off(void) BANKED {return 0;} void exp_frame(void) BANKED {}
void exp_service(void) BANKED {} void exp_fill(void) BANKED {} void exp_pitch(void) BANKED {}
void exp_waveapply(void) BANKED {} void exp_reset(void) BANKED {}
void voice_reset(void) BANKED {mono_owned=mono_wave_owner=wave_track_down=0;}
void voice_mono_frame(void) BANKED {} void voice_reclaim_wave(void) BANKED {eval_audio_resume_wave();}
void noise_close(void) BANKED {} void noise_open(void) BANKED {}
void noise_frame(void) BANKED {} void noise_render(void) BANKED {} void noise_input(uint8_t p,uint8_t e) BANKED {(void)p;(void)e;}

const uint8_t sourcehi[]={255,255,64,255,4,128,24,1,1,32,1};
uint8_t mono_tone_id(uint8_t r) BANKED {(void)r;return 0;}
uint8_t mono_fx_id(uint8_t r) BANKED {(void)r;return 0;}
int16_t voice_mono_fine(uint8_t c,int16_t d,uint8_t e) BANKED {(void)c;(void)d;(void)e;return 0;}
void eval_mono_input(uint8_t p,uint8_t e) BANKED {(void)p;(void)e;}
void eval_mono_edit(int8_t d) BANKED {(void)d;}

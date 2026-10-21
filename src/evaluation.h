#ifndef GAYBOY_EVALUATION_H
#define GAYBOY_EVALUATION_H
/* Append-only evaluation patch extension. Legacy 450-byte tone payload stays
   byte-for-byte unchanged. Eight instruments, 32 bytes each. */
#define EVAL_BYTES 144U
#define EV_MODE 0
#define EV_CLOCK 1
#define EV_DIV 2
#define EV_TIMING 3
#define EV_RETRIGGER 4
#define EV_ORDER 5
#define EV_MS 6
#define EV_ATTACK 8
#define EV_DECAY 9
#define EV_SUSTAIN 10
#define EV_RELEASE 11
#define EV_LFO_SHAPE 12
#define EV_LFO_RATE 13
#define EV_SOURCES 8
#define EV_DEPTH 9
#define EV_LEVEL_MODE 10 /* 0 hardware, 128 ADSR; legacy brightness migrated */
#define EV_LFO_DIV 24
#define EV_LFO_CLOCK 25
#define EV_PAN 14
#define EV_BRIGHT 23
#define EV_RESONANCE 24
#define EV_PHASE 25
#define EV_CHORD_HISTORY 13
#define EV_PHASE_RATE 26 /* legacy generic FX alias; individual FX use evalwavefx */
#define EV_LFO_FREE 27
#define EV_SLEW 27 /* legacy generic FX alias */
#define EV_SECOND 28
#define EV_SECOND_SHAPE 29
#define EV_FINE 11
extern uint8_t coarsepitch[8][3]; /* signed semitones, signed depth, source */
uint16_t coarse_apply(uint8_t c,uint16_t base) BANKED;
void coarse_capture(uint8_t *raw) BANKED;
void coarse_restore(const uint8_t *raw,const uint8_t *mod) BANKED;
extern uint8_t evalwavefx[27],evalwaveactive,evalsecondon,evalsecondmask;
extern uint8_t expdirty;
extern uint16_t exppcmstep[2];
void drum_synth_audition(void) BANKED;
uint16_t eval_poly_pitch(uint8_t note) BANKED;
uint16_t eval_drum_pitch(uint8_t c,uint16_t base) BANKED;
uint8_t eval_drum_level(uint8_t c,uint8_t base) BANKED;
uint8_t eval_drum_duty(uint8_t c,uint8_t base) BANKED;
void eval_wave_enter(void) BANKED;
void eval_wave_leave(void) BANKED;
void eval_wave_defaults(void) BANKED;
void eval_wave_save(uint8_t *out) BANKED;
uint8_t *eval_mono_fx(void) BANKED;
uint8_t eval_wave_value(uint8_t id) BANKED;
uint16_t eval_pitch(uint8_t c,uint16_t base) BANKED;
uint8_t eval_audio_release(uint8_t c) BANKED;
void eval_audio_note(uint8_t c) BANKED;
void eval_audio_frame(void) BANKED;
void eval_second_lut(void) BANKED;
extern uint8_t evalpatch[8][16],eval_hidden,eval_row,eval_col,eval_tab;
extern uint8_t eval_confirm,eval_pending,eval_target;
extern uint8_t eval_plotvel[7],eval_message;
void eval_load_object(uint16_t object) BANKED;
void eval_defaults(void) BANKED;
void eval_capture(uint8_t *out) BANKED;
void eval_restore(const uint8_t *in) BANKED;
void eval_render(void) BANKED;
void eval_input(uint8_t p,uint8_t edge) BANKED;
uint8_t eval_instrument(void) BANKED;
uint8_t eval_visible(uint8_t c) BANKED;
uint8_t eval_mode(uint8_t c) BANKED;
void eval_set_mode(uint8_t c,uint8_t mode) BANKED;
int8_t eval_signal(uint8_t c,uint8_t source) BANKED;
int8_t eval_amount(uint8_t c,uint8_t destination) BANKED;
void eval_note(uint8_t c,uint8_t on) BANKED;
void eval_frame(void) BANKED;
extern uint8_t eval_lfousers,eval_envusers,eval_moddirty;
extern uint16_t eval_modgeneration;
void eval_mod_configure(void) BANKED;
void eval_mod_frame(uint8_t needed) BANKED;
uint16_t eval_arp_wait(void) BANKED;
void eval_seq_tick(uint16_t ticks) BANKED;
uint8_t eval_seq_fire(uint8_t c) BANKED;
void eval_seq_off(uint8_t c) BANKED;
void eval_drum_dirty(void) BANKED;
void eval_drum_prepare(void) BANKED;
uint8_t eval_drum_allowed(uint16_t index) BANKED;
void eval_status(void) BANKED;
void eval_global_render(void) BANKED;
void eval_global_input(uint8_t p,uint8_t edge) BANKED;
#endif

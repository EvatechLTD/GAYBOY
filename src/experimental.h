#ifndef GAYBOY_EXPERIMENTAL_H
#define GAYBOY_EXPERIMENTAL_H
#define EXP_COUNT 27
extern uint8_t expconfig[EXP_COUNT],exprelease[3],expactive,expwaveon,expecho,exppan,expoutlevel;
extern int16_t expoffset[3];
extern volatile uint8_t exppending;
extern uint8_t expenv[3],expstage[3];
extern volatile uint16_t expblocks,expdrops;
extern __at (0xDA00) int8_t expalpha[256];
extern __at (0xDB00) int8_t expreslut[256];
extern __at (0xDC00) uint8_t expinterp[256];
extern __at (0xDD00) int8_t expfeedback[256];
extern __at (0xD900) int8_t expwet[256];
extern uint8_t expampmap[16],expdelayenabled;
void exp_tables(void) BANKED;
void exp_maps(uint8_t frac,uint8_t gain) BANKED;
void exp_changed(void) BANKED;
void exp_note(uint8_t note) BANKED;
uint8_t exp_off(void) BANKED;
void exp_frame(void) BANKED;
void exp_service(void) BANKED;
void exp_fill(void) BANKED;
void exp_pitch(void) BANKED;
void exp_waveapply(void) BANKED;
void exp_reset(void) BANKED;
void exp_fetch(uint8_t bank,uint16_t offset,uint8_t *dst) NONBANKED;
#endif

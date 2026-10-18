#ifndef GAYBOY_TONES_H
#define GAYBOY_TONES_H
#define TONE_OFFSET 2161U
#define TONE_SIZE 288U
#define TONE_PACK ((uint8_t *)0xBD00)
void tones_pack(void) BANKED;
uint8_t tones_decode(void) BANKED;
void tones_apply(void) BANKED;
extern uint8_t tonepresetopen,w2program;
void tone_preset_open(void) BANKED;
void tone_preset_render(void) BANKED;
void tone_preset_input(uint8_t edge) BANKED;
#endif

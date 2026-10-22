#ifndef GAYBOY_TONES_H
#define GAYBOY_TONES_H
#define TONE_OFFSET 2161U
#define TONE_SIZE 288U
#define TONE_PACK ((uint8_t *)0xBD00)
#define TONE_RAW ((uint8_t *)0xBA00)
#define TONE_RAW_BYTES 168U
#define TONE_CACHED_RAW ((uint8_t *)0xB600)
#define TONE_CACHED_FX ((uint8_t *)0xBE00)
/* Mixer-only second half; capture invalidates preparation before reusing RAW. */
#define STAGED_EVENT_ADDRESS(n) ((uint8_t *)((n)<1024U?0xB020U+(n):0xBA00U+(n)-1024U))
#define TONE_KICK_RAW (TONE_RAW+168U)
void tones_capture(void) BANKED;
void tones_pack(void) BANKED;
uint8_t tones_decode(void) BANKED;
void tones_apply(void) BANKED;
void tones_apply_buffer(const uint8_t *raw) BANKED;
uint8_t tones_match_buffer(const uint8_t *raw) BANKED;
void tones_apply_cached(void) BANKED;
void tones_finalize(void) BANKED;
uint8_t tones_apply_object(uint16_t object) BANKED;
uint8_t tones_scatter_object(uint16_t object) BANKED;
extern uint8_t tonepresetopen,w2program;
void tone_preset_open(void) BANKED;
void tone_preset_render(void) BANKED;
void tone_preset_input(uint8_t edge) BANKED;
#endif

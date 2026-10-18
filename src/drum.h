#ifndef DRUM_H
#define DRUM_H
extern uint32_t pulsekickleft;
extern uint8_t drumkit;
void kits_render(void) BANKED;
void kits_input(uint8_t p,uint8_t edge) BANKED;
extern uint8_t drumenabled,drumrow,druminit,drumnoiseowned;
extern uint16_t drummutemask,drumsolomask;
void drum_mixer_refresh(void) BANKED;
extern __at (0xAC40) uint8_t drumon[2];
void drum_fetch(uint8_t bank,uint16_t offset,uint8_t *dst) BANKED;
void drum_label(uint8_t row,uint8_t *dst) BANKED;
void drum_init(void) BANKED;
void drum_age_sync(void) BANKED;
void drum_mix(void) BANKED;
void drum_fire(uint8_t step) BANKED;
void drum_stop(void) BANKED;
void drum_tick(uint16_t ticks) BANKED;
void drum_velocity_render(void) BANKED;
void drum_velocity_edit(int8_t delta) BANKED;
void drum_input(uint8_t p,uint8_t edge) BANKED;
void drum_render(void) BANKED;
void drum_synth_render(void) BANKED;
void drum_synth_input(uint8_t p,uint8_t edge) BANKED;
void drum_enable(void) BANKED;
void roll_begin(void) BANKED;
void roll_upload(uint8_t row) BANKED;
uint16_t drum_clip_plot(uint8_t step,uint8_t row,uint16_t dur,uint8_t vel) BANKED;
#endif

#ifndef MIXER_H
#define MIXER_H
void mixer_boot(void) BANKED;
void mixer_init(void) BANKED;
void mixer_open(void) BANKED;
void mixer_render(void) BANKED;
void mixer_input(uint8_t p,uint8_t edge) BANKED;
void mixer_clock_reset(void) BANKED;
uint8_t mixer_boundary(void) BANKED;
uint8_t mixer_velocity(uint8_t track,uint8_t velocity) BANKED;
uint8_t mixer_pan(uint8_t track) BANKED;
void mixer_name(void) BANKED;
void mixer_tick(void) BANKED;
#endif

#ifndef NOISELAB_H
#define NOISELAB_H
extern uint8_t noisesaved;
void noise_open(void) BANKED;
void noise_close(void) BANKED;
void noise_input(uint8_t p,uint8_t edge) BANKED;
void noise_render(void) BANKED;
#endif

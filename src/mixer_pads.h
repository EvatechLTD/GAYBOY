#ifndef MIXER_PADS_H
#define MIXER_PADS_H
extern __at (0xACC6) uint8_t pad_names_valid;
extern __at (0xACC2) uint8_t padflash_off;
void mixer_pads_render(void) BANKED;
void mixer_pad_restore(void) BANKED;
void mixer_tick(void) BANKED;
#endif

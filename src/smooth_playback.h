#ifndef SMOOTH_PLAYBACK_H
#define SMOOTH_PLAYBACK_H
extern uint8_t smooth_playback_enabled,smooth_playback_active;
extern uint8_t smooth_playback_button,smooth_playback_target;
void smooth_playback_update(void) BANKED;
void smooth_playback_input(uint8_t pad,uint8_t edge) BANKED;
#endif

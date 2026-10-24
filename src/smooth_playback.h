#ifndef SMOOTH_PLAYBACK_H
#define SMOOTH_PLAYBACK_H
extern uint8_t smooth_playback_requested,smooth_playback_active,smooth_playback_preparing;
void smooth_playback_start(void) BANKED;
void smooth_playback_begin(void) BANKED;
void smooth_playback_ready(void) BANKED;
void smooth_playback_update(void) BANKED;
#endif

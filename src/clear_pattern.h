#ifndef GAYBOY_CLEAR_PATTERN_H
#define GAYBOY_CLEAR_PATTERN_H
void clear_capture(void) BANKED;
void clear_open(void) BANKED;
void clear_song_open(uint8_t song) BANKED;
void clear_render(void) BANKED;
void clear_input(uint8_t edge) BANKED;
uint8_t clear_available(void) BANKED;
uint8_t finder_edit_allowed(uint8_t item) BANKED;
uint8_t finder_edit_action(uint8_t item) BANKED;
#endif

#ifndef SONG_TWINK_H
#define SONG_TWINK_H
#include <gb/gb.h>
#include <stdint.h>
uint8_t song_cache_put(uint16_t at,const uint8_t *p,uint8_t n) BANKED;
void song_twink_reset(void) BANKED;
uint8_t song_twink_compile(uint8_t pad,uint16_t *used) BANKED;
void song_twink_begin(void) BANKED;
void song_twink_scene(uint8_t pad,uint32_t offset) BANKED;
void song_twink_step(void) BANKED;
void song_twink_quiet(void) BANKED;
void song_twink_commit(void) BANKED;
#endif

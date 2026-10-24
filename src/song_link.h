#ifndef SONG_LINK_H
#define SONG_LINK_H
#include <gb/gb.h>
#include <stdint.h>
extern uint8_t song_link_active;
void song_link_request(uint8_t smooth) BANKED;
void song_link_receive(uint8_t byte) BANKED;
void song_link_service(void) BANKED;
void song_link_finish(void) BANKED;
uint8_t song_prepare(uint8_t smooth,uint16_t bpm,uint32_t start) BANKED;
extern __at (0xA3E9) volatile uint8_t song_link_reload;
extern __at (0xA3FB) volatile int16_t song_link_trim;
void song_slave_timer(void) NONBANKED;
void song_arm(void) BANKED;
void song_go(void) BANKED;
void song_status(uint8_t ready) BANKED;
#endif

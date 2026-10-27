#ifndef GAYBOY_TWINK_CHORD_H
#define GAYBOY_TWINK_CHORD_H
#include <gb/gb.h>
#include <stdint.h>
extern volatile uint8_t twink_chord_work;
extern uint8_t twink_chord_check_frame;
void twink_chord_reset(void) BANKED;
void twink_chord_service(void) BANKED;
void twink_chord_step(uint8_t step) BANKED;
void twink_chord_release(void) BANKED;
uint8_t twink_chord_next_step(void) BANKED;
#endif

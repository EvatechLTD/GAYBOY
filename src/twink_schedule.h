#ifndef TWINK_SCHEDULE_H
#define TWINK_SCHEDULE_H
#include <gb/gb.h>
#include <stdint.h>
extern uint8_t twink_v2,twink_scheduled,twink_reply,twink_ack,twink_v2_blocked;
extern volatile uint8_t twink_staging,twink_received,twink_event_left,twink_event_pending;
/* These old raw-slave fields are mutually exclusive with TWINK master. */
extern __at (0xFFE8) volatile uint16_t twink_clock;
extern __at (0xFFEA) volatile uint8_t twink_clock_fraction;
extern __at (0xFFEB) volatile uint8_t twink_clock_div;
extern __at (0xFFEC) volatile uint16_t twink_last_anchor;
extern __at (0xFFEE) volatile uint8_t twink_anchor_second;
extern __at (0xFFEF) volatile uint8_t twink_anchor_pending;
uint8_t twink_queue_message(const uint8_t *data,uint8_t size) BANKED;
void twink_schedule_reset(uint8_t session) BANKED;
void twink_schedule_probe(void) BANKED;
uint8_t twink_schedule_start(void) BANKED;
void twink_schedule_stop(void) BANKED;
void twink_schedule_service(void) BANKED;
uint8_t twink_v2_clock(void) NONBANKED;
void twink_v2_irq(void) BANKED;
#endif

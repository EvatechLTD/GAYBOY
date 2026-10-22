#ifndef TWINK_H
#define TWINK_H
#define SYNC_TWINK 6
#define TWINK_TRACK 5
extern uint8_t twink_ready;
void twink_service(void) BANKED;
void twink_reset(void) BANKED;
void twink_transport(uint8_t playing) BANKED;
void twink_note(uint8_t on,uint8_t pitch,uint8_t velocity) BANKED;
void twink_panic(void) BANKED;
#endif

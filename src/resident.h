#ifndef STRIPPED_RESIDENT_H
#define STRIPPED_RESIDENT_H
#define RESIDENT_PATTERNS 5
#define RESIDENT_NOTES 256U
#define RESIDENT_EVENTS 768U
void resident_read(uint8_t slot,uint16_t offset,uint8_t *data,uint16_t count) BANKED;
void resident_write(uint8_t slot,uint16_t offset,const uint8_t *data,uint16_t count) BANKED;
void resident_events_changed(void) BANKED;
void resident_move(uint16_t to,uint16_t from,uint16_t bytes) BANKED;
#endif

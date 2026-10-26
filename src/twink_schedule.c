#pragma bank 6
#include "api.h"
#include "twink_schedule.h"
#include "twink_chord.h"
/* Compatibility names for the retired timed transport; direct serial has no
   receiver clock, admission window or return negotiation. */
uint8_t twink_v2,twink_scheduled,twink_reply,twink_ack,twink_v2_blocked;
uint16_t twink_ms_generation;
volatile uint8_t twink_staging,twink_received,twink_event_left,twink_event_pending;
__at (0xFFE8) volatile uint16_t twink_clock;
__at (0xFFEA) volatile uint8_t twink_clock_fraction;
__at (0xFFEB) volatile uint8_t twink_clock_div;
__at (0xFFEC) volatile uint16_t twink_last_anchor;
__at (0xFFEE) volatile uint8_t twink_anchor_second;
__at (0xFFEF) volatile uint8_t twink_anchor_pending;
static const uint8_t crc7_table[128]={
 0,9,18,27,36,45,54,63,72,65,90,83,108,101,126,119,
 25,16,11,2,61,52,47,38,81,88,67,74,117,124,103,110,
 50,59,32,41,22,31,4,13,122,115,104,97,94,87,76,69,
 43,34,57,48,15,6,29,20,99,106,113,120,71,78,85,92,
 100,109,118,127,64,73,82,91,44,37,62,55,8,1,26,19,
 125,116,111,102,89,80,75,66,53,60,39,46,17,24,3,10,
 86,95,68,77,114,123,96,105,30,23,12,5,58,51,40,33,
 79,70,93,84,107,98,121,112,7,14,21,28,35,42,49,56,
};
uint8_t twink_packet_crc(uint8_t type,uint8_t pitch,uint8_t velocity) BANKED {
 return crc7_table[crc7_table[crc7_table[type]^pitch]^velocity];
}
/* Snapshot spare bytes carry both CRCs; no note-time CRC calculation. */
uint16_t twink_note_crcs(uint8_t pitch,uint8_t velocity) BANKED {
 uint8_t on=twink_packet_crc(3,pitch,velocity);return on|((uint16_t)twink_packet_crc(4,pitch,0)<<8);
}
void twink_schedule_reset(uint8_t session) BANKED {(void)session;twink_v2=twink_scheduled=twink_reply=twink_staging=twink_received=twink_event_left=twink_event_pending=twink_v2_blocked=0;}
void twink_schedule_stop(void) BANKED {twink_scheduled=0;}
void twink_schedule_probe(void) BANKED {}
uint8_t twink_schedule_start(void) BANKED {twink_scheduled=1;return 1;}
void twink_schedule_service(void) BANKED {}
void twink_schedule_changed(void) BANKED {twink_ms_generation++;twink_chord_work=1;}
uint8_t twink_v2_clock(void) NONBANKED {return 0;}
void twink_v2_irq(void) BANKED {}

uint8_t twink_crc_step(uint8_t crc,uint8_t value) BANKED {return crc7_table[crc^value];}

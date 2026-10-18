#ifndef GAYBOY_STORAGE_H
#define GAYBOY_STORAGE_H
/* One shared event budget, allocated among all seven tracks. Events within
   each track retain insertion order so DRUM can evict the most recently plotted hit.
   byte0 step0..255, byte1 note1..128 / drum row1..12, byte2 velocity0..127,
   byte3 actual duration1..255, or0 for256 steps. A rest has no event. */
#define SEQ_EVENT_CAPACITY 512U
#define SEQ_EVENT_APPEND 65535U
extern uint8_t seqevents_lo[256][4];
extern __at (0xA800) uint8_t seqevents_hi[256][4];
extern uint16_t seqeventcounts[7],seqeventoffsets[7];
extern uint8_t seqeventfull;
extern uint8_t seqeventcache;
void seq_track_clear(uint8_t track) BANKED;
uint16_t seq_event_count(uint8_t track) BANKED;
uint16_t seq_event_total(void) BANKED;
uint8_t seq_event_get(uint8_t track,uint16_t index,uint8_t *event) BANKED;
uint8_t seq_event_next_step(uint8_t track,uint8_t step,uint16_t *cursor,uint8_t *event) BANKED;
uint8_t seq_note_event(uint8_t track,uint8_t step,uint8_t *event) BANKED;
uint8_t seq_event_put(uint8_t track,uint16_t index,const uint8_t *event) BANKED;
void seq_event_erase(uint8_t track,uint16_t index) BANKED;
void seq_storage_clear(void) BANKED;
uint8_t seq_note_get(uint8_t track,uint8_t step) BANKED;
uint8_t seq_velocity_get(uint8_t track,uint8_t step) BANKED;
uint16_t seq_duration_get(uint8_t track,uint8_t step) BANKED;
uint8_t seq_note_set(uint8_t track,uint8_t step,uint8_t note,uint8_t velocity,uint16_t duration) BANKED;
#endif

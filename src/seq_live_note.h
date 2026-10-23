#ifndef SEQ_LIVE_NOTE_H
#define SEQ_LIVE_NOTE_H
void seq_plot_audition(uint8_t track,uint8_t note,uint8_t velocity) BANKED;
void drum_plot_audition(uint8_t row,uint8_t velocity) BANKED;
extern uint8_t seq_live_timed;
void seq_live_current(uint8_t resize) BANKED;
void seq_live_release(void) BANKED;
void seq_live_service(void) BANKED;
#endif

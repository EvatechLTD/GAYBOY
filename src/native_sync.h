#ifndef GAYBOY_NATIVE_SYNC_H
#define GAYBOY_NATIVE_SYNC_H
/* Stopped native live-pattern preflight; never the song compiler. */
#define NATIVE_PREPARE 0xF0
#define NATIVE_WAIT 0xF9
#define NATIVE_READY 0xFE
/* 0idle,1request,2prepared,3GO,4cancel,5master polling */
extern volatile uint8_t native_prepare;
extern volatile uint8_t native_peer_running;
void seq_prepared_start(void) BANKED;
void seq_cancel_prepare(void) BANKED;
#endif

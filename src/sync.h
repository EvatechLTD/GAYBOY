#ifndef GAYBOY_SYNC_H
#define GAYBOY_SYNC_H
extern __at (0xFFDA) uint8_t syncmode;
extern __at (0xFFDB) uint8_t syncslave;
extern __at (0xFFDC) uint8_t syncpending;
extern __at (0xFFDD) uint8_t syncbusy;
extern __at (0xFF98) volatile uint8_t synctx[32];
extern __at (0xFFD8) volatile uint8_t syncr;
extern __at (0xFFD9) volatile uint8_t syncw;
extern __at (0xFFB8) volatile uint8_t syncirqphase[3];
extern __at (0xFFBB) volatile uint16_t syncincrement;
extern __at (0xFFBD) volatile uint8_t synclimit[3];
extern __at (0xFFC0) volatile uint8_t syncarmed;
extern __at (0xFFC1) uint8_t syncdivider;
extern __at (0xFFC2) uint8_t syncsub;
extern __at (0xFFC3) uint8_t syncreload;
extern __at (0xFFC4) volatile uint8_t syncdue;
extern __at (0xFFC6) volatile uint8_t synctxwait;
extern __at (0xFFC7) volatile uint8_t synctick;
extern __at (0xFFC8) volatile uint8_t syncstart;
extern __at (0xFFC9) volatile uint8_t synctxbyte;
void sync_control_service(void) BANKED;
void sync_clock_isr(void) NONBANKED;
void sync_timer_config(void) BANKED;
void sync_pattern(void) BANKED;
void sync_init(void) BANKED;
void sync_render(void) BANKED;
void sync_input(uint8_t edge) BANKED;
uint8_t sync_receive(uint8_t b) BANKED;
uint16_t sync_advance(uint16_t ticks) BANKED;
void sync_transport(uint8_t playing) BANKED;
#endif

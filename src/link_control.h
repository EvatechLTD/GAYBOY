#ifndef LINK_CONTROL_H
#define LINK_CONTROL_H
/* Optional native link plane. Never called from the oscillator interrupt. */
typedef struct {
 char names[8][16];
 uint8_t level[7],pan[7],muted,solo;
 uint16_t drummutemask,drumsolomask;
 uint8_t slot,pending,namesvalid,quant;
 uint16_t epoch;
} LinkMirror;
extern LinkMirror linkmirror;
extern uint8_t linkstate,link_names_dirty,linkcollision;
extern volatile uint8_t linktx[26],linktxread,linktxsize;
extern uint8_t linkpair,link_pair_hold,link_pair_phase;
void link_reset(void) BANKED;
void link_begin(void) BANKED;
void link_service(void) BANKED;
uint8_t link_receive(uint8_t b) BANKED;
uint8_t link_command(uint8_t track,uint8_t field,uint8_t value) BANKED;
uint8_t link_pair_request(uint8_t slot,uint8_t edit) BANKED;
uint8_t link_pair_marker(void) BANKED;
void link_pair_master_launched(void) BANKED;
void link_serial_isr(void) NONBANKED;
void mixer_remote_apply(uint8_t track,uint8_t field,uint8_t value) BANKED;
#endif

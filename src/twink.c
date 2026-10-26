#pragma bank 60
#pragma opt_code_speed
#include "api.h"
#include "twink_schedule.h"
#include "twink_chord.h"
#include "mixer_shared.h"

uint8_t twink_ready;
volatile uint8_t twinktx[32];
volatile uint8_t twink_guard,twink_ended_div;

/* MS MONO uses this RX storage as immutable chord-frame lookahead. */
volatile uint8_t twink_private_active,twink_private_next;
extern uint8_t editbuffer_reading;
extern __at (0xAC6C) uint16_t seqstepunits;
void twink_prepare_notes(void) BANKED {twink_private_next=twink_private_active=1;twink_chord_service();}

/* One-way byte burst. SIO drains the remainder; the musical timer never
   polls a link clock or receiver credits. No interrupt-enabling helpers. */
void twink_direct_kick(void) NONBANKED __naked {__asm
 push bc
 ldh a,(#0x02)
 bit 7,a
 jr nz,direct_tx_done$
 ldh a,(#0x0f)
 bit 3,a
 jr nz,direct_tx_done$
 ldh a,(_syncr)
 ld b,a
 ldh a,(_syncw)
 cp a,b
 jr z,direct_tx_done$
 ld hl,#_twinktx
 ld a,b
 add a,l
 ld l,a
 jr nc,direct_tx_address$
 inc h
direct_tx_address$:
 ld a,(hl)
 ldh (#0x01),a
 ld a,b
 inc a
 and #31
 ldh (_syncr),a
 ld a,#0x81
 ldh (#0x02),a
direct_tx_done$:
 pop bc
 ret
 __endasm;}
void twink_direct_next(void) NONBANKED __naked {__asm
 push bc
 ldh a,(#0x04)
 ld c,a
 ld b,#2
next_gap_wait$:
 ldh a,(#0x04)
 cp a,c
 jr z,next_gap_wait$
 ld c,a
 dec b
 jr nz,next_gap_wait$
 pop bc
 jp _twink_direct_kick
 __endasm;}
/* Called with interrupts disabled, or by the foreground while stopped. */
static uint8_t enqueue(uint8_t type,uint8_t pitch,uint8_t velocity,uint8_t crc){uint8_t w=syncw;
 if(((syncr-w-1)&31)<5){overflow=1;return 0;}
 twinktx[w]=0xF3;w=(w+1)&31;twinktx[w]=type;w=(w+1)&31;twinktx[w]=pitch;w=(w+1)&31;twinktx[w]=velocity;w=(w+1)&31;twinktx[w]=crc;syncw=(w+1)&31;
 twink_direct_kick();return 1;
}
uint8_t twink_queue_message(const uint8_t *data,uint8_t size) BANKED {uint8_t i,w=syncw;if(((syncr-w-1)&31)<size)return 0;for(i=0;i<size;i++){twinktx[w]=data[i];w=(w+1)&31;}__critical{syncw=w;twink_direct_kick();}return 1;}
void twink_tx_tick(void) BANKED {twink_direct_kick();}
void twink_reset(void) BANKED {twink_schedule_reset(0);twink_chord_reset();twink_ready=1;twink_guard=synctxwait=0;twink_private_active=twink_private_next=0;}
static void wire_stop(uint8_t b){__critical{syncw=syncr;twinktx[syncw]=b;syncw=(syncw+1)&31;twink_direct_kick();}}
void twink_panic(void) BANKED {if(syncmode!=SYNC_TWINK)return;twink_scheduled=0;seqplaying=0;syncarmed=syncdue=syncstart=0;wire_stop(0xFF);}
void twink_transport(uint8_t playing) BANKED {if(syncmode!=SYNC_TWINK)return;twink_scheduled=playing;syncarmed=syncdue=syncstart=0;if(!playing){twink_chord_reset();wire_stop(0xFC);}}
void twink_note(uint8_t on,uint8_t pitch,uint8_t velocity) BANKED {uint8_t c;if(syncmode!=SYNC_TWINK)return;c=twink_packet_crc(on?3:4,pitch,on?velocity:0);__critical{enqueue(on?3:4,pitch,on?velocity:0,c);}}
void twink_service(void) BANKED {}

/* Swing/unsupported local IRQ synthesis keeps its normal foreground path. */
void twink_direct_fire(void) BANKED {twink_chord_step(seqposition[5]);}

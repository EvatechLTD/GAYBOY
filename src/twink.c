#pragma bank 60
#include "api.h"
#include "twink_schedule.h"
#include "mixer_shared.h"
uint8_t twink_ready;
volatile uint8_t twinktx[32];
volatile uint8_t twink_guard,twink_ended_div;
static uint8_t off_crc;
/* Direct mode has no MIDI receive stream: reuse its 256-byte buffer as two
   immutable 32-note caches. Larger lanes retain the cartridge snapshot. */
volatile uint8_t twink_private_active,twink_private_next;
static uint8_t private_base,private_count,private_slot=255;
static uint16_t private_revision;
extern uint16_t twink_ms_generation;
extern uint8_t editbuffer_reading;
extern __at (0xAC6C) uint16_t seqstepunits;
uint8_t editbuffer_irq_event(uint8_t c,uint8_t step,uint8_t *event) NONBANKED;
void twink_prepare_notes(void) BANKED {uint16_t count=seqeventcounts[5],i;uint8_t e[4],base,reading;
 if(count>32){twink_private_next=0;return;}
 twink_private_next=1;
 if(twink_private_active&&private_slot==mx.slot&&private_revision==twink_ms_generation&&private_count==count)return;
 base=private_base^128;reading=editbuffer_reading;editbuffer_reading=0;
 for(i=0;i<count;i++){seq_event_get(5,i,e);memcpy((uint8_t *)rx+base+i*4,e,4);}
 editbuffer_reading=reading;
 __critical{private_base=base;private_count=count;private_slot=mx.slot;private_revision=twink_ms_generation;twink_private_active=1;}
}
uint8_t twink_irq_event(uint8_t step,uint8_t *e) BANKED {uint8_t i,found=0,note=255,*p;uint16_t v;
 if(!twink_private_active)return editbuffer_irq_event(5,step,e);
 p=(uint8_t *)rx+private_base;
 for(i=0;i<private_count;i++,p+=4)if(p[0]==step&&p[1]&&p[1]<note){memcpy(e,p,4);note=e[1];found=1;}
 if(!found)return 0;
 v=e[2];if(mx.level[5]!=127){v=v*mx.level[5]+63;v=(v>>7)+((uint8_t)((v&127)+(v>>7))>=127);}
 e[6]=v;e[4]=twink_packet_crc(3,e[1]-1,e[6]);e[5]=twink_packet_crc(4,e[1]-1,0);return 1;
}

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
/* IRQ entry consumes the already compiled seventh-byte velocity and CRCs. */
void twink_irq_note(const uint8_t *e) BANKED {off_crc=e[5];enqueue(3,e[1]-1,e[6],e[4]);}
void twink_irq_off(uint8_t pitch) BANKED {enqueue(4,pitch,0,off_crc);}
uint8_t twink_queue_message(const uint8_t *data,uint8_t size) BANKED {uint8_t i,w=syncw;if(((syncr-w-1)&31)<size)return 0;for(i=0;i<size;i++){twinktx[w]=data[i];w=(w+1)&31;}__critical{syncw=w;twink_direct_kick();}return 1;}
void twink_tx_tick(void) BANKED {twink_direct_kick();}
void twink_reset(void) BANKED {twink_schedule_reset(0);twink_ready=1;twink_guard=synctxwait=0;twink_private_active=twink_private_next=0;private_slot=255;}
static void wire_stop(uint8_t b){__critical{syncw=syncr;twinktx[syncw]=b;syncw=(syncw+1)&31;twink_direct_kick();}}
void twink_panic(void) BANKED {if(syncmode!=SYNC_TWINK)return;twink_scheduled=0;seqplaying=0;syncarmed=syncdue=syncstart=0;wire_stop(0xFF);}
void twink_transport(uint8_t playing) BANKED {if(syncmode!=SYNC_TWINK)return;twink_scheduled=playing;syncarmed=syncdue=syncstart=0;if(!playing)wire_stop(0xFC);}
void twink_note(uint8_t on,uint8_t pitch,uint8_t velocity) BANKED {uint8_t c;if(syncmode!=SYNC_TWINK)return;c=twink_packet_crc(on?3:4,pitch,on?velocity:0);__critical{enqueue(on?3:4,pitch,on?velocity:0,c);}}
void twink_service(void) BANKED {}

/* Swing/unsupported local IRQ synthesis keeps its normal foreground path. */
void twink_direct_fire(void) BANKED {uint8_t e[7],solos=seqsolo&111,audible;
 if(drumsolomask)solos|=64;audible=power&&!(seqmuted&32)&&(!solos||(solos&32));
 if(audible&&twink_irq_event(seqposition[5],e)&&e[2]&&e[6]){
  __critical{twink_irq_note(e);}seqowned[5]=e[1];seqsource[5]=seqposition[5];seqgateleft[5]=(uint32_t)seqstepunits*(e[3]?e[3]:256U);
 }else if((!audible||!seqgateleft[5])&&seqowned[5]){__critical{twink_irq_off(seqowned[5]-1);}seqowned[5]=0;seqgateleft[5]=0;}
}

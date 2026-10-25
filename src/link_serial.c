#include "api.h"
#include "native_sync.h"
#include "link_control.h"
#include "song_link.h"
#include "song_mode.h"
extern volatile uint8_t linkbits[16],linkbitread,linkbitqueued;
extern volatile uint8_t link_rx_ready,link_peer_capable,link_alive,link_rx_dropped;
void sync_native_anchor(uint8_t clock) BANKED;
void sync_native_timestamp(void) BANKED;
volatile uint8_t link_claiming;
static uint8_t probe_phase,idle_seen,reply_byte;
static const uint8_t probe[4]={0xF4,'G','B',1};
/* Input/output A is the complete six-bit numbered clock. Only the spare
   bit changes, and only codes below F0 can carry data. No bank or SRAM. */
uint8_t link_clock_byte(uint8_t b) NONBANKED __naked {__asm
 cp #0xb0
 ret nc
 ld c,a
 ld a,(_linkbitqueued)
 or a,a
 jr z,link_bit_done$
 ld a,(_linkbitread)
 ld hl,#_linkbits
 add a,l
 ld l,a
 jr nc,link_bit_address$
 inc h
link_bit_address$:
 ld a,(hl)
 ld (hl),#0
 dec a
 rrca
 rrca
 or a,c
 ld c,a
 ld a,(_linkbitread)
 inc a
 and #15
 ld (_linkbitread),a
 ld hl,#_linkbitqueued
 dec (hl)
link_bit_done$:
 ld a,c
 ret
 __endasm;}
/* Native-only ISR. Raw protocols continue to use the original serial_isr.
   A due clock is started BEFORE copying a reply into the foreground ring. */
void link_serial_isr(void) NONBANKED {uint8_t b=SB_REG,n;
 if(song_link_active||(b==0xFD&&!seqplaying)){song_link_receive(b);return;}
 if(!syncslave){
  if(link_claiming&&((b>=0x80&&b<0xF0)||b==0xF1||b==0xFA||b==0xF5||b==0xF7))linkcollision=1;
  if(syncstart==1&&synctxbyte==0xFA)syncstart=2;
  synctxwait=0;if(native_prepare==5)synctxwait=2;if(syncarmed){synctxwait=3;if(waveengine==3&&syncdivider==1)synctxwait=1;}
  if(syncdue&&native_prepare!=6){syncdue=0;SB_REG=link_clock_byte(0x80|synctick);SC_REG=0x81;}
  /* Reverse traffic is optional. Coalesce idle presence and drop metadata
     when its foreground mailbox is occupied; acknowledgements retry it.
     It must never fill the musical receive queue or hold a clock hostage. */
  if(b==0xF4&&linkstate==2){link_alive=1;if(idle_seen)return;idle_seen=1;}else idle_seen=0;
  if(!b&&!link_peer_capable)return;
  n=wr+1;
  if(link_rx_ready||n==rd){if(link_rx_dropped!=255)link_rx_dropped++;return;}
 }else {
  /* Rearm before ANY optional selection. The previous reply is already
     computed, so incoming clock/marker edges get the original fast path.
     Preparing the following reply never writes the active shift register. */
  if(b==NATIVE_PREPARE)native_prepare=1;
  SB_REG=native_prepare==2?NATIVE_READY:native_prepare?NATIVE_WAIT:reply_byte;SC_REG=0x80;
  if(native_prepare){if(b==0xFA&&native_prepare==2){native_peer_running=1;native_prepare=3;return;}if(b==0xFC){native_prepare=4;return;}if(!b)return;}
  if(sync_raw_ready&&seqplaying&&b>=0x80&&b<0xF0)sync_native_anchor(b);
  if(sync_raw_ready&&seqplaying&&b==0xF9){sync_native_timestamp();return;}
  /* idle_seen doubles as the slave's between-packet heartbeat flag. */
  if(b==0xF5)reply_byte=0xF6;else if(idle_seen){reply_byte=0xF4;idle_seen=0;}else if(linktxread<linktxsize){reply_byte=linktx[linktxread++];if(linktxread==linktxsize&&linkstate==2)idle_seen=1;}else {if(linkstate==2)reply_byte=0xF4;else {reply_byte=probe[probe_phase];probe_phase=(probe_phase+1)&3;}}
  n=wr+1;
 }
 if(n==rd)overflow=1;else {rx[wr]=b;wr=n;}
}

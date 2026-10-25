#pragma bank 6
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
#include "twink_schedule.h"

uint8_t twink_v2,twink_scheduled,twink_reply,twink_ack,twink_v2_blocked;
static uint8_t event_sequence;
static volatile uint8_t wire_sequence,event_window,last_admission;
volatile uint8_t twink_staging,twink_received,twink_event_left,twink_event_pending;
__at (0xFFE8) volatile uint16_t twink_clock;
__at (0xFFEA) volatile uint8_t twink_clock_fraction;
__at (0xFFEB) volatile uint8_t twink_clock_div;
__at (0xFFEC) volatile uint16_t twink_last_anchor;
__at (0xFFEE) volatile uint8_t twink_anchor_second;
__at (0xFFEF) volatile uint8_t twink_anchor_pending;
static uint8_t session,generation,scheduled_slot,probing,warming;
static uint16_t source_generation,signature,scheduled_bpm,service_clock;
static uint16_t step_units;
static uint8_t step_remainder,step_error;
static uint16_t scan_clock;
static uint8_t scan_error;
static uint32_t scan_step,play_step;
extern uint16_t pattern_generation;
extern uint8_t editbuffer_reading;
extern volatile uint8_t padread,padwrite;
extern volatile uint8_t twink_guard,twink_ended_div;
extern volatile uint8_t twinktx[32];
static uint16_t frame_time(void){uint16_t t;__critical{t=sys_time;}return t;}
static uint8_t audible(void){uint8_t solos=seqsolo&111;if(drumsolomask&&(!seqmode||experimental_mode))solos|=64;return !(seqmuted&32)&&(!solos||(solos&32));}

/* CRC7 poly09, exact for all byte pairs; foreground ROM lookup only. */
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

/* Complete frames publish atomically into the existing dedicated TX ring.
   CRC and source work are foreground-only, never part of the byte pump. */
static uint8_t frame(uint8_t type,const uint8_t *payload,uint8_t n){
 uint8_t bytes[16],i,j,crc=0,length=n+2;
 if(type==3&&twink_staging){if((uint8_t)(rd-wr-1)<length+3)return 0;}
 else if(((syncr-syncw-1)&31)<length+3)return 0;
 bytes[0]=0xF2;bytes[1]=length;bytes[2]=type;bytes[3]=session;
 if(n)memcpy(bytes+4,payload,n);
 for(j=1;j<length+2;j++)crc=crc7_table[(crc^bytes[j])&127];
 bytes[length+2]=crc;
 if(type==3&&twink_staging){uint8_t w=wr;if((uint8_t)(rd-w-1)<length+3)return 0;for(i=0;i<length+3;i++){rx[w]=bytes[i];w++;}__critical{wr=w;}return 1;}
 return twink_queue_message(bytes,length+3);
}
static uint16_t fingerprint(void){uint16_t i,h=seqlength[5]^seqeventcounts[5];uint8_t e[4],j,reading=editbuffer_reading;
 editbuffer_reading=0;
 h^=(uint16_t)audible()<<15;
 for(i=0;i<seqeventcounts[5];i++){seq_event_get(5,i,e);for(j=0;j<4;j++)h=(h<<5)^(h>>11)^e[j];}
 editbuffer_reading=reading;return h;
}
static uint8_t source_note(uint8_t step,uint8_t *e){uint8_t found,reading=editbuffer_reading;editbuffer_reading=0;found=seq_note_event(5,step,e);editbuffer_reading=reading;return found;}
static uint16_t now(void){uint16_t n;uint8_t fraction,delta;
 __critical{n=twink_clock;fraction=twink_clock_fraction;delta=DIV_REG-twink_clock_div;}
 return n+((uint16_t)fraction+delta)/16;
}
static uint8_t scheduled_event(const uint8_t *e){uint8_t b[9];uint16_t target=scan_clock;
 /* The old MIDI receive buffer is exclusive to this prebuilt event FIFO
    during negotiated TWINK playback. Reverse traffic uses IRQ mailboxes.
    Foreground prepares, but neither drawing nor parsing clocks delivery. */
 if(twink_v2==2){uint8_t crc=0,value,j,i,w;
  if((uint8_t)(rd-wr-1)<10)return 0;
  b[0]=target&127;b[1]=(target>>7)&127;b[2]=target>>14;b[3]=e[1]-1;b[4]=e[2];b[5]=e[3]&127;b[6]=e[3]>>7;b[7]=event_sequence;
  /* Compact v3 inherits session/generation, but authenticates both in CRC.
     Fixed F4 +8low-seven payload bytes +CRC; anchors may interleave. */
  for(j=0;j<11;j++){value=j==0?6:j==1?session:j==2?generation:b[j-3];crc=crc7_table[(crc^value)&127];}
  w=wr;rx[w++]=0xF4;for(i=0;i<8;i++)rx[w++]=b[i];rx[w++]=crc;__critical{wr=w;}
  event_sequence=(event_sequence+1)&63;return 1;
 }
 b[0]=generation;b[1]=target&127;b[2]=(target>>7)&127;b[3]=target>>14;b[4]=e[1]-1;b[5]=e[2];b[6]=e[3]&127;b[7]=e[3]>>7;b[8]=event_sequence;
 if(!frame(3,b,9))return 0;event_sequence=(event_sequence+1)&63;return 1;
}
static void event_flush(void){__critical{rd=wr=0;twink_event_left=twink_event_pending=0;twink_ack=last_admission=255;wire_sequence=event_sequence;event_window=(wire_sequence+1)&63;}}
static void fill(uint32_t through){uint8_t e[4],budget=16,at;uint16_t length=seqlength[5],error;
 if(!length||(twink_reply==0xD4||twink_reply==0xD5))return;
 while(scan_step<through&&budget--){
  if(twink_staging&&(uint8_t)(rd-wr-1)<(twink_v2==2?10:14))return;
  at=!(length&(length-1))?((uint8_t)scan_step&(uint8_t)(length-1)):scan_step%length;
  if(audible()&&source_note(at,e)&&e[1]&&e[2]){
   if(!scheduled_event(e))return;
  }
  scan_step++;scan_clock+=step_units;error=(uint16_t)scan_error+step_remainder;if(error>=seqbpm){error-=seqbpm;scan_clock++;}scan_error=error;
 }
}
void twink_schedule_reset(uint8_t current) BANKED {
 session=current;generation=1;twink_v2=twink_scheduled=twink_reply=twink_v2_blocked=probing=warming=event_sequence=0;twink_staging=twink_received=0;event_flush();scan_step=0;service_clock=frame_time()-15;
}
void twink_schedule_probe(void) BANKED {uint8_t version=3;
 if(seqplaying||twink_v2||twink_v2_blocked||warming)return;
 if(probing&&(uint16_t)(frame_time()-service_clock)<15)return;
 if(frame(1,&version,1)){probing=1;service_clock=frame_time();}
}
void twink_schedule_stop(void) BANKED {__critical{twink_staging=0;event_sequence=(event_sequence+1)&63;}event_flush();twink_scheduled=warming=0;twink_anchor_pending=0;}
uint8_t twink_schedule_start(void) BANKED {uint8_t b[2],poll=0xF9;uint16_t since;
 if(!twink_v2)return 0;
 warming=1;twink_scheduled=0;event_flush();twink_received=0;twink_staging=1;generation=(generation+1)&127;if(!generation)generation=1;
 twink_reply=0xD1;scan_step=play_step=0;step_units=15360U/seqbpm;step_remainder=15360U%seqbpm;
 scan_clock=0;scan_error=seqbpm/2;
 service_clock=(15360U+seqbpm/2)/seqbpm;step_error=(15360U+seqbpm/2)%seqbpm;scheduled_slot=mx.slot;scheduled_bpm=seqbpm;
 source_generation=pattern_generation;signature=fingerprint();
 __critical{twink_clock=twink_clock_fraction=0;twink_clock_div=DIV_REG;twink_last_anchor=0;twink_anchor_pending=0;}
 b[0]=seqbpm>>7;b[1]=seqbpm&127;
 since=frame_time();while(!frame(2,b,2)){sync_control_service();if((uint16_t)(frame_time()-since)>120)goto failed;}
 b[0]=generation;
 while(!frame(4,b,1)){sync_control_service();if((uint16_t)(frame_time()-since)>120)goto failed;}
 /* Eight sixteenths of prediction, including intentional initial rests.
    Receiver ARM permits an empty queue only after explicit allow-empty. */
 while(scan_step<8){fill(8);twink_service();sync_control_service();if((twink_reply==0xD4||twink_reply==0xD5)||(uint16_t)(frame_time()-since)>120)goto failed;}
 /* ARM follows every staged frame and its admission ACK. Polling runs
    in the IRQ pump even while the foreground is preparing this lookahead. */
 while(rd!=wr||twink_event_left||twink_event_pending||(SC_REG&0x80)){
  twink_service();sync_control_service();if((twink_reply==0xD4||twink_reply==0xD5)||(uint16_t)(frame_time()-since)>120)goto failed;
 }
 b[0]=generation;b[1]=1;
 while(!frame(5,b,2)){sync_control_service();if((uint16_t)(frame_time()-since)>120)goto failed;}
 while(twink_reply!=0xD2){
  /* Replies ride the next master transfer. ARM is prepared in the peer's
     foreground, so its CRC transfer cannot itself return READY. */
  if(syncr==syncw&&!(SC_REG&0x80))twink_queue_message(&poll,1);
  twink_service();sync_control_service();if((twink_reply==0xD4||twink_reply==0xD5)||(uint16_t)(frame_time()-since)>120)goto failed;
 }
 /* Leave a full16-step source runway before GO; only8receiver slots
    need admission/preparation before it starts consuming. Existing rx[]
    holds the remaining prebuilt frames while foreground draws the grid. */
 while(scan_step<16){fill(16);twink_service();sync_control_service();if((twink_reply==0xD4||twink_reply==0xD5)||(uint16_t)(frame_time()-since)>120)goto failed;}
 twink_scheduled=1;warming=0;return 1;
failed:
 twink_v2_blocked=1;twink_staging=0;event_flush();twink_v2=twink_scheduled=warming=0;twink_anchor_pending=0;__critical{syncw=syncr;}return 0;
}
void twink_schedule_service(void) BANKED {uint16_t current,hash,error;uint8_t b[2];uint32_t step;
 if(!twink_v2||!twink_scheduled||warming||!seqplaying)return;
 current=now();
 /* The next step deadline is cached. Doing a32-bit tempo division at
    every audio yield spent the preparation budget before notes needed it. */
 if((int16_t)(current-service_clock)<0&&scan_step>=play_step+16&&source_generation==pattern_generation&&scheduled_slot==mx.slot&&scheduled_bpm==seqbpm)return;
 step=play_step;
 if(scheduled_bpm!=seqbpm){step_units=15360U/seqbpm;step_remainder=15360U%seqbpm;service_clock=(uint16_t)(((step+1)*15360UL+seqbpm/2)/seqbpm);step_error=((step+1)*15360UL+seqbpm/2)%seqbpm;}
 /* Exact rounded rational deadlines. Catch-up must not do a long divide
    for every missed step: under IRQ load that work made itself fall behind. */
 while((int16_t)(current-service_clock)>=0){step++;service_clock+=step_units;error=(uint16_t)step_error+step_remainder;if(error>=seqbpm){error-=seqbpm;service_clock++;}step_error=error;}
 play_step=step;
 if(source_generation!=pattern_generation||scheduled_slot!=mx.slot||scheduled_bpm!=seqbpm){
  hash=fingerprint();
  if(hash!=signature||scheduled_slot!=mx.slot||scheduled_bpm!=seqbpm){
   b[0]=(generation+1)&127;if(!b[0])b[0]=1;
   b[1]=audible()?0:1;
   if(!frame(4,b,b[1]?2:1))return;
   event_flush();generation=b[0];scan_step=step+1;scan_clock=service_clock;scan_error=step_error;signature=hash;scheduled_slot=mx.slot;scheduled_bpm=seqbpm;
  }
  source_generation=pattern_generation;
 }
 fill(step+16);
}
/* Repeated replies describe the same absolute admission window. This
   foreground-free arithmetic runs only when its byte actually changes. */
static void admission(void){uint8_t ack,delta,end,room;
 last_admission=twink_ack;ack=(wire_sequence-twink_event_pending-1)&63;delta=((last_admission>>3)-(ack&15))&15;
 if(delta<=twink_event_pending){ack=(ack+delta)&63;twink_event_pending-=delta;end=(ack+1+(last_admission&7))&63;room=(end-wire_sequence)&63;if(room<=7&&((end-event_window)&63)<32)event_window=end;}
}
/* One prebuilt byte per call. No source lookup, CRC, division, synthesis,
   or interrupt-enabling helper. HRAM clock math avoids C stack spills in
   this1024Hz path; control and EVENT bodies stay indivisible. */
void twink_v2_irq(void) BANKED __naked {__asm
 ldh a,(#0x04)
 ld d,a
 ldh a,(_twink_clock_div)
 ld e,a
 ld a,d
 ldh (_twink_clock_div),a
 sub a,e
 ld e,a
 and #15
 ld c,a
 ldh a,(_twink_clock_fraction)
 add a,c
 ld c,a
 and #15
 ldh (_twink_clock_fraction),a
 ld a,e
 swap a
 and #15
 ld b,a
 ld a,c
 and #16
 jr z,v2_clock_add$
 inc b
v2_clock_add$:
 ldh a,(_twink_clock)
 add a,b
 ldh (_twink_clock),a
 ldh a,(_twink_clock+1)
 adc a,#0
 ldh (_twink_clock+1),a
 ld a,(_twink_guard)
 or a
 jr z,v2_bus_check$
 ld a,(_twink_ended_div)
 ld e,a
 ld a,d
 sub a,e
 cp #24
 ret c
 xor a
 ld (_twink_guard),a
v2_bus_check$:
 ldh a,(#0x02)
 bit 7,a
 ret nz
 ldh a,(#0x0f)
 bit 3,a
 ret nz
 ld a,(_twink_staging)
 or a
 jr z,v2_anchor_check$
 ld a,(_twink_ack)
 bit 7,a
 jr nz,v2_anchor_check$
 ld e,a
 ld a,(_last_admission)
 cp a,e
 jr z,v2_anchor_check$
 call _admission
v2_anchor_check$:
 ldh a,(_twink_anchor_pending)
 or a
 jr z,v2_anchor_first$
 ldh a,(_twink_anchor_second)
 ldh (#0x01),a
 xor a
 ldh (_twink_anchor_pending),a
 jp v2_send$
v2_anchor_first$:
 ldh a,(_syncarmed)
 or a
 jp z,v2_payload$
 ldh a,(_syncstart)
 or a
 jp nz,v2_payload$
 ldh a,(_twink_clock)
 ld b,a
 ldh a,(_twink_last_anchor)
 ld e,a
 ld a,b
 sub a,e
 ld e,a
 ldh a,(_twink_clock+1)
 ld c,a
 ldh a,(_twink_last_anchor+1)
 ld d,a
 ld a,c
 sbc a,d
 jr nz,v2_anchor_due$
 ld a,e
 cp #32
 jp c,v2_payload$
 ; Backlogged future notes get line headroom, while anchors still coast
 ; at most64ms (64us drift at1000ppm) before the next correction sample.
 ld a,(_twink_staging)
 or a
 jr z,v2_anchor_due$
 ld a,(_rd)
 ld hl,#_wr
 cp a,(hl)
 jr z,v2_anchor_due$
 ld a,e
 cp #64
 jp c,v2_payload$
v2_anchor_due$:
 ld a,b
 ldh (_twink_last_anchor),a
 ld a,c
 ldh (_twink_last_anchor+1),a
 and #7
 swap a
 ld d,a
 ld a,b
 swap a
 and #12
 or a,d
 ld d,a
 ldh a,(_twink_clock_fraction)
 srl a
 srl a
 or a,d
 ldh (_twink_anchor_second),a
 ld a,#1
 ldh (_twink_anchor_pending),a
 ld a,b
 and #63
 or #0x80
 ldh (#0x01),a
 jp v2_send$
v2_payload$:
 ld a,(_twink_event_left)
 or a
 jr z,v2_control$
 dec a
 ld (_twink_event_left),a
 jp v2_read_event$
v2_control$:
 ldh a,(_syncr)
 ld b,a
 ldh a,(_syncw)
 cp a,b
 jr z,v2_event_start$
 ld hl,#_twinktx
 ld a,b
 add a,l
 ld l,a
 jr nc,v2_control_address$
 inc h
v2_control_address$:
 ld a,(hl)
 ldh (_synctxbyte),a
 ldh (#0x01),a
 ld a,b
 inc a
 and #31
 ldh (_syncr),a
 jp v2_send$
v2_event_start$:
 ld a,(_twink_staging)
 or a
 ret z
 ld a,(_rd)
 ld b,a
 ld a,(_wr)
 cp a,b
 jr z,v2_poll$
 ld a,(_twink_event_pending)
 cp #4
 jr nc,v2_poll$
 ld a,(_wire_sequence)
 ld b,a
 ld a,(_event_window)
 cp a,b
 jr z,v2_poll$
 ld hl,#_twink_event_pending
 inc (hl)
 ld a,b
 inc a
 and #63
 ld (_wire_sequence),a
 ld a,(_twink_v2)
 cp #2
 ld a,#13
 jr nz,v2_event_length$
 ld a,#9
v2_event_length$:
 ld (_twink_event_left),a
v2_read_event$:
 ld a,(_rd)
 ld b,a
 ld hl,#_rx
 add a,l
 ld l,a
 jr nc,v2_event_address$
 inc h
v2_event_address$:
 ld a,(hl)
 ldh (#0x01),a
 ld a,b
 inc a
 ld (_rd),a
 jr v2_send$
v2_poll$:
 ld a,(_twink_event_pending)
 or a
 ret z
 ld a,#0xF9
 ldh (#0x01),a
v2_send$:
 ; Bound receiver rearm from the wire's completion, not from when this
 ; CPU eventually services its SIO interrupt. Standard serial takes16DIV;
 ; two extra DIV cover sampling/write phase before the24DIV safety guard.
 ldh a,(#0x04)
 add a,#18
 ld (_twink_ended_div),a
 ld a,#0x81
 ldh (#0x02),a
 ret
 __endasm;}

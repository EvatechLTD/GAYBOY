#pragma bank 14
#pragma opt_code_speed
#include "api.h"
#include "storage.h"
/* Replaces the old1152-byte melodic arrays and1024-byte live DRUM arrays.
   Do not link alongside those old arrays: the SRAM half has the same address. */
uint8_t seqevents_lo[256][4];
__at (0xA800) uint8_t seqevents_hi[256][4];
uint16_t seqeventcounts[7],seqeventoffsets[7];
uint8_t seqeventfull;
/* A quantized Mixer handoff can play the validated prefetched pool while
   copying it into live memory; audio never sees a half-installed pattern. */
uint8_t seqeventcache;
static uint8_t *event_address(uint16_t index){if(seqeventcache)return (uint8_t *)0xB020+index*4;return index<256?seqevents_lo[index]:seqevents_hi[index-256];}
static uint16_t event_total(void){return seqeventoffsets[6]+seqeventcounts[6];}
static void event_offsets(void){uint8_t c;uint16_t offset=0;for(c=0;c<7;c++){seqeventoffsets[c]=offset;offset+=seqeventcounts[c];}}
/* Near SDCC ABI: pointer DE, record count BC, step on stack. Return the
   number of records remaining at a match, or zero. Each span stays inside
   one physical memory half; note-zero Mixer placeholders are skipped. */
uint16_t storage_scan_step(uint8_t *src,uint16_t count,uint8_t step) __naked {
 __asm
 ld a,b
 or a,c
 jr z,storage_scan_done$
 ldhl sp,#2
 ld a,(hl)
 ld h,a
storage_scan_loop$:
 ld a,(de)
 cp a,h
 jr nz,storage_scan_skip$
 inc de
 ld a,(de)
 dec de
 or a,a
 jr nz,storage_scan_done$
storage_scan_skip$:
 inc de
 inc de
 inc de
 inc de
 dec bc
 ld a,b
 or a,c
 jr nz,storage_scan_loop$
storage_scan_done$:
 pop hl
 inc sp
 jp (hl)
 __endasm;
}
static uint16_t event_find(uint8_t c,uint8_t step){
 uint16_t start=seqeventoffsets[c],count=seqeventcounts[c],span,left;
 if(start<256){span=256-start;if(span>count)span=count;left=storage_scan_step(event_address(start),span,step);if(left)return start+span-left;start+=span;count-=span;}
 if(count){left=storage_scan_step(event_address(start),count,step);if(left)return start+count-left;}
 return SEQ_EVENT_APPEND;
}

static void event_move(uint16_t to,uint16_t from){uint8_t *dst=event_address(to),*src=event_address(from);dst[0]=src[0];dst[1]=src[1];dst[2]=src[2];dst[3]=src[3];}
/* Shifts are bounded by the512-event pool. Audio IRQs remain enabled and the
   foreground audio service runs every eight events; musical elapsed ticks
   accumulate until the completed edit is published. */
static void event_yield(uint16_t index){if(!(index&7))mixfill();}
uint16_t seq_event_count(uint8_t c) BANKED {return c<7?seqeventcounts[c]:0;}
uint16_t seq_event_total(void) BANKED {return event_total();}
uint8_t seq_event_get(uint8_t c,uint16_t index,uint8_t *event) BANKED {
 if(c>=7||index>=seqeventcounts[c])return 0;memcpy(event,event_address(seqeventoffsets[c]+index),4);return 1;
}
/* Cursor starts at zero. The scan stays inside this ROM bank instead of
   paying a banked trampoline for every event at every sequencer step. */
uint8_t seq_event_next_step(uint8_t c,uint8_t step,uint16_t *cursor,uint8_t *event) BANKED {
 uint16_t at,count,span,left,i;if(c>=7)return 0;i=*cursor;if(i>=seqeventcounts[c])return 0;at=seqeventoffsets[c]+i;count=seqeventcounts[c]-i;
 if(at<256){span=256-at;if(span>count)span=count;left=storage_scan_step(event_address(at),span,step);if(left){at+=span-left;goto found;}at+=span;count-=span;}
 if(count){left=storage_scan_step(event_address(at),count,step);if(left){at+=count-left;goto found;}}
 *cursor=seqeventcounts[c];return 0;
found:memcpy(event,event_address(at),4);*cursor=at-seqeventoffsets[c]+1;return 1;
}

uint8_t seq_note_event(uint8_t c,uint8_t step,uint8_t *event) BANKED {
 uint16_t i;if(c>=6)return 0;i=event_find(c,step);if(i==SEQ_EVENT_APPEND)return 0;memcpy(event,event_address(i),4);return 1;
}
uint8_t seq_event_put(uint8_t c,uint16_t index,const uint8_t *event) BANKED {
 uint16_t at,i,total;uint8_t busy,copy[4];
 if(c>=7||!event[1]||event[1]>(c==6?13:128)||event[2]>127)return 0;
 memcpy(copy,event,4);
 if(index!=SEQ_EVENT_APPEND){if(index>=seqeventcounts[c])return 0;memcpy(event_address(seqeventoffsets[c]+index),copy,4);seqeventfull=0;return 1;}
 total=event_total();if(total>=SEQ_EVENT_CAPACITY){seqeventfull=1;return 0;}
 busy=seqservicing;seqservicing=1;at=seqeventoffsets[c]+seqeventcounts[c];
 for(i=total;i>at;i--){event_move(i,i-1);event_yield(i);}
 memcpy(event_address(at),copy,4);seqeventcounts[c]++;event_offsets();seqeventfull=0;seqservicing=busy;return 1;
}
void seq_event_erase(uint8_t c,uint16_t index) BANKED {
 uint16_t i,total;uint8_t busy;if(c>=7||index>=seqeventcounts[c])return;
 busy=seqservicing;seqservicing=1;total=event_total();
 for(i=seqeventoffsets[c]+index;i+1<total;i++){event_move(i,i+1);event_yield(i);}
 seqeventcounts[c]--;event_offsets();seqeventfull=0;seqservicing=busy;
}
void seq_storage_clear(void) BANKED {uint16_t i;uint8_t busy=seqservicing;seqservicing=1;seqeventcache=0;memset(seqeventcounts,0,sizeof(seqeventcounts));memset(seqeventoffsets,0,sizeof(seqeventoffsets));for(i=0;i<512;i+=4){memset(event_address(i),0,16);mixfill();}seqeventfull=0;seqservicing=busy;}
uint8_t seq_note_get(uint8_t c,uint8_t step) BANKED {uint16_t i;if(c>=6)return 0;i=event_find(c,step);return i==SEQ_EVENT_APPEND?0:event_address(i)[1];}
uint8_t seq_velocity_get(uint8_t c,uint8_t step) BANKED {uint16_t i;if(c>=6)return 0;i=event_find(c,step);return i==SEQ_EVENT_APPEND?0:event_address(i)[2];}
uint16_t seq_duration_get(uint8_t c,uint8_t step) BANKED {uint16_t i;uint8_t d;if(c>=6)return 0;i=event_find(c,step);if(i==SEQ_EVENT_APPEND)return 0;d=event_address(i)[3];return d?d:256;}
uint8_t seq_note_set(uint8_t c,uint8_t step,uint8_t note,uint8_t velocity,uint16_t duration) BANKED {
 uint16_t i;uint8_t event[4];if(c>=6||note>128||velocity>127)return 0;
 i=event_find(c,step);
 if(!note){if(i!=SEQ_EVENT_APPEND)seq_event_erase(c,i-seqeventoffsets[c]);return 1;}
 if(!duration||duration>256)return 0;event[0]=step;event[1]=note;event[2]=velocity;event[3]=(uint8_t)duration;
 return seq_event_put(c,i==SEQ_EVENT_APPEND?SEQ_EVENT_APPEND:i-seqeventoffsets[c],event);
}

#pragma bank 14
#pragma opt_code_speed
#include "api.h"
#include "storage.h"
#include "mixer_shared.h"
#include "resident.h"
void eval_chord_dirty(uint8_t c) BANKED;
uint16_t seqeventcounts[7],seqeventoffsets[7];uint8_t seqeventfull,seqeventcache;
/* Address index only: the note records remain resident in their five pools.
   Hash collisions are filtered by track range and step; chains retain insertion order. */
__at (0xA000) uint16_t eventheads[256];
__at (0xA200) uint16_t eventnext[256];
static uint8_t indexvalid,indexslot;
static uint16_t indexcount;
static uint16_t total(void){return seqeventoffsets[6]+seqeventcounts[6];}
static void offsets(void){uint8_t c;uint16_t n=0;for(c=0;c<7;c++){seqeventoffsets[c]=n;n+=seqeventcounts[c];}}
static void changed(uint8_t c){indexvalid=0;offsets();if(c==6)eval_drum_dirty();else eval_chord_dirty(c);resident_events_changed();seqeventfull=0;}
uint16_t seq_event_count(uint8_t c) BANKED {return c<7?seqeventcounts[c]:0;}
uint16_t seq_event_total(void) BANKED {return total();}
static void readnote(uint16_t index,uint8_t *e){uint8_t a,b,c,d;uint8_t bank=1+(mx.slot>>2);const uint8_t *p=(const uint8_t *)(0xA000U+(uint16_t)(mx.slot&3)*2048U+RESIDENT_EVENTS+index*4);__critical{SWITCH_RAM_MBC5(bank);a=*p++;b=*p++;c=*p++;d=*p;SWITCH_RAM_MBC5(0);}e[0]=a;e[1]=b;e[2]=c;e[3]=d;}
uint8_t seq_event_get(uint8_t c,uint16_t i,uint8_t *e) BANKED {if(c>=7||i>=seqeventcounts[c])return 0;readnote(seqeventoffsets[c]+i,e);return 1;}
static uint8_t indexbuildbank,indexbuildhash;
static uint16_t indexbuildnext,indexbuildvalue;
/* Read only each onset byte, then link its existing record address. IRQs remain
   available between records; the note-bank selection spans just one byte read. */
static void index_track(const uint8_t *source,uint16_t count) __naked {__asm
 ld a,b
 or a,c
 ret z
index_loop$:
 push bc
 ldh a,(0xff)
 push af
 xor a
 ldh (0xff),a
 ld a,(_indexbuildbank)
 ld (#0x4000),a
 ld a,(de)
 ld l,a
 xor a
 ld (#0x4000),a
 pop af
 ldh (0xff),a
 ld a,(_indexbuildhash)
 add a,l
 add a,a
 ld l,a
 ld h,#0xa0
 jr nc,index_head$
 inc h
index_head$:
 push de
 ld c,(hl)
 inc hl
 ld b,(hl)
 ld a,(_indexbuildnext)
 ld e,a
 ld a,(_indexbuildnext+1)
 ld d,a
 ld a,c
 ld (de),a
 inc de
 ld a,b
 ld (de),a
 ld a,(_indexbuildvalue+1)
 ld (hl-),a
 ld a,(_indexbuildvalue)
 ld (hl),a
 ld hl,#_indexbuildnext
 ld a,(hl)
 sub #2
 ld (hl+),a
 ld a,(hl)
 sbc a,#0
 ld (hl),a
 ld hl,#_indexbuildvalue
 ld a,(hl)
 sub #1
 ld (hl+),a
 ld a,(hl)
 sbc a,#0
 ld (hl),a
 pop de
 dec de
 dec de
 dec de
 dec de
 pop bc
 dec bc
 ld a,b
 or a,c
 jr nz,index_loop$
 ret
 __endasm;}
static void prepare_index(void){uint16_t n=total(),end;uint8_t c;if(n<32)return;if(indexvalid&&indexslot==mx.slot&&indexcount==n)return;memset(eventheads,0,sizeof(eventheads));indexbuildbank=1+(mx.slot>>2);for(c=0;c<7;c++)if(seqeventcounts[c]){end=seqeventoffsets[c]+seqeventcounts[c];indexbuildhash=c*37;indexbuildvalue=end;indexbuildnext=0xA200U+(end-1)*2;index_track((const uint8_t *)(0xA000U+(uint16_t)(mx.slot&3)*2048U+RESIDENT_EVENTS+(end-1)*4),seqeventcounts[c]);}indexslot=mx.slot;indexcount=n;indexvalid=1;}
uint8_t seq_event_next_step(uint8_t c,uint8_t step,uint16_t *cursor,uint8_t *e) BANKED {uint16_t i,begin,end,prior;if(c>=7)return 0;if(*cursor>=seqeventcounts[c])return 0;if(total()<32||(!seqplaying&&!indexvalid)){i=*cursor;while(i<seqeventcounts[c]){readnote(seqeventoffsets[c]+i++,e);if(e[0]==step&&e[1]){*cursor=i;return 1;}}*cursor=i;return 0;}prepare_index();begin=seqeventoffsets[c];end=begin+seqeventcounts[c];i=eventheads[(uint8_t)(step+c*37)];if(*cursor){prior=begin+*cursor-1;readnote(prior,e);if(e[0]==step)i=eventnext[prior];}while(i){i--;if(i>=begin+*cursor&&i>=begin&&i<end){readnote(i,e);if(e[0]==step&&e[1]){*cursor=i-begin+1;return 1;}}i=eventnext[i];}*cursor=seqeventcounts[c];return 0;}
uint8_t seq_note_event(uint8_t c,uint8_t step,uint8_t *e) BANKED {uint16_t i=0;uint8_t next[4],found=0;while(seq_event_next_step(c,step,&i,next))if(!found||next[1]<e[1]){memcpy(e,next,4);found=1;}return found;}
void seq_event_erase(uint8_t c,uint16_t i) BANKED {uint16_t at;if(c>=7||i>=seqeventcounts[c])return;at=seqeventoffsets[c]+i;resident_move(at*4,(at+1)*4,(total()-at-1)*4);seqeventcounts[c]--;changed(c);}
uint8_t seq_event_put(uint8_t c,uint16_t i,const uint8_t *event) BANKED {uint8_t e[4],old[4];uint16_t at,n;if(c>=7||!event[1]||event[2]>127)return 0;memcpy(e,event,4);
 if(i!=65535U){if(i>=seqeventcounts[c])return 0;resident_write(mx.slot,RESIDENT_EVENTS+(seqeventoffsets[c]+i)*4,e,4);changed(c);return 1;}
 n=total();if(n>=RESIDENT_NOTES){seqeventfull=1;return 0;}i=seqeventcounts[c];
 at=seqeventoffsets[c]+i;resident_move((at+1)*4,at*4,(n-at)*4);resident_write(mx.slot,RESIDENT_EVENTS+at*4,e,4);seqeventcounts[c]++;changed(c);return 1;}
void seq_track_clear(uint8_t c) BANKED {uint16_t at,end;if(c>=7)return;at=seqeventoffsets[c];end=at+seqeventcounts[c];resident_move(at*4,end*4,(total()-end)*4);seqeventcounts[c]=0;changed(c);}
void seq_storage_clear(void) BANKED {indexvalid=0;memset(seqeventcounts,0,14);memset(seqeventoffsets,0,14);resident_events_changed();seqeventfull=0;}
static uint16_t find(uint8_t c,uint8_t step,uint8_t note){uint16_t cursor=0;uint8_t e[4];while(seq_event_next_step(c,step,&cursor,e))if(!note||e[1]==note)return cursor-1;return 65535U;}
uint8_t seq_note_get(uint8_t c,uint8_t step) BANKED {uint16_t i;uint8_t e[4];i=find(c,step,page==8?seqpitch[c]+1:0);return i==65535U?0:seq_event_get(c,i,e)?e[1]:0;}
uint8_t seq_velocity_get(uint8_t c,uint8_t step) BANKED {uint16_t i;uint8_t e[4];i=find(c,step,page==8?seqpitch[c]+1:0);return i==65535U?0:seq_event_get(c,i,e)?e[2]:0;}
uint16_t seq_duration_get(uint8_t c,uint8_t step) BANKED {uint16_t i;uint8_t e[4];i=find(c,step,page==8?seqpitch[c]+1:0);return i==65535U?0:seq_event_get(c,i,e)?e[3]?e[3]:256U:0;}
uint8_t seq_note_set(uint8_t c,uint8_t step,uint8_t note,uint8_t velocity,uint16_t duration) BANKED {uint16_t i;uint8_t e[4];if(c>=4||duration>256)return 0;i=find(c,step,note?note:seqpitch[c]+1);if(!note){if(i!=65535U)seq_event_erase(c,i);return 1;}e[0]=step;e[1]=note;e[2]=velocity;e[3]=duration;return seq_event_put(c,i,e);}
void storage_sorted_dirty(void) BANKED {indexvalid=0;} void storage_sorted_install(uint8_t mask) BANKED {(void)mask;}
void storage_sorted_prepare(void) BANKED {prepare_index();} void storage_cursor_reset(void) BANKED {}

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
/* Two immutable playback snapshots in free bank-2 SRAM, after user kits.
   256 records, byte chains with self-end sentinels, hash validity bitmap.
   Bank 2 A000..A7FF is pad 5; A800..ACFF is user kits. */
#define EB_BASE0 0xAD00U
#define EB_BASE1 0xB620U
#define EB_HEAD 1792U
#define EB_NEXT 2048U
#define EB_BITS 2304U
uint8_t editbuffer_reading,editbuffer_valid,editbuffer_ready,editbuffer_irq_mask;
static uint8_t eb_newmask;
uint16_t editbuffer_swaps,editbuffer_restarts;
static uint8_t eb_slot=255,eb_building,eb_buildtrack;
uint16_t editbuffer_base=EB_BASE0;
static uint16_t eb_target=EB_BASE1,eb_generation,eb_activegeneration,eb_left;
static uint16_t eb_counts[7],eb_offsets[7],eb_newcounts[7],eb_newoffsets[7];
extern uint16_t pattern_generation;
extern const uint16_t notes[140];
extern volatile uint8_t padread,padwrite,padsampled;
extern uint16_t seqdeadline;
void editbuffer_reset(void) BANKED {editbuffer_valid=editbuffer_ready=eb_building=editbuffer_reading=0;eb_slot=255;}
uint8_t editbuffer_active(void) BANKED {return editbuffer_valid&&seqplaying&&page==8&&eb_slot==mx.slot;}
static uint16_t total(void){return seqeventoffsets[6]+seqeventcounts[6];}
static void offsets(void){uint8_t c;uint16_t n=0;for(c=0;c<7;c++){seqeventoffsets[c]=n;n+=seqeventcounts[c];}}
static void changed(uint8_t c){indexvalid=0;offsets();if(!editbuffer_active()){if(c==6)eval_drum_dirty();else eval_chord_dirty(c);}resident_events_changed();seqeventfull=0;}
uint16_t seq_event_count(uint8_t c) BANKED {return c<7?(editbuffer_reading?eb_counts[c]:seqeventcounts[c]):0;}
uint16_t seq_event_total(void) BANKED {return total();}
static void readnote(uint16_t index,uint8_t *e){uint8_t a,b,c,d;uint8_t bank=1+(mx.slot>>2);const uint8_t *p=(const uint8_t *)(0xA000U+(uint16_t)(mx.slot&3)*2048U+RESIDENT_EVENTS+index*4);__critical{SWITCH_RAM_MBC5(bank);a=*p++;b=*p++;c=*p++;d=*p;SWITCH_RAM_MBC5(0);}e[0]=a;e[1]=b;e[2]=c;e[3]=d;}
static uint8_t eb_byte(uint16_t address){uint8_t v;__critical{SWITCH_RAM_MBC5(2);v=*(uint8_t *)address;SWITCH_RAM_MBC5(0);}return v;}
static void eb_note(uint16_t i,uint8_t *e){uint8_t a,b,c,d;const uint8_t *p=(const uint8_t *)(editbuffer_base+i*7);__critical{SWITCH_RAM_MBC5(2);a=*p++;b=*p++;c=*p++;d=*p;SWITCH_RAM_MBC5(0);}e[0]=a;e[1]=b;e[2]=c;e[3]=d;}
void seq_irq_prepare(void) BANKED;
void seq_irq_launch(void) BANKED;
void editbuffer_service(void) BANKED {uint8_t e[4],hash,mask,*dst,*bits,*head,v,amp;uint16_t at,f,scaled;
 if(!seqplaying||page!=8||mx.slot!=eb_slot){if(editbuffer_valid)seq_irq_launch();editbuffer_valid=editbuffer_ready=eb_building=0;eb_slot=mx.slot;}
 if(!seqplaying||page!=8||seqservicing||padread!=padwrite||seqticks>=seqdeadline||seqdeadline-seqticks<4)return;
 if(editbuffer_valid)seq_irq_prepare();
 if(editbuffer_valid&&eb_activegeneration==pattern_generation)return;
 /* Painting/dragging gets the foreground budget. Keep the old snapshot until
    the gesture ends, then prepare and publish the finished edit at a loop. */
 if(editbuffer_valid&&(padsampled&(J_A|J_B)))return;
 if((eb_building||editbuffer_ready)&&eb_generation!=pattern_generation){eb_building=editbuffer_ready=0;editbuffer_restarts++;}
 if(editbuffer_ready)return;
 if(!eb_building){eb_target=editbuffer_base==EB_BASE0?EB_BASE1:EB_BASE0;memcpy(eb_newcounts,seqeventcounts,14);memcpy(eb_newoffsets,seqeventoffsets,14);eb_generation=pattern_generation;eb_left=total();eb_buildtrack=6;eb_newmask=7;for(hash=0;hash<4;hash++)if(seqlength[hash]>64)eb_newmask&=~(1<<hash);for(hash=4;hash<7;hash++)if(eb_newcounts[hash])eb_newmask&=~(1<<(hash-4));
  __critical{SWITCH_RAM_MBC5(2);memset((void *)(eb_target+EB_BITS),0,32);SWITCH_RAM_MBC5(0);}eb_building=1;return;}
 if(!eb_left){editbuffer_ready=1;eb_building=0;return;}
 at=--eb_left;while(eb_buildtrack&&at<eb_newoffsets[eb_buildtrack])eb_buildtrack--;readnote(at,e);hash=e[0]+eb_buildtrack*64;
 f=eb_buildtrack<3?notes[e[1]-1+(eb_buildtrack==2?12:0)]:0;v=e[2];if(mx.level[eb_buildtrack]!=127){scaled=(uint16_t)v*mx.level[eb_buildtrack]+63;v=(scaled>>7)+((uint8_t)((scaled&127)+(scaled>>7))>=127);}
 scaled=eb_buildtrack<4?(uint16_t)param[eb_buildtrack][1]*v:0;amp=(scaled+1+(scaled>>7))>>7;
 if(eb_buildtrack==2){amp=v?(v>84?1:v>42?2:3):0;if(amp&&param[2][15]){amp+=param[2][15]-1;if(amp>3)amp=3;}else amp=0;amp<<=5;}mask=1U<<(hash&7);
 dst=(uint8_t *)(eb_target+at*7);bits=(uint8_t *)(eb_target+EB_BITS+(hash>>3));head=(uint8_t *)(eb_target+EB_HEAD+hash);
 __critical{SWITCH_RAM_MBC5(2);memcpy(dst,e,4);dst[4]=f;dst[5]=f>>8;dst[6]=amp;
 if((*bits&mask)&&eb_buildtrack<4&&e[1]>=*(uint8_t *)(eb_target+(uint16_t)*head*7+1)){uint8_t *link=(uint8_t *)(eb_target+EB_NEXT+*head);*(uint8_t *)(eb_target+EB_NEXT+at)=*link==*head?(uint8_t)at:*link;*link=at;}
 else{*(uint8_t *)(eb_target+EB_NEXT+at)=(*bits&mask)?*head:(uint8_t)at;*head=at;}*bits|=mask;SWITCH_RAM_MBC5(0);}
}
void editbuffer_boundary(void) BANKED {uint8_t c,track=255;uint16_t longest=0;
 if(page!=8||!editbuffer_ready||eb_slot!=mx.slot||eb_generation!=pattern_generation)return;
 for(c=0;c<7;c++)if((editbuffer_valid?eb_counts[c]:seqeventcounts[c])&&seqlength[c]>longest){longest=seqlength[c];track=c;}
 if(track!=255&&(uint16_t)seqposition[track]+1<seqlength[track])return;
 __critical{editbuffer_base=eb_target;memcpy(eb_counts,eb_newcounts,14);memcpy(eb_offsets,eb_newoffsets,14);eb_activegeneration=eb_generation;editbuffer_irq_mask=eb_newmask;editbuffer_valid=editbuffer_reading=1;editbuffer_ready=0;editbuffer_swaps++;}
 for(c=0;c<3;c++)eval_chord_dirty(c);eval_drum_dirty();
}
/* Called only by the timer. Interrupted foreground SRAM transactions always
   restore bank zero before re-enabling interrupts. Never bank ROM here. */
uint8_t editbuffer_irq_event(uint8_t c,uint8_t step,uint8_t *out) NONBANKED {uint8_t h=step+(c<<6),i,found=0,ie=IE_REG,*base=(uint8_t *)editbuffer_base;
 IE_REG=0;SWITCH_RAM_MBC5(2);if(base[EB_BITS+(h>>3)]&(1U<<(h&7))){i=base[EB_HEAD+h];memcpy(out,base+(uint16_t)i*7,7);found=1;}SWITCH_RAM_MBC5(0);IE_REG=ie;return found;
}
static uint8_t eb_step(uint8_t c,uint8_t step,uint16_t *cursor,uint8_t *e){uint8_t h=step+c*64,i,next;uint16_t begin=eb_offsets[c],end=begin+eb_counts[c],limit=256,best=256;
 if(*cursor>=eb_counts[c]||!(eb_byte(editbuffer_base+EB_BITS+(h>>3))&(1U<<(h&7)))){*cursor=eb_counts[c];return 0;}
 i=eb_byte(editbuffer_base+EB_HEAD+h);while(limit--){if(i>=begin+*cursor&&i>=begin&&i<end&&i<best){eb_note(i,e);if(e[0]==step&&e[1])best=i;}next=eb_byte(editbuffer_base+EB_NEXT+i);if(next==i)break;i=next;}
 if(best<256){eb_note(best,e);*cursor=best-begin+1;return 1;}*cursor=eb_counts[c];return 0;
}
uint8_t seq_event_get(uint8_t c,uint16_t i,uint8_t *e) BANKED {if(c>=7)return 0;if(editbuffer_reading){if(i>=eb_counts[c])return 0;eb_note(eb_offsets[c]+i,e);return 1;}if(i>=seqeventcounts[c])return 0;readnote(seqeventoffsets[c]+i,e);return 1;}
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
uint8_t seq_event_next_step(uint8_t c,uint8_t step,uint16_t *cursor,uint8_t *e) BANKED {uint16_t i,begin,end,prior;if(c>=7)return 0;if(editbuffer_reading)return eb_step(c,step,cursor,e);if(*cursor>=seqeventcounts[c])return 0;if(total()<32||(!seqplaying&&!indexvalid)){i=*cursor;while(i<seqeventcounts[c]){readnote(seqeventoffsets[c]+i++,e);if(e[0]==step&&e[1]){*cursor=i;return 1;}}*cursor=i;return 0;}prepare_index();begin=seqeventoffsets[c];end=begin+seqeventcounts[c];i=eventheads[(uint8_t)(step+c*37)];if(*cursor){prior=begin+*cursor-1;readnote(prior,e);if(e[0]==step)i=eventnext[prior];}while(i){i--;if(i>=begin+*cursor&&i>=begin&&i<end){readnote(i,e);if(e[0]==step&&e[1]){*cursor=i-begin+1;return 1;}}i=eventnext[i];}*cursor=seqeventcounts[c];return 0;}
uint8_t seq_note_event(uint8_t c,uint8_t step,uint8_t *e) BANKED {uint16_t i=0;uint8_t next[4],found=0;while(seq_event_next_step(c,step,&i,next))if(!found||next[1]<e[1]){memcpy(e,next,4);found=1;}return found;}
void native_edit_mark(uint8_t c,const uint8_t *old,const uint8_t *next) BANKED;
void seq_event_erase(uint8_t c,uint16_t i) BANKED {uint16_t at;uint8_t old[4];if(c>=7||i>=seqeventcounts[c])return;at=seqeventoffsets[c]+i;readnote(at,old);native_edit_mark(c,old,0);resident_move(at*4,(at+1)*4,(total()-at-1)*4);seqeventcounts[c]--;changed(c);}
uint8_t seq_event_put(uint8_t c,uint16_t i,const uint8_t *event) BANKED {uint8_t e[4],old[4];uint16_t at,n;if(c==3||c>=7||!event[1]||event[2]>127)return 0;memcpy(e,event,4);if(c<3&&eval_mode(c)&&i==65535U&&seq_note_event(c,e[0],old))e[2]=old[2];
 if(i!=65535U){if(i>=seqeventcounts[c])return 0;at=seqeventoffsets[c]+i;readnote(at,old);native_edit_mark(c,old,e);resident_write(mx.slot,RESIDENT_EVENTS+at*4,e,4);
  /* Velocity cannot change address chains or drum voice admission. */
  if(old[0]==e[0]){if(!editbuffer_active()){if(c!=6)eval_chord_dirty(c);else if(old[1]!=e[1]||old[3]!=e[3])eval_drum_dirty();}resident_events_changed();seqeventfull=0;}else changed(c);return 1;}
 n=total();if(n>=RESIDENT_NOTES){seqeventfull=1;return 0;}i=seqeventcounts[c];
 at=seqeventoffsets[c]+i;native_edit_mark(c,0,e);resident_move((at+1)*4,at*4,(n-at)*4);resident_write(mx.slot,RESIDENT_EVENTS+at*4,e,4);seqeventcounts[c]++;changed(c);return 1;}
void seq_track_clear(uint8_t c) BANKED {uint16_t at,end;if(c>=7)return;at=seqeventoffsets[c];end=at+seqeventcounts[c];resident_move(at*4,end*4,(total()-end)*4);seqeventcounts[c]=0;changed(c);}
void seq_storage_clear(void) BANKED {indexvalid=0;memset(seqeventcounts,0,14);memset(seqeventoffsets,0,14);resident_events_changed();seqeventfull=0;}
static uint16_t find(uint8_t c,uint8_t step,uint8_t note){uint16_t cursor=0;uint8_t e[4];while(seq_event_next_step(c,step,&cursor,e))if(!note||e[1]==note)return cursor-1;return 65535U;}
uint8_t seq_note_get(uint8_t c,uint8_t step) BANKED {uint16_t i;uint8_t e[4];i=find(c,step,page==8?seqpitch[c]+1:0);return i==65535U?0:seq_event_get(c,i,e)?e[1]:0;}
uint8_t seq_velocity_get(uint8_t c,uint8_t step) BANKED {uint16_t i;uint8_t e[4];i=find(c,step,page==8?seqpitch[c]+1:0);return i==65535U?0:seq_event_get(c,i,e)?e[2]:0;}
uint16_t seq_duration_get(uint8_t c,uint8_t step) BANKED {uint16_t i;uint8_t e[4];i=find(c,step,page==8?seqpitch[c]+1:0);return i==65535U?0:seq_event_get(c,i,e)?e[3]?e[3]:256U:0;}
uint8_t seq_note_set(uint8_t c,uint8_t step,uint8_t note,uint8_t velocity,uint16_t duration) BANKED {uint16_t i;uint8_t e[4];if(c==3||(c>=4&&!(c==TWINK_TRACK&&syncmode==SYNC_TWINK))||duration>256)return 0;i=find(c,step,note?note:seqpitch[c]+1);if(!note){if(i!=65535U)seq_event_erase(c,i);return 1;}e[0]=step;e[1]=note;e[2]=velocity;e[3]=duration;return seq_event_put(c,i,e);}
void storage_sorted_dirty(void) BANKED {indexvalid=0;} void storage_sorted_install(uint8_t mask) BANKED {(void)mask;}
void storage_sorted_prepare(void) BANKED {prepare_index();} void storage_cursor_reset(void) BANKED {}

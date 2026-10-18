#ifdef JOURNAL_HOST
#include "../tools/test_sparse_journal_shim.h"
#else
#pragma bank 47
#pragma opt_code_speed
#include "api.h"
#include "tones.h"
#include "mixer_shared.h"
#endif

/* One retained outgoing generation. This lives entirely in the protected
   recovery reserve, never in engine RAM, clipboard, or library pages.
   The live event arrays remain its source until phase 1 has copied them;
   incoming playback reads its immutable pool object during that interval. */
#define J_PREFIX 16U
#define J_TONES (J_PREFIX+POOL_PATTERN_BYTES)
#define J_EVENTS (J_TONES+POOL_TONE_BYTES)
#define J_REF 65534U
uint8_t sparse_journal_slot=255;
static uint8_t journal_phase;
static uint16_t journal_position,journal_object,journal_patch;
void sparse_journal_published(uint8_t slot,uint16_t pattern,uint16_t tone) BANKED;
static uint16_t word(const uint8_t *p){return p[0]|((uint16_t)p[1]<<8);}
static void setword(uint8_t *p,uint16_t n){p[0]=n;p[1]=n>>8;}
static void transfer(uint16_t at,uint8_t *data,uint16_t size,uint8_t writing){uint8_t n;uint16_t off;
 while(size){n=size>16?16:size;if(at<2048){if(n>2048-at)n=2048-at;off=6144+at;
   if(writing)writepart(3,off,data,n);else readpart(3,off,data,n);
  }else {off=7184+at-2048;if(writing)writepart(6,off,data,n);else readpart(6,off,data,n);}
  at+=n;data+=n;size-=n;
 }
}
static uint16_t event_bytes(void){uint8_t b[2];transfer(6,b,2,0);return word(b);}
static uint8_t *live(uint16_t byte){return byte<1024?(uint8_t *)seqevents_lo+byte:(uint8_t *)seqevents_hi+byte-1024;}
static void clear_marker(void){uint8_t zero=0;transfer(0,&zero,1,1);}
uint8_t sparse_journal_busy(void) BANKED {return (journal_phase&127)!=0;}
uint8_t sparse_journal_retaining(void) BANKED {return (journal_phase&127)==1;}
uint8_t sparse_journal_read(uint16_t at,uint8_t *data,uint16_t size) BANKED {uint16_t n;
 if(!journal_phase)return 0;
 while(size){if(at<POOL_PATTERN_BYTES){n=POOL_PATTERN_BYTES-at;if(n>size)n=size;transfer(J_PREFIX+at,data,n,0);}
  else {n=size;if((journal_phase&127)==1&&at-POOL_PATTERN_BYTES>=journal_position){if(at-POOL_PATTERN_BYTES<1024&&n>1024-(at-POOL_PATTERN_BYTES))n=1024-(at-POOL_PATTERN_BYTES);memcpy(data,live(at-POOL_PATTERN_BYTES),n);}
   else {if((journal_phase&127)==1&&n>journal_position-(at-POOL_PATTERN_BYTES))n=journal_position-(at-POOL_PATTERN_BYTES);transfer(J_EVENTS+at-POOL_PATTERN_BYTES,data,n,0);}}
  at+=n;data+=n;size-=n;
 }return 1;
}
void sparse_journal_tones(uint16_t at,uint8_t *data,uint16_t size) BANKED {
 if(at>POOL_TONE_BYTES||size>POOL_TONE_BYTES-at){pool_error=2;return;}
 /* The complete native patch is inside the first recovery span. readpart
    already chunks safely; avoid an extra transfer frame for each window. */
 readpart(3,6144U+J_TONES+at,data,size);
}
uint8_t sparse_journal_begin(uint8_t slot,const uint8_t *prefix,uint16_t bytes) BANKED {uint8_t h[16],zero=0,busy=seqservicing;
 if(journal_phase||slot>=8||bytes>2048)return 0;
 /* Reserve the worst-case COW footprint before retaining the outgoing
    generation. No other allocator runs until this journal is committed. */
 if(pool_free()<(((POOL_PATTERN_BYTES+bytes+6U+61U)/62U)+8U)*62U){pool_error=1;return 0;}
 /* Suppress only foreground sequencing while fixed patch/settings state is
    captured. Audio interrupts and refill remain enabled throughout. */
 seqservicing=1;memset(h,0,sizeof(h));h[4]=slot;setword(h+6,bytes);setword(h+8,word(pool_root+10)+1);h[12]=mx.quant;h[13]=mx.slot;
 transfer(0,&zero,1,1);transfer(4,h+4,12,1);transfer(J_PREFIX,(uint8_t *)prefix,POOL_PATTERN_BYTES,1);
 transfer(J_TONES,TONE_RAW,TONE_RAW_BYTES,1);transfer(J_TONES+TONE_RAW_BYTES,TONE_KICK_RAW,8,1);
 sparse_journal_slot=slot;journal_position=0;journal_phase=1;seqservicing=busy;return 1;
}
static void journal_step(void) {uint8_t b[16],n,busy,state=journal_phase&127;uint16_t size;
 if(!state||state==12)return;
 /* A prepared launch must never be called from the deep CRC/graph walk
    stack. Finish these background phases after the queued handoff. */
 if((mx.pending!=255||seqeventcache==2)&&(state==5||state==6||state==8||state==9||(state==10&&journal_position==POOL_PAGES)||(state==11&&journal_position+16>=POOL_TONE_BYTES)))return;
 size=event_bytes();
 if(state==1){n=size-journal_position>16?16:size-journal_position;if(n){busy=seqservicing;seqservicing=1;memcpy(b,live(journal_position),n);transfer(J_EVENTS+journal_position,b,n,1);journal_position+=n;seqservicing=busy;}
  if(journal_position==size){journal_phase=128|2;journal_position=0;transfer(4,b,12,0);journal_object=pool_crc(0xFFFF,b,6);journal_object=pool_crc(journal_object,b+8,4);}return;
 }
 if(state==2){size+=J_EVENTS-J_PREFIX;n=size-journal_position>16?16:size-journal_position;transfer(J_PREFIX+journal_position,b,n,0);journal_object=pool_crc(journal_object,b,n);journal_position+=n;
  if(journal_position==size){setword(b,journal_object);transfer(10,b,2,1);memcpy(b,"GBJ1",4);transfer(1,b+1,3,1);transfer(0,b,1,1);journal_phase=128|3;journal_position=0;}return;
 }
 if(state==3){journal_position=4;journal_phase=128|10;return;}
 if(state==10){
  if(journal_position==POOL_PAGES){journal_patch=pool_object_begin(POOL_PATCH,POOL_TONE_BYTES);if(journal_patch==POOL_NONE){journal_phase=128|12;return;}journal_position=0;journal_phase=128|4;return;}
  if(pool_used[journal_position>>3]&(1<<(journal_position&7))){pool_page_read(journal_position,2,b,6);
   if(b[0]==POOL_PATCH&&b[1]==1&&word(b+2)==POOL_TONE_BYTES){journal_patch=journal_position;journal_position=0;journal_phase=128|11;return;}}
  journal_position++;return;
 }
 if(state==11){uint8_t other[16];n=POOL_TONE_BYTES-journal_position>16?16:POOL_TONE_BYTES-journal_position;transfer(J_TONES+journal_position,b,n,0);
  if(!pool_object_read(journal_patch,journal_position,other,n)||memcmp(b,other,n)){journal_position=journal_patch+1;journal_phase=128|10;return;}
  journal_position+=n;if(journal_position==POOL_TONE_BYTES){if(pool_object_check(journal_patch,POOL_PATCH))journal_phase=128|6;else {journal_position=journal_patch+1;journal_phase=128|10;}}return;
 }
 if(state==4){n=POOL_TONE_BYTES-journal_position>16?16:POOL_TONE_BYTES-journal_position;transfer(J_TONES+journal_position,b,n,0);if(!pool_object_write(journal_patch,journal_position,b,n)){journal_phase=128|12;return;}journal_position+=n;if(journal_position==POOL_TONE_BYTES)journal_phase=128|5;return;}
 if(state==5){if(!pool_object_finish(journal_patch)){journal_phase=128|12;return;}journal_phase=128|6;return;}
 if(state==6){journal_object=pool_object_begin(POOL_PATTERN,POOL_PATTERN_BYTES+size);if(journal_object==POOL_NONE){journal_phase=128|12;return;}journal_position=0;journal_phase=128|7;return;}
 if(state==7){size+=POOL_PATTERN_BYTES;n=size-journal_position>16?16:size-journal_position;sparse_journal_read(journal_position,b,n);
  /* The journal prefix retains the previous patch reference. Substitute the
     prepared native patch identity only in the new immutable pool object. */
  if(journal_position<=POOL_PATCH_OFFSET&&journal_position+n>POOL_PATCH_OFFSET)b[POOL_PATCH_OFFSET-journal_position]=journal_patch;
  if(journal_position<=POOL_PATCH_OFFSET+1&&journal_position+n>POOL_PATCH_OFFSET+1)b[POOL_PATCH_OFFSET+1-journal_position]=journal_patch>>8;
  if(!pool_object_write(journal_object,journal_position,b,n)){journal_phase=128|12;return;}journal_position+=n;if(journal_position==size)journal_phase=128|8;return;
 }
 if(state==8){if(!pool_object_finish(journal_object)){journal_phase=128|12;return;}journal_phase=128|9;return;}
 if(state==9){transfer(8,b,2,0);pool_set_reference(POOL_ACTIVE+sparse_journal_slot*2,journal_object);memcpy(pool_root+10,b,2);
  if(mx.magic==0xD3){pool_root[7]=mx.slot;pool_root[8]=mx.quant;}
  if(!pool_commit()){journal_phase=128|12;return;}clear_marker();journal_phase=128|0;sparse_journal_published(sparse_journal_slot,journal_object,journal_patch);sparse_journal_slot=255;return;
 }
}
void sparse_journal_service(void) BANKED {uint8_t busy=seqservicing;
 if(journal_phase&128)return;
 /* A queued launch runs from the shallow foreground scheduler after this
    bounded quantum, never from a nested journal read/write callback. */
 if((journal_phase&127)!=5&&(journal_phase&127)!=8&&(journal_phase&127)!=9)seqservicing=1;
 journal_phase|=128;journal_step();journal_phase&=127;seqservicing=busy;
}

uint8_t sparse_journal_flush(void) BANKED {mx.pending=255;if(seqeventcache==2)sparse_finish_install();if(journal_phase==12){if(!pool_reclaim())return 0;journal_phase=3;journal_position=0;}while(journal_phase&&journal_phase!=12){sparse_journal_service();mixfill();}return !journal_phase;}
void sparse_journal_edit_barrier(void) BANKED {
 if((journal_phase&127)&&sparse_journal_slot==mx.slot){mx.pending=255;dirty=1;while((journal_phase&127)==1){sparse_journal_service();mixfill();}}
}
/* Replaying the same generation after a cut during root publication is
   idempotent. A published root records the journal identity before clearing
   its marker. A partial stage never replaces the previous committed root. */
uint8_t sparse_journal_recover(void) BANKED {uint8_t h[16],b[16],n;uint16_t size,at,crc=0xFFFF;
 journal_phase=0;sparse_journal_slot=255;transfer(0,h,16,0);if(memcmp(h,"GBJ1",4))return 1;
 if(h[4]>=8||word(h+6)>2048)return 0;size=J_EVENTS-J_PREFIX+word(h+6);crc=pool_crc(crc,h+4,6);crc=pool_crc(crc,h+12,4);
 for(at=0;at<size;at+=n){n=size-at>16?16:size-at;transfer(J_PREFIX+at,b,n,0);crc=pool_crc(crc,b,n);}if(crc!=word(h+10))return 0;
 if(word(pool_root+10)==word(h+8)){clear_marker();return 1;}
 sparse_journal_slot=h[4];journal_phase=3;journal_position=0;return sparse_journal_flush();
}

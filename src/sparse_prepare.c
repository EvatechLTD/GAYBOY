#pragma bank 60
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
#include "tones.h"

/* Mixer-only scratch, outside font uploads, outgoing journal capture and
   tone decode. Roll rendering can reuse it after leaving Mixer. */
#define HEAD ((uint8_t *)0xB500)
#define MAP ((uint8_t *)0xB570)
#define FIRST ((uint8_t *)0xB590)
#define KICK (*(uint8_t *)0xB598)
static uint8_t target=255,prepare_phase,preparing,demand=255;
static uint16_t identity,scan_cursor;
static uint16_t prepared_bpm;
static uint8_t gate_cursor;
static PoolStream tone_stream;
#define FULL ((uint8_t *)0xB5A0)
#define OFFSETS ((uint8_t *)0xB5F2)
#define EVENT_STREAM ((PoolStream *)0xB599)
#define ATTACK ((uint8_t *)0xB7C2)
/* Beat-one lookups for every melodic track and the complete drum batch.
   Ends at B820, immediately before META_BUFFER. */
#define FIRST_OTHER ((uint8_t *)0xB7D0)
#define FIRST_DRUM ((uint8_t *)0xB7E0)
static uint8_t first_drums,first_drum_overflow;
extern const uint16_t notes[140];
void seq_native_launch_begin(uint8_t slot,uint8_t count,uint8_t overflow) BANKED;
uint8_t seq_native_launch_service(void) BANKED;
void seq_native_launch_installed(uint8_t slot) BANKED;
/* Native tone records begin with two 60-byte pulse blocks. Prepare their
   zero-bend, untuned beat-one register writes before the launch boundary. */
static void prepare_attacks(void){uint8_t c,*v,*r,vol;uint16_t amplitude,f;
 for(c=0;c<2;c++){
  v=TONE_CACHED_RAW+c*60;r=ATTACK+(c?5:0);vol=FIRST[c*4+2];
  if(FULL[56+c]!=127){amplitude=(uint16_t)vol*FULL[56+c]+63;vol=amplitude>>7;vol+=((amplitude&127)+vol)>=127;}
  f=notes[FIRST[c*4+1]?FIRST[c*4+1]-1:0];
  amplitude=(uint16_t)v[1]*vol;vol=(amplitude+1+(amplitude>>7))>>7;
  if(!c)*r++=(v[4]<<4)|(v[5]<<3)|v[6];
  *r++=(v[0]<<6)|v[7];*r++=!vol&&!v[2]?8:(vol<<4)|(v[2]<<3)|v[3];*r++=f;*r=0x80|(v[8]<<6)|(f>>8);
 }
}
extern uint16_t seqcachedbpm,seqdeadline;
extern uint8_t seqcachedgate[7];
static void setword(uint8_t *p,uint16_t n){p[0]=n;p[1]=n>>8;}
static void prepare_metadata(void){uint8_t c;uint16_t at=0;
 memcpy(FULL,HEAD+16,14);
 for(c=0;c<7;c++){setword(FULL+14+c*2,HEAD[30+c]?HEAD[30+c]:256);setword(FULL+28+c*2,HEAD[37+c]?HEAD[37+c]:c==6?0:256);setword(OFFSETS+c*2,at);at+=FULL[c*2]|((uint16_t)FULL[c*2+1]<<8);}
 memcpy(FULL+42,HEAD+44,39);
}
static uint16_t word(const uint8_t *p){return p[0]|((uint16_t)p[1]<<8);}
static uint8_t native(void){return !experimental_mode&&!monomode&&(!waveengine||waveengine==3);}
/* Raw-clock tempo is measured, so its estimate can change before a dense
   pattern finishes loading. Keep immutable notes/tones rather than restarting
   that I/O forever. The launch packet still validates its own BPM; stale
   timing is recalculated by the complete-step path at the boundary. */
static uint8_t tempo_valid(void){return (syncmode>1&&syncslave)||prepared_bpm==(seqglobalbpm?seqglobalbpm:word(FULL+75));}
static uint8_t cache_valid(uint8_t slot){return prepare_phase==6&&page==18&&target==slot&&identity==sparse_slots[slot]&&tempo_valid()&&native();}
static uint16_t offset(uint8_t track){uint8_t c;uint16_t at=POOL_EVENTS_OFFSET;for(c=0;c<track;c++)at+=word(HEAD+16+c*2)*4;return at;}

/* One bounded read/scan quantum per foreground service. The playing pattern
   and its immutable source remain untouched throughout preparation. */
static void prepare_once(void){uint8_t slot,e[4],found;uint16_t count,limit;
 if(page!=18||!native()){prepare_phase=0;target=255;return;}
 if(navopen)return;
 slot=demand<8?demand:mx.pending!=255?mx.pending:mx.focus>=30&&mx.focus<38?mx.focus-30:seqplaying?(mx.slot+1)&7:255;
 if(slot==mx.slot)slot=seqplaying?(slot+1)&7:255;
 if(slot>=8||sparse_slots[slot]==POOL_NONE||sparse_slots[slot]==SPARSE_JOURNAL_REF){prepare_phase=0;target=255;return;}
 if(slot!=target||identity!=sparse_slots[slot]||(prepare_phase!=1&&!tempo_valid())){target=slot;identity=sparse_slots[slot];prepare_phase=1;mx.cachevalid=0;scan_cursor=0;memset(FIRST,0,8);memset(FIRST_OTHER,0,16);first_drums=first_drum_overflow=0;KICK=0;}
 if(prepare_phase==1){if(!pool_object_read(identity,0,HEAD,POOL_PATTERN_BYTES)){prepare_phase=7;return;}prepare_metadata();prepared_bpm=seqglobalbpm?seqglobalbpm:word(FULL+75);setword(HEAD+97,15360U/prepared_bpm);prepare_phase=13;gate_cursor=0;scan_cursor=0;return;}
 if(prepare_phase==13){setword(HEAD+83+gate_cursor*2,(word(HEAD+97)*FULL[49+gate_cursor])/100);if(++gate_cursor==7)prepare_phase=2;return;}
 if(prepare_phase==2){
  if(!scan_cursor&&!pool_stream_seek(&tone_stream,word(HEAD+100),0)){prepare_phase=7;return;}
  count=POOL_TONE_BYTES-scan_cursor;slot=count>16?16:count;
  if(!pool_stream_read(&tone_stream,TONE_CACHED_RAW+scan_cursor,slot)){prepare_phase=7;return;}scan_cursor+=slot;
  if(scan_cursor==POOL_TONE_BYTES){if(!pool_native_map(word(HEAD+100),MAP)||!pool_stream_seek(EVENT_STREAM,identity,POOL_EVENTS_OFFSET)){prepare_phase=7;return;}prepare_phase=3;scan_cursor=0;}return;
 }
 if(prepare_phase==14){if(seq_native_launch_service()){prepare_phase=6;mx.cachevalid=1;mx.cacheslot=target;dirty=1;}return;}
 if(prepare_phase==3||prepare_phase==4||(prepare_phase>=8&&prepare_phase<=12)){
  slot=prepare_phase==12?6:prepare_phase>=8?prepare_phase-6:prepare_phase-3;count=word(HEAD+16+slot*2);limit=scan_cursor+16;if(limit>count)limit=count;
  found=count&&pool_object_scan(identity,offset(slot),limit,0,&scan_cursor,e);
  if(prepare_phase==12){
   if(found){if(e[1]==13&&e[2])KICK=1;if(first_drums<16)memcpy(FIRST_DRUM+(first_drums++)*4,e,4);else first_drum_overflow=1;}
   if(scan_cursor>=count)prepare_phase=6;
  }
  else if(found){memcpy(slot<2?FIRST+slot*4:FIRST_OTHER+(slot-2)*4,e,4);prepare_phase++;scan_cursor=0;}
  else if(scan_cursor>=count){prepare_phase++;scan_cursor=0;}
  if(prepare_phase==5)prepare_phase=8;
  if(prepare_phase==6){prepare_attacks();seq_native_launch_begin(target,first_drums,first_drum_overflow);prepare_phase=14;}
 }
}
void sparse_prepare_service(void) BANKED {if(preparing)return;preparing=1;prepare_once();preparing=0;}
/* Quantize OFF still prepares before releasing the outgoing voices. Musical
   service runs between quanta; mx.pending is clear so no boundary can activate
   this request underneath the caller. The slot and loop budget are bounded. */
void sparse_prepare_now(uint8_t slot) BANKED {uint16_t budget=1024;
 if(preparing||page!=18||!native()||slot>=8||slot==mx.slot||sparse_slots[slot]==POOL_NONE||sparse_slots[slot]==SPARSE_JOURNAL_REF)return;
 demand=slot;preparing=1;
 while(budget--&&!cache_valid(slot)){prepare_once();if(prepare_phase==7)break;mixfill();}
 preparing=0;demand=255;
}
uint8_t sparse_prepare_busy(void) BANKED {uint8_t slot=mx.pending;
 if(!native()||slot>=8||slot==mx.slot||sparse_slots[slot]==POOL_NONE||sparse_slots[slot]==SPARSE_JOURNAL_REF)return 0;
 if(prepare_phase==7&&target==slot&&identity==sparse_slots[slot])return 0;
 return !cache_valid(slot);
}
uint8_t sparse_prepared_prefix(uint8_t slot,uint8_t *data) BANKED {if(!cache_valid(slot))return 0;memcpy(data,HEAD,POOL_PATTERN_BYTES);return 1;}
uint8_t sparse_prepared_map(uint16_t object,uint8_t *data) BANKED {if(!cache_valid(target)||word(HEAD+100)!=object)return 0;memcpy(data,MAP,24);return 1;}
/* 2 means cache miss; 0 is a prepared rest and 1 a prepared onset. */
uint8_t sparse_first_note(uint8_t track,uint8_t *event) BANKED {if(track>5||!cache_valid(mx.slot))return 2;memcpy(event,track<2?FIRST+track*4:FIRST_OTHER+(track-2)*4,4);return !!event[1];}
uint8_t sparse_first_drum(uint16_t *cursor,uint8_t *event) BANKED {
 if(!cache_valid(mx.slot)||first_drum_overflow)return 2;
 if(*cursor>=first_drums)return 0;
 memcpy(event,FIRST_DRUM+(*cursor)*4,4);(*cursor)++;return 1;
}
uint8_t sparse_first_kick(void) BANKED {return cache_valid(mx.slot)?KICK:2;}
uint8_t sparse_first_packet(uint8_t c,uint8_t *regs) BANKED {if(c>1||finepitch[c]||!cache_valid(mx.slot)||!FIRST[c*4+1]||!FIRST[c*4+2]||!FULL[56+c])return 0;memcpy(regs,ATTACK+(c?5:0),c?4:5);return 1;}

static void apply_metadata(void) __naked {__asm
 ld de,#0xb5a0
 .globl _seqeventcounts
 ld hl,#_seqeventcounts
 .rept 14
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqlength
 ld hl,#_seqlength
 .rept 14
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqdefaultdur
 ld hl,#_seqdefaultdur
 .rept 14
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqdefaultvel
 ld hl,#_seqdefaultvel
 .rept 7
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqgate
 ld hl,#_seqgate
 .rept 7
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _mx
 ld hl,#_mx+12
 .rept 14
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqmuted
 ld hl,#_seqmuted
 .rept 1
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqsolo
 ld hl,#_seqsolo
 .rept 1
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqbeats
 ld hl,#_seqbeats
 .rept 1
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqdenom
 ld hl,#_seqdenom
 .rept 1
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 inc de
 inc de
 inc de
 .globl _drummutemask
 ld hl,#_drummutemask
 .rept 2
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _drumsolomask
 ld hl,#_drumsolomask
 .rept 2
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqeventoffsets
 ld de,#0xb5f2
 ld hl,#_seqeventoffsets
 .rept 14
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqgateunits
 ld de,#0xb553
 ld hl,#_seqgateunits
 .rept 14
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqstepunits
 ld de,#0xb561
 ld hl,#_seqstepunits
 .rept 2
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _seqcachedgate
 ld de,#0xb5d1
 ld hl,#_seqcachedgate
 .rept 7
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 .globl _mx
 ld de,#0xb500
 ld hl,#_mx+26
 .rept 16
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 xor a
 ld (hl),a
 ret
 __endasm; }

uint8_t sparse_prepared_apply(uint8_t slot) BANKED {
 if(!cache_valid(slot))return 0;apply_metadata();seqgrouptrack=255;seqmode=0;seqbpm=(syncmode>1&&syncslave)?seqglobalbpm:prepared_bpm;seqcachedbpm=prepared_bpm;seqdeadline=1;seqeventfull=0;*(uint8_t *)0xACCF=HEAD[99];return 1;
}
uint8_t sparse_prepared_tones(uint8_t slot) BANKED {if(!cache_valid(slot))return 0;tones_apply_cached();seq_native_launch_installed(slot);return 1;}
uint8_t sparse_prepared_stream(uint8_t slot,PoolStream *stream) BANKED {if(!cache_valid(slot))return 0;memcpy(stream,EVENT_STREAM,sizeof(PoolStream));return 1;}

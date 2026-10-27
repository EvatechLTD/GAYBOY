#pragma bank 60
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
#include "song_audio.h"
#include "song_twink.h"
#include "twink_schedule.h"
#include "twink_chord.h"
/* Song-only overlay: local scenes end at A208, runtime starts at A300.
   The existing unused MIDI RX ring holds eight immutable per-frame packets.
   No extra WRAM, no live chord planner, no receiver handshake. */
typedef struct {uint16_t begin,end,length;} SongMS;
typedef char SongMSFits[(sizeof(SongMS)==6)?1:-1];
__at (0xA210) static SongMS ms_scenes[5];
__at (0xA230) static uint16_t ms_cursor;
__at (0xA232) static uint8_t ms_step;
__at (0xA233) static uint8_t ms_pad;
__at (0xA234) volatile uint16_t song_twink_overflows;
extern __at (0xA3C0) volatile uint8_t song_qread;
extern __at (0xA3C1) volatile uint8_t song_qwrite;
extern volatile uint8_t twinktx[32];
uint8_t twink_crc_step(uint8_t crc,uint8_t value) BANKED;

void song_twink_reset(void) BANKED {twink_chord_reset();memset(ms_scenes,0,sizeof(ms_scenes));ms_pad=255;song_twink_overflows=0;}
uint8_t song_twink_compile(uint8_t pad,uint16_t *used) BANKED {
 SongMS *s=&ms_scenes[pad];uint16_t step,i,end;uint8_t e[4],p[21],previous[19],count,j,k,onset,crc,vel,solos=seqsolo&111;
 if(drumsolomask)solos|=64;s->begin=*used;s->length=seqlength[5];memset(previous,255,sizeof(previous));
 if(!s->length||s->length>256){song_runtime.error=3;return 0;}
 for(step=0;step<s->length;step++){
  memset(p,0,sizeof(p));p[0]=step;p[2]=0xF5;count=onset=0;
  for(i=0;i<seqeventcounts[5];i++){
   seq_event_get(5,i,e);end=(uint16_t)e[0]+(e[3]?e[3]:256U);
   if(!e[1]||!e[2]||e[0]>step||step>=end||!power||(seqmuted&32)||(solos&&!(solos&32)))continue;
   vel=mixer_velocity(5,e[2]);if(!vel)continue;
   if(e[0]==step)onset=1;
   for(j=0;j<count&&p[4+j*2]<e[1]-1;j++);
   if(j<count&&p[4+j*2]==e[1]-1)continue;if(j==8)continue;
   if(count<8)count++;for(k=count-1;k>j;k--){p[4+k*2]=p[4+(k-1)*2];p[5+k*2]=p[5+(k-1)*2];}
   p[4+j*2]=e[1]-1;p[5+j*2]=vel;
  }
  p[3]=count;p[1]=3+count*2;crc=twink_crc_step(0,count);
  for(j=0;j<count*2;j++)crc=twink_crc_step(crc,p[4+j]);p[4+count*2]=crc;
  if(!step||onset||memcmp(previous,p+2,p[1])){
   /* Cache helper accepts arbitrary lengths for writes; reads stage <=16B. */
   if(!song_cache_put(*used,p,p[1]+2))return 0;*used+=p[1]+2;memcpy(previous,p+2,p[1]);
  }
 }
 s->end=*used;return 1;
}
void song_twink_begin(void) BANKED {rx[(uint16_t)song_qwrite<<5]=0;}
static uint8_t load_packet(void){uint8_t h[2],*out=(uint8_t *)rx+((uint16_t)song_qwrite<<5);
 song_cache_get(ms_cursor,h,2);if(h[0]!=ms_step)return 0;ms_cursor+=2;
 song_cache_get(ms_cursor,out+1,h[1]>16?16:h[1]);
 if(h[1]>16)song_cache_get(ms_cursor+16,out+17,h[1]-16);
 ms_cursor+=h[1];out[0]=h[1];return 1;
}
void song_twink_quiet(void) BANKED {uint8_t *p=(uint8_t *)rx+((uint16_t)song_qwrite<<5);p[0]=3;p[1]=0xF5;p[2]=p[3]=0;ms_pad=255;}
void song_twink_scene(uint8_t pad,uint32_t offset) BANKED {SongMS *s;uint8_t h[2];
 if(pad>=5){song_twink_quiet();return;}ms_pad=pad;s=&ms_scenes[pad];ms_cursor=s->begin;ms_step=offset%s->length;
 /* Cold seek installs the last held set, not every intervening attack. */
 while(ms_cursor<s->end){song_cache_get(ms_cursor,h,2);if(h[0]>ms_step)break;{uint8_t point=ms_step;ms_step=h[0];load_packet();ms_step=point;}}
}
void song_twink_step(void) BANKED {SongMS *s;if(ms_pad>=5)return;s=&ms_scenes[ms_pad];
 if((uint16_t)ms_step+1>=s->length){ms_step=0;ms_cursor=s->begin;}else ms_step++;
 if(ms_cursor<s->end)load_packet();
}
/* Called AFTER the local APU program, interrupts already disabled. At most
   19 bytes copied to the existing wire queue. Never wait for space or ACK.
   SIO drains it asynchronously using the hardware-qualified byte guard. */
void song_twink_commit(void) BANKED __naked {__asm
 ld a,(#_song_qread)
 swap a
 rlca
 and #0xe0
 ld e,a
 ld d,#0
 ld hl,#_rx
 add hl,de
 ld a,(hl+)
 or a,a
 ret z
 ld b,a
 ldh a,(_syncw)
 ld c,a
 ldh a,(_syncr)
 sub a,c
 dec a
 and #31
 cp a,b
 jr nc,song_ms_copy$
 ld hl,#_song_twink_overflows
 inc (hl)
 ret nz
 inc hl
 inc (hl)
 ret
song_ms_copy$:
 ld a,c
 ld de,#_twinktx
 add a,e
 ld e,a
 jr nc,song_ms_loop$
 inc d
song_ms_loop$:
 ld a,(hl+)
 ld (de),a
 inc de
 inc c
 ld a,c
 cp #32
 jr nz,song_ms_next$
 ld c,#0
 ld de,#_twinktx
song_ms_next$:
 dec b
 jr nz,song_ms_loop$
 ld a,c
 ldh (_syncw),a
 jp _twink_direct_kick
 __endasm;}

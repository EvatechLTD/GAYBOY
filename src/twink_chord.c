#pragma bank 60
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
#include "smooth_playback.h"
#include "twink_schedule.h"
#include "twink_chord.h"
/* Eight32-byte slots occupy the existing unused MIDI RX ring in TWINK mode.
   Each immutable entry has a16-bit absolute step, length and complete F5 frame. */
static volatile uint8_t chord_read,chord_write;
volatile uint8_t twink_chord_work;
uint8_t twink_chord_check_frame;
static volatile uint16_t chord_clock;
static uint16_t plan_when,plan_revision,plan_length;
static uint8_t plan_step,plan_slot,plan_key,busy,started;
extern uint16_t twink_ms_generation;
extern uint8_t editbuffer_reading;
uint8_t twink_crc_step(uint8_t crc,uint8_t value) BANKED;
static uint8_t audible(void){uint8_t solos=seqsolo&111;if(drumsolomask)solos|=64;return power&&!(seqmuted&32)&&(!solos||(solos&32));}
void twink_chord_reset(void) BANKED {__critical{chord_read=chord_write=0;chord_clock=0;started=0;twink_chord_work=1;}}
void twink_chord_release(void) BANKED {const uint8_t frame[3]={0xF5,0,0};__critical{chord_read=chord_write=0;started=0;twink_chord_work=1;twink_queue_message(frame,3);}}
void twink_chord_step(uint8_t step) BANKED {uint16_t now=chord_clock++,when;uint8_t r=chord_read,last=255,*p;const uint8_t silence[3]={0xF5,0,0};(void)step;
 while(r!=chord_write){p=(uint8_t *)rx+((uint16_t)r<<5);when=p[0]|((uint16_t)p[1]<<8);if((int16_t)(now-when)<0)break;last=r;r=(r+1)&7;}
 if(last==255)return;p=(uint8_t *)rx+((uint16_t)last<<5);
 if(twink_queue_message(audible()?p+3:silence,audible()?p[2]:3)){chord_read=r;twink_chord_work=1;}
}
void twink_chord_service(void) BANKED {uint8_t frame[19],noteset[8],velocities[8],e[4],count,r,j,k,reading,w,next,key,slot,budget=2,crc,point;uint16_t revision,length,i,n,end,soon,when,v;
 if(busy||syncmode!=SYNC_TWINK||(!seqplaying&&!smooth_playback_preparing))return;busy=1;twink_chord_check_frame=(uint8_t)sys_time;
 key=mx.level[5]|(audible()?0:128);revision=twink_ms_generation;length=seqlength[5];slot=mx.slot;
 if(!length){busy=0;return;}
 if(!started||plan_revision!=revision||plan_length!=length||plan_slot!=slot||plan_key!=key){
  __critical{chord_read=chord_write=0;plan_when=chord_clock;plan_step=seqplaying?twink_chord_next_step():0;started=1;}
  plan_revision=revision;plan_length=length;plan_slot=slot;plan_key=key;
 }
 reading=editbuffer_reading;editbuffer_reading=0;
 while(budget--&&started==1){w=chord_write;next=(w+1)&7;if(next==chord_read)break;point=plan_step;when=plan_when;soon=length;count=0;n=seq_event_count(5);
  for(i=0;i<n;i++){
   seq_event_get(5,i,e);if(!e[1])continue;end=(uint16_t)e[0]+(e[3]?e[3]:256U);
   if(e[0]>point&&e[0]<soon)soon=e[0];if(end>point&&end<soon)soon=end;
   if(e[0]>point||point>=end||!e[2]||(key&128))continue;
   for(r=0;r<count&&noteset[r]<e[1]-1;r++);if(r<count&&noteset[r]==e[1]-1)continue;if(r==8)continue;
   if(count<8)count++;for(j=count-1;j>r;j--){noteset[j]=noteset[j-1];velocities[j]=velocities[j-1];}
   noteset[r]=e[1]-1;v=e[2];if((key&127)!=127){v=v*(key&127)+63;v=(v>>7)+((uint8_t)((v&127)+(v>>7))>=127);}velocities[r]=v;
  }
  frame[0]=0xF5;frame[1]=count;crc=twink_crc_step(0,count);k=2;
  for(r=0;r<count;r++){frame[k++]=noteset[r];crc=twink_crc_step(crc,noteset[r]);frame[k++]=velocities[r];crc=twink_crc_step(crc,velocities[r]);}frame[k++]=crc;
  if(!started||revision!=twink_ms_generation||length!=seqlength[5]||slot!=mx.slot||key!=(uint8_t)(mx.level[5]|(audible()?0:128)))break;
  {uint8_t *p=(uint8_t *)rx+((uint16_t)w<<5);p[0]=when;p[1]=when>>8;p[2]=k;memcpy(p+3,frame,k);chord_write=next;}
  plan_when+=soon-point;plan_step=soon>=length?0:(uint8_t)soon;
  if(!n||(key&128))started=3;
 }
 editbuffer_reading=reading;twink_chord_work=started==1&&((chord_write+1)&7)!=chord_read;busy=0;
}

#pragma bank 48
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
#include "smooth_playback.h"
#include "mod_bypass.h"
extern uint16_t editbuffer_base,pattern_generation,resident_tone_generation,seqclock;
extern uint16_t seqstepunits;
extern uint32_t noiseleft[2];
extern __at (0xAC58) uint8_t drumnoisetail;
extern uint8_t kickreleasing,expzvolume[2],evalkickvelocity,pulsekickpatch[8];
extern __at (0xAC60) uint8_t noisepatch[2][5];
extern const uint16_t notes[140];
uint8_t eval_drum_pan(uint8_t c) BANKED;
volatile uint8_t drum_irq_active;
static uint8_t ready,slot,step,kickregs[2];
static uint16_t table,drum_phase,length,epoch,tone_epoch,bpm,kickleft;
static uint8_t scale(uint16_t v){uint8_t q=v>>7;return q+((uint8_t)((v&127)+q)>=127);}
/* The inactive immutable-note buffer is scratch while Smooth Playback forbids
   editing. A changed generation stops this consumer before a new snapshot
   can reuse it. 256 eight-byte packets fit without another RAM allocation. */
void drum_irq_prepare(void) BANKED {
 volatile uint16_t i;uint16_t s,n,duration,left[2]={0,0},kg;uint8_t e[4],packet[8],v[5],vel[2]={0,0},a,b,j,changed,ended,kick,raw,pan,vol;uint16_t f;
 ready=drum_irq_active=0;
 if(!smooth_playback_preparing||syncmode||!power||monomode||polymode||mono_owned||waveengine==3||seqswing!=50||seqmode||seq_event_count(0)||seq_event_count(3))return;
 if(!mod_bypass&&((eval_lfousers|eval_envusers)&224))return;
 if((seqmuted&64)||((seqsolo&95)&&!(seqsolo&64)))return;
 n=seq_event_count(6);if(!n)return;
 for(i=0;i<n;i++){seq_event_get(6,i,e);duration=e[3]?e[3]:256U;
  if(e[1]<11||e[1]>13||(uint16_t)e[0]+duration>seqlength[6])return;
 }
 slot=mx.slot;length=seqlength[6];bpm=seqbpm;
 table=editbuffer_base==0xAD00U?0xB620U:0xAD00U;
 kickregs[0]=(pulsekickpatch[4]<<4)|(pulsekickpatch[7]<<3)|pulsekickpatch[5];
 kickregs[1]=(pulsekickpatch[2]<<6)|((64-pulsekickpatch[6])&63);
 for(s=0;s<length;s++){
  memset(packet,0,8);changed=ended=kick=0;
  for(j=0;j<2;j++)if(left[j]){if(!--left[j])ended=1;}
  /* SDCC must reload this out-parameter cursor for each step. */
  i=0;while(seq_event_next_step(6,s,(uint16_t *)&i,e)){
   raw=e[1]-1;if((drummutemask&(1U<<raw))||(drumsolomask&&!(drumsolomask&(1U<<raw)))||!eval_drum_allowed(i-1))continue;
   duration=e[3]?e[3]:256U;
   if(e[1]<13){j=e[1]-11;left[j]=duration;vel[j]=mixer_velocity(6,e[2]);changed=1;}
   else{
    kick=1;vol=mixer_velocity(6,e[2]);packet[3]=(scale((uint16_t)eval_drum_level(7,pulsekickpatch[0])*vol)<<4)|pulsekickpatch[3];
    f=eval_drum_pitch(7,notes[pulsekickpatch[1]]);packet[4]=f;packet[5]=0xC0|(f>>8);
    pan=eval_drum_pan(7);packet[6]=(pan&1?1:0)|(pan&2?16:0);
    kg=(uint16_t)pulsekickpatch[6]*4;if(!kg)kg=4;
    if((uint32_t)seqstepunits*duration<kg)kg=seqstepunits*duration;packet[7]=kg;
   }
  }
  a=!!left[0];b=!!left[1];packet[0]=(a?16:0)|(b?32:0)|(kick?4:0);
  if((changed||ended)&&(a||b)){
   for(j=0;j<5;j++)v[j]=a&&b?(noisepatch[0][j]+noisepatch[1][j]+1)>>1:noisepatch[b?1:0][j];
   if(a&&b)vol=scale(((uint16_t)eval_drum_level(5,noisepatch[0][0])*vel[0]+(uint16_t)eval_drum_level(6,noisepatch[1][0])*vel[1]+127)>>1);
   else vol=scale((uint16_t)eval_drum_level(b?6:5,v[0])*vel[b?1:0]);
   packet[0]|=1;packet[1]=vol?(vol<<4)|v[4]:8;packet[2]=eval_drum_pitch(b?6:5,(v[1]<<4)|(v[3]<<3)|v[2]);
   pan=eval_drum_pan(b?6:5);packet[6]|=(pan&1?8:0)|(pan&2?128:0);
  }else if(ended||(!s&&!a&&!b))packet[0]|=2;
  __critical{SWITCH_RAM_MBC5(2);memcpy((void *)(table+s*8),packet,8);SWITCH_RAM_MBC5(0);}mixfill();
 }
 /* Use256Hz when the grid fits it exactly; otherwise use1024Hz. Avoid
    extra IRQ work at120/240BPM while bounding fractional-tempo quantization. */
 if(!waveengine){uint8_t reload=seqstepunits*seqbpm==15360U&&!(seqstepunits&3)?240:252;
  __critical{TMA_REG=TIMA_REG=reload;IF_REG&=~TIM_IFLAG;}}
 epoch=pattern_generation;ready=1;
}
/* Called only at a musical boundary. Every byte below was prepared while
   stopped; no note search, synthesis dispatch, divide, or pattern rebuild. */
void drum_irq_emit(void) BANKED {
 uint8_t p[8],flags;
 SWITCH_RAM_MBC5(2);memcpy(p,(void *)(table+(uint16_t)step*8),8);SWITCH_RAM_MBC5(0);flags=p[0];
 noiseleft[0]=flags&16?1:0;noiseleft[1]=flags&32?1:0;
 if(flags&1){
  route=(route&~0x88)|(p[6]&0x88);NR51_REG=route;
  NR41_REG=0;NR42_REG=p[1];NR43_REG=p[2];NR44_REG=128;
  expzvolume[1]=p[1]>>4;drumnoiseowned=1;drumnoisetail=0;
 }else if(flags&2){
  if(!(NR42_REG&7)){NR42_REG=8;NR44_REG=128;drumnoisetail=0;}else drumnoisetail=1;
  drumnoiseowned=0;
 }
 if(flags&4){
  kickleft=p[7]?p[7]:256;pulsekickleft=kickleft;kickreleasing=0;
  route=(route&~0x11)|(p[6]&0x11);NR51_REG=route;
  NR10_REG=kickregs[0];NR11_REG=kickregs[1];NR12_REG=p[3];NR13_REG=p[4];NR14_REG=p[5];expzvolume[0]=p[3]>>4;
 }
}
void drum_irq_start(void) BANKED {
 if(!ready||!seqplaying)return;
 ready=0;step=0;kickleft=0;drum_phase=seqclock+seqticks*seqbpm;tone_epoch=resident_tone_generation;
 __critical{drum_irq_active=1;drum_irq_emit();}
}
void drum_irq_tick(uint8_t elapsed) BANKED {
 uint8_t n=elapsed;
 if(!seqplaying||!power||monomode||polymode||!smooth_playback_active||syncmode||slot!=mx.slot||epoch!=pattern_generation||tone_epoch!=resident_tone_generation||bpm!=seqbpm||waveengine==3){drum_irq_active=0;return;}
 if(kickleft){
  if(kickleft<=elapsed){kickleft=0;pulsekickleft=0;kickreleasing=0;NR12_REG=8;NR14_REG=128;}
  else{kickleft-=elapsed;pulsekickleft=kickleft;}
 }
 while(n--)drum_phase+=bpm;
 while(drum_phase>=15360U){drum_phase-=15360U;if((uint16_t)step+1>=length)step=0;else step++;drum_irq_emit();}
}

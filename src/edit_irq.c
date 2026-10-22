#pragma bank 47
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
extern uint8_t editbuffer_valid,editbuffer_irq_mask;
extern uint16_t seqclock;
uint8_t editbuffer_active(void) BANKED;
uint8_t editbuffer_irq_event(uint8_t c,uint8_t step,uint8_t *out) NONBANKED;
void editirq_wave_capture(uint8_t *out) BANKED;
extern uint8_t tablemode[4],seqrecordtrack;
static uint8_t wavebytes[16],position[3],irq_patch[3][7];
volatile uint8_t editirq_enabled,editirq_running;
static uint16_t gate[3],prepared_bpm;
static volatile uint16_t editirq_phase;
static uint8_t divider_last,divider_fraction;
uint8_t editirq_max_gap;
extern uint8_t linkstate;
uint16_t editirq_attacks,editirq_underruns;
/* Unsupported synthesis modes retain the original foreground dispatcher. */
uint8_t editirq_owned(uint8_t c) NONBANKED {
 if(c>=3||page!=8||!seqplaying||!(editirq_enabled&(1<<c))||seqrecordtrack==c||seqlength[c]>64)return 0;
 return (!evalpatch[c][EV_MODE]&&!evalpatch[c][EV_CHORD_HISTORY]);
}
/* DIV measures wall time even if a register commit spans a TIMA overflow.
   All enabled paths sample more often than DIV's 15.625 ms wrap interval. */
uint8_t editirq_elapsed(uint8_t fallback) NONBANKED {uint8_t now=DIV_REG,delta;uint16_t n;
 if(!editirq_running||page!=8||!seqplaying){divider_last=now;divider_fraction=0;return fallback;}
 delta=now-divider_last;divider_last=now;if(delta>editirq_max_gap)editirq_max_gap=delta;n=(uint16_t)delta+divider_fraction;divider_fraction=n&15;return n>>4;
}
void editirq_commit(void) NONBANKED {
 uint8_t c,bit,i,e[7],mask,vol,found,solos,*patch;
 solos=seqsolo&(experimental_mode?95:79);if(drumsolomask)solos|=64;
  for(c=0,bit=1;c<3;c++,bit<<=1){if(!(editbuffer_irq_mask&bit))editirq_enabled&=~bit;if(!(editirq_enabled&bit))continue;if(!editirq_owned(c)){editirq_enabled&=~bit;continue;}
   if(++position[c]>=seqlength[c])position[c]=0;if(gate[c])gate[c]--;
   if(!power||c==0&&pulsekickleft||c==2&&waveengine){editirq_enabled&=~bit;continue;}
   found=editbuffer_irq_event(c,position[c],e);if(found&&e[2]&&!(seqmuted&bit)&&(!solos||(solos&bit))){
    gate[c]=e[3]?e[3]:256U;patch=irq_patch[c];mask=bit|(bit<<4);route=(route&~mask)|patch[6];NR51_REG=route;
    vol=(e[6]<<4)|patch[1];
    if(c==0){NR10_REG=patch[3];NR11_REG=patch[0];NR12_REG=vol;NR13_REG=e[4];NR14_REG=patch[2]|e[5];}
    else if(c==1){NR21_REG=patch[0];NR22_REG=vol;NR23_REG=e[4];NR24_REG=patch[2]|e[5];}
    else if(c==2){NR30_REG=0;for(i=0;i<16;i++)REG(0xff30+i)=wavebytes[i];NR31_REG=patch[5];NR32_REG=e[6];NR30_REG=128;NR33_REG=e[4];NR34_REG=patch[2]|e[5];}
    active[c]=1;seqowned[c]=e[1];seqsource[c]=position[c];seqgateleft[c]=0;held[c]=basepitch[c]=e[1]-1;velocity[c]=e[2];keycount[c]=1;keystack[c][0]=e[1]-1;keyvel[c][0]=e[2];editirq_attacks++;
   }else if(!gate[c]||(seqmuted&bit)||(solos&&!(solos&bit))||(found&&!e[2])){
    gate[c]=0;active[c]=0;seqowned[c]=keycount[c]=0;seqgateleft[c]=0;
    if(c==0){NR12_REG=8;NR14_REG=128;}else if(c==1){NR22_REG=8;NR24_REG=128;}else if(c==2)NR30_REG=0;
   }
  }
}
void seq_irq_tick(uint8_t elapsed) NONBANKED {
 if(!editirq_running||page!=8||!seqplaying||syncmode&&syncslave)return;
 /* Most timer calls contribute one unit. Keep packet locals and the generic
    multiplication helper out of that hot path. */
 while(elapsed--)editirq_phase+=seqbpm;
 while(editirq_phase>=15360U){editirq_phase-=15360U;editirq_commit();}
}
void seq_native_pcm_tick(void) NONBANKED {uint8_t old=seqfraction>=55?2:3,n=editirq_elapsed(old);if(editirq_running&&page==8&&seqplaying&&(!syncmode||!syncslave)){seqticks-=old;seqticks+=n;}seq_irq_tick(n);}
void seq_irq_launch(void) BANKED {uint8_t c,mask;uint16_t clock;uint32_t left;__critical{mask=editirq_enabled;clock=editirq_phase;editirq_running=editirq_enabled=0;}if(!seqplaying)return;for(c=0;c<3;c++)if(mask&(1<<c)){left=(uint32_t)gate[c]*15360U;seqgateleft[c]=left>clock?(left-clock+seqbpm-1)/seqbpm:0;}}
void seq_irq_refresh(uint8_t c) BANKED {(void)c;seq_irq_launch();}
void seq_irq_prepare(void) BANKED {
 uint8_t c,want=0;uint16_t start,units;
 if(page!=8&&!editirq_running)return;
 seqirqdirty=0;if(syncmode&&linkstate==2){if(editirq_running)seq_irq_launch();return;}if(!editbuffer_active()){if(editirq_running)seq_irq_launch();return;}
 if(editirq_running&&prepared_bpm==seqbpm)return;
 if(monomode||polymode||seqswing!=50||seqmode||syncmode&&syncslave)return;
 units=15360U/seqbpm;
 for(c=0;c<3;c++){
  if(seqrecordtrack==c||mono_owned&(1<<c))continue;
  if((c<3&&(evalpatch[c][EV_MODE]||evalpatch[c][EV_CHORD_HISTORY]))||evalpatch[c][EV_DEPTH]||evalpatch[c][EV_LEVEL_MODE]==128||coarsepitch[c][0]||coarsepitch[c][1]||finepitch[c]||bend[c]||tablemode[c]||param[c][9]||param[c][22])continue;
  if(c==0&&pulsekickleft||c==2&&(waveengine||evalwaveactive||(mono_owned&4)))continue;
  irq_patch[c][0]=(param[c][0]<<6)|param[c][7];irq_patch[c][1]=(param[c][2]<<3)|param[c][3];irq_patch[c][2]=128|(param[c][8]<<6);irq_patch[c][3]=(param[0][4]<<4)|(param[0][5]<<3)|param[0][6];irq_patch[c][5]=param[2][16];irq_patch[c][6]=(mx.pan[c]&1?1<<c:0)|(mx.pan[c]&2?16<<c:0);
  want|=1<<c;position[c]=seqposition[c];gate[c]=(seqgateleft[c]+units-1)/units;
 }
 want&=editbuffer_irq_mask;if(!want)return;editirq_wave_capture(wavebytes);prepared_bpm=seqbpm;
 __critical{start=seqclock+seqticks*seqbpm;while(start>=15360U){start-=15360U;for(c=0;c<3;c++)if(++position[c]>=seqlength[c])position[c]=0;}editirq_phase=start;divider_last=DIV_REG;divider_fraction=0;editirq_enabled=want;editirq_running=1;}
}

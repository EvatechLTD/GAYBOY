#pragma bank 47
#pragma opt_code_speed
#include "api.h"
#include "smooth_playback.h"
#include "mod_bypass.h"
#include "lfo_irq.h"
#include "mixer_shared.h"

extern uint8_t arpfirstnotes[3][4],arpfirstvel[3][4],arpindex[3],arpnote[3],arpcount[3],tablemode[4],seqrecordtrack;
extern uint16_t arpfirstfreq[3][4],seqclock;
extern uint32_t arpclock[3];
extern uint16_t pattern_generation;
void editirq_wave_capture(uint8_t *out) BANKED;

/* The timer only reads prepared packets. No ROM banks, SRAM banks, note
   searches, divisions or synthesis dispatch are involved in an attack. */
volatile uint8_t arpirq_enabled;
static volatile uint8_t lost_ownership;
uint16_t arpirq_attacks;
static uint8_t packets[3][8][6],patches[3][6],sequence_length[3],wave_image[16];
static uint8_t stage_packets[8][6],stage_patch[6],stage_wave[16];
static uint16_t arp_phase[3],periods[3],scales[3],remaining[3],generation[3];
static uint16_t attack_wait[3],whole_ticks[3],fractions[3];
static uint8_t repeating[3];
static uint8_t reset_loop[3],unit_shift[3];
static uint16_t loop_wait[3],loop_whole[3],loop_fraction[3],loop_residual[3],first_wait[3],first_residual[3];
static uint8_t continuous[3],pattern_mask;
static uint16_t pattern_gate[3];
static uint16_t prepared_bpm[3];
static uint8_t prepared_notes[3][4],prepared_vel[3][4],prepared_param[3][26],prepared_order[3],prepared_count[3],prepared_level[3],prepared_retrigger[3],prepared_custom;
static uint8_t prepared_eval[3][7];
static uint16_t prepared_length[3];
static uint16_t lasttick[3];
static volatile uint16_t timer_clock,timer_wait=65535U;

uint8_t arp_irq_owned(uint8_t c) NONBANKED {return (arpirq_enabled|lost_ownership)&(1<<c);}
void arp_irq_cancel(uint8_t c) NONBANKED;
uint8_t arp_irq_valid(uint8_t c) NONBANKED {return power&&(seqplaying||smooth_playback_preparing)&&seqswing==50&&(!syncmode||!syncslave)&&(arpirq_enabled&(1<<c))&&generation[c]==pattern_generation&&prepared_bpm[c]==seqbpm&&!bend[c];}
uint8_t arp_irq_pattern_owned(uint8_t c) NONBANKED {return c<3&&(pattern_mask&(1<<c))&&arp_irq_valid(c);}
static uint8_t eligible(uint8_t c,uint16_t period,uint16_t scale);
uint8_t arp_irq_continue(uint8_t c) BANKED {
 if(!continuous[c])return 0;if(arp_irq_valid(c))return 1;
 /* An unrelated lane edit must not retrigger this unchanged, looping chord.
    Validate actual inputs before adopting its new global generation. */
 if(!(arpirq_enabled&(1<<c))||prepared_bpm[c]!=seqbpm||prepared_length[c]!=seqlength[c]||!eligible(c,periods[c],scales[c])||prepared_level[c]!=mx.level[c]||
    memcmp(prepared_eval[c],evalpatch[c]+1,7)||memcmp(prepared_param[c],param[c],26)||
    (c==2&&(prepared_custom!=custom||(custom&&memcmp(wave_image,customwave,16)))))return 0;
 generation[c]=pattern_generation;return 1;
}
void arp_irq_cancel(uint8_t c) NONBANKED {pattern_mask&=~(1<<c);if(!(arpirq_enabled|lost_ownership))return;if(c<3){__critical{arpirq_enabled&=~(1<<c);lost_ownership&=~(1<<c);}}}
void arp_irq_reset(void) NONBANKED {__critical{arpirq_enabled=lost_ownership=pattern_mask=0;timer_wait=65535U;}}

static uint8_t eligible(uint8_t c,uint16_t period,uint16_t scale){uint8_t *p=param[c];
 return power&&(seqplaying||smooth_playback_preparing)&&(!syncmode||!syncslave)&&seqswing==50&&
  arpcount[c]&&arpcount[c]<=4&&period>=(uint16_t)(scale*2)&&
  !monomode&&!polymode&&!tablemode[c]&&!bend[c]&&!finepitch[c]&&(!(coarsepitch[c][0]||(!mod_bypass&&(coarsepitch[c][1]||evalpatch[c][EV_DEPTH])))||lfo_irq_owned(c))&&!MOD_LEVEL(c)&&!(mono_owned&(1<<c))&&
  !p[9]&&!p[22]&&!(c==0&&pulsekickleft)&&!(c==2&&(waveengine||evalwaveactive||p[17]))&&
  seqrecordtrack!=c;
}

uint8_t arp_irq_prepare(uint8_t c,uint32_t requested,uint16_t scale,uint16_t steps) BANKED {
 uint8_t count=arpcount[c],order=evalpatch[c][EV_ORDER],length,i,rank,*packet,*v=param[c],bit=1<<c;
 uint16_t amp,f,wait,whole,fraction,residual,barwhole,barfraction,barresidual,period,pending,input_scale=scale;uint8_t keep,shift=0,pattern=0,e[4];uint16_t gatewindow;uint32_t left,span,original=requested;
 while(requested>65535UL&&!(scale&1)&&!(requested&1)){requested>>=1;scale>>=1;shift++;}
 if(requested>65535UL){arp_irq_cancel(c);return 0;}period=requested;
 if(arp_irq_valid(c)&&periods[c]==period&&scales[c]==scale)return 1;
 if(!eligible(c,period,scale)||order==3||order==7||order==8||order==9){arp_irq_cancel(c);return 0;}
 /* A global edit generation also changes for painting on another lane.
    Retain the running packets when this voice's actual inputs are identical. */
 if((arpirq_enabled&bit)&&periods[c]==period&&scales[c]==scale&&prepared_bpm[c]==seqbpm&&prepared_length[c]==seqlength[c]&&!memcmp(prepared_eval[c],evalpatch[c]+1,7)&&prepared_count[c]==count&&prepared_order[c]==order&&prepared_level[c]==mx.level[c]&&prepared_retrigger[c]==evalpatch[c][EV_RETRIGGER]&&unit_shift[c]==shift&&
    !memcmp(prepared_notes[c],arpfirstnotes[c],count)&&!memcmp(prepared_vel[c],arpfirstvel[c],count)&&!memcmp(prepared_param[c],v,26)&&
    (c!=2||(prepared_custom==custom&&(!custom||!memcmp(wave_image,customwave,16))))){generation[c]=pattern_generation;return 1;}
 left=(uint32_t)steps*15360U;
 if(left<=seqclock)return 0;
 left=(left-seqclock+seqbpm-1)/seqbpm;
 if(!left||left>65535UL)return 0;
 length=count<2?1:(order==2||order==4||order==10)?count*2-2:count;
 for(i=0;i<length;i++){
  rank=i;
  if(order==1)rank=count-1-i;
  else if(order==2||order==4||order==10){if(rank>=count)rank=count*2-2-rank;if(order==4)rank=count-1-rank;else if(order==10)rank=rank&1?count-1-(rank>>1):rank>>1;}
  else if(order==5)rank=rank&1?count-1-(rank>>1):rank>>1;
  else if(order==6)rank=rank&1?(count-1)/2+(rank+1)/2:(count-1)/2-rank/2;
  packet=stage_packets[i];packet[0]=arpfirstnotes[c][rank];packet[1]=mixer_velocity(c,arpfirstvel[c][rank]);
  f=arpfirstfreq[c][rank];packet[2]=f;packet[3]=f>>8;packet[5]=rank;
  amp=(uint16_t)v[1]*packet[1];packet[4]=((amp+1+(amp>>7))>>7)<<4;
 }
 stage_patch[0]=(v[0]<<6)|v[7];stage_patch[1]=(v[2]<<3)|v[3];stage_patch[2]=128|(v[8]<<6);
 stage_patch[3]=(v[4]<<4)|(v[5]<<3)|v[6];stage_patch[4]=(v[21]&1?1<<c:0)|(v[21]&2?16<<c:0);stage_patch[5]=v[15]<<5;
 if(c==2)editirq_wave_capture(stage_wave);
 __critical{pending=seqticks;}
 span=(uint32_t)steps*15360U;left=(uint32_t)seqclock+(uint32_t)pending*seqbpm;if(left>=span)return 0;left=(span-left+seqbpm-1)/seqbpm;
 span=(arpclock[c]+(uint32_t)pending*input_scale)%original;f=span>>shift;
 wait=((uint32_t)period-f+scale-1)/scale;if(!wait)wait=1;
 whole=period/scale;fraction=period%scale;residual=(uint32_t)f+(uint32_t)wait*scale-period;
 span=(uint32_t)steps*15360U;keep=steps==seqlength[c];barwhole=span/seqbpm;barfraction=span%seqbpm;barresidual=(uint32_t)left*seqbpm+seqclock+(uint32_t)pending*seqbpm-span;
 /* A single step-zero chord can repeat with a rest entirely on the timer.
    The note snapshot proves there are no intervening chord changes. */
 gatewindow=left;
 if(evalpatch[c][EV_RETRIGGER]&&steps<seqlength[c]&&seqposition[c]==0&&seq_event_count(c)==count){
  pattern=1;for(i=0;i<count;i++){seq_event_get(c,i,e);if(e[0]||(!e[3]?256U:e[3])!=steps){pattern=0;break;}}
  if(pattern){span=(uint32_t)seqlength[c]*15360U;barwhole=span/seqbpm;barfraction=span%seqbpm;
   span-=seqclock+(uint32_t)pending*seqbpm;left=(span+seqbpm-1)/seqbpm;
   barresidual=(uint32_t)left*seqbpm+seqclock+(uint32_t)pending*seqbpm-(uint32_t)seqlength[c]*15360U;keep=1;
  }
 }
 memcpy(prepared_eval[c],evalpatch[c]+1,7);prepared_length[c]=seqlength[c];memcpy(prepared_notes[c],arpfirstnotes[c],count);memcpy(prepared_vel[c],arpfirstvel[c],count);memcpy(prepared_param[c],v,26);prepared_count[c]=count;prepared_order[c]=order;prepared_level[c]=mx.level[c];prepared_retrigger[c]=evalpatch[c][EV_RETRIGGER];if(c==2)prepared_custom=custom;
 __critical{memcpy(packets[c],stage_packets,length*6);memcpy(patches[c],stage_patch,6);if(c==2)memcpy(wave_image,stage_wave,16);lost_ownership&=~bit;periods[c]=period;scales[c]=scale;arp_phase[c]=residual;attack_wait[c]=wait;whole_ticks[c]=whole;fractions[c]=fraction;continuous[c]=keep;unit_shift[c]=shift;prepared_bpm[c]=seqbpm;repeating[c]=keep;remaining[c]=left;sequence_length[c]=length;generation[c]=pattern_generation;lasttick[c]=timer_clock;
  if(pattern){pattern_mask|=bit;pattern_gate[c]=((uint32_t)steps*15360U+seqbpm-1)/seqbpm;remaining[c]=gatewindow;}else pattern_mask&=~bit;reset_loop[c]=keep&&evalpatch[c][EV_RETRIGGER];loop_wait[c]=left;loop_whole[c]=barwhole;loop_fraction[c]=barfraction;loop_residual[c]=barresidual;first_wait[c]=whole+(fraction!=0);first_residual[c]=fraction?scale-fraction:0;
  if(pattern&&gatewindow<wait)wait=gatewindow;if(left<wait&&(!repeating[c]||reset_loop[c]))wait=left;if(wait<timer_wait)timer_wait=wait;arpirq_enabled|=bit;}
 return 1;
}

static uint16_t next_attack(uint8_t c) NONBANKED {uint16_t wait=whole_ticks[c];if(fractions[c]>arp_phase[c]){wait++;arp_phase[c]+=scales[c]-fractions[c];}else arp_phase[c]-=fractions[c];return wait;}
void arp_irq_due(void) NONBANKED {uint8_t c,bit,i,*packet,*patch,index,vol,solos;uint16_t ticks,wait,over,pitch,next=65535U;
 if(!seqplaying||syncmode&&syncslave){lost_ownership|=arpirq_enabled;arpirq_enabled=0;return;}
 solos=seqsolo&(syncmode==SYNC_TWINK?111:95);if(drumsolomask)solos|=64;
 for(c=0,bit=1;c<3;c++,bit<<=1){
  if(!(arpirq_enabled&bit)||(!remaining[c]&&!(pattern_mask&bit)))continue;
  if(!power||!evalpatch[c][EV_MODE]||c==0&&pulsekickleft||c==2&&(waveengine||evalwaveactive)){
   lost_ownership|=bit;arpirq_enabled&=~bit;continue;
  }
  ticks=timer_clock-lasttick[c];
  if(pattern_mask&bit){if(remaining[c]){
   if(remaining[c]<=ticks){remaining[c]=0;active[c]=seqowned[c]=keycount[c]=0;
    if(c==0){NR12_REG=8;NR14_REG=128;}else if(c==1){NR22_REG=8;NR24_REG=128;}else NR30_REG=0;
   }else remaining[c]-=ticks;
  }}else if(!repeating[c]){if(remaining[c]<=ticks){remaining[c]=0;continue;}remaining[c]-=ticks;}lasttick[c]=timer_clock;
  if(reset_loop[c]){
   if(ticks<loop_wait[c])loop_wait[c]-=ticks;
   else{
    over=ticks-loop_wait[c];wait=loop_whole[c];if(loop_fraction[c]>loop_residual[c]){wait++;loop_residual[c]+=prepared_bpm[c]-loop_fraction[c];}else loop_residual[c]-=loop_fraction[c];loop_wait[c]=wait-over;
    if(pattern_mask&bit)remaining[c]=pattern_gate[c]>over?pattern_gate[c]-over:0;
    index=0;arpindex[c]=sequence_length[c]==1?0:1;arp_phase[c]=first_residual[c];wait=first_wait[c];
    while(over>=wait){over-=wait;index=arpindex[c];arpindex[c]=index+1==sequence_length[c]?0:index+1;wait=next_attack(c);}
    attack_wait[c]=wait-over;goto emit;
   }
  }
  if((pattern_mask&bit)&&!remaining[c])goto deadline;
  if(ticks<attack_wait[c]){attack_wait[c]-=ticks;goto deadline;}
  over=ticks-attack_wait[c];
  do{wait=next_attack(c);
   if(over<wait)break;over-=wait;
  }while(1);
  attack_wait[c]=wait-over;
  index=arpindex[c];if(index>=sequence_length[c])index=0;
  arpindex[c]=index+1==sequence_length[c]?0:index+1;
emit:
  packet=packets[c][index];arpnote[c]=packet[5];
  if(!packet[1]||(seqmuted&bit)||(solos&&!(solos&bit))){
   active[c]=seqowned[c]=keycount[c]=0;
   if(c==0){NR12_REG=8;NR14_REG=128;}else if(c==1){NR22_REG=8;NR24_REG=128;}else NR30_REG=0;
   goto deadline;
  }
  if(lfo_irq_mask&&lfo_irq_owned(c)){lfo_irq_note(c);pitch=lfo_irq_pitch(c,packet[0]);}else pitch=packet[2]|((uint16_t)packet[3]<<8);
  patch=patches[c];route=(route&~(bit|(bit<<4)))|patch[4];NR51_REG=route;
  vol=packet[4]|patch[1];if(!packet[4]&&!(patch[1]&8))vol=8;
  if(c==0){NR10_REG=patch[3];NR11_REG=patch[0];NR12_REG=vol;NR13_REG=pitch;NR14_REG=patch[2]|(pitch>>8);}
  else if(c==1){NR21_REG=patch[0];NR22_REG=vol;NR23_REG=pitch;NR24_REG=patch[2]|(pitch>>8);}
  else{NR30_REG=0;for(i=0;i<16;i++)REG(0xff30+i)=wave_image[i];NR31_REG=param[2][16];NR32_REG=patch[5];NR30_REG=128;NR33_REG=pitch;NR34_REG=patch[2]|(pitch>>8);}
  held[c]=basepitch[c]=livepitch[c]=packet[0];velocity[c]=packet[1];active[c]=keycount[c]=1;keystack[c][0]=packet[0];keyvel[c][0]=packet[1];seqowned[c]=packet[0]+1;arpirq_attacks++;
deadline:
  wait=(pattern_mask&bit)&&!remaining[c]?loop_wait[c]:attack_wait[c];if((pattern_mask&bit)&&remaining[c]&&remaining[c]<wait)wait=remaining[c];if(!repeating[c]&&remaining[c]<wait)wait=remaining[c];if(reset_loop[c]&&loop_wait[c]<wait)wait=loop_wait[c];if(wait<next)next=wait;
 }
 timer_wait=next;
}
/* Keep the common countdown path separate from packet locals and voice work:
   it needs no stack frame, divisions, banks or voice scans. */
void arp_irq_tick(uint8_t elapsed) NONBANKED __naked {
 elapsed;
 __asm
 ld e,a
 or a
 ret z
 ld a,(_arpirq_enabled)
 or a
 ret z
 ld hl,#_timer_clock
 ld a,(hl)
 add a,e
 ld (hl+),a
 ld a,(hl)
 adc a,#0
 ld (hl),a
 ld hl,#_timer_wait
 ld a,(hl)
 sub a,e
 ld (hl+),a
 ld a,(hl)
 sbc a,#0
 ld (hl-),a
 jp c,_arp_irq_due
 or (hl)
 jp z,_arp_irq_due
 ret
 __endasm;
}

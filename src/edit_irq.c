#pragma bank 47
#pragma opt_code_speed
#include "api.h"
#include "mod_bypass.h"
#include "lfo_irq.h"
#include "mixer_shared.h"
extern uint8_t editbuffer_valid,editbuffer_irq_mask,arpirq_enabled;
extern uint8_t arp_active_mask;
void arp_irq_tick(uint8_t elapsed) NONBANKED;
void eval_arp_prepare(void) BANKED;
extern uint16_t seqclock;
uint8_t editbuffer_active(void) BANKED;
uint8_t editbuffer_irq_event(uint8_t c,uint8_t step,uint8_t *out) NONBANKED;
void editbuffer_irq_boundary(const uint8_t *position,uint8_t enabled) NONBANKED;
void editirq_wave_capture(uint8_t *out) BANKED;
extern uint8_t tablemode[4],seqrecordtrack;
static uint8_t wavebytes[16],position[3],irq_patch[3][7];
volatile uint8_t editirq_enabled,editirq_running;
static uint16_t gate[3],prepared_bpm;
static uint8_t prepared_mask,prepared_buffer,prepared_frame,prepared_wave,prepared_kick,prepared_owner,prepared_record,prepared_power;
static volatile uint16_t editirq_phase;
static uint8_t divider_last,divider_fraction;
uint8_t editirq_max_gap;
extern uint8_t linkstate;
uint16_t editirq_attacks,editirq_underruns;
/* Unsupported synthesis modes retain the original foreground dispatcher. */
uint8_t editirq_owned(uint8_t c) NONBANKED {
 if(c>=3||!seqplaying||!(editirq_enabled&editbuffer_irq_mask&(1<<c))||seqrecordtrack==c||seqlength[c]>64)return 0;
 return (!evalpatch[c][EV_MODE]&&!evalpatch[c][EV_CHORD_HISTORY]);
}
/* DIV measures wall time even if a register commit spans a TIMA overflow.
   All enabled paths sample more often than DIV's 15.625 ms wrap interval. */
uint8_t editirq_elapsed(uint8_t fallback) NONBANKED {uint8_t now=DIV_REG,delta,n;
 if(!seqplaying||(!arpirq_enabled&&!editirq_running&&!lfo_irq_mask)){divider_last=now;divider_fraction=0;return fallback;}
 delta=now-divider_last;divider_last=now;if(delta>editirq_max_gap)editirq_max_gap=delta;n=(delta&15)+divider_fraction;divider_fraction=n&15;return (delta>>4)+(n>>4);
}
void editirq_commit(void) NONBANKED {
 uint8_t c,bit,i,e[7],mask,vol,found,solos,vel,*patch;uint16_t amp,pitch;
 editbuffer_irq_boundary(position,editirq_enabled);
 solos=seqsolo&(syncmode==SYNC_TWINK?111:experimental_mode?95:79);if(drumsolomask)solos|=64;
  for(c=0,bit=1;c<3;c++,bit<<=1){if(!(editbuffer_irq_mask&bit))editirq_enabled&=~bit;if(!(editirq_enabled&bit))continue;if(!editirq_owned(c)){editirq_enabled&=~bit;continue;}
   if(++position[c]>=seqlength[c])position[c]=0;if(gate[c])gate[c]--;
   if(!power||c==0&&pulsekickleft||c==2&&waveengine){editirq_enabled&=~bit;continue;}
   found=editbuffer_irq_event(c,position[c],e);if(found&&e[2]&&mx.level[c]&&!(seqmuted&bit)&&(!solos||(solos&bit))){
    gate[c]=e[3]?e[3]:256U;patch=irq_patch[c];mask=bit|(bit<<4);route=(route&~mask)|patch[6];NR51_REG=route;
    /* Levels may change on any UI page. Keep raw note velocity in the
       snapshot and apply current levels without waiting for a new loop. */
    vel=e[2];if(mx.level[c]!=127){if(vel==127)vel=mx.level[c];else{amp=(uint16_t)vel*mx.level[c]+63;vel=(amp>>7)+((uint8_t)((amp&127)+(amp>>7))>=127);}}
    if(c<2){amp=param[c][1];if(vel!=127){amp*=vel;amp=(amp+1+(amp>>7))>>7;}e[6]=amp;}
    else{vol=vel?(vel>84?1:vel>42?2:3):0;if(vol&&param[2][15]){vol+=param[2][15]-1;if(vol>3)vol=3;}else vol=0;e[6]=vol<<5;}
    if(lfo_irq_mask&&lfo_irq_owned(c)){lfo_irq_note(c);pitch=lfo_irq_pitch(c,e[1]-1);e[4]=pitch;e[5]=pitch>>8;}
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
/* This dispatcher runs up to1024 times/s. Keep elapsed and the phase sum in
   registers; stack-spilled C arithmetic was consuming the editor's budget. */
void seq_irq_tick(uint8_t elapsed) NONBANKED __naked {
 elapsed;
 __asm
  push af
  ld a,(_lfo_irq_mask)
  or a,a
  jr z,90201$
  pop af
  push af
  call _lfo_irq_tick
90201$:
  ld a,(_arpirq_enabled)
  or a,a
  jr z,90202$
  pop af
  push af
  call _arp_irq_tick
90202$:
  pop af
  ld c,a
  ld a,(_editirq_running)
  or a,a
  ret z
  ld a,(_seqplaying)
  or a,a
  ret z
  ld a,(_syncmode)
  or a,a
  jr z,90203$
  ld a,(_syncslave)
  or a,a
  ret nz
90203$:
  ld a,(_seqbpm)
  ld e,a
  ld a,(_seqbpm+1)
  ld d,a
  ld a,(_editirq_phase)
  ld l,a
  ld a,(_editirq_phase+1)
  ld h,a
  ld a,c
  or a,a
  jr z,90205$
90204$:
  add hl,de
  dec c
  jr nz,90204$
90205$:
  ld a,l
  ld (_editirq_phase),a
  ld a,h
  ld (_editirq_phase+1),a
  cp #60
  ret c
  ld de,#-15360
  add hl,de
  ld a,l
  ld (_editirq_phase),a
  ld a,h
  ld (_editirq_phase+1),a
  call _editirq_commit
  ld a,(_editirq_phase)
  ld l,a
  ld a,(_editirq_phase+1)
  ld h,a
  jr 90205$
 __endasm;
}
void seq_native_pcm_tick(void) NONBANKED {uint8_t old=seqfraction>=55?2:3,n=editirq_elapsed(old);if((editirq_running||arpirq_enabled||lfo_irq_mask)&&seqplaying&&(!syncmode||!syncslave)){seqticks-=old;seqticks+=n;}seq_irq_tick(n);}
void seq_irq_launch(void) BANKED {uint8_t c,mask;uint16_t clock;uint32_t left;__critical{mask=editirq_enabled;clock=editirq_phase;editirq_running=editirq_enabled=0;}if(!seqplaying)return;for(c=0;c<3;c++)if(mask&(1<<c)){left=(uint32_t)gate[c]*15360U;seqgateleft[c]=left>clock?(left-clock+seqbpm-1)/seqbpm:0;}}
void seq_irq_refresh(uint8_t c) BANKED {(void)c;seq_irq_launch();}
void seq_irq_prepare(void) BANKED {
 uint8_t c,want=0,patch[3][7],image[16],changed=seqirqdirty;uint16_t start,units;
 if((eval_lfousers&7)||lfo_irq_mask)lfo_irq_prepare(changed);if(arp_active_mask)eval_arp_prepare();
 seqirqdirty=0;
 if((syncmode&&linkstate==2)||!editbuffer_active()||monomode||polymode||seqswing!=50||seqmode||syncmode&&syncslave){if(editirq_running)seq_irq_launch();return;}
 /* A page change does not change sound. Validate again on real changes or
    ownership transitions; cache an ineligible result for at most one frame. */
 if(!changed&&prepared_bpm==seqbpm&&(editirq_running||prepared_frame==(uint8_t)sys_time)&&editirq_enabled==prepared_mask&&prepared_buffer==editbuffer_irq_mask&&prepared_wave==waveengine&&prepared_kick==!!pulsekickleft&&prepared_owner==mono_owned&&prepared_record==seqrecordtrack&&prepared_power==power)return;
 prepared_frame=(uint8_t)sys_time;prepared_buffer=editbuffer_irq_mask;prepared_wave=waveengine;prepared_kick=!!pulsekickleft;prepared_owner=mono_owned;prepared_record=seqrecordtrack;prepared_power=power;
 for(c=0;c<3;c++){
  if(!power||seqlength[c]>64||seqrecordtrack==c||mono_owned&(1<<c))continue;
  if(evalpatch[c][EV_MODE]||evalpatch[c][EV_CHORD_HISTORY]||((coarsepitch[c][0]||(!mod_bypass&&(evalpatch[c][EV_DEPTH]||coarsepitch[c][1])))&&!lfo_irq_owned(c))||MOD_LEVEL(c)||finepitch[c]||bend[c]||tablemode[c]||param[c][9]||param[c][22])continue;
  if(c==0&&pulsekickleft||c==2&&(waveengine||evalwaveactive))continue;
  patch[c][0]=(param[c][0]<<6)|param[c][7];patch[c][1]=(param[c][2]<<3)|param[c][3];patch[c][2]=128|(param[c][8]<<6);patch[c][3]=(param[0][4]<<4)|(param[0][5]<<3)|param[0][6];patch[c][5]=param[2][16];patch[c][6]=(mx.pan[c]&1?1<<c:0)|(mx.pan[c]&2?16<<c:0);
  want|=1<<c;
 }
 want&=editbuffer_irq_mask;
 if(!want){if(editirq_running)seq_irq_launch();prepared_bpm=seqbpm;prepared_mask=0;return;}
 if(want&4)editirq_wave_capture(image);
 /* Refresh patch bytes atomically without resetting an unchanged clock. */
 if(editirq_running&&prepared_bpm==seqbpm&&editirq_enabled==want){
  __critical{for(c=0;c<3;c++)if(want&(1<<c))memcpy(irq_patch[c],patch[c],7);if(want&4)memcpy(wavebytes,image,16);}prepared_mask=want;return;
 }
 if(editirq_running)seq_irq_launch();
 units=15360U/seqbpm;
 for(c=0;c<3;c++){position[c]=seqposition[c];gate[c]=(seqgateleft[c]+units-1)/units;}
 prepared_bpm=seqbpm;prepared_mask=want;
 __critical{for(c=0;c<3;c++)if(want&(1<<c))memcpy(irq_patch[c],patch[c],7);if(want&4)memcpy(wavebytes,image,16);
  start=seqclock+seqticks*seqbpm;while(start>=15360U){start-=15360U;for(c=0;c<3;c++)if(++position[c]>=seqlength[c])position[c]=0;}editirq_phase=start;divider_last=DIV_REG;divider_fraction=0;editirq_enabled=want;editirq_running=1;
 }
}

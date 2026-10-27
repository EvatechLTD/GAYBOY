#pragma bank 55
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
#include "smooth_playback.h"
#include "mod_bypass.h"
#include "song_mode.h"
#include "song_link.h"
extern uint16_t editbuffer_base,editbuffer_swaps,pattern_generation,seqclock,seqstepunits,seqdeadline;
extern uint8_t editbuffer_reading;
extern uint32_t noiseleft[2];
extern __at (0xAC58) uint8_t drumnoisetail;
extern uint8_t kickreleasing,expzvolume[2],pulsekickpatch[8];
extern __at (0xAC60) uint8_t noisepatch[2][5];
extern const uint16_t notes[140];
extern volatile uint8_t padread,padwrite;
uint8_t eval_drum_pan(uint8_t c) BANKED;
volatile uint8_t drum_irq_active,drum_irq_pending;
static volatile uint8_t ready,active_table;
static uint8_t building,target,slot,step,headers[2][7],keys[48],vel[2];
static uint16_t drum_phase,lengths[2],kickleft,buildstep,source_swap,seen_generation,left[2];
volatile uint16_t drum_timer_clock,drum_timer_wait=65535U;
static uint16_t last_tick,clock_bpm,clock_units,clock_remainder,step_left;
static void deadline(uint8_t reset){uint16_t wait,residual=drum_phase;
 if(clock_bpm!=seqbpm){clock_bpm=seqbpm;clock_units=15360U/seqbpm;clock_remainder=15360U-clock_units*seqbpm;reset=1;}
 if(reset){
  /* Gate endings only subtract elapsed from step_left. Do not walk an
     almost-completed step one timer unit at a time inside the interrupt. */
  if(residual<(clock_bpm<<2)){
   step_left=clock_units;while(residual>=clock_bpm){residual-=clock_bpm;step_left--;}
   step_left+=clock_remainder>residual;
  }
  else step_left=(15360U-residual+clock_bpm-1)/clock_bpm;
 }
 wait=step_left;if(!wait)wait=1;if(kickleft&&kickleft<wait)wait=kickleft;drum_timer_wait=wait;
}
void drum_irq_reset(void) BANKED {drum_irq_active=drum_irq_pending=ready=building=0;drum_timer_wait=65535U;}

static uint8_t scale(uint16_t v){uint8_t q=v>>7;return q+((uint8_t)((v&127)+q)>=127);}
/* Dedicated SRAM bank3, outside user presets/names A000..A81F, pattern
   clipboard AA00..B1FF, note clipboard B400..B80F, and root BF80..BFFF.
   Each 1280-byte table holds256 five-byte packets; neither note snapshot
   nor either clipboard is borrowed. Split points are whole packets. */
static uint16_t address(uint8_t table,uint8_t at){uint16_t x=(uint16_t)at*5;
 if(!table)return at<96?0xA820U+x:0xB810U+x-480;
 return at<36?0xB200U+x:0xBB30U+x-180;
}
static uint8_t eligible(void){uint8_t c;
 if((!SYNC_EVENT_IRQ)||!power||monomode||polymode||mono_owned||waveengine==3||seqswing!=50||seqmode)return 0;
 if(!mod_bypass)for(c=5;c<8;c++)if(MOD_LEVEL(c)||evalpatch[c][EV_DEPTH]||coarsepitch[c][1])return 0;
 return 1;
}
static void configuration(uint8_t *k){uint8_t c;
 memcpy(k,noisepatch,10);memcpy(k+10,pulsekickpatch,8);memcpy(k+18,evalpatch[4],3);
 for(c=0;c<3;c++){memcpy(k+21+c*2,evalpatch[c+5]+EV_FINE,2);k[27+c]=evalpatch[c+5][EV_PAN];k[30+c]=coarsepitch[c+5][0];}
 k[33]=mx.level[6];k[34]=mx.pan[6];memcpy(k+35,&drummutemask,2);memcpy(k+37,&drumsolomask,2);
 k[39]=seqmuted&64;k[40]=seqsolo&95;k[41]=mod_bypass;memcpy(k+42,&seqbpm,2);memcpy(k+44,seqlength+6,2);k[46]=eligible();k[47]=waveengine;
}
void drum_irq_due(void) BANKED;
void drum_irq_configure(void) BANKED {uint8_t k[48];
 /* Account for time at the old tempo before replacing its countdown. */
 if(drum_irq_active&&clock_bpm!=seqbpm){__critical{drum_irq_due();}}
 if(!seqplaying&&!smooth_playback_preparing)return;
 if(seen_generation==pattern_generation)return;seen_generation=pattern_generation;
 configuration(k);if(!memcmp(k,keys,48))return;memcpy(keys,k,48);
 ready=building=0;drum_irq_pending=1;
 if(!k[46]||k[39]||(k[40]&&!(k[40]&64))){drum_irq_active=drum_irq_pending=0;}
}
/* Only published drum-note edits dirty this table. Painting another lane must
   not revoke timer ownership or restart unchanged percussion. */
void drum_irq_changed(uint8_t mask) BANKED {
 if(mask&9){if(seq_event_count(0)||seq_event_count(3)){drum_irq_active=ready=building=drum_irq_pending=0;return;}}
 if(mask&64){ready=building=0;drum_irq_pending=1;}
}
static uint8_t begin(void){uint16_t i,n,duration,f;uint8_t e[4],pan,*h;
 if(!eligible()||seq_event_count(0)||seq_event_count(3)||(seqmuted&64)||((seqsolo&95)&&!(seqsolo&64)))return 0;
 n=seq_event_count(6);if(!n)return 0;
 for(i=0;i<n;i++){seq_event_get(6,i,e);duration=e[3]?e[3]:256U;if(e[1]<11||e[1]>13||(uint16_t)e[0]+duration>seqlength[6])return 0;}
 target=active_table^1;lengths[target]=seqlength[6];slot=mx.slot;source_swap=editbuffer_swaps;buildstep=0;
 memset(left,0,sizeof(left));memset(vel,0,sizeof(vel));h=headers[target];
 h[0]=(pulsekickpatch[4]<<4)|(pulsekickpatch[7]<<3)|pulsekickpatch[5];h[1]=(pulsekickpatch[2]<<6)|((64-pulsekickpatch[6])&63);
 f=eval_drum_pitch(7,notes[pulsekickpatch[1]]);h[2]=f;h[3]=0xC0|(f>>8);
 pan=eval_drum_pan(5);h[4]=(pan&1?8:0)|(pan&2?128:0);pan=eval_drum_pan(6);h[5]=(pan&1?8:0)|(pan&2?128:0);
 pan=eval_drum_pan(7);h[6]=(pan&1?1:0)|(pan&2?16:0);building=1;return 1;
}
static void build_step(void){volatile uint16_t i;uint16_t duration,kg;uint8_t e[4],p[5],v[5],a,b,j,changed=0,ended=0,raw,vol;
 memset(p,0,5);for(j=0;j<2;j++)if(left[j]&&!--left[j])ended=1;
 /* SDCC must reload this banked out-parameter for every step. */
 i=0;while(seq_event_next_step(6,buildstep,(uint16_t *)&i,e)){
  raw=e[1]-1;if((drummutemask&(1U<<raw))||(drumsolomask&&!(drumsolomask&(1U<<raw)))||!eval_drum_allowed(i-1))continue;
  duration=e[3]?e[3]:256U;
  if(e[1]<13){j=e[1]-11;left[j]=duration;vel[j]=mixer_velocity(6,e[2]);changed=1;}
  else{p[0]|=4;vol=mixer_velocity(6,e[2]);p[3]=(scale((uint16_t)eval_drum_level(7,pulsekickpatch[0])*vol)<<4)|pulsekickpatch[3];
   kg=(uint16_t)pulsekickpatch[6]*4;if(!kg)kg=4;if((uint32_t)seqstepunits*duration<kg)kg=seqstepunits*duration;p[4]=kg;}
 }
 a=!!left[0];b=!!left[1];p[0]|=(a?16:0)|(b?32:0);
 if((changed||ended)&&(a||b)){
  for(j=0;j<5;j++)v[j]=a&&b?(noisepatch[0][j]+noisepatch[1][j]+1)>>1:noisepatch[b?1:0][j];
  if(a&&b)vol=scale(((uint16_t)eval_drum_level(5,noisepatch[0][0])*vel[0]+(uint16_t)eval_drum_level(6,noisepatch[1][0])*vel[1]+127)>>1);
  else vol=scale((uint16_t)eval_drum_level(b?6:5,v[0])*vel[b?1:0]);
  p[0]|=1;p[1]=vol?(vol<<4)|v[4]:8;p[2]=eval_drum_pitch(b?6:5,(v[1]<<4)|(v[3]<<3)|v[2]);
 }else if(ended||(!buildstep&&!a&&!b))p[0]|=2;
 __critical{SWITCH_RAM_MBC5(3);memcpy((void *)address(target,buildstep),p,5);SWITCH_RAM_MBC5(0);}buildstep++;
}
void drum_irq_emit(void) BANKED {uint8_t p[5],flags,*h=headers[active_table];
 SWITCH_RAM_MBC5(3);memcpy(p,(void *)address(active_table,step),5);SWITCH_RAM_MBC5(0);flags=p[0];
 noiseleft[0]=flags&16?1:0;noiseleft[1]=flags&32?1:0;
 if(flags&1){route=(route&~0x88)|h[flags&32?5:4];NR51_REG=route;NR41_REG=0;NR42_REG=p[1];NR43_REG=p[2];NR44_REG=128;expzvolume[1]=p[1]>>4;drumnoiseowned=1;drumnoisetail=0;}
 else if(flags&2){if(!(NR42_REG&7)){NR42_REG=8;NR44_REG=128;drumnoisetail=0;}else drumnoisetail=1;drumnoiseowned=0;}
 if(flags&4){kickleft=p[4]?p[4]:256;pulsekickleft=kickleft;kickreleasing=0;route=(route&~0x11)|h[6];NR51_REG=route;
  NR10_REG=h[0];NR11_REG=h[1];NR12_REG=p[3];NR13_REG=h[2];NR14_REG=h[3];expzvolume[0]=p[3]>>4;}
}
static void arm(uint8_t attack){
 __critical{active_table=target;ready=0;step=seqposition[6];kickleft=pulsekickleft>65535UL?65535U:pulsekickleft;drum_phase=seqclock+seqticks*seqbpm;
  while(drum_phase>=15360U){drum_phase-=15360U;if((uint16_t)step+1>=lengths[active_table])step=0;else step++;}
  if(step>=lengths[active_table])step=0;drum_timer_clock=last_tick=0;drum_irq_active=1;if(attack)drum_irq_emit();deadline(1);}
}
void drum_irq_service(void) BANKED {uint8_t budget=2,reading,busy;
 if(song_playing||song_link_active)return;
 if(!drum_irq_pending||ready)return;
 if(!smooth_playback_preparing&&(!seqplaying||seqservicing||padread!=padwrite||seqticks>=seqdeadline||seqdeadline-seqticks<4))return;
 do{
  reading=editbuffer_reading;busy=seqservicing;editbuffer_reading=seqservicing=1;
  if(building&&source_swap!=editbuffer_swaps)building=0;
  if(!building&&!begin()){drum_irq_active=drum_irq_pending=0;editbuffer_reading=reading;seqservicing=busy;return;}
  build_step();editbuffer_reading=reading;seqservicing=busy;mixfill();
  if(slot!=mx.slot){building=ready=0;drum_irq_active=0;return;}
  if(source_swap!=editbuffer_swaps){building=0;return;}
  if(seen_generation!=pattern_generation){drum_irq_configure();if(!building)return;}
  if(buildstep>=lengths[target]){
   building=drum_irq_pending=0;
   if(!waveengine){uint8_t reload=(!syncmode||syncmode==SYNC_TWINK)&&seqstepunits*seqbpm==15360U&&!(seqstepunits&3)?240:252;__critical{TMA_REG=reload;if(!seqplaying){TIMA_REG=reload;IF_REG&=~TIM_IFLAG;}}}
   __critical{ready=1;}
   if(seqplaying&&!drum_irq_active){mixfill();if(slot==mx.slot)arm(0);}return;
  }
  if(!smooth_playback_preparing&&padread!=padwrite)return;
 }while(--budget);
}
void drum_irq_prepare(void) BANKED {uint16_t guard=512;
 drum_irq_active=ready=building=0;drum_irq_pending=1;seen_generation=pattern_generation;configuration(keys);
 while(drum_irq_pending&&guard--)drum_irq_service();
 /* Compute tempo divisions before the first attack, with transport stopped. */
 clock_bpm=seqbpm;clock_units=15360U/seqbpm;clock_remainder=15360U-clock_units*seqbpm;
}
void drum_irq_start(void) BANKED {if(ready&&seqplaying)arm(1);}
/* Most timer interrupts only update a clock and countdown in fixed ROM.
   The banked dispatcher runs for actual steps/gate endings, not every tick. */
void drum_irq_due(void) BANKED {uint8_t boundary=0;uint16_t elapsed=drum_timer_clock-last_tick;last_tick=drum_timer_clock;
 if(!seqplaying||!power||monomode||polymode||(!SYNC_EVENT_IRQ)||slot!=mx.slot||waveengine==3){drum_irq_active=0;return;}
 if(kickleft){if(kickleft<=elapsed){kickleft=0;pulsekickleft=0;kickreleasing=0;NR12_REG=8;NR14_REG=128;}else{kickleft-=elapsed;pulsekickleft=kickleft;}}
 if(step_left>elapsed)step_left-=elapsed;else step_left=0;
 drum_phase+=elapsed*clock_bpm;
 while(drum_phase>=15360U){boundary=1;drum_phase-=15360U;if(ready){active_table=target;ready=0;}
  if((uint16_t)step+1>=lengths[active_table])step=0;else step++;drum_irq_emit();}
 deadline(boundary);
}
void drum_irq_tick(uint8_t elapsed) NONBANKED __naked {
 elapsed;
 __asm
 ld e,a
 or a,a
 ret z
 ld hl,#_drum_timer_clock
 ld a,(hl)
 add a,e
 ld (hl+),a
 ld a,(hl)
 adc a,#0
 ld (hl),a
 ld hl,#_drum_timer_wait
 ld a,(hl)
 sub a,e
 ld (hl+),a
 ld a,(hl)
 sbc a,#0
 ld (hl-),a
 jr c,drum_deadline_due$
 or (hl)
 ret nz
 drum_deadline_due$:
 ld e,#b_drum_irq_due
 ld hl,#_drum_irq_due
 call ___sdcc_bcall_ehl
 ret
 __endasm;
}

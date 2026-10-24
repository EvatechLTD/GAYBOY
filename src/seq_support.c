#pragma bank 60
#include "api.h"
extern uint16_t seqwholeunits,seqclock;
extern __at (0xAC6A) uint16_t seqcachedbpm;
extern __at (0xAC6C) uint16_t seqstepunits;
extern __at (0xAC6E) uint16_t seqgateunits[7];
extern __at (0xACF0) uint8_t seqcachedgate[7];
extern uint8_t seqgate[7];
void seq_gates(void) BANKED {uint8_t c,busy=seqservicing;memset(seqgate,100,SEQ_TRACKS);if(seqwholeunits&&seqcachedbpm==seqbpm){for(c=0;c<SEQ_TRACKS;c++)if(seqcachedgate[c]!=seqgate[c])break;if(c==SEQ_TRACKS)return;}seqservicing=1;seqstepunits=15360U/seqbpm;seqwholeunits=(245760UL+seqbpm-1)/seqbpm;for(c=0;c<SEQ_TRACKS;c++){seqgateunits[c]=seqstepunits;seqcachedgate[c]=seqgate[c];mixfill();}seqcachedbpm=seqbpm;seqservicing=busy;}
static uint8_t seq_track_neighbor(uint8_t track,uint8_t right){

 return right?(track+1)%7:(track?track-1:6);
}
uint8_t seq_track_page(uint8_t right) BANKED {uint8_t next=seqtrack,tries;
 for(tries=0;tries<7;tries++){next=seq_track_neighbor(next,right);if(eval_visible(next))return next;}return seqtrack;
}

void editirq_clock_reset(void) NONBANKED;
/* Configure a defined standalone epoch while every voice is still stopped.
   TIMA reload alone leaves the first interval dependent on DIV's low phase.
   Keep PCM's selected timer mode and leave all external sync clocks alone. */
void seq_clock_epoch(void) BANKED {uint8_t control;
 __critical {control=TAC_REG;if(!syncmode){TAC_REG=0;DIV_REG=0;}editirq_clock_reset();TIMA_REG=TMA_REG;IF_REG&=~TIM_IFLAG;seqclock=seqticks=seqfraction=0;seqplaying=1;if(!syncmode)TAC_REG=control;}
}

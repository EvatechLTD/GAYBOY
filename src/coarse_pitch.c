#pragma bank 47
#include "api.h"
/* Per-instrument settings; every modulator remains shared. */
uint8_t coarsepitch[8][3];
static const uint16_t down[12]={4096,3866,3649,3444,3251,3068,2896,2734,2580,2435,2299,2170};
static uint32_t shifted(uint32_t period,int16_t semitones,uint32_t maximum){uint16_t ratio;
 while(semitones>=12){period=(period+1)>>1;semitones-=12;}
 while(semitones<=-12){period<<=1;semitones+=12;if(period>maximum)return maximum;}
 ratio=semitones<0?down[12+semitones]*2:down[semitones];period=(period*ratio+2048UL)>>12;
 return period<1?1:period>maximum?maximum:period;
}
uint16_t coarse_apply(uint8_t c,uint16_t base) BANKED {int16_t semitones=(int8_t)coarsepitch[c][0]+eval_amount(c,1);uint32_t period;uint8_t clock=0,div;
 if(!semitones)return base;
 if(c==3||c==5||c==6){div=base&7;period=shifted((uint32_t)(div?div*2:1)<<(base>>4),semitones,458752UL);while(period>14&&clock<15){period=(period+1)>>1;clock++;}div=period<=1?0:(period+1)/2;if(div>7)div=7;return (clock<<4)|(base&8)|div;}
 return 2048U-(uint16_t)shifted(2048U-base,semitones,2048UL);
}
/* Use the 24 reserved bytes already present in the 320-byte tone record. */
static const uint16_t offsets[24]={27,28,29,30,31,59,60,61,62,63,91,92,93,94,95,123,124,125,126,127,166,167,318,319};
void coarse_capture(uint8_t *raw) BANKED {uint8_t i;for(i=0;i<24;i++)raw[offsets[i]]=((uint8_t *)coarsepitch)[i];}
void coarse_restore(const uint8_t *raw,const uint8_t *mod) BANKED {uint8_t i;for(i=0;i<22;i++)((uint8_t *)coarsepitch)[i]=raw[offsets[i]];((uint8_t *)coarsepitch)[22]=mod[142];((uint8_t *)coarsepitch)[23]=mod[143];eval_moddirty=1;}

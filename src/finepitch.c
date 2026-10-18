#pragma bank 14
#include "api.h"
int16_t finepitch[5],finelo[5],finehi[5];
uint16_t finebase[5];
uint8_t finemode[5],finevalid[5];
/* High-word fixed-point products: exact integer bounds for all 16-bit bases.
   Coefficients are (2^(1/12)-1) and (1-2^(-1/12)) in Q0.32. */
uint16_t fine_up(uint16_t n){return ((uint32_t)n*3896+(((uint32_t)n*63790)>>16))>>16;}
uint16_t fine_down(uint16_t n){return ((uint32_t)n*3678+(((uint32_t)n*16583)>>16))>>16;}
void fine_bounds(uint8_t c,uint16_t base,uint8_t direct,uint8_t refill){uint16_t distance;int16_t lo,hi;
 if(finevalid[c]&&finebase[c]==base&&finemode[c]==direct)return;
 if(refill)mixfill();
 if(direct){lo=-(int16_t)fine_down(base);if(refill)mixfill();hi=fine_up(base);if(base+hi>32767)hi=32767-base;}
 else{distance=2048-base;lo=-(int16_t)fine_up(distance);if(refill)mixfill();hi=fine_down(distance);if(lo<-(int16_t)base)lo=-(int16_t)base;if(hi>2047-base)hi=2047-base;}
 finelo[c]=lo;finehi[c]=hi;finebase[c]=base;finemode[c]=direct;finevalid[c]=1;
 if(refill)mixfill();
}
uint16_t fine_apply(uint16_t base,uint8_t c,uint8_t direct) BANKED {
 int16_t value=finepitch[c];
 if(!value){finebase[c]=base;finemode[c]=direct;finevalid[c]=0;return base;}
 fine_bounds(c,base,direct,0);if(value<finelo[c])value=finelo[c];if(value>finehi[c])value=finehi[c];
 if(value!=finepitch[c]){finepitch[c]=value;dirty=1;}return base+value;
}
void fine_edit(uint8_t c,int8_t delta) BANKED {
 uint8_t direct=c==4||(c==2&&waveengine==2),note;uint16_t base=finebase[c];int16_t value;
 if(!base||finemode[c]!=direct){note=c==4?36:c<4&&held[c]!=255?held[c]:60;base=direct?ddsnotes[note>107?107:note]:notes[note+(c==2?12:0)];finevalid[c]=0;}
 fine_bounds(c,base,direct,1);value=finepitch[c]+delta;if(value<finelo[c])value=finelo[c];if(value>finehi[c])value=finehi[c];finepitch[c]=value;
 if(c<3)updatepitch(c);dirty=1;
}

const uint8_t fxmodmax[6]={15,4,3,7,16,63};
void fx_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
void fx_number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits,uint8_t inv){uint16_t place=digits==4?1000:digits==3?100:10;uint8_t d,*dst=canvas+y*20+x;while(digits--){d=0;while(n>=place){n-=place;d++;}*dst++=16+d+(inv?96:0);place/=10;}}
void fine_display(uint8_t c,uint8_t y,uint8_t inv) BANKED {int16_t f=finepitch[c];fx_text(14,y,f<0?"-":"+",inv);fx_number(15,y,f<0?-f:f,4,inv);}
void fx_render(void) BANKED {uint8_t i,inv,id;int16_t f;const char *labels[]={"FINE TICKS","VIBRATO","SLIDE","GATE","PAN"};for(i=0;i<5;i++){mixfill();inv=cursor[6]==i;if(inv)memset(canvas+(5+i)*20,96,20);fx_text(1,5+i,selected==3?(i==0?"NOISE SHIFT":i==1?"NOISE DIV":i==2?"ENV RATE":labels[i]):labels[i],inv);
 if(!i&&selected<3){f=finepitch[selected];fx_text(14,5,f<0?"-":"+",inv);fx_number(15,5,f<0?-f:f,4,inv);}else{if(selected==3&&i<3){id=i==0?18:i==1?20:3;f=param[3][id];}else f=i==4?param[selected][21]:mods[selected][i==1?3:i==2?4:5];fx_number(16,5+i,f,3,inv);}}
 fx_text(0,12,selected==3?"NOISE RATE STEPS":"ONE STEP = ONE TICK",0);
}
void fx_edit(int8_t delta) BANKED {uint8_t row=cursor[6],id,*cell,hi;int16_t n;
 if(!row&&selected<3){fine_edit(selected,delta);return;}
 if(selected==3&&row<3){id=row==0?18:row==1?20:3;cell=&param[3][id];hi=limits[id];}
 else if(row==4){id=21;cell=&param[selected][id];hi=3;}
 else{id=row==1?3:row==2?4:5;cell=&mods[selected][id];hi=fxmodmax[id];}
 n=(int16_t)*cell+delta;*cell=n<0?0:n>hi?hi:n;
 if(row==4||(selected==3&&row<3)){cc(selected,41+id,((uint16_t)*cell*128+hi)/(hi+1));}edited[selected]=1;dirty=1;
}

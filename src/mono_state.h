/* Isolated native mono: two pulses and one hardware wavetable. */
uint8_t monomode,monoosc,monocount,monodown,monovel=127;
uint8_t monovol[3],monokeys[8],monostage[3];
uint16_t monoticks[3];
/* octave (pulse 0=unshifted, wave 0=-1 octave), peak level (wave 0..3), attack, decay, duty, wave shape */
uint8_t monoset[3][7]={{0,12,0,0,2,2,1},{0,10,0,0,2,2,1},{1,3,0,0,16,0,1}};
void monoevent(uint8_t t,uint8_t a,uint8_t b);
void monoframe(void);
#include "mono_waves.h"
uint8_t monodepth[3][7],monoeffective[3][7],monocol;
/* Mod ADSR times in frames; sustain 0..64; LFO type 0..4, rate 0..32. */
uint8_t monosource[11]={12,24,64,24,0,0,2,0,1,0,0};
uint16_t monophase[3][7],monoarpclock;
uint8_t monoarpstep;
uint8_t envstage,envlevel,envfrom,envclock,lfophase,lfocycle,modtail;
const uint8_t lfosine[17]={0,6,12,19,24,30,36,41,45,49,53,56,59,61,63,64,64};
/* Shared clock, evaluated at a target-specific offset; S/H uses cycle identity. */
int8_t monolfo(uint8_t offset){uint16_t turn;uint8_t p,noise,v;turn=(uint16_t)lfophase+offset;p=turn;switch(monosource[4]){case 0:return p<128?(int16_t)p-64:191-(int16_t)p;case 1:return (p>>1)-64;case 2:return p<128?64:-64;case 4:noise=p&63;if(p&64)noise=64-noise;v=lfosine[noise>>2];if(noise<64)v+=((lfosine[(noise>>2)+1]-v)*(noise&3)+2)>>2;return p&128?-(int8_t)v:v;default:noise=(lfocycle+(turn>>8))*73+37;return (noise>>1)-64;}}

uint8_t monomax(uint8_t c,uint8_t id){return id==6?3:id==0?5:id==1?(c==2?4:16):id==2||id==3?8:id==4?(c==2?32:4):32;}
uint8_t monovalue(uint8_t c,uint8_t id){uint8_t base=monoset[c][id],depth=monodepth[c][id],lo,hi,lower,upper;uint16_t amount;if(!depth)return base;lo=id==4&&c==2?1:0;hi=monomax(c,id)-1;if(id==4&&c==2)hi=32;amount=monosource[8]?(uint16_t)depth*envlevel/64:depth;
 if(!monosource[8]){lower=amount>base-lo?lo:base-amount;upper=base+amount>hi?hi:base+amount;return lower+((uint16_t)(monolfo(((monophase[c][id]*32)+22)/45)+64)*(upper-lower)+64)/128;}
 return base+amount>hi?hi:base+amount;}
void modreset(void){envstage=envlevel=envfrom=envclock=modtail=0;}

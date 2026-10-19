#pragma bank 11
#include "api.h"
uint16_t noiserandom=0xACED;
uint8_t noise_random(void){noiserandom^=noiserandom<<7;noiserandom^=noiserandom>>9;noiserandom^=noiserandom<<8;return (uint8_t)noiserandom;}
/* Independent performance patch; restore the player's mono patch on exit. */
uint8_t noisevalues[16]={36,24,3,5,4,15,20,3,12,12,3,24,8,7,12,12};
const uint8_t noisecaps[16]={83,31,3,7,7,15,31,32,64,32,32,64,15,12,32,32};
const uint8_t noisemaps[16]={255,255,255,21,22,6,10,11,12,13,14,23,24,25,8,255};
const char * const noisenames[]={"PITCH","WAVE","LEVEL","CUTOFF","RESONANCE","BRIGHTNESS","PHASE DEPTH","PHASE RATE","DETUNE","CHORUS DEPTH","CHORUS RATE","DELAY TIME","DELAY MIX","FEEDBACK","FILTER CHAOS","CHAOS RATE"};
uint8_t noisecursor,noiseedit,noiseon,noisepitch,noisesaved;
uint8_t noiseset[21],noisedepth[21],noisesource[11],noiseconfig[EXP_COUNT],noiserelease[3];
void noise_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *dst=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*dst++=*s++-32+(inv?96:0);}
void noise_number(uint8_t x,uint8_t y,uint8_t n,uint8_t inv){uint8_t d=0,*dst=canvas+(uint16_t)y*20+x;while(n>=100){n-=100;d++;}*dst++=16+d+(inv?96:0);d=0;while(n>=10){n-=10;d++;}*dst++=16+d+(inv?96:0);*dst=16+n+(inv?96:0);}
void noise_apply(void){uint8_t i;for(i=3;i<15;i++)expconfig[noisemaps[i]]=noisevalues[i];monoset[2][5]=noisevalues[1];monoset[2][1]=noisevalues[2];expconfig[9]=2;monosource[4]=3;monosource[5]=noisevalues[15];monosource[8]=0;exp_changed();if(noiseon){if(noisepitch!=noisevalues[0]){event(0x84,noisepitch,0);noisepitch=noisevalues[0];event(0x94,noisepitch,127);}else monoapply(2);}dirty=1;}
void noise_open(void) BANKED {uint8_t i;memcpy(noiseset,monoset,21);memcpy(noisedepth,monodepth,21);memcpy(noisesource,monosource,11);memcpy(noiseconfig,expconfig,EXP_COUNT);memcpy(noiserelease,exprelease,3);noisesaved=1;monoenable();memset(monodepth,0,21);memset(expconfig,0,EXP_COUNT);memset(exprelease,0,3);memset(monosource,0,11);for(i=0;i<3;i++){monoset[i][1]=0;monoset[i][2]=monoset[i][3]=0;}monoset[2][0]=1;monoset[2][6]=1;expconfig[0]=1;expconfig[4]=64;noiseon=noiseedit=0;noise_apply();}
void noise_close(void) BANKED {panic();noiseon=noiseedit=0;if(noisesaved){memcpy(monoset,noiseset,21);memcpy(monodepth,noisedepth,21);memcpy(monosource,noisesource,11);memcpy(expconfig,noiseconfig,EXP_COUNT);memcpy(exprelease,noiserelease,3);exp_changed();noisesaved=0;}}
void noise_change(int8_t delta){int16_t n=(int16_t)noisevalues[noisecursor]+delta;noisevalues[noisecursor]=n<0?0:n>noisecaps[noisecursor]?noisecaps[noisecursor]:n;noise_apply();}
void noise_input(uint8_t p,uint8_t edge) BANKED {uint8_t i;if(!monocount)noiseon=0;if(p&J_SELECT){if(edge&J_A){if(noiseon){event(0x84,noisepitch,0);noiseon=0;}else{noisepitch=noisevalues[0];event(0x94,noisepitch,127);noiseon=1;}dirty=1;}if(edge&J_B){for(i=1;i<16;i++)noisevalues[i]=noise_random()%(noisecaps[i]+1);noise_apply();}return;}if(p&J_B){if(edge&J_UP)noise_change(1);if(edge&J_DOWN)noise_change(-1);if(edge&J_RIGHT)noise_change(10);if(edge&J_LEFT)noise_change(-10);return;}if(edge&J_A){noiseedit^=1;dirty=1;}if(edge&J_UP){if(noiseedit)noise_change(1);else noisecursor=(noisecursor+15)%16;dirty=1;}if(edge&J_DOWN){if(noiseedit)noise_change(-1);else noisecursor=(noisecursor+1)%16;dirty=1;}if(edge&J_LEFT)noise_change(-1);if(edge&J_RIGHT)noise_change(1);}
/* The main loop clears dirty before dispatching ui_render. Render on every
   dispatch so opening this page and editing a running drone refresh the LCD. */
void noise_render(void) BANKED {uint8_t r,start=noisecursor>=8?8:0,id;if(!monocount)noiseon=0;memset(canvas,0,sizeof(canvas));memset(canvas,96,20);noise_text(0,0,"MASTURBATE",1);noise_text(12,0,noiseon?"DRONE ON":"STOPPED",1);noise_text(0,2,"PARAMETER",0);noise_text(16,2,"VAL",0);for(r=0;r<8;r++){id=start+r;noise_text(0,4+r,noisenames[id],id==noisecursor);noise_number(16,4+r,noisevalues[id],id==noisecursor);mixfill();}noise_text(0,14,"DSP / CH5",0);noise_text(0,16,"DRONE",0);noise_text(8,16,noiseon?"ON":"OFF",0);noise_text(14,16,noiseedit?"EDIT":"MOVE",0);}

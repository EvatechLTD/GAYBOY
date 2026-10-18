#pragma bank 15
#include "api.h"
#include "tones.h"
/* Musical release keeps the pulse DAC bias steady. NRx2 writes alone do not
   latch zero volume on DMG (and may invoke zombie mode): trigger immediately
   after writing zero volume, increasing direction, disabled envelope pace.
   No deferred release can silence a newer owner. Panic and DAC OFF retain
   explicit shutdown. Bank this control path to leave the fixed bank room. */
void stop(uint8_t c) BANKED {
 if(c==0&&pulsekickleft)return;
 if(c==2&&waveengine==3)return;
 active[c]=0;
 if(c<2&&!monomode){
  if(c==0){NR12_REG=param[0][22]?0:8;if(!param[0][22])NR14_REG=0x80;}
  else{NR22_REG=param[1][22]?0:8;if(!param[1][22])NR24_REG=0x80;}
 }else if(c==0)NR12_REG=0;
 else if(c==1)NR22_REG=0;
 else if(c==2){if(waveengine)enginestop();NR30_REG=0;}
 else NR42_REG=0;
}
void panic_audio(void) BANKED{uint8_t c;seqapending=seqamoved=0;seqplaying=0;seqticks=0;drum_stop();exp_reset();monocount=monodown=0;modreset();monovol[0]=monovol[1]=monovol[2]=0;memset(keycount,0,4);memset(monostage,0,3);polysustain=0;for(c=0;c<4;c++){stop(c);held[c]=255;sustain[c]=0;}NR12_REG=NR22_REG=0;}
extern uint8_t seqgate[7];
extern uint16_t seqcachedbpm;
uint8_t experimental_mode=0;
const char * const native_voices[]={"PULSE1","PULSE2","WAVE1","NOISE"};
const char * const native_names[]={"DUTY","VOLUME","ENV DIR","ENV RATE","SWEEP TIME","SWEEP DIR","SWEEP SHIFT","LENGTH","LENGTH ON","MUTE","MASTER R","VIN R","MASTER L","VIN L","WAVE SHAPE","WAVE LEVEL","WAVE LENGTH","WAVE DAC OFF","NOISE SHIFT","NOISE WIDTH","NOISE DIV","PAN","DAC OFF","SUSTAIN","STOP","BEND RANGE"};
const uint8_t native_ids[4][20]={
 {0,1,2,3,26,4,5,6,7,8,9,21,22,25,10,12,11,13},
 {0,1,2,3,26,7,8,9,21,22,25,10,12,11,13},
 {14,15,16,17,8,9,21,25,10,12,11,13},
 {1,2,3,18,19,20,7,8,9,21,22,10,12,11,13}};
const uint8_t native_counts[]={18,15,12,15};

void global_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
void global_number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits,uint8_t inv){uint16_t place=digits==3?100:10;uint8_t d;while(digits--){d=0;while(n>=place){n-=place;d++;}canvas[y*20+x++]=16+d+(inv?96:0);place/=10;}}
uint8_t native_value(uint8_t id){if(id==26)return seqgate[selected];if(id==10)return master&7;if(id==12)return(master>>4)&7;if(id==11)return !!(vin&8);if(id==13)return !!(vin&128);if(id==21)return ((route>>selected)&1)|(((route>>(selected+4))&1)<<1);return param[selected][id];}
void native_edit(int8_t delta,uint8_t reset){uint8_t id=native_ids[selected][cursor[1]],max=id==26?100:limits[id],v=native_value(id);if(id==26){seqgate[selected]=reset?100:delta<0?(v>1?v-1:1):(v<100?v+1:100);seqcachedbpm=0;dirty=1;return;}if(reset)v=patch(program[selected])->v[id];else if(delta<0)v=v?v-1:max;else v=v>=max?0:v+1;cc(selected,41+id,((uint16_t)v*128+max)/(max+1));if(id==16)param[selected][id]=v;dirty=1;}

void global_set(uint8_t enabled) BANKED {
 uint8_t c;enabled=!!enabled;if(enabled==experimental_mode)return;
 panic();enginestop();experimental_mode=enabled;
 monomode=polymode=0;if(!enabled)expactive=0;else exp_changed();waveengine=w2enabled=0;TAC_REG=0;IF_REG&=~TIM_IFLAG;
 seqmode=0;seqsolo&=79;if(selected>3)selected=0;if(seqtrack>3&&seqtrack!=6)seqtrack=0;
 route=0;for(c=0;c<4;c++)if(!param[c][9]){if(param[c][21]&1)route|=1<<c;if(param[c][21]&2)route|=0x10<<c;}globals();
 cursor[1]=0;seqdrawvalid=0;dirty=1;
}
void global_render(void) BANKED {
 uint8_t i;for(i=0;i<18;i++)memset(canvas+i*20,0,20);
 memset(canvas,96,20);global_text(0,0,"GLOBAL SETTINGS",1);
 global_text(0,4,"EXPERIMENTAL MODE",0);global_text(1,6,experimental_mode?"[X] ON":"[ ] OFF",0);
 global_text(0,10,experimental_mode?"SOFTWARE AUDIO + FX":"HARDWARE + SAMPLES",0);
 global_text(0,12,"A: TOGGLE",0);
}
void global_input(uint8_t p,uint8_t edge) BANKED {
 p;if(edge&J_A)global_set(!experimental_mode);
 else if(edge&J_LEFT)global_set(0);else if(edge&J_RIGHT)global_set(1);
}
void modulate(void) BANKED {
 if(!experimental_mode)return;uint8_t c,*m,ph,duty,tp,shape,pan,mask;uint16_t f,base;
 if(monomode){monoframe();return;}if(waveengine)engineframe();for(c=0;c<4;c++){mixfill();if(c==3&&drumnoiseowned)continue;if(c==2&&waveengine)continue;if(!active[c])continue;m=mods[c];if(!tablemode[c]&&!(m[1]|m[2]|m[3]|m[4]|m[5]))continue;if(age[c]<255)age[c]=((uint16_t)age[c]+frameadvance)>255?255:age[c]+frameadvance;
 if(m[5]&&age[c]>=m[5]){stop(c);continue;}
 if((stepclock[c]+=frameadvance)<(m[0]?m[0]:1))continue;stepclock[c]=0;ph=phase[c]++;
 tp=tablepos[c];tablerow[c]=tp;
 if(tablemode[c]){shape=tables[c][tp][1];pan=tables[c][tp][2];mask=(1<<c)|(0x10<<c);route&=~mask;if(pan&1)route|=1<<c;if(pan&2)route|=0x10<<c;NR51_REG=route;
 if(c<2){liveduty[c]=shape&3;REG(c?0xff16:0xff11)=((shape&3)<<6)|param[c][7];}
 else if(c==3)NR43_REG=((shape&15)<<4)|(param[c][19]<<3)|param[c][20];
 if(tablemode[c]!=3){if(tablepos[c]+1<tablelen[c])tablepos[c]++;else if(tablemode[c]==1)tablepos[c]=0;}
 }
 if(c==3)continue;
 f=pitchvalue(c);
 base=c==0?0xff13:c==1?0xff18:0xff1d;REG(base)=f;REG(base+1)=(param[c][8]<<6)|(f>>8);
 if(c==2&&tablemode[c]&&!custom&&!wavepending){uint8_t old=param[2][14];param[2][14]=tables[c][tp][1]&15;wave();param[2][14]=old;NR30_REG=param[2][17]?0:0x80;REG(base)=f;REG(base+1)=0x80|(param[c][8]<<6)|(f>>8);}
 if(c<2&&m[2]&&!tablemode[c]){duty=m[2]==1?(ph&3):m[2]==2?((ph&1)?0:2):((ph&3)==0?0:1);liveduty[c]=duty;REG(c?0xff16:0xff11)=(duty<<6)|param[c][7];}
 }
}


void native_render(void) BANKED {
 uint8_t i,id,row,inv,start;if(page!=1&&cursor[1]>=native_counts[selected])cursor[1]=0;for(i=0;i<18;i++)memset(canvas+i*20,0,20);
 memset(canvas,96,20);global_text(0,0,native_voices[selected],1);global_text(9,0,page==4?"CC":page==1?"TONE":"NATIVE",1);
 if(page==0){global_text(0,3,"HARDWARE CHANNEL",0);global_text(0,5,native_voices[selected],0);global_text(0,8,"A: TONE",0);global_text(0,10,"B: AUDITION",0);return;}
 start=cursor[1]<native_counts[selected]?cursor[1]/9*9:0;
 for(i=0;i<9&&start+i<native_counts[selected];i++){
  id=native_ids[selected][start+i];row=3+i;inv=cursor[1]==start+i;if(inv)memset(canvas+row*20,96,20);
  global_text(0,row,id==26?"GATE %":id==2?"ENV DIRECTION":id==3?"ENV PERIOD":native_names[id],inv);
  if(page==4&&id!=26)global_number(16,row,41+id,3,inv);
  else if(id==2)global_text(15,row,param[selected][2]?"RISE":"FALL",inv);
  else global_number(16,row,native_value(id),3,inv);
 }
 if(page==1){global_text(1,13,"LOAD PRESET",cursor[1]==native_counts[selected]);global_text(0,14,cursor[1]==native_counts[selected]?"A: OPEN PRESET LIST":"A: RESET  B: SOUND",0);global_text(0,16,"L/R: EDIT",0);}
}
void native_input(uint8_t p,uint8_t edge) BANKED {
 if(edge&J_SELECT){if(auditionvoice<4)stop(auditionvoice);auditionvoice=255;selected=(selected+1)%(experimental_mode?5:4);cursor[1]=0;dirty=1;return;}
 if(page==0){if(edge&J_A){page=1;dirty=1;}}
 else{
  if(edge&J_UP){cursor[1]=cursor[1]?cursor[1]-1:native_counts[selected]-(page==1?0:1);dirty=1;}
  if(edge&J_DOWN){cursor[1]=(cursor[1]+1)%(native_counts[selected]+(page==1));dirty=1;}
  if(page==1&&cursor[1]==native_counts[selected]){if(edge&J_A)tone_preset_open();dirty=1;return;}
  if(page==1){if(edge&J_LEFT)native_edit(-1,0);if(edge&J_RIGHT)native_edit(1,0);if(edge&J_A)native_edit(0,1);}
 }
 if(edge&J_B){play(selected,60,110);auditionvoice=selected;}p;
}

uint8_t ui_menu_allowed(uint8_t item) BANKED {if(item==26)return clear_available();if(item==24||item==25)return sparse_enabled==1;if(item==23)return 1;if(item>=21)return page==8;if(!experimental_mode&&(item==2||item==5||item==6||item==7||item==9||item==14))return 0;return item&&(!(item>=1&&item<=6)||page<7);}

void bendupdate(uint8_t c) BANKED {int16_t wheel=(int16_t)wheellast[c]-8192;uint16_t magnitude=wheel<0?-wheel:wheel,result;uint8_t range=param[c][25];result=(magnitude>>6)*range+(((magnitude&63)*range)>>6);bend[c]=wheel<0?-(int16_t)result:result;updatepitch(c);}

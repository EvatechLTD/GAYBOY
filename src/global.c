#pragma bank 15
#include "api.h"
extern uint8_t globalmod[10];
extern uint8_t seqnativelaunchfired;
void seq_native_touch(void) NONBANKED;
#include "tones.h"
#include "mixer_shared.h"
extern uint8_t link_ui_hold;
void seq_native_cancel_voice(uint8_t c) BANKED;
/* Musical release keeps the pulse DAC bias steady. NRx2 writes alone do not
   latch zero volume on DMG (and may invoke zombie mode): trigger immediately
   after writing zero volume, increasing direction, disabled envelope pace.
   No deferred release can silence a newer owner. Panic and DAC OFF retain
   explicit shutdown. Bank this control path to leave the fixed bank room. */
void stop(uint8_t c) BANKED {
 seq_native_cancel_voice(c);
 /* A newly committed IRQ attack already replaced this sequencer release. */
 if(!syncmode&&c<2&&seqplaying&&seqservicing&&(seqirqfired&(1<<c)))return;
 if(c==0&&pulsekickleft){if(!eval_audio_release(c))active[c]=0;return;}
 if(experimental_mode&&c<3&&(mono_owned&(1<<c))){if(c==2){wave_track_down=0;eval_note(2,0);if(evalpatch[2][EV_LEVEL_MODE]!=128||!globalmod[3])active[2]=0;}else if(!eval_audio_release(c))active[c]=0;return;}
 if(c==2&&waveengine==3){if(experimental_mode){wave_track_down=0;eval_note(2,0);if(evalpatch[2][EV_LEVEL_MODE]!=128||!globalmod[3])active[2]=0;}return;}
 if(experimental_mode&&c==3&&drumnoiseowned){if(!eval_audio_release(c))active[c]=0;return;}
 if(!monomode&&c==2&&evalwaveactive){wave_track_down=0;eval_note(2,0);if(exp_off()&4)return;}
 if(eval_audio_release(c))return;
 active[c]=0;
 if(c<2&&!monomode){
  if(c==0){NR12_REG=param[0][22]?0:8;if(!param[0][22])NR14_REG=0x80;}
  else{NR22_REG=param[1][22]?0:8;if(!param[1][22])NR24_REG=0x80;}
 }else if(c==0)NR12_REG=0;
 else if(c==1)NR22_REG=0;
 else if(c==2){if(waveengine)enginestop();NR30_REG=0;}
 else NR42_REG=0;
}
void panic_audio(void) BANKED{uint8_t c;seqapending=seqamoved=0;seqplaying=0;seqticks=0;drum_stop();exp_reset();monocount=monodown=0;modreset();memset(keycount,0,4);voice_reset();polysustain=0;for(c=0;c<4;c++){active[c]=0;stop(c);held[c]=255;sustain[c]=0;}NR12_REG=NR22_REG=0;}
extern uint8_t seqgate[7];
extern uint16_t seqcachedbpm;
uint8_t experimental_mode=1;
const char * const native_voices[]={"PULSE1","PULSE2","WAVE1","NOISE"};
const char * const native_names[]={"DUTY","VOLUME","ENV DIR","ENV RATE","SWEEP TIME","SWEEP DIR","SWEEP SHIFT","LENGTH","LENGTH ON","MUTE","MASTER R","VIN R","MASTER L","VIN L","WAVE SHAPE","WAVE LEVEL","WAVE LENGTH","WAVE DAC OFF","NOISE SHIFT","NOISE WIDTH","NOISE DIV","PAN","DAC OFF","SUSTAIN","STOP","BEND RANGE"};
const uint8_t native_ids[4][20]={
 {0,1,2,3,4,5,6,7,8,9,21,22,25,10,12,11,13},
 {0,1,2,3,7,8,9,21,22,25,10,12,11,13},
 {14,15,16,17,8,9,21,25,10,12,11,13},
 {1,2,3,18,19,20,7,8,9,21,22,10,12,11,13}};
const uint8_t native_counts[]={17,14,12,15};

void global_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
void global_number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits,uint8_t inv){uint16_t place=digits==3?100:10;uint8_t d;while(digits--){d=0;while(n>=place){n-=place;d++;}canvas[y*20+x++]=16+d+(inv?96:0);place/=10;}}
uint8_t native_value(uint8_t id){if(id==26)return seqgate[selected];if(id==10)return master&7;if(id==12)return(master>>4)&7;if(id==11)return !!(vin&8);if(id==13)return !!(vin&128);if(id==21)return ((route>>selected)&1)|(((route>>(selected+4))&1)<<1);return param[selected][id];}
void native_edit(int8_t delta,uint8_t reset){uint8_t id=native_ids[selected][cursor[1]],max=id==26?100:limits[id],v=native_value(id);if(id==15){v=v?4-v:0;if(!reset){v=delta<0?(v?v-1:0):(v<3?v+1:3);cc(selected,56,((uint16_t)(v?4-v:0)*128+3)/4);dirty=1;return;}}if(id==26){seqgate[selected]=reset?100:delta<0?(v>1?v-1:1):(v<100?v+1:100);seqcachedbpm=0;seq_native_touch();dirty=1;return;}if(reset)v=patch(program[selected])->v[id];else if(delta<0)v=v?v-1:0;else v=v>=max?max:v+1;cc(selected,41+id,((uint16_t)v*128+max)/(max+1));if(id==16)param[selected][id]=v;dirty=1;}

void global_set(uint8_t enabled) BANKED {
 uint8_t c;enabled=!!enabled;if(enabled==experimental_mode)return;
 eval_wave_leave();panic();enginestop();experimental_mode=enabled;
 monomode=polymode=0;if(!enabled)expactive=0;else exp_changed();waveengine=w2enabled=0;TAC_REG=0;IF_REG&=~TIM_IFLAG;
 seqmode=0;seqsolo&=79;if(selected>3)selected=0;if(seqtrack>3&&seqtrack!=6)seqtrack=0;
 route=0;for(c=0;c<4;c++)if(!param[c][9]){if(param[c][21]&1)route|=1<<c;if(param[c][21]&2)route|=0x10<<c;}globals();
 cursor[1]=0;seqdrawvalid=0;dirty=1;
}
void global_render(void) BANKED {if(pageconfig==1||pageconfig==2)page_menu_settings_render();else eval_global_render();}
void global_input(uint8_t p,uint8_t edge) BANKED {if(pageconfig==1||pageconfig==2)page_menu_settings_input(p,edge);else eval_global_input(p,edge);}
void modulate(void) BANKED {}
void eval_native_footer(uint8_t id) BANKED;
void native_render(void) BANKED {
 uint8_t i,id,row,inv,start;if(page!=1&&cursor[1]>=native_counts[selected])cursor[1]=0;for(i=0;i<18;i++)memset(canvas+i*20,0,20);
 memset(canvas,96,20);global_text(0,0,native_voices[selected],1);global_text(9,0,page==4?"CC":page==1?"TONE":"NATIVE",1);
 if(page==0){global_text(0,3,"HARDWARE CHANNEL",0);global_text(0,5,native_voices[selected],0);global_text(0,8,"A: TONE",0);global_text(0,10,"B: AUDITION",0);return;}
 start=cursor[1]<native_counts[selected]?cursor[1]/9*9:0;
 for(i=0;i<9&&start+i<native_counts[selected];i++){
  mixfill();id=native_ids[selected][start+i];row=3+i;inv=cursor[1]==start+i;if(inv)memset(canvas+row*20,96,20);
  global_text(0,row,id==26?"GATE %":id==2?"ENV DIRECTION":id==3?"ENV PERIOD":native_names[id],inv);
  if(page==4&&id!=26)global_number(16,row,41+id,3,inv);
  else if(id==2)global_text(15,row,param[selected][2]?"RISE":"FALL",inv);
  else if(id==15)global_number(16,row,native_value(id)?4-native_value(id):0,3,inv);else global_number(16,row,native_value(id),3,inv);
 }
 if(page==1){global_text(1,13,"LOAD PRESET",cursor[1]==native_counts[selected]);global_text(0,14,cursor[1]==native_counts[selected]?"A: OPEN PRESET LIST":"A: RESET  B: SOUND",0);global_text(0,16,"B+ARROWS: EDIT",0);if(cursor[1]<native_counts[selected])eval_native_footer(native_ids[selected][cursor[1]]);}
}
void native_input(uint8_t p,uint8_t edge) BANKED {
 int8_t d=0;uint8_t i;if(edge&J_SELECT){selected=(selected+1)%4;cursor[1]=0;dirty=1;return;}
 if(page==0){if(edge&J_A){page=1;dirty=1;}return;}
 if((edge&(J_A|J_B))&&!(p&(J_UP|J_DOWN|J_LEFT|J_RIGHT))&&cursor[1]<native_counts[selected]&&native_ids[selected][cursor[1]]<26&&limits[native_ids[selected][cursor[1]]]==1){native_edit(native_value(native_ids[selected][cursor[1]])?-1:1,0);dirty=1;return;}
 if(p&(J_A|J_B)){if(edge&J_UP)d=1;if(edge&J_DOWN)d=-1;if(edge&J_LEFT)d=-10;if(edge&J_RIGHT)d=10;
  if(cursor[1]<native_counts[selected])for(i=0;i<(d<0?-d:d);i++)native_edit(d<0?-1:1,0);
 }else {if(edge&J_UP)cursor[1]=cursor[1]?cursor[1]-1:native_counts[selected];if(edge&J_DOWN)cursor[1]=(cursor[1]+1)%(native_counts[selected]+1);if(edge&J_A){if(cursor[1]==native_counts[selected])tone_preset_open();else {play(selected,60,100);auditionvoice=selected;}}}dirty=1;
}

uint8_t ui_menu_allowed(uint8_t item) BANKED {if(item==7||item==9||item==14||item==5||item==6)return 0;if(item==2)return 1;if(item==27)return 1;if(item==26)return clear_available();if(item==24||item==25)return 0;if(item==23)return 1;if(item>=21)return page==8;if(!experimental_mode&&(item==2||item==5||item==6||item==7||item==9||item==14))return 0;return item&&(!(item>=1&&item<=6)||page<7);}

void bendupdate(uint8_t c) BANKED {int16_t wheel=(int16_t)wheellast[c]-8192;uint16_t magnitude=wheel<0?-wheel:wheel,result;uint8_t range=param[c][25];result=(magnitude>>6)*range+(((magnitude&63)*range)>>6);bend[c]=wheel<0?-(int16_t)result:result;updatepitch(c);if(!syncmode)seq_irq_refresh(c);}

/* Keep frame-rate FX work out of the scarce fixed-ROM interrupt bank. */
uint8_t seq_native_fx_idle(void) BANKED;
void service_frame(void) BANKED {uint16_t now,delta;__critical {now=sys_time;}
 if(lastframe!=now){delta=now-lastframe;frameadvance=delta>255?255:delta;lastframe=now;
  if(!seqnativelaunchfired){eval_frame();mixfill();eval_audio_frame();}
  if(midiage)midiage--;
 }
}

/* Mixer pad input is safe at foreground I/O yields. Consume before dispatch
   so nested audio service cannot repeat an edge; never enter from an action. */
extern volatile uint8_t padqueue[32],padwrite,padread;
extern uint8_t lastpad;
void mixer_poll_input(void) BANKED {uint8_t p,edge;
 if(page!=18||navopen||link_ui_hold||mx.focus<30||mx.focus>=38||seqservicing||*(uint8_t *)0xA427||padread==padwrite)return;
 p=padqueue[padread];if(p&(J_START|J_SELECT))return;
 padread=(padread+1)&31;edge=p&~lastpad;ui_input(p,edge);lastpad=p;
}

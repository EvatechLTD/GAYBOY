#pragma bank 12
#include "api.h"
void seq_native_touch(void) NONBANKED;
#include "tones.h"
void mixer_pattern_changed(void) BANKED;
void event(uint8_t s,uint8_t a,uint8_t b) BANKED {uint8_t c=s&15,t=s&0xf0;if(t==0xb0||t==0xc0)mixer_pattern_changed();if(!experimental_mode&&c>3)return;if(waveengine==3&&(c==2||c==5)){
 if(mixrunning||drumon[0]|drumon[1]||t!=0x90||!b)return;
 TAC_REG=0;enginestop();waveengine=0;TMA_REG=TIMA_REG=240;if(syncarmed)sync_timer_config();IF_REG&=~TIM_IFLAG;if(seqplaying)TAC_REG=4;
 }if(c==3&&drumnoiseowned&&(t==0x90||t==0x80))return;if(monomode){if(c==4)monoevent(t,a,b);return;}if(c==5){w2_event(t,a,b);return;}if(c==4){polyevent(t,a,b);return;}if(c>3)return;
 if(c==2&&waveengine&&(t==0x90||t==0x80)){if(t==0x90&&b)enginenote(a,b,0);else engineoff(a);return;}
 if(t==0x90||t==0x80)keyevent(c,a,t==0x90?b:0);
 else if(t==0xe0){seq_native_touch();wheellast[c]=((uint16_t)b<<7)|a;if(c==2&&waveengine==2)pitchdirty=1;else bendupdate(c);}
 else if(t==0xb0)cc(c,a,b);else if(t==0xc0&&a<100){load(c,a);if(c==selected)choice=a;}
}

uint8_t w2enabled,w2settings[5]={24,15,45,24,0},w2age,w2velocity,w2pitch,w2row;
uint8_t w2tablemode,w2tablelen=8,w2tablespeed=6,w2tablestep,w2tableclock;
int8_t w2tables[8][3]={{0,0,15},{0,0,15},{0,0,15},{0,0,15},{0,0,15},{0,0,15},{0,0,15},{0,0,15}};
const uint8_t w2defaults[5]={24,15,45,24,0};
const char *w2pagetitles[]={"WAVE2","TONE","MODULATION","BANK","CC","TABLE","FX"};
const char *w2names[]={"PITCH","LEVEL","DECAY","PITCH DROP","WAVEFORM"};
const uint8_t w2hi[5]={48,15,120,48,3};
const uint8_t w2sine[32]={8,9,10,12,13,14,14,15,15,15,14,14,13,12,10,9,8,6,5,3,2,1,1,0,0,0,1,1,2,3,5,6};
#include "w2_gain.h"
uint8_t w2lastshape=255,w2lastlevel=255;
void w2_sound(void) {
 uint8_t n,shape=w2settings[4];uint16_t level;int16_t pitch;
 if(!w2enabled||waveengine!=2||!softon[1]||softowned[1]!=2)return;
 mixfill();
 if(w2age>=w2settings[2]){softon[1]=0;return;}
 level=((uint16_t)(w2settings[2]-w2age)*w2velocity)/w2settings[2];level*=w2settings[1];/* Exact floor(x/127), x <= 15*127. */level=(level+1+(level>>7))>>7;mixfill();
 pitch=w2pitch+(w2age<8?((uint16_t)w2settings[3]*(8-w2age))/8:0);
 if(w2tablemode){pitch+=w2tables[w2tablestep][0];shape=w2tables[w2tablestep][1];level=(level*w2tables[w2tablestep][2])/15;}
 n=pitch<0?0:pitch>107?107:pitch;softstep[1]=ddsfine(n,4);
 if(shape!=w2lastshape||level!=w2lastlevel){memcpy(softlut[1],w2gain[(shape<<4)+level],32);w2lastshape=shape;w2lastlevel=level;}
}
void w2_frame(void) BANKED {uint16_t ticks;if(!w2enabled||waveengine!=2||!softon[1]||softowned[1]!=2)return;w2_sound();
 if((uint16_t)w2age+frameadvance>255)w2age=255;else w2age+=frameadvance;
 if(w2tablemode){ticks=(uint16_t)w2tableclock+frameadvance;while(ticks>=w2tablespeed){ticks-=w2tablespeed;if(++w2tablestep>=w2tablelen)w2tablestep=0;}w2tableclock=ticks;}
}
void w2_event(uint8_t t,uint8_t a,uint8_t b) BANKED {if(waveengine==3)return;
 if(t==0x90&&b){int16_t n=(int16_t)a+w2settings[0]-48;w2pitch=n<0?0:n>83?83:n;w2age=w2tablestep=w2tableclock=0;w2velocity=b;w2_start(w2pitch,b);w2_sound();}
 else if(t==0x80||(t==0x90&&!b)){if(softowned[1]==2)softon[1]=0;}
 else if(t==0xb0){if(a==120||a==123){if(softowned[1]==2)softon[1]=0;}else if(a==112)w2tablemode=b>=64;else if(a==113)w2tablespeed=1+(b>>2);else if(a==114){w2tablelen=1+(b>>4);if(w2tablestep>=w2tablelen)w2tablestep=0;}else if(a>=41&&a<=45){const uint8_t hi[5]={48,15,120,48,3};w2settings[a-41]=((uint16_t)b*(hi[a-41]+1))>>7;if(a==43&&!w2settings[2])w2settings[2]=1;}}
 if(!(seqplaying&&page==8&&(t==0x90||t==0x80)))dirty=1;
}
void w2_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
void w2_number(uint8_t x,uint8_t y,uint8_t n,uint8_t inv){char num[4];num[0]='0'+n/100;mixfill();num[1]='0'+(n/10)%10;num[2]='0'+n%10;num[3]=0;w2_text(x,y,num,inv);}
uint8_t w2_rows(void){return page==2?3:page==5||page==4?8:page==3?1:page==6?4:page==1?6:5;}
void w2_reset(void){uint8_t i;memcpy(w2settings,w2defaults,5);w2tablemode=0;w2tablelen=8;w2tablespeed=6;for(i=0;i<8;i++){w2tables[i][0]=w2tables[i][1]=0;w2tables[i][2]=15;}dirty=1;}
void w2_render(void) BANKED {
 uint8_t i,inv,value;const char *modlabels[]={"TABLE MODE","TABLE SPEED","TABLE LEN"};
 if(w2row>=w2_rows())w2row=0;
 for(i=0;i<18;i++){mixfill();memset(canvas+i*20,0,20);}memset(canvas,96,20);w2_text(0,0,w2pagetitles[page],1);w2_text(0,2,"WAVE2 / MIDI CH6",0);
 if(page==5){w2_text(0,4,"ST PITCH WAVE LEVEL",0);for(i=0;i<8;i++){mixfill();inv=w2row==i;w2_number(0,5+i,i+1,inv);w2_text(4,5+i,w2tables[i][0]<0?"-":"+",inv&&tablefield==0);w2_number(5,5+i,w2tables[i][0]<0?-w2tables[i][0]:w2tables[i][0],inv&&tablefield==0);w2_number(10,5+i,w2tables[i][1],inv&&tablefield==1);w2_number(16,5+i,w2tables[i][2],inv&&tablefield==2);}return;}
 if(page==2){for(i=0;i<3;i++){mixfill();inv=w2row==i;value=i==0?w2tablemode:i==1?w2tablespeed:w2tablelen;w2_text(1,5+i*2,modlabels[i],inv);w2_number(16,5+i*2,value,inv);}return;}
 if(page==4){for(i=0;i<8;i++){mixfill();inv=w2row==i;w2_number(0,5+i,i<5?41+i:112+i-5,inv);w2_text(4,5+i,i<5?w2names[i]:modlabels[i-5],inv);value=i<5?w2settings[i]:i==5?w2tablemode:i==6?w2tablespeed:w2tablelen;w2_number(16,5+i,value,inv);}return;}
 if(page==3){w2_text(0,5,"001 808 KICK",1);w2_text(0,8,"A LOAD  B AUDITION",0);return;}
 if(page==6){const char *labels[]={"FINE TICKS","PITCH DROP","DECAY","LEVEL"};const uint8_t ids[4]={0,3,2,1};for(i=0;i<4;i++){mixfill();inv=w2row==i;w2_text(1,5+i*2,labels[i],inv);if(!i){fine_display(4,5,inv);}else w2_number(16,5+i*2,w2settings[ids[i]],inv);}return;}

 if(page==1)w2_text(1,15,"LOAD PRESET",w2row==5);
 for(i=0;i<5;i++){mixfill();inv=w2row==i;if(page==4)w2_number(0,5+i*2,41+i,inv);w2_text(page==4?4:1,5+i*2,w2names[i],inv);mixfill();w2_number(16,5+i*2,w2settings[i],inv);}
}
void w2_input(uint8_t p,uint8_t edge) BANKED {
 uint8_t rows=w2_rows();int8_t *cell;int16_t n,lo=0,hi;int8_t delta=edge&J_LEFT?-1:1;(void)p;
 if(w2row>=rows)w2row=0;if(edge&J_UP)w2row=w2row?w2row-1:rows-1;if(edge&J_DOWN)w2row=(w2row+1)%rows;
 if(page==1&&w2row==5){if(edge&J_A)tone_preset_open();if(edge)dirty=1;return;}
 if(page==5){if(edge&J_A)tablefield=(tablefield+1)%3;if(edge&(J_LEFT|J_RIGHT)){cell=&w2tables[w2row][tablefield];lo=tablefield==0?-24:0;hi=tablefield==0?24:tablefield==1?3:15;n=*cell+delta;*cell=n<lo?lo:n>hi?hi:n;}}
 else if(page==2){if(edge&(J_LEFT|J_RIGHT)){n=(w2row==0?w2tablemode:w2row==1?w2tablespeed:w2tablelen)+delta;lo=w2row?1:0;hi=w2row==0?1:w2row==1?32:8;n=n<lo?lo:n>hi?hi:n;if(w2row==0)w2tablemode=n;else if(w2row==1)w2tablespeed=n;else{w2tablelen=n;if(w2tablestep>=n)w2tablestep=0;}}}
 else if(page==3){if(edge&J_A)w2_reset();}
 else if(page==6){const uint8_t ids[4]={0,3,2,1};if(!w2row){if(edge&(J_LEFT|J_RIGHT))fine_edit(4,delta*(p&J_B?10:1));if(edge&J_A)finepitch[4]=0;}else if(edge&(J_LEFT|J_RIGHT)){uint8_t id=ids[w2row];n=w2settings[id]+delta;lo=id==2?1:0;w2settings[id]=n<lo?lo:n>w2hi[id]?w2hi[id]:n;}}
 else if(page!=6&&page!=4){if(edge&(J_LEFT|J_RIGHT)){n=w2settings[w2row]+delta;lo=w2row==2?1:0;w2settings[w2row]=n<lo?lo:n>w2hi[w2row]?w2hi[w2row]:n;}if(edge&J_A)w2_event(0x90,60,110);}
 if((edge&J_B)&&page!=6)w2_event(0x90,60,110);if(edge)dirty=1;
}

/* Elapsed VBlank time keeps acceleration consistent, with quick grid repeats. */
/* Samples of 8 + 20*log2(1 + seconds*2), in level units per second.
   Interpolate at quarter-second intervals; retain fractional steps so slow
   renders do not interrupt a held fader or discard its elapsed time. */
static const uint8_t mixrates[17]={8,20,28,34,40,44,48,51,54,57,60,62,64,66,68,70,71};
static uint16_t mixphase;
uint8_t ui_repeat(uint8_t p,uint8_t edge) BANKED {uint8_t axis,interval,resetmask=J_A|J_B|J_SELECT|J_START;uint16_t now,elapsed,steps;__critical{now=sys_time;}repeatsteps=1;
 if(page==8||page==9||page==10){axis=p&(J_UP|J_DOWN|J_LEFT|J_RIGHT);if((p&J_SELECT)||!axis||(axis&(axis-1))){repeataxis=0;return edge;}}
 else if(page==7){axis=p&(J_UP|J_DOWN);resetmask|=J_LEFT|J_RIGHT;if((!(p&J_B)&&!monoedit)||(p&J_SELECT)||(axis!=J_UP&&axis!=J_DOWN)){repeataxis=0;return edge;}}
 else if(page==18){axis=p&(J_UP|J_DOWN);resetmask|=J_LEFT|J_RIGHT;if(!(p&(J_A|J_B))||(p&J_SELECT)||(axis!=J_UP&&axis!=J_DOWN)){repeataxis=0;return edge;}}
 else{axis=p&(J_LEFT|J_RIGHT);resetmask|=J_UP|J_DOWN;if(!(page==1||page==2||page==5||page==6)||(axis!=J_LEFT&&axis!=J_RIGHT)){repeataxis=0;return edge;}}
 if(navopen||(p&J_START)||(edge&resetmask)){repeataxis=0;mixphase=0;return edge;}
 if(axis!=repeataxis||(edge&axis)){repeataxis=axis;repeatstart=repeatlast=now;mixphase=0;return edge;}
 elapsed=now-repeatstart;
 if(page==18){uint8_t rate,index;
  if(elapsed>=240)rate=71;
  else{index=elapsed/15;rate=mixrates[index]+(uint16_t)(mixrates[index+1]-mixrates[index])*(elapsed%15)/15;}
  steps=now-repeatlast;if(steps>60)steps=60;repeatlast=now;
  mixphase+=steps*rate;steps=mixphase/60;if(steps>8)steps=8;
  mixphase-=steps*60;
  if(steps){repeatsteps=steps;edge|=axis;}return edge;
 }
 if(page==8&&!seqhead){if(elapsed<8)return edge;interval=elapsed<24?4:elapsed<48?2:1;}
 else{if(elapsed<18)return edge;interval=elapsed<60?8:elapsed<120?3:1;}
 if((uint16_t)(now-repeatlast)>=interval){if(repeatlast==repeatstart){repeatlast=now;steps=1;}else{steps=(uint16_t)(now-repeatlast)/interval;if(steps>8){steps=8;repeatlast=now;}else repeatlast+=steps*interval;}repeatsteps=steps;edge|=axis;}return edge;
}

void mixer_pattern_changed(void) BANKED;
extern uint8_t seqrecordtrack;
void seq_record_finish(void) BANKED;
void ui_input(uint8_t p,uint8_t edge) BANKED {uint8_t i;if(sparse_enabled&&edge)sparse_finish_install();if(seqrecordtrack!=255&&(!(p&J_B)||page!=8||navopen||(p&(J_START|J_SELECT))))seq_record_finish();edge=ui_repeat(p,edge);for(i=0;i<repeatsteps;i++){mixfill();/* Navigation alone cannot edit a pattern; conservatively track all input on editable pages. */if(edge&&!navopen&&!(p&J_START)&&(page<18||page==23))mixer_pattern_changed();ui_action(p,edge);}}

/* Durations are one byte (zero means256); avoid a generic32-bit multiply
   in the real-time onset path. Validated tempo/gate bounds fit24 bits. */
static uint32_t gate_multiply(uint32_t value,uint8_t count){uint32_t total=0;while(count){if(count&1)total+=value;count>>=1;if(count)value<<=1;}return total;}
uint32_t seq_gate_length(uint16_t units,uint8_t duration,uint8_t gate) BANKED {uint32_t total=duration?gate_multiply(units,duration):(uint32_t)units<<8;if(gate!=100)total=gate_multiply(total,gate)/100;return total?total:1;}

void load(uint8_t c,uint8_t n) BANKED {seq_native_touch();keycount[c]=0;stop(c);if(c<3)polyowner[c]=0;memcpy(param[c],patch(n)->v,26);memcpy(mods[c],patch(n)->mod,6);phase[c]=age[c]=stepclock[c]=0;tablemode[c]=patch(n)->tconfig&3;tablelen[c]=(patch(n)->tconfig>>2)+1;stocktable(c,patch(n)->table);tablepos[c]=notestep[c]=0;program[c]=n;held[c]=255;bend[c]=0;wheellast[c]=8192;route&=~((1<<c)|(0x10<<c));if(param[c][21]&1)route|=1<<c;if(param[c][21]&2)route|=0x10<<c;NR51_REG=route;edited[c]=0;if(c==2)custom=0;if(!syncmode)seq_irq_refresh(c);dirty=1;}

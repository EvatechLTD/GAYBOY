#pragma bank 59
#include "api.h"
#include "ui_fields.h"
void seq_track_view(void) BANKED;
/* Preview owns the existing track clipboard; no new SRAM allocation. */
uint8_t genopen;
/* Free tail of bank-zero renderer scratch, after drumselectcache. */
__at (0xAFF0) uint8_t genrow;
__at (0xAFF1) uint8_t genpreview;
__at (0xAFF2) uint8_t generror;
__at (0xAFF3) uint8_t gentype;
__at (0xAFF4) uint8_t genstyle;
__at (0xAFF5) uint8_t genroot;
__at (0xAFF6) uint8_t genscale;
__at (0xAFF7) uint8_t gendensity;
__at (0xAFF8) uint8_t genmovement;
__at (0xAFF9) uint8_t genregister;
__at (0xAFFA) uint16_t genseed;
static __at (0xAFFC) uint16_t rng;
static const uint8_t scales[4][7]={{0,2,4,5,7,9,11},{0,2,3,5,7,8,10},{0,2,3,5,7,9,10},{0,3,5,7,10,12,15}};
static void gen_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){while(*s&&x<20)canvas[(uint16_t)y*20+x++]=*s++-32+(inv?96:0);}
static void gen_number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits,uint8_t inv){uint16_t place=digits==3?100:10;uint8_t d;while(digits--){d=(n/place)%10;canvas[(uint16_t)y*20+x++]=16+d+(inv?96:0);place/=10;}}
extern void mixer_pattern_changed(void) BANKED;
extern void seq_clear_release(uint8_t track) BANKED;
static uint8_t random8(void){rng=(rng>>1)^((rng&1)?0xB400U:0);return rng^(rng>>8);}
void gen_cancel(void) BANKED {if(!genopen)return;if(genpreview){seq_paste();}genopen=genpreview=0;seq_dimensions();seq_track_view();seqdrawvalid=0;dirty=1;}
static void generate(void);
void gen_open(void) BANKED {
 if(seq_event_total()>512){seqeventfull=1;dirty=1;return;}
 seqgrouptrack=255;seq_copy();gentype=genstyle=0;genroot=9;genscale=1;gendensity=5;genmovement=genregister=3;genseed=1;genopen=1;genrow=generror=genpreview=0;generate();dirty=1;
}
static uint8_t candidate(uint16_t step,uint8_t *e){
 uint8_t r=random8(),beat=step&15,degree,note,dur=1,c=seqtrack;
 e[0]=step;e[2]=beat%4?88:112;e[3]=1;
 if(c==6){
  /* One hit per step keeps sample overlap and the event budget bounded. */
  if(genstyle==0&&!(beat&3))e[1]=beat==4||beat==12?2:1;
  else if(genstyle!=0&&(beat==4||beat==12))e[1]=2;
  else if(!beat||(genstyle==1&&beat==10))e[1]=1;
  else if((beat&1)==0&&r%10<gendensity)e[1]=3;
  else if(r%20<gendensity)e[1]=genstyle==2?4:3;
  else return 0;
  return 1;
 }
 if(gentype==3){if(((step*gendensity)%16)>=gendensity)return 0;degree=0;}
 else {
  if(beat&&r%10>=gendensity)return 0;
  if(gentype==1)degree=(beat&3)?((r&1)?4:0):0;
  else if(gentype==2)degree=((step%3)*2);
  else {degree=(step&3)==0?((step>>2)%3)*2:(r%(genmovement+1));}
 }
 note=(genregister+1)*12+genroot+scales[genscale][degree%7];
 if(note>127)note=127;e[1]=note+1;
 if(gentype==1)dur=genstyle==0?1:2;else if(gentype==0&&genstyle==2)dur=2;
 if(step+dur>seqlength[c])dur=seqlength[c]-step;e[3]=dur;return 1;
}
static void generate(void){uint16_t i,n,needed=0,outside=0;uint8_t e[4],busy;
 /* Count before editing, including inactive notes that must be retained. */
 n=seq_event_count(seqtrack);for(i=0;i<n;i++){seq_event_get(seqtrack,i,e);if(e[0]>=seqlength[seqtrack])outside++;}
 rng=genseed?genseed:1;for(i=0;i<seqlength[seqtrack];i++)needed+=candidate(i,e);
 if(seq_event_total()-n+outside+needed>512){generror=1;return;}
 busy=seqservicing;seqservicing=1;seq_clear_release(seqtrack);
 i=n;while(i){seq_event_get(seqtrack,--i,e);if(e[0]<seqlength[seqtrack])seq_event_erase(seqtrack,i);}
 rng=genseed?genseed:1;for(i=0;i<seqlength[seqtrack];i++){if(candidate(i,e))seq_event_put(seqtrack,SEQ_EVENT_APPEND,e);mixfill();}
 /* Timer ticks accumulate while the event pool is protected; keep the
    transport position and clock intact, then service the elapsed time. */
 seqservicing=busy;if(seqplaying)seq_frame();genpreview=1;generror=0;seqdrawvalid=0;mixer_pattern_changed();
}
void gen_input(uint8_t p,uint8_t edge) BANKED {if(!edge)return;int16_t value;uint8_t *cell=0,max=0,changed=0;
 if(edge&J_SELECT){gen_cancel();return;}
 
 if(!(p&(J_A|J_B))){if(edge&J_UP)genrow=genrow?genrow-1:9;if(edge&J_DOWN)genrow=(genrow+1)%10;}
 switch(genrow){case 0:cell=&gentype;max=3;break;case 1:cell=&genstyle;max=2;break;case 2:cell=&genroot;max=11;break;case 3:cell=&genscale;max=3;break;case 4:cell=&gendensity;max=10;break;case 5:cell=&genmovement;max=6;break;case 6:cell=&genregister;max=7;break;}
 if(cell&&(p&(J_A|J_B))&&(edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN))){value=*cell+(edge&J_UP?1:edge&J_DOWN?-1:edge&J_RIGHT?10:-10);*cell=value<0?max:value>max?0:value;changed=1;}
 if(genrow==7&&(p&(J_A|J_B))&&(edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN))){genseed=(genseed+(edge&J_UP?1:edge&J_DOWN?999:edge&J_RIGHT?10:990))%1000;changed=1;}
 if(changed)generate();
 if(edge&(J_A|J_B|J_START)){if(genrow==8){if(genpreview&&!generror){genopen=genpreview=0;page=8;seqhead=seqfocus=0;seq_dimensions();seq_track_view();seqdrawvalid=0;}}else if(genrow==9)gen_cancel();}
 dirty=1;(void)p;
}
void gen_render(void) BANKED {
 uint8_t i;const char *labels[]={"TYPE","STYLE","ROOT","SCALE","DENSITY","MOVEMENT","OCTAVE","SEED","KEEP","CANCEL"};
 const char *types[]={"MELODY","BASS","ARP","EUCLID"},*styles[]={"HOUSE","HIPHOP","CHIP"},*names[]={"MAJOR","MINOR","DORIAN","MIN PENT"},*roots[]={"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
 memset(canvas,0,360);memset(canvas,96,20);gen_text(0,0,"THEORY",1);
 for(i=0;i<10;i++)gen_text(1,i+2,labels[i],i>=8&&genrow==i);
 field_text(11,2,9,seqtrack==6?"DRUMS":types[gentype],genrow==0,0);field_text(11,3,9,styles[genstyle],genrow==1,0);field_text(11,4,9,roots[genroot],genrow==2,0);field_text(11,5,9,names[genscale],genrow==3,0);
 field_number(11,6,9,gendensity,genrow==4);field_number(11,7,9,genmovement,genrow==5);field_number(11,8,9,genregister,genrow==6);field_number(11,9,9,genseed%1000,genrow==7);
 gen_text(0,14,generror?"FULL: NO CHANGE":genpreview?"LIVE PREVIEW":"USES COPY CLIPBOARD",0);
 gen_text(0,16,genrow==0?"NOTE PATTERN FAMILY":genrow==1?"RHYTHM AND CONTOUR":genrow==2?"TONAL ROOT NOTE":genrow==3?"ALLOWED PITCH SET":genrow==4?"NUMBER OF NOTE HITS":genrow==5?"PITCH MOTION AMOUNT":genrow==6?"BASE NOTE REGISTER":genrow==7?"REPEATABLE VARIATION":genrow==8?"ACCEPT THIS PREVIEW":"RESTORE OLD PATTERN",0);gen_text(0,17,"A/B EDIT SELECT BACK",0);seqflushpending=1;HIDE_SPRITES;
}



extern uint8_t seqgate[7],seqbeats,seqdenom;
void seq_settings_render(void) BANKED {
 const char *channels[]={"PULSE1","PULSE2","WAVE","NOISE","MONO5","WAVE2","DRUM"};
 uint8_t c=seqtrack,i;const char *labels[]={"BPM","LENGTH","GATE %","VELOCITY","DURATION","MUTE","BEATS","BEAT UNIT","VELOCITY VIEW","ZOOM STEPS","SWING %"};
 uint16_t values[11];
 if(genopen){gen_render();return;}
 mixfill();memset(canvas,0,sizeof(canvas));memset(canvas,96,20);gen_text(0,0,"SEQ SETTINGS",1);gen_text(0,2,channels[c],0);
 gen_text(0,16,seqfocus==1?"QUARTER NOTES / MIN":seqfocus==2?"PATTERN STEP COUNT":seqfocus==5?"NEW NOTE DURATION":seqfocus==6?"MUTE THIS TRACK":seqfocus==7?"BEATS IN EACH BAR":seqfocus==8?"BAR BEAT UNIT":seqfocus==9?"SHOW VELOCITY SLIDERS":seqfocus==10?"VISIBLE STEPS IN ROLL":"LONG/SHORT STEP RATIO",0);gen_text(0,17,"A/B+ARROWS TO EDIT",0);
 values[0]=seqbpm;values[1]=seqlength[c];values[2]=seqgate[c];values[3]=seqdefaultvel[c];values[4]=seqdefaultdur[c];values[5]=!!(seqmuted&(1<<c));values[6]=seqbeats;values[7]=seqdenom;values[8]=!seqvelocityhidden;values[9]=seqcols;values[10]=seqswing;
 for(i=0;i<11;i++){if(i==2||i==3)continue;mixfill();gen_text(1,4+i,labels[i],seqfocus==i+1&&(seqedit||(lastpad&(J_A|J_B))));if(i==5||i==8)gen_text(16,4+i,values[i]?"ON ":"OFF",seqfocus==i+1);else if(i==4&&c==6&&!values[i])gen_text(16,4+i,"AUTO",seqfocus==i+1);else gen_number(16,4+i,values[i],3,seqfocus==i+1);}
}

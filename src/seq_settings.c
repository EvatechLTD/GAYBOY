#pragma bank 51
#include "api.h"
#include "seq_scale.h"
extern uint8_t genopen;
void gen_render(void) BANKED;
static void gen_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){while(*s&&x<20)canvas[(uint16_t)y*20+x++]=*s++-32+(inv?96:0);}
static void gen_number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits,uint8_t inv){uint16_t place=digits==3?100:10;uint8_t d;while(digits--){d=(n/place)%10;canvas[(uint16_t)y*20+x++]=16+d+(inv?96:0);place/=10;}}
extern uint8_t seqgate[7],seqbeats,seqdenom;
static uint8_t *feedback_header_number(uint8_t *dst,uint16_t value,uint8_t base);
void seq_settings_render(void) BANKED {
 const char *channels[]={"PULSE1","PULSE2","WAVE","NOISE","MONO5","WAVE2","DRUM"};
 const char *labels[]={"BPM","BARS","GATE %","VELOCITY","DURATION","MUTE","TIME SIG","","VELOCITY VIEW","ZOOM","SWING %","EXACT STEPS"};
 uint8_t c=seqtrack,i,row=4,*dst,active;uint16_t values[12],bar=(uint16_t)seqbeats*(16/seqdenom);
 if(genopen){gen_render();return;}
 mixfill();memset(canvas,0,sizeof(canvas));memset(canvas,96,20);gen_text(0,0,"SEQ SETTINGS",1);gen_text(0,2,c==TWINK_TRACK?"MS":channels[c],0);
 gen_text(0,16,seqfocus==1?"QUARTER NOTES / MIN":seqfocus==2?"RESIZE TRACK IN BARS":seqfocus==6?"MUTE THIS TRACK":seqfocus==7?"TIME SIG: TOP NUMBER":seqfocus==8?"TIME SIG: BOTTOM":seqfocus==9?"SHOW VELOCITY SLIDERS":seqfocus==10?"HALF / ONE / TWO BARS":seqfocus==12?"CUSTOM LENGTH STEPS":"LONG/SHORT STEP RATIO",0);
 gen_text(0,17,"A/B+ARROWS TO EDIT",0);
 if(seqfocus==2){memset(canvas+320,0,20);gen_number(0,16,bar,3,0);gen_text(4,16,"STEPS/BAR  1/16",0);}
 values[0]=seqbpm;values[1]=seqlength[c]/bar;values[2]=seqgate[c];values[3]=seqdefaultvel[c];values[4]=seqdefaultdur[c];values[5]=!!(seqmuted&(1<<c));values[6]=seqbeats;values[7]=seqdenom;values[8]=!seqvelocityhidden;values[9]=seqcols;values[10]=seqswing;values[11]=seqlength[c];
 for(i=0;i<12;i++){
  if(i==2||i==3||i==4||i==7)continue;mixfill();
  active=seqfocus==i+1||(i==6&&seqfocus==8);
  gen_text(1,row,labels[i],active&&(seqedit||(lastpad&(J_A|J_B))));
  if(i==6){dst=feedback_header_number(canvas+row*20+14,seqbeats,seqfocus==7?96:0);*dst++='/'-32;feedback_header_number(dst,seqdenom,seqfocus==8?96:0);}
  else if(i==1&&seqlength[c]%bar)gen_text(14,row,"CUSTOM",seqfocus==2);
  else if(i==9){uint16_t width=seqzoom==0?(bar+1)/2:seqzoom==1?bar:bar*2;gen_text(12,row,width>32?"32 STEPS":seqzoom==0?"1/2 BAR":seqzoom==1?"1 BAR":"2 BARS",active);}
  else if(i==5||i==8)gen_text(16,row,values[i]?"ON ":"OFF",active);
  else {dst=feedback_header_number(canvas+row*20+16,values[i],active?96:0);}
  row++;
 }
}

void mixer_pattern_changed(void) BANKED;
/* Meter changes regroup existing steps; only explicit length edits resize them. */
void seq_meter_edit(uint8_t field,int16_t delta) BANKED {
 uint8_t beats=seqbeats,denom=seqdenom;int16_t value;
 if(field==7){value=(int16_t)beats+delta;beats=value<1?1:value>32?32:value;}
 else {if(delta>0&&denom<16)denom<<=1;if(delta<0&&denom>2)denom>>=1;}
 if(beats==seqbeats&&denom==seqdenom)return;
 seqbeats=beats;seqdenom=denom;seqzoom=1;
 mixer_pattern_changed();seqdrawvalid=0;dirty=1;
}
static uint8_t *feedback_header_number(uint8_t *dst,uint16_t value,uint8_t base){uint8_t digit,hundreds=value>=100;if(hundreds){digit=value/100;*dst++='0'+digit-32+base;value-=digit*100;}if(hundreds||value>=10){digit=value/10;*dst++='0'+digit-32+base;value-=digit*10;}*dst++='0'+value-32+base;return dst;}
void roll_header_range(void) BANKED {
 uint8_t base=seqhead!=4?96:0,*dst;uint16_t bar=(uint16_t)seqbeats*(16/seqdenom),count=seqlength[seqtrack]/bar;
 memset(canvas+13,base,7);
 if(seqlength[seqtrack]%bar){gen_text(13,0,"CUSTOM",base!=0);return;}
 dst=feedback_header_number(canvas+13,count,base);
 if(count<100)*dst++=base;
 *dst++='B'-32+base;*dst++='A'-32+base;*dst++='R'-32+base;
 if(count!=1)*dst='S'-32+base;
}

extern uint8_t seqpopupchoice,seqpopupstep,seqpopuppitch,seqpopuperror,seqselectused;
uint8_t seq_region_duplicate(void) BANKED;
void seq_popup_input(uint8_t edge) BANKED {uint8_t ok;
 repeatsteps=1;seqselectused=1;
 if(edge&J_SELECT){seqpopup=0;seqdrawvalid=0;dirty=1;return;}
 if(edge&J_UP)seqpopupchoice=seqpopupchoice?seqpopupchoice-1:5;
 if(edge&J_DOWN)seqpopupchoice=(seqpopupchoice+1)%6;
 if(edge&(J_UP|J_DOWN))seqpopuperror=0;
 if(edge&(J_A|J_B|J_START)){ok=seqpopupchoice>=4?seq_region_scale(seqpopupchoice==4):seqpopupchoice==3?seq_region_duplicate():seqpopupchoice==2?seq_region_paste(seqpopupstep,seqpopuppitch):seq_region_copy(seqpopupchoice==1);if(ok==1){seqpopup=0;seqdrawvalid=0;}else seqpopuperror=seqpopupchoice>=4?ok:1;}
 dirty=1;
}
void seq_popup_render(void) BANKED {uint8_t y;memcpy(canvas,seqscreen,360);
 for(y=5;y<16;y++)memset(canvas+y*20+2,0,16);
 gen_text(3,5,"SELECTION",0);gen_text(4,7,"COPY",seqpopupchoice==0);gen_text(4,8,"CUT",seqpopupchoice==1);gen_text(4,9,"PASTE",seqpopupchoice==2);gen_text(4,10,"DUPLICATE",seqpopupchoice==3);
 gen_text(4,11,"X2",seqpopupchoice==4);gen_text(4,12,"/2",seqpopupchoice==5);
 gen_text(0,14,seqpopuperror?(seqpopupchoice>=4?seq_scale_error(seqpopuperror):"CAN'T DO THAT"):"A/B OK SELECT BACK",0);seqflushpending=1;HIDE_SPRITES;
}

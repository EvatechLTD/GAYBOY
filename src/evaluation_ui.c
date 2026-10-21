#pragma bank 20
#include "api.h"
#include "evaluation.h"
#include "ui_fields.h"
extern uint8_t globalmod[10],seqgate[7],drumsynthvoice,pulsekickpatch[8],noisepatch[2][5];
#include "stripped_ui.h"
void eval_preview_channel(uint8_t c) BANKED;
uint8_t eval_value_named(uint8_t c,uint8_t id,uint8_t row,uint8_t inv) BANKED;
static const char * const names[]={"PULSE1","PULSE2","WAVE","NOISE","","HIHAT","SNARE","PULSEKICK"};
static const char * const params[]={"DUTY","LEVEL","ENV DIR","ENV RATE","SWP TIME","SWP DIR","SWP SHIFT","LENGTH","LENGTH ON","MUTE","MASTER R","VIN R","MASTER L","VIN L","WAVE","LEVEL","LENGTH","DAC","CLOCK","WIDTH","DIVISOR","PAN","DAC","SUSTAIN","STOP","BEND"};
static const char * const kn[]={"LEVEL","PITCH","DUTY","FALL RATE","SWP TIME","SWP SHIFT","LENGTH","SWP DIR"};
static const char * const nn[]={"LEVEL","CLOCK","DIVISOR","METALLIC","FALL RATE"};
static const char * const shapes[]={"TRIANGLE","SAW","SQUARE","S/H","SINE"};
static const char * const orders[]={"UP","DOWN","UP/DOWN","RANDOM","DOWN/UP","OUT-IN","IN-OUT","NO RPT","SHUFFLE","WALK","CONV/DIV"};
/* These small signatures live in reserved control SRAM, outside song data. */
__at (0xA475) uint8_t evalui[11];
__at (0xA480) static uint8_t evalrows[14][5];
static uint8_t eval_row_changed(uint8_t c,uint8_t r,uint8_t index,uint8_t inv,uint8_t full){uint8_t sig[5]={0,0,0,0,0},id;
 sig[4]=inv?eval_col+1:0;
 if(page==2)sig[0]=globalmod[r];
 else if(eval_tab==3){if(!r)sig[0]=evalpatch[c][EV_CLOCK];else if(r==1){sig[0]=evalpatch[c][EV_DIV];sig[1]=evalpatch[c][6];sig[2]=evalpatch[c][7];sig[3]=evalpatch[c][EV_CLOCK];}else sig[0]=evalpatch[c][r==2?EV_TIMING:r==3?EV_RETRIGGER:EV_ORDER];}
 else{id=tone_id(c,r);if(id==107)memcpy(sig,coarsepitch[c],3);else if(id==102){if(c<3){sig[0]=finepitch[c];sig[1]=(uint16_t)finepitch[c]>>8;}else{sig[0]=evalpatch[c][EV_FINE];sig[1]=evalpatch[c][EV_FINE+1];}sig[2]=evalpatch[c][EV_DEPTH];sig[3]=evalpatch[c][EV_SOURCES];}
 else if(id==106)sig[0]=c<4?param[c][21]:evalpatch[c][EV_PAN];else if(id<26){sig[0]=c<4?param[c][id]:c==7?pulsekickpatch[id]:noisepatch[c-5][id];sig[1]=evalpatch[c][EV_LEVEL_MODE];}}
 if(!full&&!memcmp(sig,evalrows[index],5))return 0;memcpy(evalrows[index],sig,5);return 1;
}
void eval_render(void) BANKED {uint8_t c=eval_instrument(),r,y,id,inv,n,top=eval_hidden&128?2:5,visible=eval_hidden&128?14:10,start,full;int16_t v;const char *label,*s;
 n=page==2?10:eval_tab==3?5:tone_count(c);if(eval_row>=n)eval_row=n-1;start=page==2?0:n>visible&&eval_row>visible-2?eval_row-(visible-2):0;
 full=evalui[0]!=91||evalui[1]!=page||evalui[2]!=c||evalui[3]!=eval_tab||evalui[4]!=top||evalui[5]!=start||evalui[6]!=n;
 evalui[0]=91;evalui[1]=page;evalui[2]=c;evalui[3]=eval_tab;evalui[4]=top;evalui[5]=start;evalui[6]=n;
 if(full){memset(canvas,0,360);memset(canvas,96,20);}
 if(page==2){const char *labels[]={"ATTACK","DECAY","SUSTAIN","RELEASE","LFO WAVE","LFO RATE","LFO DIV","LFO CLOCK","LFO TIMING","LFO PHASE"};field_text(0,0,20,"MOD",1,0);for(r=0;r<10;r++){y=2+r;inv=eval_row==r;if(!eval_row_changed(c,r,r,inv,full))continue;memset(canvas+y*20,0,20);field_text(0,y,12,labels[r],inv,0);s=0;if(r==4)s=shapes[globalmod[r]%5];else if(r==7)s=globalmod[r]?"TEMPO":"FREE";else if(r==8)s=globalmod[r]==1?"TRIPLET":globalmod[r]==2?"DOTTED":"WHOLE";else if(r==9)s=globalmod[r]?"FREE":"KEY";if(s)field_text(12,y,8,s,inv,1);else if(r==6){id=globalmod[6];field_ratio(y,id>8?1U<<(id-8):1,id<8?1U<<(8-id):1,inv);}else field_number(12,y,8,globalmod[r],inv);mixfill();}field_text(0,16,20,eval_row<4?"SHARED ADSR ALL PARTS":"SHARED LFO ALL PARTS",0,0);field_text(0,17,20,"A/B+ARROWS TO EDIT",0,0);return;}
 if(full){field_text(0,0,12,names[c],1,0);field_text(12,0,8,eval_tab==3?"ARP":"TONE",1,1);}if(!(eval_hidden&128))eval_preview_channel(c);
 n=eval_tab==3?5:tone_count(c);if(eval_row>=n)eval_row=n-1;start=n>visible&&eval_row>visible-2?eval_row-(visible-2):0;
 for(r=start,y=top;r<n&&r<start+visible;r++,y++){inv=r==eval_row;if(!eval_row_changed(c,r,r-start,inv,full))continue;memset(canvas+y*20,0,20);s=0;if(eval_tab==3){const char *labels[]={"CLOCK","RATE","TIMING","RETRIGGER","ORDER"};label=labels[r];v=evalpatch[c][r==1?EV_DIV:0];if(!r)s=evalpatch[c][EV_CLOCK]?"FREE":"TEMPO";else if(r==2)s=evalpatch[c][EV_TIMING]==1?"TRIPLET":evalpatch[c][EV_TIMING]==2?"DOTTED":"WHOLE";else if(r==3)s=evalpatch[c][EV_RETRIGGER]?"ON":"OFF";else if(r==4)s=orders[evalpatch[c][EV_ORDER]%11];field_text(0,y,12,label,inv,0);if(s)field_text(12,y,8,s,inv,1);else if(!evalpatch[c][EV_CLOCK])field_ratio(y,v>8?1U<<(v-8):1,v<8?1U<<(8-v):1,inv);else field_number(12,y,8,evalpatch[c][6]|((uint16_t)evalpatch[c][7]<<8),inv);}
 else{id=tone_id(c,r);label=id==107?"PITCH":id==102?"FINE":id==103?"LOAD PRESET":id==104?"SAVE PRESET":id==105?"PRESET BANKS":id==106?"PAN":c<4?params[id]:c==7?kn[id]:nn[id];
 if(id==102||id==107){field_text(0,y,5,label,0,0);v=id==107?(int8_t)coarsepitch[c][0]:c<3?finepitch[c]:(int16_t)(evalpatch[c][EV_FINE]|((uint16_t)evalpatch[c][EV_FINE+1]<<8));field_number(5,y,5,v,inv&&eval_col==0);field_number(10,y,5,(int8_t)(id==107?coarsepitch[c][1]:evalpatch[c][EV_DEPTH]),inv&&eval_col==1);field_text(16,y,4,(id==107?coarsepitch[c][2]:evalpatch[c][EV_SOURCES]&1)?"LFO":"ADSR",inv&&eval_col==2,0);}
 else{field_text(0,y,12,label,inv,0);if(!eval_value_named(c,id,y,inv)){v=c<4?param[c][id]:c==7?pulsekickpatch[id]:noisepatch[c-5][id];if(c==2&&id==15)v=v?4-v:0;field_number(12,y,8,v,inv);}}}mixfill();}
 field_text(0,16,20,eval_tab==3?"SELECT+L/R INSTRUMENT":(tone_id(c,eval_row)==102||tone_id(c,eval_row)==107)?(eval_col==1?"SIGNED MOD STRENGTH":eval_col==2?"SHARED ADSR OR LFO":tone_id(c,eval_row)==107?"PITCH IN SEMITONES":"DIRECT PITCH TICKS"):"A/B+ARROWS TO EDIT",0,0);field_text(0,17,20,"RELEASE: NAVIGATE",0,0);
}
void eval_native_footer(uint8_t id) BANKED {(void)id;}

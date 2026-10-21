#pragma bank 48
#pragma opt_code_speed
#include "api.h"
#include "drum_rows.h"
#include "mixer_shared.h"
#include "mixer_drum_names.h"
uint8_t drumvelrow;
extern uint8_t seqdrag,seqbused;
__at (0xA440) static uint8_t values[32];
__at (0xA460) static uint32_t pending;
__at (0xA464) static uint8_t velocityvalid;
__at (0xA465) static uint8_t viewbase;
__at (0xA466) static uint8_t viewcols;
__at (0xA467) static uint8_t viewslot;
__at (0xA468) static uint8_t viewrow;
extern __at (0xBA00) uint8_t rollrow[320];
extern __at (0xBC80) uint8_t rollx[41];
extern __at (0xADB8) uint8_t rolloldvel[40];
extern volatile uint8_t padread,padwrite;
void drum_velocity_span(uint8_t y,uint8_t left,uint8_t right,uint8_t color) BANKED;
void roll_upload(uint8_t row) BANKED;
uint8_t roll_velocity_bar(uint8_t col,uint8_t oldheight,uint8_t height) BANKED;
static uint8_t scale(uint8_t value){return value?1+((uint16_t)value*20)/127:0;}
static uint8_t ready(void){return velocityvalid==97&&viewbase==seqbase&&viewcols==seqcols&&viewslot==mx.slot&&viewrow==drumvelrow;}
static void velocity_load(void){uint16_t i,count=seq_event_count(6);uint8_t e[4],col,retained=viewbase==seqbase&&viewcols==seqcols&&viewslot==mx.slot&&viewrow==drumvelrow;
 memset(values,0,32);for(i=0;i<count;i++){seq_event_get(6,i,e);if(e[1]==DRUM_VOICE_ROW(drumvelrow)+1&&e[0]>=seqbase&&(uint16_t)e[0]<seqbase+seqcols){col=e[0]-seqbase;if(!values[col])values[col]=e[2];}if(!(i&7))mixfill();}
 velocityvalid=97;viewbase=seqbase;viewcols=seqcols;viewslot=mx.slot;viewrow=drumvelrow;pending=0;if(!retained)memset(rolloldvel,255,32);for(col=0;col<seqcols;col++)if(rolloldvel[col]!=scale(values[col]))pending|=1UL<<col;
}
void drum_velocity_status(void) BANKED {const char *name=mixer_drum_name(drumkit,DRUM_VOICE_ROW(drumvelrow));uint8_t i,v=0,col=seqcursor[6]-seqbase;
 for(i=0;i<3;i++){canvas[15*20+i]=name[i]?name[i]-32:0;canvas[16*20+i]='-'-32;}
 if(ready()&&col<seqcols)v=values[col];if(v){canvas[16*20]=16+v/100;canvas[16*20+1]=16+(v/10)%10;canvas[16*20+2]=16+v%10;}
}
void drum_velocity_refresh(void) BANKED {velocityvalid=0;}
void drum_velocity_set(uint8_t row,uint8_t step,uint8_t value) BANKED {uint8_t col;if(row!=drumvelrow||!ready()||step<seqbase||(uint16_t)step>=seqbase+seqcols)return;col=step-seqbase;values[col]=value;pending|=1UL<<col;}
void drum_velocity_render(void) BANKED {uint8_t row,col,y,height,pad,left,right;
 velocity_load();for(row=14;row<17;row++){memset(rollrow,0,320);if(row==14)drum_velocity_span(0,0,160,2);
  for(col=0;col<seqcols;col++){height=scale(values[col]);left=rollx[col];right=rollx[col+1];pad=right-left<6?1:2;if(height)for(y=0;y<8;y++)if((uint8_t)((row-14)*8+y)>=24-height)drum_velocity_span(y,left+pad,right-pad,3);mixfill();}
  roll_upload(row);service();
 }for(col=0;col<seqcols;col++)rolloldvel[col]=scale(values[col]);pending=0;drum_velocity_status();
}
void drum_velocity_service(void) BANKED {uint8_t col,height;if(page!=8||seqtrack!=6||navopen||seqpopup||seqvelocityhidden||seqdrawvalid!=1||padread!=padwrite)return;
 if(!ready())velocity_load();if(!pending)return;for(col=0;col<seqcols;col++)if(pending&(1UL<<col))break;if(col==seqcols)return;
 height=scale(values[col]);if(roll_velocity_bar(col,rolloldvel[col],height)){rolloldvel[col]=height;pending&=~(1UL<<col);}drum_velocity_status();
}
uint16_t roll_drum_onset(uint8_t step,uint8_t row) BANKED;
static uint16_t velocity_event(uint8_t *e){uint16_t cursor=0,n=roll_drum_onset(seqcursor[6],drumvelrow);
 if(n==65535U)return n;if(n!=65534U&&seq_event_get(6,n,e)&&e[0]==seqcursor[6]&&e[1]==DRUM_VOICE_ROW(drumvelrow)+1)return n;
 while(seq_event_next_step(6,seqcursor[6],&cursor,e))if(e[1]==DRUM_VOICE_ROW(drumvelrow)+1)return cursor-1;return 65535U;
}
void drum_velocity_edit(int8_t delta) BANKED {uint16_t index;uint8_t e[4],col,next;int16_t value;
 index=velocity_event(e);if(index==65535U)return;value=(int16_t)e[2]+delta;next=value<1?1:value>127?127:value;if(next==e[2])return;e[2]=next;seq_event_put(6,index,e);eval_plotvel[6]=e[2];
 if(!ready())velocity_load();col=e[0]-seqbase;values[col]=e[2];pending|=1UL<<col;if(roll_velocity_bar(col,rolloldvel[col],scale(e[2]))){rolloldvel[col]=scale(e[2]);pending&=~(1UL<<col);}drum_velocity_status();dirty=1;
}

void drum_velocity_input(uint8_t p,uint8_t edge) BANKED {int8_t delta=0;if(!edge)return;
 if(p&(J_A|J_B)){if(edge&J_UP)delta++;if(edge&J_DOWN)delta--;if(edge&J_LEFT)delta-=10;if(edge&J_RIGHT)delta+=10;if(delta)drum_velocity_edit(delta);return;}
 if(edge&J_LEFT){if(seqcursor[6]==seqbase){drumrow=drumvelrow;seqhead=6;}else seqcursor[6]--;}
 if((edge&J_RIGHT)&&(uint16_t)seqcursor[6]+1<seqlength[6])seqcursor[6]++;
 if(edge&J_UP){drumrow=drumvelrow;seqhead=6;}dirty=1;
}
void drum_name_input(uint8_t p,uint8_t edge) BANKED {
 (void)p;if(!edge)return;if(edge&(J_A|J_B)){drumvelrow=drumrow;if(seqvelocityhidden){seqvelocityhidden=0;seqdrawvalid=0;}velocityvalid=0;seqcursor[6]=seqbase;seqhead=5;seqedit=0;seqapending=seqdrag=0;seqbused=1;dirty=1;return;}
 if(edge&J_LEFT){if(seqbase){seqcursor[6]=seqbase-1;seqhead=0;}}
 if(edge&J_RIGHT){seqcursor[6]=seqbase;seqhead=0;}
 if(edge&J_UP){if(drumrow)drumrow--;else seqhead=2;}
 if((edge&J_DOWN)&&drumrow<12)drumrow++;dirty=1;
}

uint8_t roll_note_feedback(uint8_t c,const uint8_t *e,uint8_t erase) BANKED;
void seq_clear_release(uint8_t c) BANKED;
void seq_brush_toggle(void) BANKED {uint8_t c=seqtrack,e[4],fast;uint16_t cursor=0;
 while(seq_event_next_step(c,seqcursor[c],&cursor,e))if(e[1]==seqpitch[c]+1){fast=roll_note_feedback(c,e,1);if(seqplaying&&seqsource[c]==e[0])seq_clear_release(c);seq_event_erase(c,cursor-1);seqdrawvalid=fast;dirty=1;return;}
 e[0]=seqcursor[c];e[1]=seqpitch[c]+1;e[2]=eval_plotvel[c];e[3]=seqdefaultdur[c];fast=seq_event_total()<256?roll_note_feedback(c,e,0):0;if(!seq_event_put(c,65535U,e))fast=0;seqdrawvalid=fast;dirty=1;
}

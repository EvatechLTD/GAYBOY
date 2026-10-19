#pragma bank 60
#include "api.h"
#include "mixer_shared.h"
extern uint8_t mixer_hidden[4],layout_cursor;
static const char * const tracks[7]={"P1","P2","WV1","NS","M5","WV2","DRM"};
static uint8_t layout_hidden(uint8_t id){return mixer_hidden[id>>3]&(1U<<(id&7));}
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
static void num(uint8_t x,uint8_t y,uint8_t n,uint8_t inv){char s[4];s[0]='0'+n/100;s[1]='0'+n/10%10;s[2]='0'+n%10;s[3]=0;text(x,y,s,inv);}
void mixer_layout_render(void) BANKED{uint8_t i,start=layout_cursor>5?layout_cursor-5:0;char label[17];if(start>18)start=18;
 memset(canvas,0,360);memset(canvas,96,20);text(0,0,"MIXER LAYOUT",1);
 for(i=start;i<start+10;i++){uint8_t row=3+i-start;num(0,row,i<20?i+1:i-19,layout_cursor==i);
  if(i<7)text(4,row,tracks[i],layout_cursor==i);
  else if(i<20){text(4,row,"DRUM",layout_cursor==i);num(9,row,i-6,0);}
  else {getname(i-20,label);text(4,row,label[0]?label:"PAD",layout_cursor==i);}
  text(16,row,layout_hidden(i)?"HIDE":"SHOW",layout_cursor==i);mixfill();
 }
 text(0,14,"A SHOW/HIDE",0);text(0,15,"B SHOW ALL",0);text(0,17,"SELECT CLOSE",0);
}

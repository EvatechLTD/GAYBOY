#pragma bank 60
#include "api.h"
#include "mixer_shared.h"
#include "sparse_store.h"
#include "link_control.h"
extern uint8_t mixer_hidden[8],layout_cursor,mixer_device;
extern uint8_t mixer_layout_dirty;
/* Root 110..120 was erased/reserved in GBD1. Redundant-root CRC and commit
   publication protect this optional project layout without moving objects. */
/* Legacy-only 3:BC10..BC2F was unassigned. Sparse recovery owns this region
   in sparse format, so these records are NEVER touched with sparse enabled. */
static uint8_t layout_valid(uint8_t *p){uint8_t c=0,i;for(i=2;i<12;i++)c+=p[i];return p[0]=='M'&&p[1]==1&&p[12]==c&&p[13]==(uint8_t)(c^255)&&p[14]=='L'&&p[15]==0xA5&&p[11]<2;}
static uint8_t layout_latest(uint8_t *p){uint8_t a=layout_valid(p),b=layout_valid(p+16);return b&&(!a||(uint8_t)(p[18]-p[2])<128)?1:a?0:255;}
void mixer_layout_load(void) BANKED {uint8_t data[32],copy;memset(mixer_hidden,0,8);linkpair=0;
 if(sparse_enabled==1&&pool_root[118]=='M'&&pool_root[119]==1){memcpy(mixer_hidden,pool_root+110,8);linkpair=pool_root[120]==1;}
 else if(!sparse_enabled){readpart(8,2064,data,32);copy=layout_latest(data);if(copy<2){memcpy(mixer_hidden,data+copy*16+3,8);linkpair=data[copy*16+11];}}
 mixer_layout_dirty=0;
}
void mixer_layout_service(void) BANKED {uint8_t data[32],copy,next,i,zero=0;
 if(seqplaying||sparse_journal_busy()||mixer_prepare_busy())return;
 if(sparse_enabled==1){memcpy(pool_root+110,mixer_hidden,8);pool_root[118]='M';pool_root[119]=1;pool_root[120]=linkpair;if(pool_commit())mixer_layout_dirty=0;}
 else if(!sparse_enabled){readpart(8,2064,data,32);copy=layout_latest(data);next=copy<2?copy^1:0;
  data[2]=copy<2?data[copy*16+2]+1:0;data[0]='M';data[1]=1;memcpy(data+3,mixer_hidden,8);data[11]=linkpair;data[12]=0;for(i=2;i<12;i++)data[12]+=data[i];data[13]=data[12]^255;data[14]='L';data[15]=0xA5;
  writepart(8,2064+next*16,&zero,1);writepart(8,2065+next*16,data+1,15);writepart(8,2064+next*16,data,1);mixer_layout_dirty=0;
 }
}
static const char * const tracks[7]={"P1","P2","WV1","NS","M5","WV2","DRM"};
static uint8_t layout_hidden(uint8_t id){return mixer_hidden[mixer_device*4+(id>>3)]&(1U<<(id&7));}
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
static void num(uint8_t x,uint8_t y,uint8_t n,uint8_t inv){char s[4];s[0]='0'+n/100;s[1]='0'+n/10%10;s[2]='0'+n%10;s[3]=0;text(x,y,s,inv);}
void mixer_layout_render(void) BANKED{uint8_t i,start=layout_cursor>5?layout_cursor-5:0;char label[17];if(start>18)start=18;
 memset(canvas,0,360);memset(canvas,96,20);text(0,0,mixer_device?"LINK LAYOUT":"LOCAL LAYOUT",1);
 for(i=start;i<start+10;i++){uint8_t row=3+i-start;num(0,row,i<20?i+1:i-19,layout_cursor==i);
  if(i<7)text(4,row,tracks[i],layout_cursor==i);
  else if(i<20){text(4,row,"DRUM",layout_cursor==i);num(9,row,i-6,0);}
  else {if(mixer_device){memcpy(label,linkmirror.names[i-20],16);label[16]=0;}else getname(i-20,label);text(4,row,label[0]?label:"PAD",layout_cursor==i);}
  text(16,row,layout_hidden(i)?"HIDE":"SHOW",layout_cursor==i);mixfill();
 }
 text(0,14,"A SHOW/HIDE",0);text(0,15,"B SHOW ALL",0);text(0,17,"SELECT CLOSE",0);
}

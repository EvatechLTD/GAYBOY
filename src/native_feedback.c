#pragma bank 61
#pragma opt_code_speed
#include "api.h"

/* Native and drum sequencers never render simultaneously. Reuse the drum
   hit-test workspace for the native chord compositor, with no new WRAM. */
__at (0xA500) static uint8_t lowest[32];
__at (0xA540) static uint8_t cells[16][32];
__at (0xA740) static uint8_t onsets[32][4];
__at (0xA469) static uint8_t pending;
__at (0xA46A) static uint8_t edittrack;
__at (0xA46B) static uint8_t editbase;
__at (0xA46C) static uint8_t edittop;
__at (0xA46D) static uint8_t editcols;
__at (0xA46E) static uint8_t editheight;
__at (0xA46F) static uint8_t firsttile;
__at (0xA470) static uint8_t lasttile;
__at (0xA471) static uint16_t velocitybits;
__at (0xA473) static uint16_t dirtyrows;
extern __at (0xAD80) uint8_t rollcache[10];
extern __at (0xAF00) uint8_t rollonsets[40][4];
extern __at (0xB000) uint8_t rolltiles[128][16];
extern __at (0xBA00) uint8_t rollrow[320];
extern __at (0xBD40) uint8_t rollbasepixels[2][320];
extern __at (0xBC80) uint8_t rollx[41];
extern __at (0xBCC0) uint8_t rollnotes[40];
extern __at (0xBD00) uint8_t rollkind[40];
extern __at (0xB980) uint8_t rollnotey[40];
extern __at (0xAD90) uint8_t rolloldkind[40];
extern __at (0xADB8) uint8_t rolloldvel[40];
extern __at (0xA420) uint16_t feedbackpending;
void roll_feedback_begin(void) BANKED;
uint8_t roll_feedback_intern(uint8_t *pixels) BANKED;
void roll_clear_transition(void) BANKED;
uint8_t roll_velocity_bar(uint8_t col,uint8_t oldheight,uint8_t height) BANKED;
extern uint8_t seqbused;
extern __at (0xACF7) uint8_t rollbuilding;
static const uint8_t masks[9]={255,127,63,31,15,7,3,1,0};
static uint8_t indexof(uint8_t id){return id>=64&&id<96?id-64:id>=160&&id<244?id-128:id>=252?id-136:255;}
static uint8_t ready(void){return page==8&&seqtrack<4&&!navopen&&!seqpopup&&seqfontdirty&&rollcache[0]==168&&seqviewtrack==seqtrack&&seqviewbase==seqbase&&seqviewcols==seqcols&&seqviewtop==seqtop[seqtrack]&&rollcache[4]==seqgridheight;}
static void span(uint8_t left,uint8_t right,uint8_t top,uint8_t bottom,uint8_t color){uint8_t x,end,mask,y,*p;
 for(x=left;x<right;x=end){end=(x|7)+1;if(end>right)end=right;mask=masks[x&7]^masks[((end-1)&7)+1];p=rollrow+(uint16_t)(x>>3)*16;
  for(y=top;y<bottom;y++){p[y*2]=(p[y*2]&~mask)|((color&1)?mask:0);p[y*2+1]=(p[y*2+1]&~mask)|((color&2)?mask:0);}
 }
}
static void markspan(uint16_t begin,uint16_t end){uint8_t a,b;if(end<=seqbase||begin>=(uint16_t)seqbase+seqcols)return;
 a=rollx[begin<seqbase?0:begin-seqbase]>>3;b=(rollx[end>(uint16_t)seqbase+seqcols?seqcols:end-seqbase]+7)>>3;
 if(a<firsttile)firsttile=a;if(b>lasttile)lasttile=b;
}
static void markpitch(uint8_t note){int16_t y=((int16_t)seqtop[seqtrack]-(note-1))*seqheight;uint8_t row;if(y<0||y>=seqgridheight)return;row=y>>3;dirtyrows|=1U<<row;if(seqheight==16)dirtyrows|=1U<<(row+1);}
void native_edit_mark(uint8_t c,const uint8_t *old,const uint8_t *next) BANKED {uint16_t a,b;uint8_t col;
 if(c!=seqtrack||!ready())return;
 if(!pending){edittrack=c;editbase=seqbase;edittop=seqtop[c];editcols=seqcols;editheight=seqgridheight;firsttile=20;lasttile=0;velocitybits=dirtyrows=0;pending=1;}
 if(old&&old[0]>=seqbase&&old[0]<(uint16_t)seqbase+16){col=old[0]-seqbase;velocitybits|=1U<<col;}
 if(next&&next[0]>=seqbase&&next[0]<(uint16_t)seqbase+16){col=next[0]-seqbase;velocitybits|=1U<<col;}
 if(old&&next&&old[0]==next[0]&&old[1]==next[1]){if(old[3]==next[3])return;markpitch(old[1]);a=old[0]+(old[3]?old[3]:256U);b=next[0]+(next[3]?next[3]:256U);markspan(a<b?a-1:b-1,a>b?a:b);return;}
 if(old){markpitch(old[1]);markspan(old[0],old[0]+(old[3]?old[3]:256U));}if(next){markpitch(next[1]);markspan(next[0],next[0]+(next[3]?next[3]:256U));}
}
/* Reconstruct only changed columns. Each cell stores the colors of its left
   edge, body and right edge, preserving adjoining onsets and overlapping tails. */
static uint8_t compose(void){uint16_t n=seq_event_count(seqtrack),i,s,last=256,duration=0,begin,end,at,*refs=(uint16_t *)rollonsets;uint8_t e[4],col,limit,row,color,value,lastnote=0,x,t,style,top,bottom,left,right,old,id,idx;int16_t y;
 memset(cells,0,512);memset(onsets,0,128);memset(lowest,255,32);
 for(i=0;i<n;i++){seq_event_get(seqtrack,i,e);if(!e[1])continue;begin=e[0];end=begin+(e[3]?e[3]:256U);
  if(begin<seqbase){if(last==256||begin>last){last=begin;lastnote=e[1];duration=e[3]?e[3]:256U;}}else if(begin<(uint16_t)seqbase+seqcols)memcpy(onsets[begin-seqbase],e,4);
  if(experimental_mode&&evalpatch[seqtrack][EV_CHORD_HISTORY]&&!eval_mode(seqtrack)&&end>seqbase&&begin<(uint16_t)seqbase+seqcols)markpitch(e[1]);
  if(end>seqbase&&begin<(uint16_t)seqbase+seqcols){col=begin<seqbase?0:begin-seqbase;limit=end>(uint16_t)seqbase+seqcols?seqcols:end-seqbase;for(;col<limit;col++)if(e[1]-1<lowest[col])lowest[col]=e[1]-1;}
  if(!(i&7))service();
 }
 for(col=0;col<seqcols;col++){s=(uint16_t)seqbase+col;if(onsets[col][1]){last=s;lastnote=onsets[col][1];duration=onsets[col][3]?onsets[col][3]:256U;}
  rollnotes[col]=rollkind[col]=rolloldkind[col]=0;rollnotey[col]=255;
  if(last!=256&&s-last<duration){rollnotes[col]=lastnote;rollkind[col]=rolloldkind[col]=last==s?1:2;y=((int16_t)seqtop[seqtrack]-(lastnote-1))*seqheight;if(y>=0&&y<seqgridheight)rollnotey[col]=y;}
 }
 for(col=0;col<seqcols;col++)if(rollnotey[col]!=255){row=rollnotey[col]/seqheight;color=(uint16_t)seqbase+col>=seqlength[seqtrack]?2:3;value=color;if(rollkind[col]!=1)value|=color<<2;if(col+1<seqcols&&rollnotes[col+1]==rollnotes[col]&&rollkind[col+1]!=1)value|=color<<4;cells[row][col]=value;}
 if(experimental_mode&&evalpatch[seqtrack][EV_CHORD_HISTORY])for(i=0;i<n;i++){seq_event_get(seqtrack,i,e);y=(int16_t)seqtop[seqtrack]-(e[1]-1);if(!e[1]||y<0||y>=seqrows)continue;row=y;begin=e[0];end=begin+(e[3]?e[3]:256U);
  if(end<=seqbase||begin>=(uint16_t)seqbase+seqcols)continue;col=begin<seqbase?0:begin-seqbase;limit=end>(uint16_t)seqbase+seqcols?seqcols:end-seqbase;
  for(;col<limit;col++){s=(uint16_t)seqbase+col;color=s>=seqlength[seqtrack]?2:eval_mode(seqtrack)==1||e[1]-1==lowest[col]?3:1;value=cells[row][col];value=(value&60)|color;if(s!=begin)value=(value&51)|(color<<2);if(s+1!=end)value=(value&15)|(color<<4);cells[row][col]=value;}
  if(!(i&7))service();
 }
 if(!rollbuilding)roll_feedback_begin();
 for(t=0;t<seqgridheight/8;t++){if(!(dirtyrows&(1U<<t)))continue;style=seqheight>8?(((t+1)*8)&(seqheight-1))==0:0;memcpy(rollrow,rollbasepixels[style],320);row=t*8/seqheight;top=t*8%seqheight?0:1;bottom=seqheight==8||style?7:8;
  for(col=0;col<seqcols;col++){value=cells[row][col];if(!value||rollx[col+1]<=firsttile*8||rollx[col]>=lasttile*8)continue;left=rollx[col];right=rollx[col+1];if(value&12)span(left,left+1,top,bottom,(value>>2)&3);if(value&3)span(left+1,right-1,top,bottom,value&3);if(value&48)span(right-1,right,top,bottom,(value>>4)&3);}
  /* Retain the published selection until its edge update runs. */
  if(rollcache[5]==seqtrack){int16_t sy=((int16_t)seqtop[seqtrack]-rollcache[9])*seqheight,ey=((int16_t)seqtop[seqtrack]-rollcache[8]+1)*seqheight;uint16_t a=rollcache[6],b=(uint16_t)rollcache[7]+1;uint8_t yy,mask,stop,*pixel;
   if(a<seqbase)a=seqbase;if(b>(uint16_t)seqbase+seqcols)b=(uint16_t)seqbase+seqcols;
   if(a<b&&t*8>=sy&&t*8<ey){left=rollx[a-seqbase];right=rollx[b-seqbase];if(left<firsttile*8)left=firsttile*8;if(right>lasttile*8)right=lasttile*8;
    for(x=left;x<right;x=stop){stop=(x|7)+1;if(stop>right)stop=right;mask=masks[x&7]^masks[((stop-1)&7)+1];pixel=rollrow+(uint16_t)(x>>3)*16;for(yy=0;yy<16;yy++)pixel[yy]^=mask;}
   }
  }
  for(x=firsttile;x<lasttile;x++){at=(uint16_t)(t+1)*20+x;old=canvas[at];idx=indexof(old);if(idx==255)return 0;if(!memcmp(rolltiles[idx],rollrow+x*16,16))continue;id=roll_feedback_intern(rollrow+x*16);if(seqtileoverflow){roll_clear_transition();seqfontdirty=0;return 0;}refs[idx]--;refs[indexof(id)]++;canvas[at]=seqscreen[at]=id;mixfill();}service();
 }
 seqdrawvalid=2;roll_commit();seqflushpending=1;return 1;
}
void native_edit_flush(void) BANKED {uint8_t col,e[4],height,old,selection;uint16_t i,n;
 if(!pending)return;pending=0;
 if(!ready()||edittrack!=seqtrack||editbase!=seqbase||edittop!=seqtop[seqtrack]||editcols!=seqcols||editheight!=seqgridheight)return;
 if(!seqdrawvalid&&firsttile<lasttile&&!compose())return;
 selection=seqdrawvalid;if(selection==2)seqdrawvalid=1;
 if(seqcols==16&&!seqvelocityhidden){feedbackpending=0;memset(onsets,0,128);n=seq_event_count(seqtrack);for(i=0;i<n;i++){seq_event_get(seqtrack,i,e);if(e[0]>=seqbase&&e[0]<(uint16_t)seqbase+16){col=e[0]-seqbase;if(!onsets[col][1]||e[1]<onsets[col][1])memcpy(onsets[col],e,4);}if(!(i&7))service();}
  for(col=0;col<16;col++)if(velocitybits&(1U<<col)){height=onsets[col][1]?1+((uint16_t)onsets[col][2]*20)/127:0;old=rolloldvel[col];if(roll_velocity_bar(col,old,height))rolloldvel[col]=height;}}
 if(selection==2&&seqdrawvalid)seqdrawvalid=2;
}
void native_velocity_edit(int8_t delta) BANKED {uint8_t e[4],c=seqtrack;uint16_t cursor=0;int16_t value;
 if(c>=4||!seq_note_event(c,seqcursor[c],e))return;value=(int16_t)e[2]+delta;if(value<1)value=1;if(value>127)value=127;if(value==e[2])return;
 while(seq_event_next_step(c,seqcursor[c],&cursor,e)){e[2]=value;seq_event_put(c,cursor-1,e);}eval_plotvel[c]=value;seqbused=1;dirty=1;
}

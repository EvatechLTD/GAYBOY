#pragma bank 61
#pragma opt_code_speed
#include "api.h"
extern volatile uint8_t padread,padwrite;
void editbuffer_service(void) BANKED;

/* Native and drum sequencers never render simultaneously. Reuse the drum
   hit-test workspace for the native chord compositor, with no new WRAM. */
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
uint8_t roll_selection_update(void) BANKED;
void roll_velocity_queue(uint8_t c,uint8_t col,uint8_t value) BANKED;
extern uint8_t seqbused;
extern __at (0xACF7) uint8_t rollbuilding;
extern uint8_t seqbeats,seqdenom;
static uint8_t editbeats,editdenom,editmode,editchords;
static uint16_t editlength;
static uint8_t composephase,composerow,composecol,composenote;
static uint16_t composeindex,composelast,composeduration;
static uint8_t onsetpitch[16],onsetvelocity[16];
static const uint8_t masks[9]={255,127,63,31,15,7,3,1,0};
static uint8_t indexof(uint8_t id){return id>=64&&id<96?id-64:id>=160&&id<244?id-128:id>=252?id-136:255;}
static uint8_t ready(void){return page==8&&seqtrack<4&&!navopen&&!seqpopup&&seqfontdirty&&rollcache[0]==168&&seqviewtrack==seqtrack&&seqviewbase==seqbase&&seqviewcols==seqcols&&seqviewtop==seqtop[seqtrack]&&rollcache[4]==seqgridheight;}
/* Pending note pixels do not invalidate the published background. Selection
   can XOR that image between compositor batches, including partly updated
   rows. Future batches apply the newly published selection mask. */
uint8_t native_edit_feedback(void) BANKED {
 if(!pending||!ready())return 0;
 if(rollcache[5]!=seqgrouptrack||rollcache[6]!=seqgroupx0||rollcache[7]!=seqgroupx1||rollcache[8]!=seqgroupy0||rollcache[9]!=seqgroupy1){
  seqdrawvalid=2;if(!roll_selection_update()){pending=composephase=0;seqdrawvalid=0;return 0;}
  roll_commit();seqflushpending=1;seqdrawvalid=0;
 }
 return 1;
}
static void native_run(uint8_t *pixels,uint8_t mask,uint8_t first,uint8_t count,uint8_t low,uint8_t high) __naked {__asm
 push bc
 ld b,a
 ldhl sp,#4
 ld a,(hl+)
 add a,a
 add a,e
 ld e,a
 jr nc,native_run_pointer$
 inc d
native_run_pointer$:
 ld c,(hl)
 inc hl
 ld a,(hl+)
 push af
 ld a,(hl)
 ld l,a
 pop af
 ld h,a
 ld a,b
 cpl
 ld b,a
 ld a,c
 or a,a
 jr z,native_run_done$
native_run_row$:
 ld a,(de)
 and a,b
 or a,h
 ld (de),a
 inc de
 ld a,(de)
 and a,b
 or a,l
 ld (de),a
 inc de
 dec c
 jr nz,native_run_row$
native_run_done$:
 pop bc
 pop hl
 add sp,#4
 jp (hl)
 __endasm;}
static void span(uint8_t left,uint8_t right,uint8_t top,uint8_t bottom,uint8_t color){uint8_t x,end,mask;
 for(x=left;x<right;x=end){end=(x|7)+1;if(end>right)end=right;mask=masks[x&7]^masks[((end-1)&7)+1];
  native_run(rollrow+(uint16_t)(x>>3)*16,mask,top,bottom-top,(color&1)?mask:0,(color&2)?mask:0);
 }
}
static void markspan(uint16_t begin,uint16_t end){uint8_t a,b;if(end<=seqbase||begin>=(uint16_t)seqbase+seqcols)return;
 a=rollx[begin<seqbase?0:begin-seqbase]>>3;b=(rollx[end>(uint16_t)seqbase+seqcols?seqcols:end-seqbase]+7)>>3;
 if(a<firsttile)firsttile=a;if(b>lasttile)lasttile=b;
}
static void markpitch(uint8_t note){int16_t y=((int16_t)seqtop[seqtrack]-(note-1))*seqheight;uint8_t row;if(y<0||y>=seqgridheight)return;row=y>>3;dirtyrows|=1U<<row;if(seqheight==16)dirtyrows|=1U<<(row+1);}
void native_edit_mark(uint8_t c,const uint8_t *old,const uint8_t *next) BANKED {uint16_t a,b;uint8_t col;
 if(c!=seqtrack||!ready())return;
 composephase=0;
 if(!pending){edittrack=c;editbase=seqbase;edittop=seqtop[c];editcols=seqcols;editheight=seqgridheight;editbeats=seqbeats;editdenom=seqdenom;editlength=seqlength[c];editmode=evalpatch[c][EV_MODE];editchords=evalpatch[c][EV_CHORD_HISTORY];firsttile=20;lasttile=0;velocitybits=dirtyrows=0;pending=1;}
 if(old&&old[0]>=seqbase&&old[0]<(uint16_t)seqbase+16){col=old[0]-seqbase;velocitybits|=1U<<col;}
 if(next&&next[0]>=seqbase&&next[0]<(uint16_t)seqbase+16){col=next[0]-seqbase;velocitybits|=1U<<col;}
 if(old&&next&&old[0]==next[0]&&old[1]==next[1]){if(old[3]==next[3])return;markpitch(old[1]);a=old[0]+(old[3]?old[3]:256U);b=next[0]+(next[3]?next[3]:256U);markspan(a<b?a-1:b-1,a>b?a:b);return;}
 if(old){markpitch(old[1]);markspan(old[0],old[0]+(old[3]?old[3]:256U));}if(next){markpitch(next[1]);markspan(next[0],next[0]+(next[3]?next[3]:256U));}
}
/* Playback mode no longer changes any note's appearance. */
uint8_t native_mode_feedback(uint8_t c) BANKED {(void)c;return 1;}
/* Reconstruct changed columns in bounded foreground quanta: eight events
   per scan or two tiles per upload. New edits restart the staged composition
   from current note data while retaining the union of dirty regions. */
static uint8_t compose(void){uint16_t n=seq_event_count(seqtrack),i,s,last=256,duration=0,begin,end,at,*refs=(uint16_t *)rollonsets;uint8_t e[4],col,limit,row,color,value,lastnote=0,x,t,style,top,bottom,left,right,old,id,idx,stop,clipleft,clipright;int16_t y;
 if(!composephase){memset(cells,0,512);memset(onsets,0,128);memset(onsetpitch,0,16);memset(onsetvelocity,0,16);composeindex=0;composelast=256;composenote=0;composeduration=0;composephase=1;}
 if(composephase==1){
  limit=4;for(i=composeindex;i<n&&limit;i++,limit--){seq_event_get(seqtrack,i,e);if(!e[1])continue;begin=e[0];end=begin+(e[3]?e[3]:256U);
   if(begin<seqbase){if(composelast==256||begin>composelast){composelast=begin;composenote=e[1];composeduration=e[3]?e[3]:256U;}}else if(begin<(uint16_t)seqbase+seqcols)memcpy(onsets[begin-seqbase],e,4);
   if(begin>=seqbase&&begin<(uint16_t)seqbase+16){col=begin-seqbase;if(!onsetpitch[col]||e[1]<onsetpitch[col]){onsetpitch[col]=e[1];onsetvelocity[col]=e[2];}}
   service();
  }
  composeindex=i;if(i<n)return 2;composephase=2;
 }
 if(composephase==2){
  last=composelast;lastnote=composenote;duration=composeduration;
  for(col=0;col<seqcols;col++){s=(uint16_t)seqbase+col;if(onsets[col][1]){last=s;lastnote=onsets[col][1];duration=onsets[col][3]?onsets[col][3]:256U;}
   rollnotes[col]=rollkind[col]=rolloldkind[col]=0;rollnotey[col]=255;
   if(last!=256&&s-last<duration){rollnotes[col]=lastnote;rollkind[col]=rolloldkind[col]=last==s?1:2;y=((int16_t)seqtop[seqtrack]-(lastnote-1))*seqheight;if(y>=0&&y<seqgridheight)rollnotey[col]=y;}
  }
  for(col=0;col<seqcols;col++)if(rollnotey[col]!=255){row=rollnotey[col]/seqheight;color=3;value=color;if(rollkind[col]!=1)value|=color<<2;if(col+1<seqcols&&rollnotes[col+1]==rollnotes[col]&&rollkind[col+1]!=1)value|=color<<4;cells[row][col]=value;}
  composeindex=0;composephase=n>1?3:4;composerow=0;composecol=firsttile;
 }
 if(composephase==3){
  limit=4;
  for(i=composeindex;i<n&&limit;i++,limit--){seq_event_get(seqtrack,i,e);y=(int16_t)seqtop[seqtrack]-(e[1]-1);if(!e[1]||y<0||y>=seqrows)continue;row=y;begin=e[0];end=begin+(e[3]?e[3]:256U);
   if(end<=seqbase||begin>=(uint16_t)seqbase+seqcols)continue;col=begin<seqbase?0:begin-seqbase;top=end>(uint16_t)seqbase+seqcols?seqcols:end-seqbase;
   for(;col<top;col++){s=(uint16_t)seqbase+col;value=3;old=cells[row][col];old=(old&60)|value;if(s!=begin)old=(old&51)|(value<<2);if(s+1!=end)old=(old&15)|(value<<4);cells[row][col]=old;}
   service();
  }
  composeindex=i;if(i<n)return 2;composephase=4;
 }
 if(!rollbuilding)roll_feedback_begin();
 for(t=composerow;t<seqgridheight/8;t++){if(!(dirtyrows&(1U<<t)))continue;stop=composecol+2;if(stop>lasttile)stop=lasttile;clipleft=composecol*8;clipright=stop*8;style=seqheight>8?(((t+1)*8)&(seqheight-1))==0:0;memcpy(rollrow+(uint16_t)composecol*16,rollbasepixels[style]+(uint16_t)composecol*16,(stop-composecol)*16);row=t*8/seqheight;top=t*8%seqheight?0:1;bottom=seqheight==8||style?7:8;
  for(col=0;col<seqcols;col++){value=cells[row][col];if(!value||rollx[col+1]<=clipleft||rollx[col]>=clipright)continue;left=rollx[col];right=rollx[col+1];if((value&12)&&left>=clipleft)span(left,left+1,top,bottom,(value>>2)&3);if((value&3)&&left+1<clipright&&right-1>clipleft)span(left+1<clipleft?clipleft:left+1,right-1>clipright?clipright:right-1,top,bottom,value&3);if((value&48)&&right<=clipright)span(right-1,right,top,bottom,(value>>4)&3);}
  /* Retain the published selection until its edge update runs. */
  if(rollcache[5]==seqtrack){int16_t sy=((int16_t)seqtop[seqtrack]-rollcache[9])*seqheight,ey=((int16_t)seqtop[seqtrack]-rollcache[8]+1)*seqheight;uint16_t a=rollcache[6],b=(uint16_t)rollcache[7]+1;uint8_t yy,mask,stop,*pixel;
   if(a<seqbase)a=seqbase;if(b>(uint16_t)seqbase+seqcols)b=(uint16_t)seqbase+seqcols;
   if(a<b&&t*8>=sy&&t*8<ey){left=rollx[a-seqbase];right=rollx[b-seqbase];if(left<clipleft)left=clipleft;if(right>clipright)right=clipright;
    for(x=left;x<right;x=stop){stop=(x|7)+1;if(stop>right)stop=right;mask=masks[x&7]^masks[((stop-1)&7)+1];pixel=rollrow+(uint16_t)(x>>3)*16;for(yy=0;yy<16;yy++)pixel[yy]^=mask;}
   }
  }
  for(x=composecol;x<stop;x++){at=(uint16_t)(t+1)*20+x;old=canvas[at];idx=indexof(old);if(idx==255){composephase=0;return 0;}if(!memcmp(rolltiles[idx],rollrow+x*16,16))continue;id=roll_feedback_intern(rollrow+x*16);if(seqtileoverflow){composephase=0;roll_clear_transition();seqfontdirty=0;return 0;}refs[idx]--;refs[indexof(id)]++;canvas[at]=seqscreen[at]=id;mixfill();}
  composerow=t;composecol=stop;if(composecol==lasttile){composerow++;composecol=firsttile;}
  roll_commit();
  /* Publish this bounded tile span before yielding or starting another one.
     Cache pins and the actual displayed map then describe the same image. */
  at=(uint16_t)(t+1)*20+(clipleft>>3);
  ui_upload_map(0x9800U+(uint16_t)(t+1)*32+(clipleft>>3),canvas+at,(clipright-clipleft)>>3);
  memcpy(visible+at,canvas+at,(clipright-clipleft)>>3);
  seqflushpending=1;if(composecol==firsttile&&(composerow>=seqgridheight/8||!(dirtyrows>>composerow)))goto composed;return 2;
 }
 composed:
 composephase=0;seqdrawvalid=2;roll_commit();seqflushpending=1;return 1;
}
uint8_t native_edit_flush(void) BANKED {uint8_t col,e[4],selection,composed=0,result;uint16_t i,n,bits;
 if(!pending)return 0;
 if(!ready()||edittrack!=seqtrack||editbase!=seqbase||edittop!=seqtop[seqtrack]||editcols!=seqcols||editheight!=seqgridheight||editbeats!=seqbeats||editdenom!=seqdenom||editlength!=seqlength[seqtrack]){pending=composephase=0;seqdrawvalid=0;return 0;}
 if((composephase||!seqdrawvalid)&&firsttile<lasttile){result=compose();if(result==2){seqdrawvalid=0;return 1;}if(!result){pending=0;return 0;}composed=1;}
 pending=0;
 selection=seqdrawvalid;if(selection==2)seqdrawvalid=1;
 if(seqcols==16&&!seqvelocityhidden){
  /* Fast note feedback already queued these columns. A composed edit has
     rebuilt exact onset values, including overlapping notes, in onsets[]. */
  bits=composed?velocitybits:velocitybits&~feedbackpending;
  if(bits){
   if(!composed){memset(onsets,0,128);n=seq_event_count(seqtrack);for(i=0;i<n;i++){seq_event_get(seqtrack,i,e);if(e[0]>=seqbase&&e[0]<(uint16_t)seqbase+16){col=e[0]-seqbase;if(!onsets[col][1]||e[1]<onsets[col][1])memcpy(onsets[col],e,4);}if(!(i&7))service();}}
   for(col=0;col<16;col++)if(bits&(1U<<col))roll_velocity_queue(seqtrack,col,composed?onsetvelocity[col]:onsets[col][1]?onsets[col][2]:0);
  }
 }
 if(selection==2&&seqdrawvalid)seqdrawvalid=2;return 0;
}
void native_velocity_edit(int8_t delta) BANKED {uint8_t e[4],c=seqtrack;uint16_t cursor=0;int16_t value;
 if(c>=4||!seq_note_event(c,seqcursor[c],e))return;value=(int16_t)e[2]+delta;if(value<1)value=1;if(value>127)value=127;if(value==e[2])return;
 while(seq_event_next_step(c,seqcursor[c],&cursor,e)){e[2]=value;seq_event_put(c,cursor-1,e);}eval_plotvel[c]=value;seqbused=1;dirty=1;
}
/* Drain several small batches while input is idle. Check actual queued edges
   between every batch, rather than paying a complete UI pass per two tiles. */
uint8_t native_edit_service(void) BANKED {uint8_t budget=4;
 if(!pending)return 0;
 do{if(padread!=padwrite)return 1;if(!native_edit_flush())return 0;service();editbuffer_service();}while(--budget);
 return 1;
}

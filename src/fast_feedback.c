#pragma bank 43
#pragma opt_code_speed
#include "api.h"
#include "drum_rows.h"
extern uint8_t seqdenom,seqbeats;
extern __at (0xB000) uint8_t rolltiles[128][16];
extern __at (0xAD80) uint8_t rollcache[10];
extern __at (0xAF00) uint8_t rollonsets[40][4];
extern __at (0xBC80) uint8_t rollx[41];
extern __at (0xBB40) uint8_t rollbackground[320];
extern __at (0xBCC0) uint8_t rollnotes[40];
extern __at (0xBD00) uint8_t rollkind[40];
extern __at (0xB980) uint8_t rollnotey[40];
extern __at (0xAD90) uint8_t rolloldkind[40];
extern __at (0xADB8) uint8_t rolloldvel[40];
extern __at (0xACF7) uint8_t rollbuilding;
void roll_feedback_begin(void) BANKED;
uint8_t roll_feedback_intern(uint8_t *pixels) BANKED;
void roll_clear_transition(void) BANKED;
static const uint8_t feedback_masks[9]={255,127,63,31,15,7,3,1,0};
static const uint32_t feedback_low[33]={0UL,1UL,3UL,7UL,15UL,31UL,63UL,127UL,255UL,511UL,1023UL,2047UL,4095UL,8191UL,16383UL,32767UL,65535UL,131071UL,262143UL,524287UL,1048575UL,2097151UL,4194303UL,8388607UL,16777215UL,33554431UL,67108863UL,134217727UL,268435455UL,536870911UL,1073741823UL,2147483647UL,4294967295UL};
static const uint32_t feedback_bit[32]={1UL,2UL,4UL,8UL,16UL,32UL,64UL,128UL,256UL,512UL,1024UL,2048UL,4096UL,8192UL,16384UL,32768UL,65536UL,131072UL,262144UL,524288UL,1048576UL,2097152UL,4194304UL,8388608UL,16777216UL,33554432UL,67108864UL,134217728UL,268435456UL,536870912UL,1073741824UL,2147483648UL};
static uint8_t feedback_index(uint8_t id){return id>=64&&id<96?id-64:id>=160&&id<244?id-128:id>=252?id-136:255;}
/* The published DRUM grid provides O(1) editing hit tests. Values are local
   event indices plus one; zero means an empty cell, including a genuine index0. */
__at (0xA500) uint32_t fastrowbits[13];
__at (0xA534) uint16_t fastoverlap;
__at (0xA536) uint16_t fastghostrows;
extern __at (0xBA00) uint8_t rollrow[320];
void drum_feedback_span(uint8_t left,uint8_t right) BANKED;
__at (0xA800) uint16_t fastcells[13][32];
__at (0xA540) uint8_t fastcoverorigin[13][32];
__at (0xA410) static uint8_t feedbackvel[16];
__at (0xA420) static uint16_t feedbackpending;
__at (0xA422) static uint8_t feedbackphase;
__at (0xA423) static uint8_t feedbacktrack;
__at (0xA424) static uint8_t feedbackbase;
__at (0xA425) static uint8_t feedbackrow;
__at (0xA426) static uint8_t feedbackbatch;
void roll_edit_batch(uint8_t enabled) BANKED {feedbackbatch=enabled;if(!enabled&&seqdrawvalid)roll_commit();}
extern volatile uint8_t padsampled,padread,padwrite;
void roll_feedback_cancel(void) BANKED {feedbackpending=feedbackphase=feedbackbatch=0;}
static void feedback_velocity_queue(uint8_t c,uint8_t col,uint8_t value){if(feedbacktrack!=c||feedbackbase!=seqbase||feedbackrow!=drumrow){feedbackpending=feedbackphase=0;}feedbacktrack=c;feedbackbase=seqbase;feedbackrow=drumrow;feedbackvel[col]=value;feedbackpending|=1U<<col;feedbackphase=0;}
void roll_feedback_velocity_row(void) BANKED {uint8_t col,value,height;uint16_t prior=feedbackpending;feedbackpending=feedbackphase=0;feedbacktrack=6;feedbackbase=seqbase;feedbackrow=drumrow;for(col=0;col<16;col++){value=rollbackground[(uint16_t)drumrow*16+col];height=value?1+((uint16_t)value*20)/127:0;if(height!=rolloldvel[col]||(prior&(1U<<col))){feedbackvel[col]=value;feedbackpending|=1U<<col;}}seqviewtop=drumrow;}
static uint8_t feedback_ready(uint8_t c){return page==8&&!navopen&&!seqpopup&&seqdrawvalid==1&&seqfontdirty&&rollcache[0]==168&&(!rollbuilding||feedbackbatch)&&seqviewtrack==c&&seqtrack==c&&seqviewbase==seqbase&&seqviewcols==seqcols&&(c==6||seqviewtop==seqtop[c]);}
uint16_t roll_drum_onset(uint8_t step,uint8_t row) BANKED {uint16_t id;if(!feedback_ready(6)||row>=13||step<seqbase||(uint16_t)step>=seqbase+seqcols)return 65534U;id=fastcells[row][step-seqbase];return id?id-1:65535U;}
uint16_t roll_drum_hit(uint8_t step,uint8_t row) BANKED {uint16_t id;uint8_t origin,col;if(!feedback_ready(6)||row>=13||step<seqbase||(uint16_t)step>=seqbase+seqcols)return 65534U;col=step-seqbase;id=fastcells[row][col];if(id)return id-1;if(!(fastrowbits[row]&feedback_bit[col]))return 65535U;origin=fastcoverorigin[row][col];if(origin<seqbase)return 65534U;id=fastcells[row][origin-seqbase];return id?id-1:65534U;}
/* Read/write note colors underneath the cached selection rectangle. This
   lets group edits retain the selection instead of rebuilding its grid. */
static uint8_t feedback_selection_mask(uint8_t x,uint8_t y){
 uint16_t a,b;int16_t top,bottom;
 if(rollcache[5]!=seqtrack)return 0;
 a=rollcache[6];b=(uint16_t)rollcache[7]+1;
 if(a<seqbase)a=seqbase;if(b>(uint16_t)seqbase+seqcols)b=(uint16_t)seqbase+seqcols;if(a>=b)return 0;
 if(seqtrack==6){if(y>=24&&y<32)return 0;top=DRUM_SCREEN_ROW(rollcache[8])*8;bottom=((uint16_t)DRUM_SCREEN_ROW(rollcache[9])+1)*8;}
 else{top=((int16_t)seqtop[seqtrack]-rollcache[9])*seqheight;bottom=((int16_t)seqtop[seqtrack]-rollcache[8]+1)*seqheight;}
 if(y<top||y>=bottom)return 0;
 a=rollx[a-seqbase];b=rollx[b-seqbase];
 if(a>=x+8||b<=x)return 0;
 return feedback_masks[a>x?a-x:0]^feedback_masks[b<x+8?b-x:8];
}
static uint8_t feedback_pixel(uint8_t x,uint8_t y){uint8_t id=feedback_index(seqscreen[(uint16_t)(1+(y>>3))*20+(x>>3)]),mask=128>>(x&7),*p;if(id==255)return 0;p=rolltiles[id]+((y&7)<<1);return (!!(p[0]&mask)|(!!(p[1]&mask)<<1))^((feedback_selection_mask(x&248,y)&mask)?3:0);}
/* A constant-color masked run touches at most eight scanlines. */
static void feedback_run(uint8_t *pixels,uint8_t mask,uint8_t first,uint8_t count,uint8_t low,uint8_t high) __naked {__asm
 push bc
 ld b,a
 ldhl sp,#4
 ld a,(hl+)
 add a,a
 add a,e
 ld e,a
 jr nc,run_pointer$
 inc d
run_pointer$:
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
 jr z,run_done$
run_row$:
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
 jr nz,run_row$
run_done$:
 pop bc
 pop hl
 add sp,#4
 jp (hl)
 __endasm;}
static void feedback_region(uint8_t left,uint8_t right,uint8_t top,uint8_t bottom,uint8_t erase,uint8_t bar){uint8_t t,x,i,lo,hi,mask,id,n,old,pixels[16],base0,base1,bit,color,sx,first,last,from,barmask;uint16_t at,step;uint16_t *refs=(uint16_t *)rollonsets;
 for(t=top>>3;t<((bottom+7)>>3);t++)for(x=left>>3;x<((right+7)>>3);x++){
  at=(uint16_t)(t+1)*20+x;old=canvas[at];n=feedback_index(old);if(n==255){seqtileoverflow=1;return;}memcpy(pixels,rolltiles[n],16);lo=left>x*8?left-x*8:0;hi=right<(x+1)*8?right-x*8:8;mask=feedback_masks[lo]^feedback_masks[hi];first=top>t*8?top-t*8:0;last=bottom<(t+1)*8?bottom-t*8:8;base0=base1=0;
  if(bar){feedback_run(pixels,mask,first,last-first,0,0);if(t==14&&!first)feedback_run(pixels,mask,0,1,0,mask);if(bar>1){if(seqtrack!=6&&t==16&&last==8)feedback_run(pixels,mask,7,1,0,mask);from=136-(bar-1)>t*8?136-(bar-1)-t*8:0;if(from<first)from=first;if(from<last&&left+2<right-2&&left+2<(x+1)*8&&right-2>x*8){lo=left+2>x*8?left+2-x*8:0;hi=right-2<(x+1)*8?right-2-x*8:8;barmask=feedback_masks[lo]^feedback_masks[hi];feedback_run(pixels,barmask,from,last-from,barmask,barmask);}}}
  else{if(erase){uint8_t *base=seqtrack==6?(uint8_t *)0xBD40:rollbackground;base0=base[(uint16_t)x*16+2];base1=base[(uint16_t)x*16+3];}else base0=base1=255;feedback_run(pixels,mask,first,last-first,base0&mask,base1&mask);}
  if(!bar&&rollcache[5]==seqtrack){bit=feedback_selection_mask(x*8,t*8+first)&mask;for(i=first;i<last;i++){pixels[i*2]^=bit;pixels[i*2+1]^=bit;}}
  id=roll_feedback_intern(pixels);if(seqtileoverflow)return;if(old!=id){refs[n]--;refs[feedback_index(id)]++;canvas[at]=seqscreen[at]=id;}mixfill();
 }
}
uint8_t roll_note_feedback(uint8_t c,const uint8_t *e,uint8_t erase) BANKED {uint8_t row=0,col,endcol,left,right,top,bottom,x,k,voices,height;uint16_t begin=e[0],end=begin+(e[3]?e[3]:256U),at,id;uint32_t bits=0;int16_t y;
 if(!feedback_ready(c)||c==4||c==5)return 0;if(c!=6&&(eval_mode(c)||evalpatch[c][EV_CHORD_HISTORY]))return 0;if(end<=seqbase||begin>=(uint16_t)seqbase+seqcols)return 0;col=begin<seqbase?0:begin-seqbase;endcol=end>(uint16_t)seqbase+seqcols?seqcols:end-seqbase;
 if(c==6){row=DRUM_VIEW_ROW(e[1]-1);if(row>=13)return 0;bits=(feedback_low[endcol]^feedback_low[col]);if((erase||row>=3)&&(fastoverlap&(1U<<row)))return 0;if(!erase&&row>=3&&(fastrowbits[row]&bits))return 0;
  /* Edits which can change another PCM hit's admission use the full renderer.
     The common non-overlapping drum and hat gestures need no admission scan. */
  if(row>=3)for(k=col;k<endcol;k++){voices=0;x=rollx[k]+2;for(row=3;row<13;row++){height=feedback_pixel(x,DRUM_SCREEN_ROW(row)*8+2);if(erase&&height==2)return 0;if(height==3)voices++;}if(!erase&&voices>=2)return 0;}row=DRUM_VIEW_ROW(e[1]-1);top=DRUM_SCREEN_ROW(row)*8+1;bottom=top+6;
 }else{for(k=col;k<endcol;k++)if(!erase&&rollnotes[k]&&(rollnotes[k]!=e[1]||(k>col&&rollkind[k]==1)))return 0;if(!erase&&endcol<seqcols&&rollnotes[endcol]==e[1]&&rollkind[endcol]==2)return 0;if(erase&&e[3]!=1&&col&&rollnotes[col-1]==e[1])return 0;y=((int16_t)seqtop[c]-(e[1]-1))*seqheight;if(y<0||y+seqheight>seqgridheight)return 0;top=y+1;bottom=y+seqheight-1;}
 left=rollx[col]+(begin>=seqbase);right=rollx[endcol]-(c!=6&&end<=(uint16_t)seqbase+seqcols);if(right<=left)return 0;
 if(!feedbackbatch||!rollbuilding)roll_feedback_begin();if(c!=6&&!erase&&begin>=seqbase)feedback_region(left-1,left,top,bottom,1,0);feedback_region(left,right,top,bottom,erase,0);
 if(seqcols==16&&!seqvelocityhidden&&begin>=seqbase&&begin<(uint16_t)seqbase+16){col=begin-seqbase;feedback_velocity_queue(c,col,erase?0:e[2]);if(c==6){rollbackground[(uint16_t)row*16+col]=erase?0:e[2];id=seq_event_count(6)+(erase?-1:1);rollcache[1]=id;rollcache[3]=id>>8;}}

 if(seqtileoverflow){roll_clear_transition();seqfontdirty=seqdrawvalid=0;dirty=1;return 0;}
 if(c==6){if(erase){fastrowbits[row]&=~bits;if(begin>=seqbase)fastcells[row][begin-seqbase]=0;}else{for(k=begin<seqbase?0:begin-seqbase;k<endcol;k++)if(!(fastrowbits[row]&feedback_bit[k]))fastcoverorigin[row][k]=begin;if(fastrowbits[row]&bits)fastoverlap|=1U<<row;fastrowbits[row]|=bits;if(begin>=seqbase)fastcells[row][begin-seqbase]=seq_event_count(6)+1;}}
 else for(k=begin<seqbase?0:begin-seqbase;k<endcol;k++){rollnotes[k]=erase?0:e[1];rollkind[k]=erase?0:k+seqbase==begin?1:2;rollnotey[k]=erase?255:top-1;rolloldkind[k]=rollkind[k];}
 /* Publish the few changed tiles before the note-store mutation. */
 if(feedbackbatch){seqflushpending=1;return 1;}
 roll_commit();for(k=top>>3;k<((bottom+7)>>3);k++){at=(uint16_t)(k+1)*20+(left>>3);height=((right+7)>>3)-(left>>3);ui_upload_map(0x9800U+(uint16_t)(k+1)*32+(left>>3),canvas+at,height);memcpy(visible+at,canvas+at,height);}

 seqflushpending=1;return 1;
}
/* Isolated drum resizing changes only the tail, regardless of note length. */
static uint8_t feedback_drum_resize(const uint8_t *old,const uint8_t *next){
 uint16_t a=old[0]+(old[3]?old[3]:256U),b=next[0]+(next[3]?next[3]:256U),lo,hi,at;
 uint8_t row=DRUM_VIEW_ROW(old[1]-1),first,last,k,r,voices,pixel,left,right,top,width,erase=b<a;
 uint32_t bits;
 if(!feedback_ready(6)||row>=13||(fastoverlap&(1U<<row)))return 0;
 lo=erase?b:a;hi=erase?a:b;
 if(lo<seqbase)lo=seqbase;if(hi>(uint16_t)seqbase+seqcols)hi=(uint16_t)seqbase+seqcols;
 if(lo>=hi)return 1;
 first=lo-seqbase;last=hi-seqbase;bits=(feedback_low[last]^feedback_low[first]);
 if(!erase&&(fastrowbits[row]&bits))return 0;
 if(row>=3)for(k=first;k<last;k++){
  voices=0;for(r=3;r<13;r++){pixel=feedback_pixel(rollx[k]+2,DRUM_SCREEN_ROW(r)*8+2);if(pixel==2)return 0;if(r!=row&&pixel==3)voices++;}
  if(!erase&&voices>=2)return 0;
 }
 left=rollx[first];right=rollx[last];top=DRUM_SCREEN_ROW(row)*8+1;
 if(!feedbackbatch||!rollbuilding)roll_feedback_begin();feedback_region(left,right,top,top+6,erase,0);
 if(seqtileoverflow){roll_clear_transition();seqfontdirty=seqdrawvalid=0;dirty=1;return 0;}
 if(erase)fastrowbits[row]&=~bits;
 else{fastrowbits[row]|=bits;for(k=first;k<last;k++)fastcoverorigin[row][k]=old[0];}
 if(feedbackbatch){seqflushpending=1;return 1;}
 roll_commit();at=(uint16_t)(DRUM_SCREEN_ROW(row)+1)*20+(left>>3);width=((right+7)>>3)-(left>>3);
 ui_upload_map(0x9800U+(uint16_t)(DRUM_SCREEN_ROW(row)+1)*32+(left>>3),canvas+at,width);memcpy(visible+at,canvas+at,width);
 seqflushpending=1;return 1;
}
/* A mono note's unchanged body does not need erasing during a resize. */
static uint8_t feedback_native_resize(uint8_t c,const uint8_t *old,const uint8_t *next){
 uint16_t a=old[0]+(old[3]?old[3]:256U),b=next[0]+(next[3]?next[3]:256U),at;
 uint8_t left,right,top,bottom,k,first,last,width,erase=b<a;int16_t y;
 if(!feedback_ready(c)||c>=3||eval_mode(c)||evalpatch[c][EV_CHORD_HISTORY])return 0;
 y=((int16_t)seqtop[c]-(old[1]-1))*seqheight;if(y<0||y+seqheight>seqgridheight)return 0;
 if(a<=seqbase||b<=seqbase||old[0]>=(uint16_t)seqbase+seqcols)return 0;
 first=(erase?b:a)>=(uint16_t)seqbase+seqcols?seqcols:(erase?b:a)-seqbase;last=(erase?a:b)>=(uint16_t)seqbase+seqcols?seqcols:(erase?a:b)-seqbase;
 if(!erase)for(k=first;k<last;k++)if(rollnotes[k])return 0;
 if(!erase&&last<seqcols&&rollnotes[last]==old[1]&&rollkind[last]==2)return 0;
 left=rollx[first]-(first<seqcols);right=rollx[last]-(last<seqcols);if(right<=left)return 1;
 top=y+1;bottom=y+seqheight-1;if(!feedbackbatch||!rollbuilding)roll_feedback_begin();
 feedback_region(left,right,top,bottom,erase,0);
 if(seqtileoverflow){roll_clear_transition();seqfontdirty=seqdrawvalid=0;dirty=1;return 0;}
 for(k=first;k<last;k++){rollnotes[k]=erase?0:old[1];rollkind[k]=rolloldkind[k]=erase?0:2;rollnotey[k]=erase?255:y;}
 if(feedbackbatch){seqflushpending=1;return 1;}
 roll_commit();width=((right+7)>>3)-(left>>3);for(k=top>>3;k<((bottom+7)>>3);k++){at=(uint16_t)(k+1)*20+(left>>3);ui_upload_map(0x9800U+(uint16_t)(k+1)*32+(left>>3),canvas+at,width);memcpy(visible+at,canvas+at,width);}
 seqflushpending=1;return 1;
}
/* Replacement keeps the resident event index and count unchanged. The erase
   and insert paths touch only the old/new rectangles; difficult admission
   changes fall back before the next published full render. */
uint8_t roll_replace_feedback(uint8_t c,const uint8_t *old,const uint8_t *next,uint16_t index) BANKED {
 uint16_t count;uint8_t col;
 if(old[0]==next[0]&&old[1]==next[1]){if(old[3]==next[3])return feedback_ready(c);if(c==6)return feedback_drum_resize(old,next);return feedback_native_resize(c,old,next);}
 if(!roll_note_feedback(c,old,1))return 0;
 if(!roll_note_feedback(c,next,0)){seqdrawvalid=0;return 0;}
 if(c==6){count=seq_event_count(6);rollcache[1]=count;rollcache[3]=count>>8;
  if(next[0]>=seqbase&&(uint16_t)next[0]<seqbase+seqcols){col=next[0]-seqbase;fastcells[DRUM_VIEW_ROW(next[1]-1)][col]=index+1;}}
 return 1;
}
/* Keep visible event handles aligned when compacting the last track. */
void roll_drum_erase_handles(uint16_t deleted) BANKED __naked {__asm
 ; BANKED entry arguments reside after the six-byte call frame.
 ldhl sp,#6
 ld a,(hl+)
 ld e,a
 ld d,(hl)
 inc de
 ld hl,#0xa800
 ld bc,#416
handle_loop$:
 push bc
 ld a,(hl+)
 ld c,a
 ld a,(hl)
 ld b,a
 cp a,d
 jr c,handle_store$
 jr nz,handle_decrement$
 ld a,c
 cp a,e
 jr c,handle_store$
 jr nz,handle_decrement$
 ld bc,#0
 jr handle_store$
handle_decrement$:
 dec bc
handle_store$:
 ld (hl),b
 dec hl
 ld (hl),c
 inc hl
 inc hl
 pop bc
 dec bc
 ld a,b
 or a,c
 jr nz,handle_loop$
 ret
 __endasm;}

/* One slider scanline-row per idle frame. Queued input always wins. */
void roll_feedback_service(void) BANKED {uint8_t col,height,row,left,width;uint16_t at;if(!feedbackpending)return;if(!feedback_ready(feedbacktrack)||seqcols!=16||seqvelocityhidden||feedbackbase!=seqbase||feedbackrow!=drumrow){feedbackpending=feedbackphase=0;return;}if(padread!=padwrite||padsampled&(J_A|J_B|J_LEFT|J_RIGHT|J_UP|J_DOWN|J_START|J_SELECT))return;for(col=0;col<16;col++)if(feedbackpending&(1U<<col))break;if(col>=16){feedbackpending=0;return;}height=feedbackvel[col]?1+((uint16_t)feedbackvel[col]*20)/127:0;row=14+feedbackphase;roll_feedback_begin();feedback_region(rollx[col],rollx[col+1],row*8,row*8+8,0,1+height);if(seqtileoverflow){feedbackpending=0;roll_clear_transition();seqfontdirty=seqdrawvalid=0;dirty=1;return;}roll_commit();left=rollx[col]>>3;width=((rollx[col+1]+7)>>3)-left;at=(uint16_t)(row+1)*20+left;ui_upload_map(0x9800U+(uint16_t)(row+1)*32+left,canvas+at,width);memcpy(visible+at,canvas+at,width);if(++feedbackphase==3){feedbackphase=0;feedbackpending&=~(1U<<col);rolloldvel[col]=height;}}

static uint8_t *feedback_header_number(uint8_t *dst,uint16_t value,uint8_t base){uint8_t digit,hundreds=value>=100;if(hundreds){digit=value/100;*dst++='0'+digit-32+base;value-=digit*100;}if(hundreds||value>=10){digit=value/10;*dst++='0'+digit-32+base;value-=digit*10;}*dst++='0'+value-32+base;return dst;}
__at (0xA428) static uint8_t feedbackheader[7];
__at (0xA42F) static uint16_t feedbacklength;
__at (0xA431) static uint8_t feedbackfirst;
__at (0xA432) static uint8_t feedbackheadvalid;
void roll_header_range(void) BANKED {uint8_t base=seqhead!=4?96:0,*dst,i;if(feedbackheadvalid!=113||feedbacklength!=seqlength[seqtrack]||feedbackfirst!=seqbase){memset(feedbackheader,0,7);dst=feedback_header_number(feedbackheader,(uint16_t)seqbase+1,0);*dst++='/'-32;feedback_header_number(dst,seqlength[seqtrack],0);feedbackheadvalid=113;feedbacklength=seqlength[seqtrack];feedbackfirst=seqbase;}for(i=0;i<7;i++)canvas[13+i]=feedbackheader[i]+base;}

uint8_t roll_group_add(uint8_t c,const uint8_t *e,uint16_t index) BANKED {uint16_t count;if(!roll_note_feedback(c,e,0))return 0;if(c==6){count=seq_event_count(c);rollcache[1]=count;rollcache[3]=count>>8;if(e[0]>=seqbase&&(uint16_t)e[0]<seqbase+seqcols)fastcells[DRUM_VIEW_ROW(e[1]-1)][e[0]-seqbase]=index+1;}return 1;}

/* Group edits resolve the drum cells once, then compose each changed tile once.
   The inactive piano base image provides the continuation masks. */
static uint32_t feedback_changed_tiles(uint16_t begin,uint16_t end){uint8_t first,last;
 if(end<=seqbase||begin>=(uint16_t)seqbase+seqcols)return 0;
 first=rollx[begin<seqbase?0:begin-seqbase]>>3;last=(rollx[end>(uint16_t)seqbase+seqcols?seqcols:end-seqbase]+7)>>3;
 return (feedback_low[last]^feedback_low[first]);
}
uint8_t roll_drum_group_refresh(int8_t dx,int8_t dy,int8_t resize) BANKED {
 uint32_t *continued=(uint32_t *)0xBE80,occupied=0,second=0,bits,changedtiles=0;
 uint16_t i,count,begin,end,changed=0,at,*refs=(uint16_t *)rollonsets;
 uint8_t e[4],row,col,last,x,left,right,mask,bit,low,high,color,k,n,id,old,pixels[16],selection,firstrow=seqgroupy0+(dy<0?dy:0),lastrow=seqgroupy1+(dy>0?dy:0);
 if(!feedback_ready(6))return 0;
 if(lastrow>=3&&(fastghostrows&0x1FF8))return 0;
 memset(fastrowbits,0,52);memset(fastcells,0,832);memset(continued,0,52);memset(rollbackground,0,208);fastoverlap=0;count=seq_event_count(6);
 for(i=0;i<count;i++){
  if(!seq_event_get(6,i,e)||!e[1]||e[1]>13)continue;row=DRUM_VIEW_ROW(e[1]-1);begin=e[0];end=begin+(e[3]?e[3]:256U);
  if(end<=seqbase||begin>=(uint16_t)seqbase+seqcols)continue;
  if(begin>=seqgroupx0+dx&&begin<=seqgroupx1+dx&&row>=seqgroupy0+dy&&row<=seqgroupy1+dy){
   if(resize)changedtiles|=feedback_changed_tiles(resize>0?end-resize:end,resize>0?end:end-resize);
   else{changedtiles|=feedback_changed_tiles(begin,end);changedtiles|=feedback_changed_tiles(begin-dx,end-dx);}
  }
  col=begin<seqbase?0:begin-seqbase;last=end>(uint16_t)seqbase+seqcols?seqcols:end-seqbase;bits=(feedback_low[last]^feedback_low[col]);
  if(row>=3){if(lastrow>=3&&(second&bits))return 0;second|=occupied&bits;occupied|=bits;}else if(row==2&&firstrow<=2&&lastrow>=2&&(fastrowbits[row]&bits))return 0;
  if(fastrowbits[row]&bits)fastoverlap|=1U<<row;
  for(k=col;k<last;k++)if(!(fastrowbits[row]&feedback_bit[k]))fastcoverorigin[row][k]=begin;
  fastrowbits[row]|=bits;if(begin<seqbase)continued[row]|=bits;else{if(col+1<last)continued[row]|=bits&~feedback_bit[col];if(!fastcells[row][col])fastcells[row][col]=i+1;if(seqcols==16)rollbackground[(uint16_t)row*16+col]=e[2];}
  if(!(i&7))service();
 }
 roll_feedback_begin();
 for(row=firstrow;row<=lastrow;row++){
  memcpy(rollrow,(const void *)0xBD40,320);bits=1UL;
  for(col=0;col<seqcols;col++,bits<<=1)if(fastrowbits[row]&bits){left=rollx[col]+(!col||!(continued[row]&bits));right=rollx[col+1];drum_feedback_span(left,right);}
  for(x=3;x<20;x++){
   if(!(changedtiles&feedback_bit[x]))continue;
   low=rollrow[x*16+2];high=rollrow[x*16+3];
   at=(uint16_t)(DRUM_SCREEN_ROW(row)+1)*20+x;old=canvas[at];n=feedback_index(old);if(n==255)return 0;selection=feedback_selection_mask(x*8,DRUM_SCREEN_ROW(row)*8+2);low^=selection;high^=selection;
   if(rolltiles[n][2]==low&&rolltiles[n][3]==high)continue;
   memcpy(pixels,rolltiles[n],16);feedback_run(pixels,255,1,6,low,high);
   id=roll_feedback_intern(pixels);if(seqtileoverflow){roll_clear_transition();seqfontdirty=0;return 0;}
   refs[n]--;refs[feedback_index(id)]++;canvas[at]=seqscreen[at]=id;changed|=1U<<row;mixfill();
  }
  service();
 }
 rollcache[1]=count;rollcache[3]=count>>8;
 if(seqcols==16&&!seqvelocityhidden)roll_feedback_velocity_row();
 if(dx||dy){seqflushpending=1;return 1;}
 roll_commit();for(row=0;row<13;row++)if(changed&(1U<<row)){at=(uint16_t)(DRUM_SCREEN_ROW(row)+1)*20+3;ui_upload_map(0x9800U+(uint16_t)(DRUM_SCREEN_ROW(row)+1)*32+3,canvas+at,17);memcpy(visible+at,canvas+at,17);mixfill();}
 seqflushpending=1;return 1;
}

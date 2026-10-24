#pragma bank 41
#include "api.h"
#include "resident.h"
#include "mixer_shared.h"
#include "song_mode.h"
/* Global arrangement occupies otherwise unused 480..767 in all five
   resident records. Copy/paste deliberately preserves this padding. */
static void bytes(uint16_t at,uint8_t *data,uint8_t n,uint8_t writing){uint8_t part,pad;uint16_t left;
 while(n){pad=at/288;left=288-at%288;part=left>n?n:left;
  if(writing)resident_write(pad,480+at%288,data,part);else resident_read(pad,480+at%288,data,part);
  data+=part;at+=part;n-=part;
 }
}
static void header(uint8_t *h){bytes(0,h,8,0);if(memcmp(h,"THG1",4)||h[4]>SONG_CAPACITY||h[5]){memcpy(h,"THG1",4);h[4]=h[5]=0;h[6]=1;h[7]=0;bytes(0,h,8,1);}}
uint16_t song_count(void) BANKED {uint8_t h[8];header(h);return h[4];}
uint8_t song_loop(void) BANKED {uint8_t h[8];header(h);return !!h[6];}
void song_loop_set(uint8_t on) BANKED {uint8_t h[8];header(h);h[6]=!!on;bytes(0,h,8,1);}
void song_read(uint16_t i,SongClip *c) BANKED {if(i>=SONG_CAPACITY){memset(c,0,sizeof(*c));c->pad=255;return;}bytes(8+i*9,(uint8_t *)c,9,0);}
uint16_t song_find(uint32_t at) BANKED {uint16_t i,n=song_count();SongClip c;
 for(i=0;i<n;i++){song_read(i,&c);if(c.start>at)break;if(at-c.start<c.length)return i;}return SONG_NONE;}
uint32_t song_end(void) BANKED {SongClip c;uint16_t n=song_count();if(!n)return 0;song_read(n-1,&c);return c.start+c.length;}
void song_delete(uint16_t i) BANKED {uint8_t h[8];*(uint8_t *)0xBEA1=1;SongClip c;header(h);if(i>=h[4])return;while(i+1<h[4]){song_read(i+1,&c);bytes(8+i*9,(uint8_t *)&c,9,1);i++;}h[4]--;bytes(0,h,8,1);}
uint8_t song_put(uint16_t old,const SongClip *input) BANKED {SongClip c,previous;uint16_t i,n=song_count(),rank=0;uint8_t h[8];
 if(old!=SONG_NONE&&old>=n)return 0;
 if(input->pad>=5||!input->length||input->start+input->length<input->start)return 0;
 for(i=0;i<n;i++){if(i==old)continue;song_read(i,&c);if(input->start<c.start+c.length&&c.start<input->start+input->length)return 0;if(c.start<input->start)rank++;}
 if(old==SONG_NONE&&n>=SONG_CAPACITY)return 0;
 c=*input;if(old!=SONG_NONE){song_delete(old);n--;}
 for(i=n;i>rank;i--){song_read(i-1,&previous);bytes(8+i*9,(uint8_t *)&previous,9,1);}
 *(uint8_t *)0xBEA1=1;bytes(8+rank*9,(uint8_t *)&c,9,1);header(h);h[4]=n+1;bytes(0,h,8,1);
 return 1;
}
uint32_t song_pattern_length(uint8_t pad) BANKED {uint8_t b[28],c;uint16_t longest=0,n,length;
 if(pad==mx.slot){for(c=0;c<7;c++)if(seqeventcounts[c]&&seqlength[c]>longest)longest=seqlength[c];}
 else{resident_read(pad,32,b,28);for(c=0;c<7;c++){n=b[c*2]|((uint16_t)b[c*2+1]<<8);length=b[14+c*2]|((uint16_t)b[15+c*2]<<8);if(n&&length>longest)longest=length;}}
 if(!longest){if(pad==mx.slot){for(c=0;c<7;c++)if((c<3||c==6)&&seqlength[c]>longest)longest=seqlength[c];}else for(c=0;c<7;c++)if(c<3||c==6){length=b[14+c*2]|((uint16_t)b[15+c*2]<<8);if(length>longest)longest=length;}}
 if(!longest)longest=16;return longest;
}

/* Editing-only selection overlay. Playback uses this region for its queue,
   so entry and exit clear it explicitly. No WRAM is allocated. */
__at (0xA7C0) static uint8_t pick[20];
__at (0xA7D4) static uint32_t pick_anchor;
__at (0xA7D8) static uint8_t pick_lane;
void song_pick_clear(void) BANKED {*(uint8_t *)0xBEA1=1;memset(pick,0,20);}
uint8_t song_pick_has(uint16_t i) BANKED {return i<SONG_CAPACITY&&(pick[i>>3]&(1<<(i&7)));}
void song_pick_begin(uint32_t at,uint8_t lane) BANKED {song_pick_clear();pick_anchor=at;pick_lane=lane;}
void song_pick_box(uint32_t at,uint8_t lane,uint16_t unit) BANKED {uint32_t lo=at<pick_anchor?at:pick_anchor,hi=at>pick_anchor?at:pick_anchor;uint8_t bottom=lane<pick_lane?lane:pick_lane,top=lane>pick_lane?lane:pick_lane;uint16_t i,n=song_count();SongClip c;
 song_pick_clear();if(hi+unit>=hi)hi+=unit;
 for(i=0;i<n;i++){song_read(i,&c);if(c.pad>=bottom&&c.pad<=top&&c.start<hi&&lo<c.start+c.length)pick[i>>3]|=1<<(i&7);}
}
uint8_t song_pick_edit(int16_t delta,uint8_t resizing) BANKED {uint16_t i,j,k,n=song_count();uint8_t *in=(uint8_t *)0xB000,*out=(uint8_t *)0xB700,*p;SongClip c;uint32_t end=0;
 /* Selected and unselected records are each already sorted. Translate into
    editor-only scratch, merge the two streams, then validate once. Nothing
    persistent changes if any final interval overlaps. */
 for(i=0;i<n;i++){
  song_read(i,&c);in[i*10+9]=!!song_pick_has(i);
  if(in[i*10+9]){if(resizing){if(delta<0&&c.length<=(uint16_t)-delta)return 0;c.length+=delta;}else{if(delta<0&&c.start<(uint16_t)-delta)return 0;c.start+=delta;}}
  if(!c.length||c.start+c.length<c.start)return 0;memcpy(in+i*10,&c,9);
 }
 i=j=0;
 for(k=0;k<n;k++){
  while(i<n&&!in[i*10+9])i++;while(j<n&&in[j*10+9])j++;
  if(i<n&&(j==n||((SongClip *)(in+i*10))->start<((SongClip *)(in+j*10))->start)){p=in+i*10;i++;}else{p=in+j*10;j++;}
  memcpy(&c,p,9);if(c.start<end)return 0;end=c.start+c.length;memcpy(out+k*10,p,10);
 }
 song_pick_clear();for(k=0;k<n;k++){bytes(8+k*9,out+k*10,9,1);if(out[k*10+9])pick[k>>3]|=1<<(k&7);}return 1;
}

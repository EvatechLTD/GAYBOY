#pragma bank 2
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
#include "resident.h"
#include "song_mode.h"
#include "song_link.h"
#include "smooth_playback.h"
extern uint8_t seqselectused,seqtilesready;
__at (0xA4ED) SongView song_view;
/* Match the normal UI's uppercase font. Lowercase IDs overlap grid tiles. */
static void text(uint8_t x,uint8_t y,const char *p,uint8_t inv){uint8_t c;while(*p&&x<20){c=*p++;if(c>='a'&&c<='z')c-=32;if(c<32||c>95)c='?';canvas[(uint16_t)y*20+x++]=c-32+(inv?96:0);}}
/* Retained display signatures, outside the stopped group-edit staging area.
   Song playback/editor exclusively own this ordinary roll scratch. */
#define TILESTATE ((uint8_t *)0xBE00)
#define TILEVALID (*(uint8_t *)0xBEA0)
static void song_number(uint8_t x,uint8_t y,uint32_t n){uint8_t b[10],i=0;do{b[i++]=n%10;n/=10;}while(n&&i<10);while(i&&x<20)canvas[(uint16_t)y*20+x++]=16+b[--i];}

#define CONTENTDIRTY (*(uint8_t *)0xBEA1)
#define LASTBASE (*(uint32_t *)0xBEA2)
#define LASTCOL (*(uint8_t *)0xBEA6)
#define LASTLANE (*(uint8_t *)0xBEA7)
#define LASTHEAD (*(uint8_t *)0xBEA8)
#define LASTSELECT (*(uint16_t *)0xBEAA)
#define LASTPLAY (*(uint8_t *)0xBEAC)
#define LASTERROR (*(uint8_t *)0xBEAD)
static void cell(uint8_t index,uint8_t state){uint8_t buf[16],y,lo,hi,tile;
 if(TILEVALID&&TILESTATE[index]==state)return;
 for(y=0;y<8;y++){
  lo=y==0||y==7?255:128;hi=state&32?128:0;
  if((state&1)&&y>0&&y<7){lo|=126;hi|=126;}
  if((state&8)&&y>1&&y<6){lo^=60;hi^=60;}
  if((state&2)&&y>0&&y<7){lo|=128;hi|=128;}
  if((state&4)&&y>0&&y<7){lo&=254;hi&=254;}
  if(state&16){if(y==0||y==7)lo=hi=255;else{lo|=129;hi|=129;}}
  buf[y*2]=lo;buf[y*2+1]=hi;
 }
 tile=index<32?64+index:128+index;ui_upload_tile(tile,buf,0);TILESTATE[index]=state;
}
static void cursor_cell(uint8_t lane,uint8_t col,uint8_t on){uint8_t index,state;
 if(col>=16)return;index=lane*16+col;state=TILESTATE[index]&~16;if(on)state|=16;cell(index,state);
}
static void header(void){
 memset(canvas,0,40);memset(canvas,96,20);
 text(0,0,"SONG",song_view.head!=1);text(6,0,song_loop()?"LOOP":"ONCE",song_view.head!=2);text(12,0,"BPM",song_view.head!=3);song_number(16,0,seqbpm);
 text(0,1,song_playing?"PLAYING":song_link_active||smooth_playback_preparing?"BUFFERING":"STOPPED",0);text(10,1,"16 BARS",0);
}
void song_status(uint8_t ready) BANKED {
 if(smooth_playback_active){if(ready)smooth_playback_ready();return;}
 header();memset(canvas+20,0,10);text(0,1,ready?"PLAYING":"BUFFERING",0);
 memset(canvas+320,0,20);text(0,16,ready?"SELECT+A TO STOP":"BUFFERING",0);
 ui_upload_map(0x9820U,canvas+20,20);memcpy(visible+20,canvas+20,20);
 ui_upload_map(0x9A00U,canvas+320,20);memcpy(visible+320,canvas+320,20);CONTENTDIRTY=1;
}
static void view(void){song_view.base=song_view.cursor&~255UL;}
void song_open(void) BANKED {TILEVALID=0;if(seqplaying)seq_transport();if(song_view.used!=84){memset(&song_view,0,sizeof(song_view));song_view.reserved=0;song_view.selected=SONG_NONE;song_view.used=84;}song_view.reserved=0;song_view.cursor&=~15UL;if(song_view.head>3)song_view.head=3;song_view.error=0;song_view.selected=SONG_NONE;song_view.gesture=0;song_pick_clear();view();seqdrawvalid=0;dirty=1;}
void song_input(uint8_t p,uint8_t edge) BANKED {uint32_t unit=16,old=song_view.cursor;SongClip c;uint16_t found;uint8_t directions=edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN);
 if((p&(J_START|J_SELECT))==(J_START|J_SELECT)&&(edge&(J_START|J_SELECT))){navblocked=seqselectused=1;if(song_playing)song_stop();else song_start(1);return;}
 if(song_playing){if((p&J_SELECT)&&(edge&J_A))song_stop();return;}
 if(song_link_active){if((p&J_SELECT)&&(edge&J_A))song_start(0);return;}
 if((lastpad&J_B)&&!(p&J_B)&&song_view.gesture==2){song_delete(song_view.selected);song_pick_clear();song_view.selected=SONG_NONE;song_view.gesture=0;dirty=1;}
 if((lastpad&J_A)&&!(p&J_A)&&song_view.selected!=SONG_NONE){song_view.selected=SONG_NONE;CONTENTDIRTY=1;dirty=1;}
 /* Release completes a gesture; it does not require another full redraw. */
 if(!edge){if(!(p&J_A)&&song_view.gesture==4)song_view.gesture=0;if(!p)song_view.gesture=0;return;}
 if((p&J_SELECT)&&(edge&J_A)){seqselectused=1;song_start(0);return;}
 if(p&J_SELECT){seqselectused=1;
  if(edge&J_LEFT){song_view.cursor=0;song_view.head=0;view();dirty=1;}
  else if((edge&J_RIGHT)&&song_view.cursor+256UL>=song_view.cursor){song_view.cursor+=256UL;song_view.head=0;view();dirty=1;}
  return;
 }
 if(!song_view.head&&((p&(J_A|J_B))||(edge&(J_A|J_B))))CONTENTDIRTY=1;
 if(song_view.head){
  if((p&(J_A|J_B))&&(directions||(edge&(J_A|J_B)))){
   if(song_view.head==1){song_start(0);return;}
   if(song_view.head==2)song_loop_set(!song_loop());
   if(song_view.head==3){mixer_tempo_edit(edge&(J_LEFT|J_DOWN|J_B)?-1:1);}dirty=1;return;
  }
  if(edge&J_LEFT&&song_view.head>1)song_view.head--;if(edge&J_RIGHT&&song_view.head<3)song_view.head++;if(edge&J_DOWN)song_view.head=0;dirty=1;return;
 }
 found=song_find(old);
 if(edge&J_A){if(found!=SONG_NONE){song_read(found,&c);if(c.pad!=song_view.lane)found=SONG_NONE;}
  if(found==SONG_NONE){song_pick_begin(old,song_view.lane);song_view.gesture=4;}else if(!song_pick_has(found))song_pick_clear();
 }
 if(song_view.gesture==4){
  if(p&J_A){if(edge&J_LEFT&&song_view.cursor>=unit)song_view.cursor-=unit;if(edge&J_RIGHT&&song_view.cursor+unit>=song_view.cursor)song_view.cursor+=unit;if(edge&J_UP&&song_view.lane)song_view.lane--;if(edge&J_DOWN&&song_view.lane<4)song_view.lane++;song_pick_box(song_view.cursor,song_view.lane,unit);view();dirty=1;return;}
  song_view.gesture=0;
 }
 if((p&(J_A|J_B))&&(edge&(J_LEFT|J_RIGHT))&&found!=SONG_NONE&&song_pick_has(found)){
  song_read(found,&c);if(song_pick_edit(edge&J_LEFT?-(int16_t)unit:(int16_t)unit,!!(p&J_B))){song_view.cursor=p&J_B?c.start+c.length+(edge&J_LEFT?-(int16_t)unit:(int16_t)unit)-1:old+(edge&J_LEFT?-(int16_t)unit:(int16_t)unit);song_view.cursor&=~15UL;song_view.selected=song_find(song_view.cursor);song_view.gesture=1;song_view.error=0;}else song_view.error=8;view();dirty=1;return;
 }

 if((p&(J_A|J_B))&&directions&&found!=SONG_NONE){song_read(found,&c);
  if(c.pad!=song_view.lane)return;
  if(edge&(J_UP|J_DOWN))return;
  if(p&J_B){if(edge&J_LEFT){if(c.length<=unit)return;c.length-=unit;}else if(c.length+unit>c.length)c.length+=unit;}
  else {if(edge&J_LEFT){if(c.start<unit)return;c.start-=unit;}else if(c.start+unit>=c.start)c.start+=unit;}
  if(song_put(found,&c)){song_view.cursor=(p&J_B)?c.start+c.length-1:c.start;song_view.cursor&=~15UL;song_view.selected=song_find(c.start);song_view.gesture=1;song_view.error=0;}else song_view.error=8;
  view();dirty=1;return;
 }
 if(edge&J_LEFT){if(old>=unit)song_view.cursor-=unit;else song_view.cursor=0;}
 if(edge&J_RIGHT&&old+unit>=old)song_view.cursor+=unit;
 if(!(p&(J_A|J_B))){if(edge&J_UP){if(song_view.lane)song_view.lane--;else song_view.head=1;}if(edge&J_DOWN&&song_view.lane<4)song_view.lane++;}
 if(edge&J_A){song_view.selected=found;}
 if(edge&J_B){if(found!=SONG_NONE){song_read(found,&c);if(c.pad==song_view.lane){song_view.selected=found;song_view.gesture=2;}}
  else {c.start=song_view.cursor&~15UL;c.length=(song_pattern_length(song_view.lane)+15)&~15UL;c.pad=song_view.lane;found=c.start?song_find(c.start-1):SONG_NONE;if(found!=SONG_NONE){SongClip previous;song_read(found,&previous);if(previous.pad==c.pad&&previous.start+previous.length==c.start){c.start=previous.start;c.length+=previous.length;}else found=SONG_NONE;}song_pick_clear();if(song_put(found,&c)){song_view.selected=SONG_NONE;song_view.gesture=1;song_view.error=0;}else song_view.error=song_count()>=SONG_CAPACITY?9:8;}
 }
 if(!p)song_view.gesture=0;view();dirty|=!!edge;
}
void song_render(void) BANKED {uint8_t cells[5][16],lane,col,i,tile,a,index,cur;uint16_t n,at,first,last;uint32_t right;SongClip c;char name[17];
 HIDE_SPRITES;view();
 cur=!song_playing&&!song_view.head?(song_view.cursor-song_view.base)>>4:255;
 if(TILEVALID&&!CONTENTDIRTY&&LASTBASE==song_view.base&&LASTSELECT==song_view.selected&&LASTPLAY==song_playing&&LASTERROR==song_view.error){
  if(LASTCOL!=cur||LASTLANE!=song_view.lane){cursor_cell(LASTLANE,LASTCOL,0);cursor_cell(song_view.lane,cur,1);}
  if(LASTHEAD!=song_view.head||song_view.head)header();
  LASTHEAD=song_view.head;LASTCOL=cur;LASTLANE=song_view.lane;seqflushpending=1;return;
 }
 right=song_view.base+256;if(right<song_view.base)right=0xffffffffUL;memset(cells,0,sizeof(cells));memset(canvas,0,360);header();
 text(0,2,"BAR",0);song_number(4,2,song_view.base/16+1);text(11,2,"TO",0);song_number(14,2,(right>>4)+!!(right&15));
 n=song_count();for(at=0;at<n;at++){song_read(at,&c);if(c.start>=right)break;if(c.start+c.length<=song_view.base||c.pad>=5)continue;
  first=c.start>song_view.base?(c.start-song_view.base)>>4:0;last=((c.start+c.length<right?c.start+c.length:right)-song_view.base+15)>>4;if(last>16)last=16;
  for(col=first;col<last;col++)cells[c.pad][col]|=1|((((lastpad&J_A)&&song_view.selected==at)||song_pick_has(at))&&!song_playing?8:0);
  if(c.start>=song_view.base)cells[c.pad][first]|=2;if(c.start+c.length<=right&&last)cells[c.pad][last-1]|=4;
 }
 cur=!song_playing&&!song_view.head?(song_view.cursor-song_view.base)>>4:255;
 for(lane=0;lane<5;lane++){
  resident_read(lane,16,(uint8_t *)name,16);name[16]=0;song_number(0,3+lane*2,lane+1);text(2,3+lane*2,name,0);song_number(0,4+lane*2,lane+1);
  for(i=0;i<16;i++){
   index=lane*16+i;a=cells[lane][i];
   if(lane==song_view.lane&&cur==i)a|=16;if(!(i&3))a|=32;cell(index,a);
   if(song_playing&&!(i&3))song_service();
   tile=lane*16+i;tile=tile<32?64+tile:128+tile;canvas[(uint16_t)(4+lane*2)*20+4+i]=tile;
  }
 }
 text(0,14,"1 CELL = 1 BAR",0);text(0,15,"B PLOT  A MOVE",0);text(0,16,song_playing?"SELECT+A TO STOP":song_link_active?"BUFFERING":"B+LR LENGTH",0);text(0,17,"START+SELECT SMOOTH",0);
 if(song_view.error){static const char * const errors[]={"","EMPTY SONG","AUDIO CACHE FULL","UNSUPPORTED PATCH","PCM NOT PREPARED","P1 / KICK SHARED","STOP PATTERN FIRST","SYNC OFF REQUIRED","CLIPS CANNOT OVERLAP","SONG MEMORY FULL","PAST SONG END","LINK NOT READY"};memset(canvas+300,0,40);text(0,15,errors[song_view.error<12?song_view.error:3],0);}
 LASTBASE=song_view.base;LASTCOL=cur;LASTLANE=song_view.lane;LASTHEAD=song_view.head;LASTSELECT=song_view.selected;LASTPLAY=song_playing;LASTERROR=song_view.error;CONTENTDIRTY=0;
 TILEVALID=1;seqfontdirty=1;seqtilesready=0;*(uint8_t *)0xAD80=0;seqdrawvalid=0;seqflushpending=1;
}

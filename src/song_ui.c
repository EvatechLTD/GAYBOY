#pragma bank 2
#include "api.h"
#include "mixer_shared.h"
#include "resident.h"
#include "song_mode.h"
#include "smooth_playback.h"
extern uint8_t seqselectused,seqtilesready;
__at (0xA4ED) SongView song_view;
static const uint16_t zooms[9]={2,4,8,16,32,64,128,256,512};
static const char * const zoomnames[9]={"1/8","1/4","1/2","1BAR","2BAR","4BAR","8BAR","16BAR","32BAR"};
static void text(uint8_t x,uint8_t y,const char *p,uint8_t inv){while(*p&&x<20)canvas[(uint16_t)y*20+x++]=*p++-32+(inv?96:0);}
static void song_number(uint8_t x,uint8_t y,uint32_t n){uint8_t b[10],i=0;do{b[i++]=n%10;n/=10;}while(n&&i<10);while(i&&x<20)canvas[(uint16_t)y*20+x++]=16+b[--i];}
static void view(void){uint32_t width=(uint32_t)zooms[song_view.zoom]*32;song_view.base=(song_view.cursor/width)*width;}
void song_open(void) BANKED {if(seqplaying)seq_transport();if(song_view.used!=84){memset(&song_view,0,sizeof(song_view));song_view.zoom=3;song_view.selected=SONG_NONE;song_view.used=84;}song_view.error=0;song_pick_clear();view();seqdrawvalid=0;dirty=1;}
void song_input(uint8_t p,uint8_t edge) BANKED {uint32_t unit=zooms[song_view.zoom],old=song_view.cursor;SongClip c;uint16_t found;uint8_t directions=edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN);
 if((p&(J_START|J_SELECT))==(J_START|J_SELECT)&&(edge&(J_START|J_SELECT))){navblocked=seqselectused=1;if(song_playing)song_stop();else song_start(1);return;}
 if(song_playing){if((p&J_SELECT)&&(edge&J_A))song_stop();return;}
 if((lastpad&J_B)&&!(p&J_B)&&song_view.gesture==2){song_delete(song_view.selected);song_pick_clear();song_view.selected=SONG_NONE;song_view.gesture=0;dirty=1;}
 if((p&J_SELECT)&&(edge&J_A)){seqselectused=1;song_start(0);return;}
 if(p&J_SELECT){if(edge&J_UP){if(song_view.zoom)song_view.zoom--;seqselectused=1;}if(edge&J_DOWN){if(song_view.zoom<8)song_view.zoom++;seqselectused=1;}view();dirty=1;return;}
 if(song_view.head){
  if((p&(J_A|J_B))&&(directions||(edge&(J_A|J_B)))){
   if(song_view.head==1){song_start(0);return;}
   if(song_view.head==2)song_loop_set(!song_loop());
   if(song_view.head==3){if((edge&(J_LEFT|J_UP|J_B))&&song_view.zoom)song_view.zoom--;else if(song_view.zoom<8)song_view.zoom++;view();}
   if(song_view.head==4){mixer_tempo_edit(edge&(J_LEFT|J_DOWN|J_B)?-1:1);}dirty=1;return;
  }
  if(edge&J_LEFT&&song_view.head>1)song_view.head--;if(edge&J_RIGHT&&song_view.head<4)song_view.head++;if(edge&J_DOWN)song_view.head=0;dirty=1;return;
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
  song_read(found,&c);if(song_pick_edit(edge&J_LEFT?-(int16_t)unit:(int16_t)unit,!!(p&J_B))){song_view.cursor=p&J_B?c.start+c.length+(edge&J_LEFT?-(int16_t)unit:(int16_t)unit)-1:old+(edge&J_LEFT?-(int16_t)unit:(int16_t)unit);song_view.selected=song_find(song_view.cursor);song_view.gesture=1;song_view.error=0;}else song_view.error=8;view();dirty=1;return;
 }

 if((p&(J_A|J_B))&&directions&&found!=SONG_NONE){song_read(found,&c);
  if(c.pad!=song_view.lane)return;
  if(edge&(J_UP|J_DOWN))return;
  if(p&J_B){if(edge&J_LEFT){if(c.length<=unit)return;c.length-=unit;}else if(c.length+unit>c.length)c.length+=unit;}
  else {if(edge&J_LEFT){if(c.start<unit)return;c.start-=unit;}else if(c.start+unit>=c.start)c.start+=unit;}
  if(song_put(found,&c)){song_view.cursor=(p&J_B)?c.start+c.length-1:c.start;song_view.selected=song_find(c.start);song_view.gesture=1;song_view.error=0;}else song_view.error=8;
  view();dirty=1;return;
 }
 if(edge&J_LEFT){if(old>=unit)song_view.cursor-=unit;else song_view.cursor=0;}
 if(edge&J_RIGHT&&old+unit>=old)song_view.cursor+=unit;
 if(!(p&(J_A|J_B))){if(edge&J_UP){if(song_view.lane)song_view.lane--;else song_view.head=1;}if(edge&J_DOWN&&song_view.lane<4)song_view.lane++;}
 if(edge&J_A){song_view.selected=found;}
 if(edge&J_B){if(found!=SONG_NONE){song_read(found,&c);if(c.pad==song_view.lane){song_view.selected=found;song_view.gesture=2;}}
  else {c.start=song_view.cursor;c.length=song_pattern_length(song_view.lane);c.pad=song_view.lane;found=c.start?song_find(c.start-1):SONG_NONE;if(found!=SONG_NONE){SongClip previous;song_read(found,&previous);if(previous.pad==c.pad&&previous.start+previous.length==c.start){c.start=previous.start;c.length+=previous.length;}else found=SONG_NONE;}song_pick_clear();if(song_put(found,&c)){song_view.selected=song_find(c.start);song_view.error=0;}else song_view.error=song_count()>=SONG_CAPACITY?9:8;}
 }
 if(!p)song_view.gesture=0;view();dirty|=!!edge;
}
void song_render(void) BANKED {uint8_t cells[5][32],buf[16],lane,col,i,y,bits,state,tile;uint16_t n,at,first,last;uint32_t unit=zooms[song_view.zoom],right;SongClip c;char name[17];
 HIDE_SPRITES;view();right=song_view.base+unit*32;if(right<song_view.base)right=0xffffffffUL;memset(cells,0,sizeof(cells));memset(canvas,0,360);memset(canvas,96,20);
 text(0,0,"SONG",song_view.head!=1);text(6,0,song_loop()?"LOOP":"ONCE",song_view.head!=2);text(12,0,zoomnames[song_view.zoom],song_view.head!=3);
 text(0,1,song_playing?"PLAYING":"STOPPED",0);text(10,1,"BPM",song_view.head==4);song_number(14,1,seqbpm);
 text(0,2,"BAR",0);song_number(4,2,song_view.base/16+1);text(11,2,"TO",0);song_number(14,2,(right>>4)+!!(right&15));
 n=song_count();for(at=0;at<n;at++){song_read(at,&c);if(c.start>=right)break;if(c.start+c.length<=song_view.base||c.pad>=5)continue;
  first=c.start>song_view.base?(c.start-song_view.base)/unit:0;last=((c.start+c.length<right?c.start+c.length:right)-song_view.base+unit-1)/unit;if(last>32)last=32;
  for(col=first;col<last;col++)cells[c.pad][col]|=1|((song_view.selected==at||song_pick_has(at))&&!song_playing?8:0);
  if(c.start>=song_view.base)cells[c.pad][first]|=2;if(c.start+c.length<=right&&last)cells[c.pad][last-1]|=4;
 }
 for(lane=0;lane<5;lane++){
  resident_read(lane,16,(uint8_t *)name,16);name[16]=0;song_number(0,3+lane*2,lane+1);text(2,3+lane*2,name,0);song_number(0,4+lane*2,lane+1);
  for(i=0;i<16;i++){
   memset(buf,0,16);for(col=0;col<2;col++){state=cells[lane][i*2+col];for(y=0;y<8;y++){
    bits=y==7?1:0;if(state&1){if(y>=2&&y<=5)bits=15;if((state&2)&&y>=1&&y<=6)bits|=8;if((state&4)&&y>=1&&y<=6)bits|=1;}
    if(state&8)bits^=15;
    if(!song_playing&&!song_view.head&&lane==song_view.lane&&(song_view.cursor-song_view.base)/unit==i*2+col&&(y==0||y==7))bits^=15;
    buf[y*2]|=bits<<(col?0:4);buf[y*2+1]=buf[y*2];
   }}
   tile=lane*16+i;tile=tile<32?64+tile:128+tile;ui_upload_tile(tile,buf,0);if(song_playing&&!(i&3))song_service();canvas[(uint16_t)(4+lane*2)*20+4+i]=tile;
  }
 }
 text(0,14,"SEL+UP/DN ZOOM",0);text(0,15,"B PLOT  A MOVE",0);text(0,16,"B+LR LENGTH",0);text(0,17,"START+SELECT SMOOTH",0);
 if(song_view.error){static const char * const errors[]={"","EMPTY SONG","AUDIO CACHE FULL","UNSUPPORTED PATCH","PCM NOT PREPARED","P1 / KICK SHARED","STOP PATTERN FIRST","SYNC OFF REQUIRED","CLIPS CANNOT OVERLAP","SONG MEMORY FULL"};memset(canvas+300,0,40);text(0,15,errors[song_view.error<10?song_view.error:3],0);}
 seqfontdirty=1;seqtilesready=0;*(uint8_t *)0xAD80=0;seqdrawvalid=0;seqflushpending=1;
}

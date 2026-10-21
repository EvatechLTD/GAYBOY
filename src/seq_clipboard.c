#pragma bank 38
#include "api.h"
#include "drum_rows.h"
void roll_clear_transition(void) BANKED;
void mixer_pattern_changed(void) BANKED;
extern uint16_t seqclock,seqdeadline;
#define CLIP ((uint8_t *)0xB400)
#define CACHE ((uint8_t *)0xB000)
static void ram(uint8_t b){ENABLE_RAM;SWITCH_RAM(b);}
static uint16_t getword(const uint8_t *p){return p[0]|((uint16_t)p[1]<<8);}
static void setword(uint8_t *p,uint16_t n){p[0]=n;p[1]=n>>8;}
static void clip_part(uint16_t offset,uint8_t *data,uint16_t count,uint8_t writing){
 uint8_t buf[16],n;while(count){n=count>16?16:count;
  if(writing)memcpy(buf,data,n);
  __critical {ram(3);if(writing)memcpy(CLIP+offset,buf,n);else memcpy(buf,CLIP+offset,n);ram(0);}
  if(!writing)memcpy(data,buf,n);data+=n;offset+=n;count-=n;mixfill();
 }
}
extern uint16_t drum_clip_plot(uint8_t step,uint8_t row,uint16_t dur,uint8_t vel) BANKED;
/* Region clipboard uses the same reserved SRAM as track copy, with a distinct
   tag. Positions are relative to the selection's upper-left grid cell. */
static uint8_t region_selected(const uint8_t *e){uint8_t y=seqtrack==6?DRUM_VIEW_ROW(e[1]-1):e[1]-1;return e[1]&&e[0]>=seqgroupx0&&e[0]<=seqgroupx1&&y>=seqgroupy0&&y<=seqgroupy1;}
uint8_t seq_region_copy(uint8_t cut) BANKED {
 uint8_t c=seqtrack,e[4],meta[16];uint16_t i,count=0,n=seq_event_count(c);
 if(seqgrouptrack!=c)return 0;
 for(i=0;i<n;i++){seq_event_get(c,i,e);if(region_selected(e))count++;}
 if(!count)return 0;
 memset(meta,0,16);clip_part(0,meta,1,1);meta[1]=c;setword(meta+2,count);setword(meta+4,(uint16_t)seqgroupx1-seqgroupx0+1);meta[6]=seqgroupy1-seqgroupy0;meta[7]=seqgroupy0;meta[12]=c==6;meta[11]=0x74;clip_part(1,meta+1,15,1);
 count=0;for(i=0;i<n;i++){seq_event_get(c,i,e);if(!region_selected(e))continue;e[0]-=seqgroupx0;e[1]=c==6?e[1]:seqgroupy1+2-e[1];clip_part(16+count*4,e,4,1);count++;}
 meta[0]=0xC9;clip_part(0,meta,1,1);
 if(cut){i=n;while(i){i--;seq_event_get(c,i,e);if(region_selected(e))seq_event_erase(c,i);}if(c==6)drum_stop();else {uint8_t note=seqowned[c];seqowned[c]=0;seqgateleft[c]=0;if(note)event(0x80|c,note-1,0);}}
 seqdrawvalid=0;dirty=1;return 1;
}
uint8_t seq_region_paste(uint8_t step,uint8_t pitch) BANKED {
 uint8_t c=seqtrack,meta[16],e[4],busy;uint16_t count,i,total=seq_event_total(),needed;int16_t x,y;uint16_t duration;
 clip_part(0,meta,16,0);count=getword(meta+2);
 if(meta[0]!=0xC9||meta[11]!=0x74||!count||count>256||meta[1]>6||((c==6)!=(meta[1]==6)))return 0;
 if(c==6&&meta[12])pitch=meta[7];
 if((uint16_t)step+getword(meta+4)>seqlength[c]||(c==6?(uint16_t)pitch+meta[6]>12:pitch<meta[6]))return 0;
 clip_part(16,CACHE,count*4,0);roll_clear_transition();seqfontdirty=0;needed=count;
 /* Validate every destination before making any changes. */
 for(i=0;i<count;i++){memcpy(e,CACHE+i*4,4);x=(uint16_t)step+e[0];y=c==6?(meta[12]?DRUM_VIEW_ROW(e[1]-1):(int16_t)pitch+e[1]-1):(int16_t)pitch-e[1]+1;duration=e[3]?e[3]:256;
  if(!e[1]||x>=seqlength[c]||x+duration>seqlength[c]||y<0||y>(c==6?12:127))return 0;
  if(c!=6){uint16_t scan=0;uint8_t old[4];while(seq_event_next_step(c,x,&scan,old))if(old[1]==y+1){needed--;break;}}
  e[0]=x;e[1]=c==6?DRUM_VOICE_ROW(y)+1:y+1;memcpy(CACHE+i*4,e,4);
 }
 if(total+needed>256){seqeventfull=1;return 0;}
 busy=seqservicing;seqservicing=1;if(c<5)evalpatch[c][EV_CHORD_HISTORY]=1;
 for(i=0;i<count;i++){memcpy(e,CACHE+i*4,4);if(c==6)drum_clip_plot(e[0],DRUM_VIEW_ROW(e[1]-1),e[3]?e[3]:256,e[2]);else {uint16_t scan=0,found=65535;uint8_t old[4];while(seq_event_next_step(c,e[0],&scan,old))if(old[1]==e[1]){found=scan-1;break;}seq_event_put(c,found,e);}mixfill();}
 seqservicing=busy;seqgrouptrack=c;seqgroupx0=step;seqgroupx1=step+getword(meta+4)-1;
 seqgroupy0=c==6?pitch:pitch-meta[6];seqgroupy1=c==6?pitch+meta[6]:pitch;
 seqdrawvalid=0;dirty=1;return 1;
}

void seq_swing_step(void) BANKED{if(seqswing==50){seqthreshold=15360U;return;}uint16_t amount=seqswing-50,first=15360U+amount*307U+(amount*20U)/100U;if(seqswing==66)first=20480U;seqthreshold=seqswingphase?30720U-first:first;}

void seq_swing_edit(int16_t delta) BANKED {int16_t value;if(seqplaying)seq_frame();value=(int16_t)seqswing+delta;if(!syncmode){seqirqready=0;seqirqdirty=1;}seqswing=value<50?50:value>100?100:value;seq_swing_step();if(seqthreshold&&seqclock>=seqthreshold)seqclock=seqthreshold-1;seqdeadline=1;dirty=1;return;}


extern uint8_t seqmeterbeats,seqmeterdenom,seqbeats,seqdenom;
void seq_meterbuild(void) BANKED{uint8_t i,beat=0,within=0,steps;if(seqmeterbeats==seqbeats&&seqmeterdenom==seqdenom)return;steps=16/seqdenom;for(i=0;i<64;i++){seqgrid[i]=within?64:beat?76:160;if(++within==steps){within=0;if(++beat==seqbeats)beat=0;}if(!(i&7)){mixfill();if(monomode&&expconfig[0])exp_fill();}}seqmeterbeats=seqbeats;seqmeterdenom=seqdenom;}

/* The track and region clipboards share SRAM, with explicit menu actions. */
uint8_t seq_clip_kind(void) BANKED {uint8_t meta[16];clip_part(0,meta,16,0);return meta[0]==0xC8&&meta[11]==0x73?1:meta[0]==0xC9&&meta[11]==0x74?2:0;}
void seq_copy_track(void) BANKED {uint8_t group=seqgrouptrack;seqgrouptrack=255;seq_copy();seqgrouptrack=group;}
void seq_select_visible(void) BANKED {uint16_t end;uint8_t c=seqtrack;
 seq_dimensions();end=(uint16_t)seqbase+seqcols;if(end>seqlength[c])end=seqlength[c];
 seqgrouptrack=c;seqgroupx0=seqbase;seqgroupx1=end-1;seqgroupy1=c==6?12:seqtop[c];seqgroupy0=c==6?0:seqtop[c]+1-seqrows;
 seqcursor[c]=seqbase;if(c==6)drumrow=0;else seqpitch[c]=seqgroupy1;seqapending=seqamoved=seqhead=seqfocus=0;if(seqdrawvalid)seqdrawvalid=2;dirty=1;
}
void seq_clear_release(uint8_t track) BANKED;
void seq_delete_selection(void) BANKED {uint8_t e[4],c=seqtrack;uint16_t i;
 if(seqgrouptrack!=c)return;sparse_journal_edit_barrier();sparse_finish_install();i=seq_event_count(c);
 while(i){i--;seq_event_get(c,i,e);if(region_selected(e))seq_event_erase(c,i);mixfill();}
 seq_clear_release(c);mixer_pattern_changed();seqdrawvalid=0;dirty=1;
}

/* Duplicate directly from the original event range; leave the clipboard intact.
   Preflight the complete operation so capacity/bounds errors make no edits. */
uint8_t seq_region_duplicate(void) BANKED {
 uint8_t c=seqtrack,e[4];uint16_t i,n=seq_event_count(c),count=0,width=(uint16_t)seqgroupx1-seqgroupx0+1,x;
 if(seqgrouptrack!=c||(uint16_t)seqgroupx1+width>=seqlength[c])return 0;
 for(i=0;i<n;i++){seq_event_get(c,i,e);if(!region_selected(e))continue;count++;x=(uint16_t)e[0]+width;if(x+(e[3]?e[3]:256U)>seqlength[c])return 0;mixfill();}
 if(!count)return 0;if(seq_event_total()+count>256){seqeventfull=1;return 0;}
 for(i=0;i<n;i++){seq_event_get(c,i,e);if(!region_selected(e))continue;e[0]+=width;seq_event_put(c,65535U,e);mixfill();}
 seqgroupx0+=width;seqgroupx1+=width;seqcursor[c]=seqgroupx0;seqdrawvalid=0;mixer_pattern_changed();dirty=1;return 1;
}

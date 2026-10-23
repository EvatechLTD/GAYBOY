#pragma bank 51
#include "api.h"
#include "sequencer_limits.h"
#include "mixer_shared.h"
extern uint16_t pattern_generation;
extern uint8_t seqbused;
void eval_seq_off_track(uint8_t c) BANKED;
void eval_seq_clamp_cursor(void) BANKED{uint8_t c=seqtrack,minimum=SEQ_NOTE_MINIMUM(c),maximum=seq_note_maximum(c);if(c==6)minimum=0;if(seqcursor[c]>=seqlength[c])seqcursor[c]=seqlength[c]-1;if(seqpitch[c]<minimum)seqpitch[c]=minimum;if(seqpitch[c]>maximum)seqpitch[c]=maximum;if(seqtop[c]>maximum)seqtop[c]=maximum;if(seqtop[c]<minimum+seqrows-1)seqtop[c]=minimum+seqrows-1;if(seqpitch[c]>seqtop[c])seqtop[c]=seqpitch[c];if(seqpitch[c]+seqrows-1<seqtop[c])seqtop[c]=seqpitch[c]+seqrows-1;}
static uint8_t selectedbits[32];
static uint8_t selectionvalid,selectiontrack,selectionslot,selectionbox[4];
static uint16_t selectiongeneration,selectioncount;
static uint8_t selection_matches(uint8_t c,uint16_t count){return selectionvalid&&selectiontrack==c&&selectionslot==mx.slot&&selectiongeneration==pattern_generation&&selectioncount==count&&seqgrouptrack==c&&selectionbox[0]==seqgroupx0&&selectionbox[1]==seqgroupx1&&selectionbox[2]==seqgroupy0&&selectionbox[3]==seqgroupy1;}
static void selection_remember(uint8_t c,uint16_t count){selectionvalid=1;selectiontrack=c;selectionslot=mx.slot;selectiongeneration=pattern_generation;selectioncount=count;selectionbox[0]=seqgroupx0;selectionbox[1]=seqgroupx1;selectionbox[2]=seqgroupy0;selectionbox[3]=seqgroupy1;}
static uint8_t selected_event(uint8_t *e){return e[1]&&seqgrouptrack==seqtrack&&e[0]>=seqgroupx0&&e[0]<=seqgroupx1&&e[1]>seqgroupy0&&e[1]<=seqgroupy1+1;}
uint8_t roll_note_feedback(uint8_t c,const uint8_t *e,uint8_t erase) BANKED;
void roll_edit_batch(uint8_t enabled) BANKED;
uint8_t roll_group_add(uint8_t c,const uint8_t *e,uint16_t index) BANKED;
uint8_t roll_replace_feedback(uint8_t c,const uint8_t *old,const uint8_t *next,uint16_t index) BANKED;
void eval_seq_group_move(uint8_t edge) BANKED{uint8_t c=seqtrack,e[4],other[4],cached;uint16_t i,j,dur,selected=0,count=seq_event_count(c);int8_t dx=0,dy=0;int16_t at,pitch;
 seqamoved=1;if(edge&J_LEFT)dx--;if(edge&J_RIGHT)dx++;if(edge&J_UP)dy++;if(edge&J_DOWN)dy--;
 if((int16_t)seqgroupx0+dx<0||(int16_t)seqgroupx1+dx>=seqlength[c]||(int16_t)seqgroupy0+dy<SEQ_NOTE_MINIMUM(c)||(int16_t)seqgroupy1+dy>seq_note_maximum(c))return;
 cached=selection_matches(c,count);if(!cached){selectionvalid=0;memset(selectedbits,0,32);}
 for(i=0;i<count;i++){if(cached&&!(selectedbits[i>>3]&(1<<(i&7))))continue;seq_event_get(c,i,e);if(!cached){if(!selected_event(e))continue;selectedbits[i>>3]|=1<<(i&7);}at=e[0]+dx;pitch=(int16_t)e[1]+dy;dur=e[3]?e[3]:256;
  if(at<0||at+dur>seqlength[c]||pitch<SEQ_NOTE_MINIMUM(c)+1||pitch>seq_note_maximum(c)+1)return;
  selected++;mixfill();
 }if(!selected)return;
 if(dx&&selected<count)for(i=0;i<count;i++){if(!(selectedbits[i>>3]&(1<<(i&7))))continue;seq_event_get(c,i,e);at=e[0]+dx;dur=e[3]?e[3]:256;
  for(j=0;j<count;j++){if(selectedbits[j>>3]&(1<<(j&7)))continue;seq_event_get(c,j,other);if(other[1]&&((!eval_mode(c)&&!evalpatch[c][EV_CHORD_HISTORY])||other[1]==e[1]+dy)&&at<other[0]+(other[3]?other[3]:256)&&other[0]<at+dur)return;}mixfill();
 }
 for(i=0;i<count;i++){if(!(selectedbits[i>>3]&(1<<(i&7))))continue;seq_event_get(c,i,e);if(seqplaying&&seqsource[c]==e[0])eval_seq_off_track(c);e[0]+=dx;e[1]+=dy;seq_event_put(c,i,e);mixfill();}
 seqgroupx0+=dx;seqgroupx1+=dx;seqgroupy0+=dy;seqgroupy1+=dy;seqaanchor+=dx;seqcursor[c]+=dx;seqpitch[c]+=dy;eval_seq_clamp_cursor();selection_remember(c,count);seqdrawvalid=0;dirty=1;
}

void eval_seq_group_resize(int8_t delta) BANKED {uint8_t c=seqtrack,e[4],old[4],fast=seqdrawvalid,local=eval_mode(seqtrack)||evalpatch[seqtrack][EV_CHORD_HISTORY];uint16_t i,count=seq_event_count(c);int16_t n;
 if(local)fast=0;seqamoved=seqbused=1;
 if(!seq_length_step(seqaanchor+seq_duration_get(c,seqaanchor)-1,seqaanchor+seq_duration_get(c,seqaanchor)-1+delta))return;
 selectionvalid=0;memset(selectedbits,0,32);
 for(i=0;i<count;i++){seq_event_get(c,i,e);if(selected_event(e)){selectedbits[i>>3]|=1<<(i&7);n=(e[3]?e[3]:256)+delta;if(n<1||n>seqlength[c]-e[0])return;}mixfill();}
 roll_edit_batch(1);for(i=0;i<count;i++){if(!(selectedbits[i>>3]&(1<<(i&7))))continue;seq_event_get(c,i,e);memcpy(old,e,4);e[3]=(e[3]?e[3]:256)+delta;if(!local&&!roll_replace_feedback(c,old,e,i))fast=0;seq_event_put(c,i,e);mixfill();}
 seqdefaultdur[c]=seq_duration_get(c,seqaanchor);seqcursor[c]=seqaanchor+seqdefaultdur[c]-1;seqdrawvalid=fast;roll_edit_batch(0);dirty=1;
}

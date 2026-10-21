#pragma bank 51
#include "api.h"
#include "sequencer_limits.h"
extern uint8_t seqbused;
void eval_seq_off_track(uint8_t c) BANKED;
void eval_seq_clamp_cursor(void) BANKED{uint8_t c=seqtrack,minimum=SEQ_NOTE_MINIMUM(c),maximum=seq_note_maximum(c);if(c==6)minimum=0;if(seqcursor[c]>=seqlength[c])seqcursor[c]=seqlength[c]-1;if(seqpitch[c]<minimum)seqpitch[c]=minimum;if(seqpitch[c]>maximum)seqpitch[c]=maximum;if(seqtop[c]>maximum)seqtop[c]=maximum;if(seqtop[c]<minimum+seqrows-1)seqtop[c]=minimum+seqrows-1;if(seqpitch[c]>seqtop[c])seqtop[c]=seqpitch[c];if(seqpitch[c]+seqrows-1<seqtop[c])seqtop[c]=seqpitch[c]+seqrows-1;}
static uint8_t selected_event(uint8_t *e){return e[1]&&seq_group_contains(e[0],e[1]-1);}
uint8_t roll_note_feedback(uint8_t c,const uint8_t *e,uint8_t erase) BANKED;
void roll_edit_batch(uint8_t enabled) BANKED;
uint8_t roll_group_add(uint8_t c,const uint8_t *e,uint16_t index) BANKED;
uint8_t roll_replace_feedback(uint8_t c,const uint8_t *old,const uint8_t *next,uint16_t index) BANKED;
void eval_seq_group_move(uint8_t edge) BANKED{uint8_t c=seqtrack,e[4],other[4],old[4],found=0,fast=seqdrawvalid,local=1;uint16_t i,j,dur,selected=0;int8_t dx=0,dy=0;int16_t at,pitch;
 if(local)fast=0;seqamoved=1;if(edge&J_LEFT)dx--;if(edge&J_RIGHT)dx++;if(edge&J_UP)dy++;if(edge&J_DOWN)dy--;
 if((int16_t)seqgroupx0+dx<0||(int16_t)seqgroupx1+dx>=seqlength[c]||(int16_t)seqgroupy0+dy<SEQ_NOTE_MINIMUM(c)||(int16_t)seqgroupy1+dy>seq_note_maximum(c))return;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(!selected_event(e))continue;found=1;at=e[0]+dx;pitch=(int16_t)e[1]+dy;dur=e[3]?e[3]:256;
  if(at<0||at+dur>seqlength[c]||pitch<SEQ_NOTE_MINIMUM(c)+1||pitch>seq_note_maximum(c)+1)return;
  selected++;mixfill();
 }if(!found)return;
 if(dx&&selected<seq_event_count(c))for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(!selected_event(e))continue;at=e[0]+dx;dur=e[3]?e[3]:256;
  for(j=0;j<seq_event_count(c);j++){seq_event_get(c,j,other);if(other[1]&&!selected_event(other)&&((!eval_mode(c)&&!evalpatch[c][EV_CHORD_HISTORY])||other[1]==e[1]+dy)&&at<other[0]+(other[3]?other[3]:256)&&other[0]<at+dur)return;}mixfill();
 }
 roll_edit_batch(1);if(!local)for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(selected_event(e)&&!roll_note_feedback(c,e,1)){fast=0;seqdrawvalid=0;}}for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(!selected_event(e))continue;if(seqplaying&&seqsource[c]==e[0])eval_seq_off_track(c);memcpy(old,e,4);e[0]+=dx;e[1]+=dy;if(!local&&!roll_group_add(c,e,i))fast=0;seq_event_put(c,i,e);mixfill();}
 seqgroupx0+=dx;seqgroupx1+=dx;seqgroupy0+=dy;seqgroupy1+=dy;seqaanchor+=dx;seqcursor[c]+=dx;seqpitch[c]+=dy;eval_seq_clamp_cursor();seqdrawvalid=fast?2:0;roll_edit_batch(0);dirty=1;
}

void eval_seq_group_resize(int8_t delta) BANKED {uint8_t c=seqtrack,e[4],old[4],fast=seqdrawvalid,local=eval_mode(seqtrack)||evalpatch[seqtrack][EV_CHORD_HISTORY];uint16_t i;int16_t n;
 if(local)fast=0;seqamoved=seqbused=1;
 if(!seq_length_step(seqaanchor+seq_duration_get(c,seqaanchor)-1,seqaanchor+seq_duration_get(c,seqaanchor)-1+delta))return;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if((e[1]&&seq_group_contains(e[0],e[1]-1))){n=(e[3]?e[3]:256)+delta;if(n<1||n>seqlength[c]-e[0])return;}mixfill();}
 roll_edit_batch(1);for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if((e[1]&&seq_group_contains(e[0],e[1]-1))){memcpy(old,e,4);e[3]=(e[3]?e[3]:256)+delta;if(!local&&!roll_replace_feedback(c,old,e,i))fast=0;seq_event_put(c,i,e);}mixfill();}
 seqdefaultdur[c]=seq_duration_get(c,seqaanchor);seqcursor[c]=seqaanchor+seqdefaultdur[c]-1;seqdrawvalid=fast;roll_edit_batch(0);dirty=1;
}

#pragma bank 51
#include "api.h"
#include "sequencer_limits.h"
void eval_seq_off_track(uint8_t c) BANKED;
void eval_seq_clamp_cursor(void) BANKED{uint8_t c=seqtrack,minimum=SEQ_NOTE_MINIMUM(c),maximum=seq_note_maximum(c);if(c==6)minimum=0;if(seqcursor[c]>=seqlength[c])seqcursor[c]=seqlength[c]-1;if(seqpitch[c]<minimum)seqpitch[c]=minimum;if(seqpitch[c]>maximum)seqpitch[c]=maximum;if(seqtop[c]>maximum)seqtop[c]=maximum;if(seqtop[c]<minimum+seqrows-1)seqtop[c]=minimum+seqrows-1;if(seqpitch[c]>seqtop[c])seqtop[c]=seqpitch[c];if(seqpitch[c]+seqrows-1<seqtop[c])seqtop[c]=seqpitch[c]+seqrows-1;}
static uint8_t selected_event(uint8_t *e){return e[1]&&seq_group_contains(e[0],e[1]-1);}
void eval_seq_group_move(uint8_t edge) BANKED{uint8_t c=seqtrack,e[4],other[4],found=0;uint16_t i,j,dur;int8_t dx=0,dy=0;int16_t at,pitch;
 seqamoved=1;if(edge&J_LEFT)dx--;if(edge&J_RIGHT)dx++;if(edge&J_UP)dy++;if(edge&J_DOWN)dy--;
 if((int16_t)seqgroupx0+dx<0||(int16_t)seqgroupx1+dx>=seqlength[c]||(int16_t)seqgroupy0+dy<SEQ_NOTE_MINIMUM(c)||(int16_t)seqgroupy1+dy>seq_note_maximum(c))return;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(!selected_event(e))continue;found=1;at=e[0]+dx;pitch=(int16_t)e[1]+dy;dur=e[3]?e[3]:256;
  if(at<0||at+dur>seqlength[c]||pitch<SEQ_NOTE_MINIMUM(c)+1||pitch>seq_note_maximum(c)+1)return;
  if(dx)for(j=0;j<seq_event_count(c);j++){seq_event_get(c,j,other);if(other[1]&&!selected_event(other)&&at<other[0]+(other[3]?other[3]:256)&&other[0]<at+dur)return;}mixfill();
 }if(!found)return;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(!selected_event(e))continue;if(seqplaying&&seqsource[c]==e[0])eval_seq_off_track(c);e[0]+=dx;e[1]+=dy;seq_event_put(c,i,e);mixfill();}
 seqgroupx0+=dx;seqgroupx1+=dx;seqgroupy0+=dy;seqgroupy1+=dy;seqaanchor+=dx;seqcursor[c]+=dx;seqpitch[c]+=dy;eval_seq_clamp_cursor();seqdrawvalid=0;dirty=1;
}

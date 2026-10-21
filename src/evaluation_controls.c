#pragma bank 50
#include "api.h"
#include "tones.h"
void mixer_pattern_changed(void) BANKED;
extern const uint8_t limits[26];
#include "user_presets.h"
extern uint8_t globalmod[10],seqgate[7],drumsynthvoice,pulsekickpatch[8],noisepatch[2][5];
#include "stripped_ui.h"
void eval_input(uint8_t p,uint8_t e) BANKED {uint8_t c=eval_instrument(),id=0,n,col=1,*cell,hi;int16_t d=delta(e),v;
 if(page==2){c=0;n=10;}else{n=eval_tab==3?5:tone_count(c);id=eval_tab==3?0:tone_id(c,eval_row);if(id==102)col=3;}
 if(page!=2&&(p&J_SELECT)&&(e&(J_LEFT|J_RIGHT))){eval_tab=eval_tab==3?0:c<3?3:0;eval_row=eval_col=0;dirty=1;return;}
 if(page==17&&(e&J_SELECT)){drumsynthvoice=(drumsynthvoice+1)%3;eval_row=eval_col=0;dirty=1;return;}
 if(!(p&(J_A|J_B))){if(e&J_UP)eval_row=eval_row?eval_row-1:n-1;if(e&J_DOWN)eval_row=(eval_row+1)%n;if(e&J_LEFT)eval_col=eval_col?eval_col-1:col-1;if(e&J_RIGHT)eval_col=(eval_col+1)%col;dirty=1;return;}
 if(page!=2&&eval_tab!=3&&id>=103&&id<=105&&(e&(J_A|J_B))&&!d){tone_user_open(id-103);return;}
 if(!d){if(!(e&(J_A|J_B)))return;if(page==2&&(eval_row==7||eval_row==9))d=globalmod[eval_row]?-1:1;else if(page!=2&&id==102&&eval_col==2)d=evalpatch[c][EV_SOURCES]&1?-1:1;else if(eval_tab==3&&(eval_row==0||eval_row==3))d=evalpatch[c][eval_row==0?EV_CLOCK:EV_RETRIGGER]?-1:1;else if(page!=2&&eval_tab!=3&&(id==2||id==5||id==8||id==19||c<7&&c>=5&&id==3||c==7&&id==7))d=native_value(id)?-1:1;else return;}
 if(page==2){id=eval_row;hi=id==2?64:id==4?4:id==5?128:id==6?16:id==7||id==9?1:id==8?2:255;if(id==6&&(e&(J_LEFT|J_RIGHT)))d=d>0?-1:1;else if(id>=4&&id!=5)d=d>0?1:-1;globalmod[id]=clamp(globalmod[id]+d,0,hi);}
 else if(eval_tab==3){id=eval_row;id=id==0?EV_CLOCK:id==1?EV_DIV:id==2?EV_TIMING:id==3?EV_RETRIGGER:EV_ORDER;if(id==EV_DIV&&evalpatch[c][EV_CLOCK]){v=(evalpatch[c][6]|((uint16_t)evalpatch[c][7]<<8))+d;v=clamp(v,1,32767);evalpatch[c][6]=v;evalpatch[c][7]=v>>8;}else evalpatch[c][id]=clamp(evalpatch[c][id]+(d>0?1:-1),0,id==EV_DIV?16:id==EV_ORDER?10:id==EV_TIMING?2:1);}
 else if(id==102){if(eval_col==1)evalpatch[c][EV_DEPTH]=(int8_t)clamp((int8_t)evalpatch[c][EV_DEPTH]+d,-127,127);else if(eval_col==2)evalpatch[c][EV_SOURCES]=d>0;else if(c<3)fine_edit(c,d);else{v=(int16_t)(evalpatch[c][EV_FINE]|((uint16_t)evalpatch[c][EV_FINE+1]<<8))+d;v=clamp(v,-2047,2047);evalpatch[c][EV_FINE]=v;evalpatch[c][EV_FINE+1]=v>>8;}}
 else if(id==1&&c<2||id==15&&c==2||c==3&&id==1||c>=5&&id==0){cell=c<4?&param[c][id]:c==7?pulsekickpatch:noisepatch[c-5];hi=c==2?3:15;v=evalpatch[c][EV_LEVEL_MODE]==128?-1:c==2?(*cell?4-*cell:0):*cell;v=clamp(v+d,-1,hi);evalpatch[c][EV_LEVEL_MODE]=v<0?128:0;if(v>=0)*cell=c==2?(v?4-v:0):v;}
 else if(id==106){v=evalpatch[c][EV_PAN]&128?evalpatch[c][EV_PAN]&3:3;evalpatch[c][EV_PAN]=128|clamp(v+d,0,3);}
 else if(c<4){param[c][id]=clamp(param[c][id]+d,0,limits[id]);liveparam(c,id);}else{cell=c==7?pulsekickpatch+id:noisepatch[c-5]+id;hi=c==7?kickmax[id]:noisemax[id];*cell=clamp(*cell+d,c==7&&id==1?36:0,hi);}
 mixer_pattern_changed();dirty=1;seqirqdirty=1;
}

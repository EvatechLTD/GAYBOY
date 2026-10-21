#pragma bank 37
#include "api.h"
#include "evaluation.h"
#include "ui_fields.h"
#include "sequencer_limits.h"
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
#include "mixer_shared.h"
extern uint8_t mixer_layout_dirty;
static const char * const names[]={"PULSE1","PULSE2","WAVE","NOISE","MONOSYNTH","HIHAT","SNARE","PULSEKICK"};
static int16_t delta(uint8_t edge){return edge&J_UP?1:edge&J_DOWN?-1:edge&J_RIGHT?10:edge&J_LEFT?-10:0;}
static void tip(const char *a,const char *b){text(0,16,a,0);text(0,17,b,0);}
void eval_status(void) BANKED {if(seqvelocityhidden){memset(canvas+340,0,20);text(0,17,seqeventfull?"PATTERN FULL":eval_message==1?"VOICE FULL: DIM OFF":eval_message==2?"MONO: LOWEST PLAYS":seqmuted&(1<<seqtrack)?"TRACK MUTED":seqplaying?"SELECT+A TO STOP":"SELECT+A TO PLAY",0);}}
void eval_global_render(void) BANKED {uint8_t i;static const uint8_t tracks[]={0,1,2,3,6};memset(canvas,0,360);memset(canvas,96,20);text(0,0,"GLOBAL SETTINGS",1);text(0,3,"PAGE MENU",eval_row==0);for(i=0;i<5;i++){text(0,5+i,names[tracks[i]],eval_row==i+1);text(14,5+i,eval_hidden&(1<<tracks[i])?"HIDE":"SHOW",eval_row==i+1);}text(0,12,"WAVEFORMS",eval_row==6);text(15,12,eval_hidden&128?"OFF":"ON",eval_row==6);tip(eval_row==6?"SHOW WAVE PREVIEWS":eval_row?"HIDE SEQUENCER PAGE":"CUSTOMIZE PAGE MENU","A/B OR HOLD+ARROWS");}
void eval_global_input(uint8_t p,uint8_t edge) BANKED {static const uint8_t tracks[]={0,1,2,3,6};int16_t d=delta(edge);uint8_t mask;if(!(p&(J_A|J_B))){if(edge&J_UP)eval_row=eval_row?eval_row-1:6;if(edge&J_DOWN)eval_row=(eval_row+1)%7;}else if(edge&(J_A|J_B)||d){if(!eval_row){pageconfig=1;}else{mask=eval_row==6?128:1<<tracks[eval_row-1];if(!d)eval_hidden^=mask;else if(d>0)eval_hidden&=~mask;else eval_hidden|=mask;previewshape=255;if(sparse_enabled==1){pool_root[122]='V';pool_root[123]=eval_hidden;mixer_layout_dirty=1;}}}dirty=1;}

void seq_track_view(void) BANKED{uint8_t c=seqtrack,e[4],low=255,maximum=seq_note_maximum(c);uint16_t i,n;if(c==6)return;n=seq_event_count(c);for(i=0;i<n;i++){seq_event_get(c,i,e);if(e[1]&&e[1]-1<low)low=e[1]-1;if(!(i&15))mixfill();}if(low==255)low=36;if(low<SEQ_NOTE_MINIMUM(c))low=SEQ_NOTE_MINIMUM(c);if(low>maximum)low=maximum;seqpitch[c]=low;seqtop[c]=low>maximum-(seqrows-1)?maximum:low+seqrows-1;seqdrawvalid=0;}


extern uint8_t pulsekickpatch[8],noisepatch[2][5];
void eval_preview_channel(uint8_t c) BANKED{uint8_t i,x,y,a,prev=8,shape=c<2?3:c==3?31:0,width=16;uint16_t off,seed=123;
 if(eval_hidden&128)return;
 if(c<2){const uint8_t widths[4]={4,8,16,24};width=widths[param[c][0]&3];}else if(c==2)shape=param[2][14]&31;
 if(c>=5)shape=c==7?3:31;
 if(shape==31)width=c==3?(param[3][18]|(param[3][19]<<4)|(param[3][20]<<5)):c<7?(noisepatch[c-5][1]|(noisepatch[c-5][3]<<4)|(noisepatch[c-5][2]<<5)):0;
 for(i=0;i<40;i++)canvas[20+i]=i<32?64+i:160+i-32;if(previewshape==(shape|128)&&previewwidth==width)return;previewshape=shape|128;previewwidth=width;
 memset(wavepixels,0,640);
 for(x=0;x<160;x++){i=x/5;if(shape==31){if(!(x%(1+((width&15)>>1)))){uint8_t bit=(seed^(seed>>1))&1;seed=(seed>>1)|((uint16_t)bit<<14);if(width&16)seed=(seed&~64U)|(bit<<6);a=seed&1?15:0;}else a=15-prev;}else if(shape==3)a=i<width?15:0;else{a=monowaves[shape][i>>1];a=i&1?a&15:a>>4;}y=2+(uint16_t)(15-a)*11/15;
  do{off=(uint16_t)(prev>>3)*320+(uint16_t)(x>>3)*16+(prev&7)*2;wavepixels[off]|=128>>(x&7);wavepixels[off+1]=wavepixels[off];if(prev==y)break;prev+=prev<y?1:-1;}while(1);
 }
 for(i=0;i<40;i++){uint8_t tile=i<32?64+i:160+i-32;ui_upload_tile(tile,wavepixels+(uint16_t)i*16,0);canvas[20+i]=tile;if(!(i&7))mixfill();}
}

uint8_t eval_value_named(uint8_t c,uint8_t id,uint8_t row,uint8_t inv) BANKED {uint8_t v=c<4&&id<26?param[c][id]:0;const char *s=0;
 if(id==100)s=eval_mode(c)==1?"ARP":"MONO";
 else if(id>=103&&id<=105)s=">";else if(id==101)s=eval_mode(0)==2?"ON":"OFF";
 else if(c<4){if((id==1||id==15)&&evalpatch[c][EV_LEVEL_MODE]==128)s="ADSR";else if(id==0&&c<2){const char *duties[]={"12.5%","25%","50%","75%"};s=duties[v&3];}else if(id==2)s=v?"RISE":"FALL";else if(id==5)s=v?"DOWN":"UP";else if(id==19)s=v?"7 BIT":"15 BIT";else if(id==8||id==9||id==11||id==13||id==17||id==22||id==23)s=v?"ON":"OFF";else if(id==14)s=monowavenames[v&31];else if(id==21){const char *pan[]={"OFF","RIGHT","LEFT","BOTH"};s=pan[v&3];}}
 else if(c>=5&&id==0&&evalpatch[c][EV_LEVEL_MODE]==128)s="ADSR";else if(c>=5&&id==106){const char *pan[]={"OFF","RIGHT","LEFT","BOTH"};s=pan[evalpatch[c][EV_PAN]&128?evalpatch[c][EV_PAN]&3:3];}else if(c<7&&id==3)s=noisepatch[c-5][3]?"ON":"OFF";
 else if(c==7&&id==1){uint8_t note=pulsekickpatch[1],oct=note/12;char label[5];if(note<36)s="MIN";else{label[0]="CCDDEFFGGAAB"[note%12];label[1]=(0x54A&(1U<<(note%12)))?'#':' ';label[2]='0'+oct-1;label[3]=0;field_text(12,row,8,label,inv,1);return 1;}}else if(c==7&&id==2){const char *duties[]={"12.5%","25%","50%","75%"};s=duties[pulsekickpatch[2]&3];}else if(c==7&&id==7)s=pulsekickpatch[7]?"DOWN":"UP";
 if(s){field_text(12,row,8,s,inv,1);return 1;}return 0;
}

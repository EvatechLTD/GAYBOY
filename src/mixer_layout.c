#pragma bank 38
#include "api.h"
#include "smooth_playback.h"
#include "ui_fields.h"
#include "mixer_shared.h"
#include "mixer_drum_names.h"
#include "sparse_store.h"
#include "link_control.h"
extern uint8_t mixer_hidden[8],layout_cursor,mixer_device;
extern uint8_t mixer_layout_dirty,sticky_start;
void mixer_layout_load(void) BANKED {memset(mixer_hidden,0,8);linkpair=mixer_device=0;if(pool_root[118]=='M'){memcpy(mixer_hidden,pool_root+110,8);linkpair=pool_root[120]==1;mixer_device=pool_root[121]==1;}eval_hidden=pool_root[122]=='V'?pool_root[123]:128;sticky_start=pool_root[124]==1;smooth_playback_enabled=pool_root[125]=='S'&&pool_root[126]==1;mixer_layout_dirty=0;}
void mixer_layout_service(void) BANKED {memcpy(pool_root+110,mixer_hidden,8);pool_root[118]='M';pool_root[119]=1;pool_root[120]=linkpair;pool_root[121]=mixer_device;if(pool_commit())mixer_layout_dirty=0;}
static const char * const linked_tracks[7]={"P3","P4","W3","N2","M2","W4","D2"};
static const char * const tracks[7]={"P1","P2","WV","N","","","DR"};
static uint8_t layout_hidden(uint8_t id){return mixer_hidden[(mx.focus==5?4:0)+(id>>3)]&(1U<<(id&7));}
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
static void num(uint8_t x,uint8_t y,uint8_t n,uint8_t inv){char s[4];s[0]='0'+n/100;s[1]='0'+n/10%10;s[2]='0'+n%10;s[3]=0;text(x,y,s,inv);}
static uint8_t layout_id(uint8_t row){return row<3?row:row==3?6:row<7?row+13:row;}
void mixer_layout_render(void) BANKED{uint8_t i,start=layout_cursor>5?layout_cursor-5:0;char label[17];if(start>7)start=7;
 memset(canvas,0,360);memset(canvas,96,20);text(0,0,mx.focus==5?"LINK LAYOUT":"LOCAL LAYOUT",1);
 for(i=start;i<start+10;i++){uint8_t row=3+i-start,id=layout_id(i);num(0,row,i+1,layout_cursor==i);
  if(id<7)text(4,row,mx.focus==5?linked_tracks[id]:tracks[id],layout_cursor==i);
  else if(id<20)text(4,row,mixer_drum_name(mx.focus==5?linkmirror.kit:drumkit,id-7),layout_cursor==i);
  else {if(mx.focus==5){memcpy(label,linkmirror.names[i-20],16);label[16]=0;}else getname(i-20,label);text(4,row,label[0]?label:"PAD",layout_cursor==i);}
  text(16,row,layout_hidden(id)?"HIDE":"SHOW",layout_cursor==i);mixfill();
 }
 text(0,14,"B+ARROWS SHOW/HIDE",0);text(0,15,"RELEASE B NAVIGATES",0);text(0,17,"SELECT CLOSE",0);
}

extern uint8_t syncrole;
static const char * const settings_modes[]={"OFF","GAYBOY","LSDJ","ARDUBOY","PO","GATE","TWINK"};
void mixer_settings_open(void) BANKED {mx.focus=mx.edit=0;layout_cursor=0;mx.error=0;}
void mixer_settings_render(void) BANKED {uint8_t i;static const char * const labels[]={"MIXER VIEW","PAIR PATS","SYNC TYPE","SYNC ROLE","LOCAL LAYOUT","LINK LAYOUT","BACK TO MIXER"};
 if(mx.edit){mixer_layout_render();return;}
 memset(canvas,0,360);memset(canvas,96,20);text(0,0,"MIXER SETTINGS",1);
 for(i=0;i<7;i++)field_text(0,2+i*2,i<4?12:20,labels[i],mx.focus==i,0);
 field_text(12,2,8,mixer_device?"LINK":"LOCAL",mx.focus==0,1);field_text(12,4,8,linkpair?"ON":"OFF",mx.focus==1,1);field_text(12,6,8,settings_modes[syncmode],mx.focus==2,1);
 field_text(12,8,8,syncmode==1&&!syncrole?"AUTO":syncslave?"SLAVE":"MASTER",mx.focus==3,1);
 text(0,16,mx.focus==0?(mixer_device?"SHOW PAIRED DEVICE":"SHOW LOCAL DEVICE"):mx.focus==1?(linkpair?"LAUNCH PADS TOGETHER":"LAUNCH PADS SEPARATE"):mx.focus==2?settings_modes[syncmode]:mx.focus==3?(syncmode==1&&!syncrole?"AUTOMATIC CLOCK ROLE":syncslave?"FOLLOW EXTERNAL CLOCK":"SEND MASTER CLOCK"):mx.focus==4||mx.focus==5?"HIDE MIXER ITEMS":"RETURN TO MIXER",0);text(0,17,"A/B+ARROWS EDIT",0);
}
static void settings_adjust(int8_t delta){int8_t current,target;
 if(!mx.focus){mixer_device=delta>0;mixer_layout_dirty=1;if(mixer_device&&syncmode==1&&!syncslave&&!seqplaying&&!linkstate)link_begin();}
 else if(mx.focus==1&&!link_pair_phase){linkpair=delta>0;mixer_layout_dirty=1;}
 else if(mx.focus==2||mx.focus==3){current=mx.focus==2?syncmode:syncmode==1?syncrole:syncslave;target=current+delta;if(target<0)target=0;if(target>(mx.focus==2?6:syncmode==1?2:1))target=mx.focus==2?6:syncmode==1?2:1;while(current!=target){sync_setting_edit(mx.focus-2,current<target?J_RIGHT:J_LEFT);current+=current<target?1:-1;}}
}
void mixer_settings_input(uint8_t p,uint8_t edge) BANKED {if(!edge)return;uint8_t device,*cell,mask,id;int8_t d=edge&J_UP?1:edge&J_DOWN?-1:edge&J_RIGHT?10:edge&J_LEFT?-10:0;
 if(mx.edit){device=mx.focus==5;if(edge&J_SELECT){mx.edit=0;dirty=1;return;}id=layout_id(layout_cursor);cell=mixer_hidden+device*4+(id>>3);mask=1U<<(id&7);
  if((edge&(J_A|J_B))&&!(p&(J_UP|J_DOWN|J_LEFT|J_RIGHT))){*cell^=mask;mixer_layout_dirty=1;}
  else if(p&(J_A|J_B)){if(d){if(d>0)*cell&=~mask;else *cell|=mask;mixer_layout_dirty=1;}}
  else{if(edge&J_UP)layout_cursor=layout_cursor?layout_cursor-1:16;if(edge&J_DOWN)layout_cursor=(layout_cursor+1)%17;}
 }else{
  if(edge&J_SELECT){page=18;mixer_open();dirty=1;return;}
  if((edge&(J_A|J_B))&&!(p&(J_UP|J_DOWN|J_LEFT|J_RIGHT))){if(mx.focus>=4){if(mx.focus==6){page=18;mixer_open();}else{mx.edit=1;layout_cursor=0;}}else if(mx.focus<2)settings_adjust((mx.focus?linkpair:mixer_device)?-1:1);else if(mx.focus==3&&syncmode!=1)settings_adjust(syncslave?-1:1);}
  else if(p&(J_A|J_B)){if(d)settings_adjust(d);}
  else{if(edge&J_UP)mx.focus=mx.focus?mx.focus-1:6;if(edge&J_DOWN)mx.focus=(mx.focus+1)%7;}
 }mx.padcache=0;dirty=1;
}

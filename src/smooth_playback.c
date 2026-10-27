#pragma bank 37
#include "api.h"
#include "smooth_playback.h"
#include "song_link.h"
uint8_t smooth_playback_requested,smooth_playback_active,smooth_playback_preparing;
static uint8_t saved_lcdc,saved_oam;
/* A one-shot transport request, never a saved/global playback preference. */
void smooth_playback_start(void) BANKED {
 if(seqplaying)return;
 if(syncmode==1){pattern_link_request();return;}
 smooth_playback_requested=1;seq_transport();smooth_playback_requested=0;
}
void smooth_playback_begin(void) BANKED {
 uint8_t row;uint16_t frame,now;
 if(smooth_playback_active)return;
 saved_lcdc=LCDC_REG;saved_oam=_shadow_OAM_base;
 smooth_playback_preparing=smooth_playback_active=1;
 /* Leave LCD/VBlank running; upload the entire static screen before music. */
 _shadow_OAM_base=0;LCDC_REG&=~0x23;
 memset(canvas,0,360);{const char *text="BUFFERING";for(row=0;text[row];row++)canvas[160+row]=text[row]-32;}
 for(row=0;row<18;row++){ui_upload_map(0x9800U+(uint16_t)row*32,canvas+(uint16_t)row*20,20);mixfill();}
 memcpy(visible,canvas,360);LCDC_REG|=1;
 /* Two VBlanks guarantee a complete visible scanout, whichever scanline
    the upload finished on. Musical time remains stopped throughout. */
 __critical{frame=sys_time;}
 do{mixfill();__critical{now=sys_time;}}while((uint16_t)(now-frame)<2);
}
void smooth_playback_ready(void) BANKED {uint8_t i;uint16_t frame,now;const char *text="START+SELECT TO STOP";
 if(!smooth_playback_active)return;
 memset(canvas+160,0,20);for(i=0;text[i];i++)canvas[160+i]=text[i]-32;
 ui_upload_map(0x9900U,canvas+160,20);memcpy(visible+160,canvas+160,20);
 /* Finish this last status upload before arming the musical clock. */
 __critical{frame=sys_time;}do{mixfill();__critical{now=sys_time;}}while((uint16_t)(now-frame)<2);
}
void smooth_playback_update(void) BANKED {
 if(seqplaying||smooth_playback_preparing){
  if(!smooth_playback_active)smooth_playback_begin();
 }else if(smooth_playback_active){
  smooth_playback_active=smooth_playback_preparing=0;
  LCDC_REG=saved_lcdc;_shadow_OAM_base=saved_oam;
  *(uint8_t *)0xA475=0;*(uint8_t *)0xA4D0=0;
  if(page==18)mixer_open();seqdrawvalid=0;dirty=1;
 }
}

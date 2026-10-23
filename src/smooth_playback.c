#pragma bank 37
#include "api.h"
#include "smooth_playback.h"
uint8_t smooth_playback_enabled,smooth_playback_active;
static uint8_t saved_lcdc,saved_oam;
void smooth_playback_update(void) BANKED {
 if(smooth_playback_enabled&&seqplaying){
  if(smooth_playback_active)return;
  saved_lcdc=LCDC_REG;saved_oam=_shadow_OAM_base;
  /* Keep LCD timing/VBlank alive for clocks and joypad sampling. Only the
     background/window/sprites and automatic OAM transfer are disabled. */
  _shadow_OAM_base=0;LCDC_REG&=~0x23;smooth_playback_active=1;
 }else if(smooth_playback_active){
  smooth_playback_active=0;LCDC_REG=saved_lcdc;_shadow_OAM_base=saved_oam;
  seqdrawvalid=0;dirty=1;
 }
}

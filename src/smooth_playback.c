#pragma bank 37
#include "api.h"
#include "smooth_playback.h"
#include "mixer_shared.h"
#include "link_control.h"
void mixer_open(void) BANKED;
uint8_t smooth_playback_enabled,smooth_playback_active;
uint8_t smooth_playback_button,smooth_playback_target;
static uint8_t saved_lcdc,saved_oam;
extern uint16_t seqdeadline;
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inverse){
 uint8_t c;while(*s&&x<20){c=*s++;if(c>='a'&&c<='z')c-=32;if(c<32||c>95)c='?';canvas[(uint16_t)y*20+x++]=c-32+(inverse?96:0);}
}
static void quant_text(void){
 const char *q=mx.quant==0?"NOW":mx.quant==6?"1/16":mx.quant==1?"1/8":mx.quant==2?"1/4":mx.quant==3?"1/2":mx.quant==5?"LONG":"1/1";
 memset(canvas+300,0,20);text(0,15,"QUANT",0);text(6,15,q,0);
}
static void legend(void){
 uint8_t i;char name[17];memset(canvas,0,360);memset(canvas,96,20);text(2,0,"SMOOTH PLAYBACK",1);
 text(5,2,"1",0);text(5,3,"^",0);text(1,4,"4 < + > 2",0);text(5,5,"V",0);text(5,6,"3",0);
 text(14,3,"(B) 5",0);text(14,5,"(A)",0);text(12,6,"UP/DN Q",0);text(0,8,"--------------------",0);
 for(i=0;i<5;i++){canvas[(uint16_t)(9+i)*20]='1'+i-32;getname(i,name);if(i==mx.slot&&mx.name[0])memcpy(name,mx.name,17);text(2,9+i,name[0]?name:"EMPTY",0);}
 quant_text();text(0,16,"HOLD PAD TO REPEAT",0);text(0,17,"SELECT+A STOP",0);
 for(i=0;i<18;i++){ui_upload_map(0x9800U+(uint16_t)i*32,canvas+(uint16_t)i*20,20);memcpy(visible+(uint16_t)i*20,canvas+(uint16_t)i*20,20);mixfill();}
}
void smooth_playback_input(uint8_t p,uint8_t edge) BANKED {
 uint8_t button=0,target=255,q;
 if((p&J_SELECT)&&(edge&J_A)){mixer_prepare_cancel();seq_transport();return;}
 if((p&J_SELECT)&&(edge&J_START)){mixer_prepare_cancel();panic();return;}
 if(p&(J_SELECT|J_START))return;
 if(!edge&&linkpair&&MIXER_LINK_AVAILABLE&&mx.quant&&mx.pending==255&&!mx.error&&!link_pair_phase&&!mixer_prepare_busy()&&
    (((p&J_A)&&(p&(J_UP|J_DOWN)))||((p&smooth_playback_button)&&smooth_playback_target==mx.slot))){mixer_launch_request(mx.slot,0);return;}
 if((p&J_A)&&(p&(J_UP|J_DOWN))&&(edge&(J_A|J_UP|J_DOWN))){
  q=mx.quant;mx.quant=(p&J_UP)?(q==6?6:MIXER_QUANT_DOWN(q)):MIXER_QUANT_UP(q);
  if(syncmode&&syncslave&&!mx.quant)mx.quant=6;
  if(mx.quant!=q){seqdeadline=1;quant_text();ui_upload_map(0x9800U+15*32,canvas+300,20);memcpy(visible+300,canvas+300,20);}
  return;
 }
 if(edge&J_B){button=J_B;target=4;}
 else if(edge&J_RIGHT){button=J_RIGHT;target=1;}
 else if(edge&J_LEFT){button=J_LEFT;target=3;}
 else if(!(p&J_A)&&(edge&J_UP)){button=J_UP;target=0;}
 else if(!(p&J_A)&&(edge&J_DOWN)){button=J_DOWN;target=2;}
 if(target<5){smooth_playback_button=button;smooth_playback_target=target;mx.error=0;mixer_launch_request(target,0);}
}
void smooth_playback_update(void) BANKED {
 if(smooth_playback_enabled&&seqplaying){
  if(smooth_playback_active)return;
  saved_lcdc=LCDC_REG;saved_oam=_shadow_OAM_base;
  /* Render the legend once; retain LCD timing/input and suppress sprites,
     automatic OAM transfer and all normal frame-by-frame UI work. */
  _shadow_OAM_base=0;LCDC_REG&=~0x23;smooth_playback_button=0;smooth_playback_active=1;
  legend();LCDC_REG=(saved_lcdc&~0x22)|1;
 }else if(smooth_playback_active){
  smooth_playback_active=0;LCDC_REG=saved_lcdc;_shadow_OAM_base=saved_oam;
  smooth_playback_button=0;seqdrawvalid=0;*(uint8_t *)0xA475=0;*(uint8_t *)0xA4D0=0;
  if(page==18)mixer_open();dirty=1;
 }
}

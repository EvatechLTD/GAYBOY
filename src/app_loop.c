#pragma bank 60
#include "api.h"
#include "native_sync.h"
#include "mod_bypass.h"
#include "link_control.h"
#include "mixer_shared.h"
#include "smooth_playback.h"
#include "song_mode.h"
#include "song_link.h"
extern volatile uint8_t padqueue[32],padwrite,padread,padsampled;
extern volatile uint8_t drum_irq_pending;
extern uint16_t lastframe;
extern uint8_t mixer_layout_dirty;
void input_vblank(void);
void drum_irq_service(void) BANKED;
void seq_native_touch(void) NONBANKED;
void roll_feedback_service(void) BANKED;
void mixer_layout_service(void) BANKED;
void mixer_fader_service(void) BANKED;
void editbuffer_service(void) BANKED;
void editbuffer_priority_service(void) BANKED;
uint8_t seq_twink_input_service(void) BANKED;
/* Foreground control belongs in banked ROM. The boot/IRQ entries stay fixed. */
void app_run(void) BANKED {uint8_t p,edge,frame=0;sync_init();intro_run();DISPLAY_OFF;NR52_REG=0x80;globals();drum_init();startup();eval_defaults();ui_loading_begin();mixer_boot();navblocked=1;navchoice=8;lastpad=J_START;ui_init();DISPLAY_ON;
 disable_interrupts();padsampled=lastpad;add_VBL(input_vblank);add_SIO(serial_isr);add_TIM(engine_timer);SB_REG=0;SC_REG=0x80;set_interrupts(VBL_IFLAG|SIO_IFLAG|TIM_IFLAG);enable_interrupts();
 /* Preparation runs on Mixer; its private journal commit (phase18 atACB4)
    also finishes off-page. Avoid an idle bank round-trip on other pages. */
 *(uint8_t *)0xA427=0;lastframe=sys_time;{uint16_t inputframe=sys_time;uint8_t end;while(1){if(!(syncmode==SYNC_TWINK&&seqplaying&&padread!=padwrite&&seq_twink_input_service()))service();editbuffer_service();if(sparse_enabled)sparse_service();else if(page==18||link_ui_hold||*(volatile uint8_t *)0xACB4==18)mixer_prepare_service();if(inputframe!=sys_time||padread!=padwrite){__critical{inputframe=sys_time;end=padwrite;p=padsampled;}
 if(syncmode>1&&syncslave&&seqplaying)sync_advance(0);
 if(syncmode==1&&!song_link_active)link_service();
 if(mixer_layout_dirty&&!seqplaying)mixer_layout_service();
 if(padread==end){if(!link_ui_hold){ui_input(p,0);if(p&&page!=18&&!smooth_playback_active)seq_native_touch();}lastpad=p;}
 else while(padread!=padwrite){p=padqueue[padread];padread=(padread+1)&31;edge=p&~lastpad;if(!link_ui_hold||((p&(J_SELECT|J_START))==(J_SELECT|J_START)&&(edge&(J_SELECT|J_START)))){ui_input(p,edge);if(page!=18&&!smooth_playback_active)seq_native_touch();}lastpad=p;service();}
 if(!syncmode&&seqplaying&&!seqservicing&&seqirqdirty&&!seqirqready&&!seqirqfired){seqservicing=1;seq_irq_prepare();seqservicing=0;}
 /* Release/edit edges above may have made a playback snapshot eligible.
    Give its bounded prep batch priority before starting foreground drawing. */
 editbuffer_priority_service();if(drum_irq_pending)drum_irq_service();
 if(smooth_playback_active&&!seqplaying&&!smooth_playback_preparing)smooth_playback_update();
 if(smooth_playback_active)continue;
 /* Settings pages change on input. Periodic refresh is only for live views. */
 if(!link_ui_hold){if(!(page==18&&seqplaying&&sparse_enabled&&mx.pending<8)&&(dirty||(!navopen&&(page==0||page==9)&&!(++frame&3)))){dirty=0;ui_render();}if(seqplaying&&(syncmode==1||syncmode==SYNC_TWINK)&&padread!=padwrite)continue;ui_flush();if(page==8)roll_feedback_service();else if(page==18)mixer_fader_service();}}
 }
}
}

#pragma bank 60
#include "api.h"
#include "native_sync.h"
#include "smooth_playback.h"
#include "mixer_shared.h"
#include "twink_schedule.h"
extern uint16_t seqwholeunits,seqclock;
extern __at (0xAC6A) uint16_t seqcachedbpm;
extern __at (0xAC6C) uint16_t seqstepunits;
extern __at (0xAC6E) uint16_t seqgateunits[7];
extern __at (0xACF0) uint8_t seqcachedgate[7];
extern uint8_t seqgate[7];
void seq_gates(void) BANKED {uint8_t c,busy=seqservicing;memset(seqgate,100,SEQ_TRACKS);if(seqwholeunits&&seqcachedbpm==seqbpm){for(c=0;c<SEQ_TRACKS;c++)if(seqcachedgate[c]!=seqgate[c])break;if(c==SEQ_TRACKS)return;}seqservicing=1;seqstepunits=15360U/seqbpm;seqwholeunits=(245760UL+seqbpm-1)/seqbpm;for(c=0;c<SEQ_TRACKS;c++){seqgateunits[c]=seqstepunits;seqcachedgate[c]=seqgate[c];mixfill();}seqcachedbpm=seqbpm;seqservicing=busy;}
static uint8_t seq_track_neighbor(uint8_t track,uint8_t right){

 return right?(track+1)%7:(track?track-1:6);
}
uint8_t seq_track_page(uint8_t right) BANKED {uint8_t next=seqtrack,tries;
 for(tries=0;tries<7;tries++){next=seq_track_neighbor(next,right);if(eval_visible(next))return next;}return seqtrack;
}

void editirq_clock_reset(void) NONBANKED;
/* Configure a defined standalone epoch while every voice is still stopped.
   TIMA reload alone leaves the first interval dependent on DIV's low phase.
   Keep PCM's selected timer mode and leave all external sync clocks alone. */
void seq_clock_epoch(void) BANKED {uint8_t control;
 __critical {control=TAC_REG;if(!syncmode){TAC_REG=0;DIV_REG=0;}editirq_clock_reset();TIMA_REG=TMA_REG;IF_REG&=~TIM_IFLAG;seqclock=seqticks=seqfraction=0;seqplaying=1;if(!syncmode)TAC_REG=control;}
}

void seq_launch_events(void) BANKED;
void eval_seq_startup_prepare(void) BANKED;
void drum_irq_prepare(void) BANKED;
void seq_irq_prepare(void) BANKED;
extern uint8_t editbuffer_reading;
/* Cold native note packets belong before the shared GO, alongside drums.
   In local playback keep the established startup path until qualified. */
void seq_startup_prepare(void) BANKED {
 editbuffer_reading=1;eval_mod_configure();eval_seq_startup_prepare();drum_irq_prepare();
 if(syncmode)seq_irq_prepare();
 editbuffer_reading=0;
}
/* Both peers enter this short path only after preparing their normal live
   snapshots. The first note still uses the ordinary editable sequencer. */
void seq_prepared_start(void) BANKED {
 seqservicing=1;smooth_playback_preparing=0;
 if(syncmode==1||syncmode==SYNC_TWINK)syncstart=1;
 seq_clock_epoch();
 if(syncmode){sync_transport(1);if(!seqplaying){seqservicing=0;dirty=1;return;}}
 seq_launch_events();
}

uint8_t seq_top_entry(void) BANKED {uint8_t col=seqcursor[seqtrack]-seqbase;uint8_t width=seqtrack==6?136:144;uint16_t x=(seqtrack==6?24:16)+((uint16_t)col*width+width/2)/seqcols;return x<68&&seqtrack!=6?1:x<84?2:x<96?3:4;}

extern uint8_t editbuffer_ready,editbuffer_valid,editbuffer_reading;
extern volatile uint8_t drum_irq_active;
extern uint8_t midi_launch_enabled,seqrecordtrack,arp_active_mask;
extern volatile uint8_t padsampled;
uint8_t editirq_owned(uint8_t c) NONBANKED;
uint8_t arp_irq_valid(uint8_t c) NONBANKED;
uint8_t arp_irq_continue(uint8_t c) BANKED;
void eval_seq_phase_add(uint16_t phase) BANKED;
/* Already-executed IRQ notes must not be replayed as foreground catch-up.
   This path only advances the presentation/transport bookkeeping when every
   populated local lane has a proven autonomous owner and no handoff is due. */
static uint8_t twink_autonomous(void){
 uint8_t c;
 if(!seqplaying||seqbpm<30||seqbpm>240||syncmode!=SYNC_TWINK||!twink_scheduled||!twink_v2||twink_reply==0xD4||twink_reply==0xD5||!editbuffer_valid||editbuffer_ready||seqirqdirty||
    monomode||polymode||seqmode||waveengine==3||seqswing!=50||seqrecordtrack!=255||
    mx.pending!=255||midi_launch_enabled||(page==18&&!navopen&&mx.focus>=30&&mx.focus<35&&(padsampled&J_A)))return 0;
 for(c=0;c<SEQ_TRACKS;c++)if((c<3||c>=5)&&!seqlength[c])return 0;
 for(c=0;c<3;c++){
  if(seqgateleft[c])return 0;
  if(arp_active_mask&(1<<c)){
   if(!arp_irq_valid(c)||evalpatch[c][EV_CLOCK]||evalpatch[c][EV_DIV]!=4||evalpatch[c][EV_TIMING]||!arp_irq_continue(c))return 0;
  }
  if(!seq_event_count(c))continue;
  if(editirq_owned(c)||(arp_active_mask&(1<<c)))continue;
  return 0;
 }
 if(seq_event_count(6)&&!drum_irq_active)return 0;
 return 1;
}
uint8_t seq_twink_autonomous(void) BANKED {return twink_autonomous();}
uint8_t seq_twink_catchup(uint16_t ticks) BANKED {
 uint8_t c;uint16_t steps,pos,length,high,low,oldclock,delta;
 if(!twink_autonomous())return 0;
 /* 15360 = 60*256. Form the 24-bit elapsed product in two small
    pieces, then divide only its high sixteen bits. BPM<=240 bounds every
    intermediate below65536, even with the full uint16 tick backlog. */
 oldclock=seqclock;low=(uint16_t)(uint8_t)ticks*seqbpm;
 high=(ticks>>8)*seqbpm+(low>>8)+(oldclock>>8);
 low=(low&255)+(oldclock&255);high+=low>>8;
 steps=high/60;seqclock=((high-steps*60)<<8)|(uint8_t)low;
 delta=seqclock>=oldclock?seqclock-oldclock:seqclock+15360U-oldclock;
 eval_seq_phase_add(delta);
 if(steps){
  for(c=0;c<SEQ_TRACKS;c++)if((c<3||c>=5)){
   length=seqlength[c];pos=(uint16_t)seqposition[c]+steps;
   seqposition[c]=!(length&(length-1))?pos&(length-1):pos%length;
  }
  mx.boundary=(mx.boundary+steps)&15;seqswingphase^=steps&1;
  if(page==8)seqflushpending=1;
 }
 return 1;
}

/* Queued input may precede optional future refill when all audible events
   already have autonomous owners. Retire musical bookkeeping before the
   action; the normal main-loop service immediately follows that action. */
uint8_t seq_twink_input_service(void) BANKED {
 if(!twink_autonomous())return 0;
 seq_frame();return 1;
}

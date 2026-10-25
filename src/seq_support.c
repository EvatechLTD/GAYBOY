#pragma bank 60
#include "api.h"
#include "native_sync.h"
#include "smooth_playback.h"
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

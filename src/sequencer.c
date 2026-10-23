#pragma bank 10
#include "api.h"
#include "seq_live_note.h"
uint8_t native_edit_flush(void) BANKED;
uint8_t native_edit_service(void) BANKED;
extern uint8_t seqeditpreview,seqpreviewpinned;
uint8_t native_edit_feedback(void) BANKED;
uint8_t roll_preview_service(void) BANKED;
extern uint8_t editbuffer_reading;
void arp_irq_reset(void) NONBANKED;
uint8_t editirq_owned(uint8_t c) NONBANKED;
uint8_t editbuffer_active(void) BANKED;
void editbuffer_boundary(void) BANKED;
void editbuffer_reset(void) BANKED;
void native_velocity_edit(int8_t delta) BANKED;
void seq_brush_input(uint8_t edge) BANKED;
void seq_brush_reset(void) BANKED;
void drum_name_input(uint8_t p,uint8_t edge) BANKED;
void drum_velocity_input(uint8_t p,uint8_t edge) BANKED;
void drum_velocity_status(void) BANKED;
void roll_feedback_cancel(void) BANKED;
void roll_feedback_velocity_row(void) BANKED;
uint8_t roll_note_feedback(uint8_t c,const uint8_t *e,uint8_t erase) BANKED;
#include "sequencer_limits.h"
#include "sequencer.h"
#include "mixer_shared.h"
#include "link_control.h"
void mixer_pattern_changed(void) BANKED;
void seq_audition_stop(void) BANKED;
void seq_irq_launch(void) BANKED;
extern volatile uint8_t padread,padwrite;
void seq_native_launch_clear(void) BANKED;
/* Zero is a rest; notes 0..127 are stored as 1..128. Patterns are volatile. */

uint16_t seqlength[SEQ_TRACKS]={16,16,16,16,16,16,16};
uint8_t seqdefaultvel[SEQ_TRACKS]={100,100,100,100,100,100,100};
uint16_t seqdefaultdur[SEQ_TRACKS]={1,1,1,1,1,4,0};
uint8_t seqgate[SEQ_TRACKS]={100,100,100,100,100,100,100};
uint8_t seqposition[SEQ_TRACKS],seqcursor[SEQ_TRACKS];
uint8_t seqpitch[SEQ_TRACKS]={60,60,60,60,60,60,60},seqtop[SEQ_TRACKS]={71,71,71,71,71,71,71};
uint8_t seqowned[SEQ_TRACKS],seqsource[SEQ_TRACKS];
uint32_t seqgateleft[SEQ_TRACKS];
uint16_t seqbpm=120;
/* Zero follows each pattern; otherwise all patterns share this tempo. */
uint16_t seqglobalbpm;
uint16_t seqwholeunits;
uint8_t seqswing=50,seqswingphase;
uint16_t seqthreshold=15360U;
void seq_swing_step(void) BANKED;
void seq_swing_edit(int16_t delta) BANKED;
uint8_t seqvelocityhidden=1,seqviewinitialized;
uint8_t seqplaying,seqtrack,seqmode,seqfocus,seqedit,seqmuted,seqsolo,seqhead;
uint16_t seqclock;
volatile uint16_t seqticks;
uint16_t seqdeadline=1;
extern uint32_t noiseleft[2];
__at (0xACF0) uint8_t seqcachedgate[7];
__at (0xAC6A) uint16_t seqcachedbpm;
__at (0xAC6C) uint16_t seqstepunits;
__at (0xAC6E) uint16_t seqgateunits[7];
uint8_t seqflushpending=1,seqservicing;
uint8_t seqbeats=4,seqdenom=4,seqdrag,seqdragstart;
uint8_t seqgrid[64],seqmeterbeats,seqmeterdenom;
uint8_t seqscreen[360],seqdrawvalid,seqdrawplaying,seqdrawpos=255;
uint8_t seqselectused,seqbused,seqtilesready;
uint8_t seqauditionnote,seqauditiontrack;
uint8_t seqapending,seqamoved,seqaoffset;
uint8_t seqpopup;
/* Four free control bytes after the cached gate units preserve WRAM reserve. */
__at (0xAC7C) uint8_t seqpopupchoice;
__at (0xAC7D) uint8_t seqpopupstep;
__at (0xAC7E) uint8_t seqpopuppitch;
__at (0xAC7F) uint8_t seqpopuperror;
uint16_t seqaanchor;
uint8_t seqgrouptrack=255,seqgroupx0,seqgroupx1,seqgroupy0,seqgroupy1;
uint8_t seqrecordtrack=255,seqrecordstart,seqrecordvelocity;
uint16_t seqrecordlength;
uint8_t seqzoom=1,seqbase,seqcols=16,seqrows=17,seqheight=8,seqtilecount,seqtileoverflow;
const char seqshort[7][5]={"P1","P2","WV","NS","M5","MS","DRUM"};
const char seqchannels[7][7]={"PULSE1","PULSE2","WAVE","NOISE","MONO5","MS","DRUM"};
void seq_audio(void){mixfill();if(monomode&&expconfig[0])exp_fill();}
/* Keep drawing helpers in the same bank as the roll. */
void seq_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *dst=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*dst++=*s++-32+(inv?96:0);}
void seq_number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits,uint8_t inv){uint8_t i,d,*dst=canvas+(uint16_t)y*20+x;uint16_t place=digits==3?100:digits==2?10:1;for(i=0;i<digits;i++){d=0;while(n>=place){n-=place;d++;}dst[i]=16+d+(inv?96:0);place=place==100?10:1;}}
uint16_t seq_dur(uint8_t c,uint8_t s){return seq_duration_get(c,s); }
uint8_t seq_vel(uint8_t c,uint8_t s){return seq_velocity_get(c,s); }
#pragma opt_code_speed
uint8_t seq_enabled(uint8_t c){return c<3||c==6||(c==TWINK_TRACK&&syncmode==SYNC_TWINK);}
void seq_off(uint8_t c){uint8_t note;eval_seq_off(c);if(!syncmode&&!seqservicing&&c<2){__critical {seqirqready&=~(1<<c);seqirqfired&=~(1<<c);}seqirqdirty=1;}if(c==6){drum_stop();return;}note=seqowned[c];seqowned[c]=0;seqgateleft[c]=0;if(c==TWINK_TRACK){if(note)twink_note(0,note-1,0);return;}if(note){seq_audio();if(c<2&&!monomode)keyevent(c,note-1,0);else event(0x80|c,note-1,0);seq_audio();}}
void seq_clear_release(uint8_t track) BANKED {if(!editbuffer_reading&&editbuffer_active())return;seq_off(track);}

void seq_stop(void){uint8_t c;arp_irq_reset();seq_native_launch_clear();editbuffer_reset();if(!syncmode)seqirqready=seqirqfired=0;seqrecordtrack=255;seqrecordlength=0;seqplaying=0;if(syncmode)sync_transport(0);for(c=0;c<SEQ_TRACKS;c++)seq_off(c);seqplaying=0;seqswingphase=0;seq_swing_step();seqclock=seqticks=0;seqdeadline=1;if(!waveengine&&!monomode&&!(evalwaveactive&&expconfig[0]))TAC_REG=0;dirty=1;}
uint8_t seq_audible(uint8_t c){uint8_t solos=seqsolo&(syncmode==SYNC_TWINK?111:experimental_mode?95:79);if(drumsolomask&&(!seqmode||experimental_mode))solos|=64;return !(seqmuted&(1<<c))&&(!solos||(solos&(1<<c)));}
void seq_gates(void) BANKED;
uint32_t seq_gate_length(uint16_t units,uint8_t duration,uint8_t gate) BANKED;
void seq_pulse_fire(uint8_t c,const uint8_t *event) BANKED;
uint8_t resident_first_note(uint8_t c,uint8_t *e) BANKED;
void resident_first_clear(void) BANKED;
static uint8_t seqlaunching;
extern uint8_t resident_same_tones;
void seq_fire(uint8_t c){
 uint8_t data[4],s,note,v=0,oldvelocity=0,oldlevel=0,level,pan,keep=0;
 if(editirq_owned(c))return;
 if(c==3||c==seqrecordtrack)return;
 if(c<6&&!seq_event_count(c)){if(seqowned[c])seq_off(c);return;}
 if((c<3||c==4)&&seq_audible(c)&&eval_seq_fire(c))return;
 if(!experimental_mode&&(c==2||(c==5&&syncmode!=SYNC_TWINK))&&waveengine==3&&(mixrunning||drumon[0]|drumon[1]))return;
 if(!experimental_mode&&c==3&&drumnoiseowned)return;
 if(c==6){if(seq_audible(c))drum_fire(seqposition[c]);else if(seqlaunching)drum_stop();return;}
 s=seqposition[c];keep=seqlaunching?resident_first_note(c,data):2;if(!(keep==2?seq_note_event(c,s,data):keep)||!seq_audible(c)){if(seqlaunching)seq_off(c);return;}note=data[1];keep=0;
 if(seqcachedbpm!=seqbpm)seq_gates();
 if(c<2&&!monomode){seq_pulse_fire(c,data);return;}
 /* A same-patch wave note crossing a quantized boundary keeps its oscillator. */
 if(seqlaunching&&resident_same_tones&&!waveengine&&!evalwaveactive&&!(mono_owned&4)&&c==2&&keycount[2]<=1&&active[2]&&(NR52_REG&4)&&seqowned[2]==note&&velocity[2]==mixer_velocity(2,data[2])&&param[2][21]==mx.pan[2])keep=1;
 if(keep){}else if(c==3&&seqowned[c]&&keycount[c]<=1&&data[2]&&mx.level[c]){keycount[c]=0;seqowned[c]=0;seqgateleft[c]=0;}else if(c==2&&evalwaveactive&&seqowned[c]&&keycount[c]<=1){keycount[c]=0;seqowned[c]=0;seqgateleft[c]=0;}else if(experimental_mode&&c==4&&seqowned[c]&&monocount<=1){monocount=0;seqowned[c]=0;seqgateleft[c]=0;}else seq_off(c);
 seqsource[c]=s;seqowned[c]=note;
 if(data[3]==1)seqgateleft[c]=seqgateunits[c];
 /* Common sustained steps need only a shift. Preserve the generic order of
    operations for fractional gates, where early rounding changes length. */
 else if(seqgate[c]==100&&data[3]==2)seqgateleft[c]=(uint32_t)seqstepunits<<1;
 else if(seqgate[c]==100&&data[3]==4)seqgateleft[c]=(uint32_t)seqstepunits<<2;
 else if(seqgate[c]==100&&data[3]==8)seqgateleft[c]=(uint32_t)seqstepunits<<3;
 /* Round a whole note once; rounding each sixteenth cuts its tail early. */
 else if(seqgate[c]==100&&data[3]==16)seqgateleft[c]=seqwholeunits;
 else seqgateleft[c]=seq_gate_length(seqstepunits,data[3],seqgate[c]);
 if(!seqgateleft[c])seqgateleft[c]=1;if(keep)return;seq_audio();
 if(c<4){param[c][21]=mx.magic==0xD3?mx.pan[c]:3;liveparam(c,9);}
 if(c==TWINK_TRACK){twink_note(1,note-1,data[2]);return;}
 if(c==5){pan=mixer_pan(c);route&=~0x44;if(pan&1)route|=4;if(pan&2)route|=0x40;NR51_REG=route;}
 if(c>=2||monomode){v=data[2];v=mixer_velocity(c,v);}
 if(!experimental_mode&&c==2&&waveengine!=2){oldlevel=param[2][15];level=v?(v>84?1:v>42?2:3):0;if(level&&oldlevel){level+=oldlevel-1;if(level>3)level=3;}else level=0;param[2][15]=level;}
 /* Internal pulse notes already have a validated channel/type. Keep their
    held-note bookkeeping, without an extra banked MIDI dispatch round trip. */
 event(0x90|c,note-1,v);
 if(!experimental_mode&&c==2&&waveengine!=2)param[2][15]=oldlevel;
 seq_audio();
}
/* A prepared, same-mode pattern handoff keeps the timer's pending elapsed
   time. Stopping/restarting transport here would lose time on every change. */
void seq_pattern_release(void) BANKED {uint8_t c,busy=seqservicing;if(!syncmode)seqirqready=seqirqfired=0;seqservicing=1;seqrecordtrack=255;seqrecordlength=0;
 /* A full pattern release clears foreground track ownership. Prepared
    same-pattern continuity is handled by the ordinary handoff path. */
 for(c=0;c<SEQ_TRACKS;c++)seq_off(c);
 seqservicing=busy;}
static void pattern_start(uint8_t preserve){uint8_t c,busy=seqservicing;arp_irq_reset();if(!syncmode)seqirqready=seqirqfired=0;seqservicing=1;memset(seqposition,0,SEQ_TRACKS);if(!preserve)seqswingphase=0;seq_swing_step();seqdeadline=1;seq_irq_launch();

 if(seqcachedbpm!=seqbpm)seq_gates();if(!preserve)mixer_clock_reset();if(syncmode&&(!preserve||syncslave))sync_pattern();
 seqlaunching=1;
 {for(c=0;c<SEQ_NOTE_TRACKS;c++){if(seq_enabled(c))seq_fire(c);else seq_off(c);}
 if(seq_enabled(6))seq_fire(6);}seqlaunching=0;resident_same_tones=0;resident_first_clear();seqservicing=busy;
}
/* Transport and a received native beat-one marker establish a new grid.
   Local slave launches replace notes without resetting that running grid,
   its swing half, pending clocks, or the receiver's fractional remainder. */
void seq_pattern_start(void) BANKED {pattern_start(0);}
void seq_pattern_handoff(void) BANKED {
 if(syncmode&&syncslave){
  if(!experimental_mode&&((seqmode&&!monomode)||(!seqmode&&(monomode||polymode)))){uint16_t pending=seqticks;
   /* Engine configuration calls panic(), which clears playback/ticks.
      Preserve received time without restarting the sync receiver. */
   if(seqmode)monoenable();
   else {uint8_t c;panic();monomode=polymode=0;TAC_REG=waveengine?4:0;route=0;for(c=0;c<4;c++)if(!param[c][9]){if(param[c][21]&1)route|=1<<c;if(param[c][21]&2)route|=0x10<<c;}globals();}
   seqticks+=pending;seqplaying=1;
  }
  pattern_start(1);
 }else pattern_start(MIXER_KEEP_SYNC_GRID);
}
void seq_next_deadline(void) BANKED;
uint8_t sync_local_stop_allowed(void) BANKED;
void eval_drum_prepare(void) BANKED;
void storage_sorted_prepare(void) BANKED;
void seq_transport(void) BANKED {uint8_t c,oldmono=monomode;seq_audition_stop();if(seqplaying){if(syncmode==1&&syncslave&&!syncbusy&&!sync_local_stop_allowed())return;if(!seqservicing)seq_frame();seq_stop();return;}seq_stop();
 if(experimental_mode){monomode=polymode=0;}else if(seqmode){if(!monomode)monoenable();}
 else {if(monomode||polymode)panic();monomode=polymode=0;if(oldmono){TAC_REG=waveengine?4:0;route=0;for(c=0;c<4;c++)if(!param[c][9]){if(param[c][21]&1)route|=1<<c;if(param[c][21]&2)route|=0x10<<c;}globals();}}
 memset(seqposition,0,SEQ_TRACKS);seqclock=seqticks=seqfraction=0;if(!(TAC_REG&4)){TMA_REG=240;TIMA_REG=240;IF_REG&=~TIM_IFLAG;TAC_REG=4;}seq_gates();mixer_clock_reset();seqservicing=1;
 /* Select the step-zero PCM timer before establishing the transport epoch.
    All first-step events then share the same clock origin as later steps. */
 if(waveengine!=3&&seq_enabled(6)&&seq_audible(6)){uint8_t e[4];uint16_t cursor=0,bit;
  while(seq_event_next_step(6,0,&cursor,e))if(e[1]&&e[1]<=10){bit=1U<<(e[1]-1);if(!(drummutemask&bit)&&(!drumsolomask||(drumsolomask&bit))){drum_init();drum_enable();break;}}
 }
 storage_sorted_prepare();eval_drum_prepare();
 __critical {TIMA_REG=TMA_REG;IF_REG&=~TIM_IFLAG;seqclock=seqticks=seqfraction=0;seqplaying=1;}
 if(syncmode){sync_transport(1);if(!seqplaying){seqservicing=0;dirty=1;return;}}
 seq_irq_launch();
 {for(c=0;c<SEQ_NOTE_TRACKS;c++)if(seq_enabled(c))seq_fire(c);
 if(seq_enabled(6))seq_fire(6);}seq_next_deadline();seq_irq_prepare();seqservicing=0;dirty=1;
}
/* The timer keeps elapsed time even while no event is due. Avoid rescanning
   seven gates on every audio block: wake only for the next gate or step. */
/* Hardware timer time is independent of video refresh. 1024 time units/sec;
   the existing 256 Hz audio-block interrupt contributes four units per tick. */
void seq_frame(void) BANKED {uint8_t c,expired,boundary,budget=4;uint16_t ticks,left,slice,advance,over;if(!seqplaying||seqservicing)return;seqservicing=1;editbuffer_reading=editbuffer_active();
 __critical {ticks=seqticks;seqticks=0;}
 if(syncmode&&!syncslave)ticks=sync_advance(ticks);
 while(ticks&&seqplaying){
  slice=ticks>128?128:ticks;{uint16_t wait=eval_arp_wait();if(wait<slice)slice=wait;}left=seqclock>=seqthreshold?0:seqthreshold-seqclock;advance=slice*seqbpm;boundary=advance>=left;
  if(boundary){over=advance-left;
   /* Normal timer wakeups overshoot by at most a few units. Keep the generic
      division for delayed foreground catch-up rather than looping unbounded. */
   if(over<(seqbpm<<2)){while(over>=seqbpm){slice--;advance-=seqbpm;over-=seqbpm;}}
   else{slice=(left+seqbpm-1)/seqbpm;advance=slice*seqbpm;}
  }
  expired=0;
  for(c=0;c<SEQ_TRACKS;c++)if(seqgateleft[c]){if(seqgateleft[c]<=slice){
   /* At an adjacent pulse onset, replace the note directly. A rest still
      releases immediately after that boundary has been processed. */
   if(c<SEQ_NOTE_TRACKS&&!monomode&&seqgate[c]==100&&!boundary&&seqgateleft[c]==slice&&advance+seqbpm>=left)seqgateleft[c]=1;
   else if(c<SEQ_NOTE_TRACKS&&boundary){seqgateleft[c]=0;expired|=1<<c;}else seq_off(c);
  }else seqgateleft[c]-=slice;}
  {eval_seq_tick(slice);if(drumnoiseowned||pulsekickleft)drum_tick(slice);}seqclock+=advance;ticks-=slice;
  if(boundary){seqclock-=seqthreshold;seqswingphase^=1;seqthreshold=30720U-seqthreshold;
   /* A quantized handoff may service the new pattern while copying its tail.
      Publish any time already elapsed beyond this boundary before that call. */
   if(ticks){__critical {seqticks+=ticks;}}
   if(mixer_boundary()){for(c=0;c<2;c++)if((expired&(1<<c))&&!seqgateleft[c])seq_off(c);break;}
   /* No handoff consumed the published tail. Keep processing it here rather
      than deferring overdue steps until another foreground service call.
      Timer ticks received during the callback remain pending globally. */
   if(ticks){__critical {seqticks-=ticks;}}
   editbuffer_boundary();
   for(c=0;c<SEQ_TRACKS;c++)if(seq_enabled(c)){if(++seqposition[c]>=seqlength[c])seqposition[c]=0;}
   if(seqrecordtrack!=255&&seqrecordlength&&seqrecordlength<seqlength[seqrecordtrack]){seqrecordlength++;if(seq_note_set(seqrecordtrack,seqrecordstart,seqowned[seqrecordtrack],seqrecordvelocity,seqrecordlength))mixer_pattern_changed();if(page==8&&seqtrack==seqrecordtrack){seqdrawvalid=0;dirty=1;}}
   {for(c=0;c<SEQ_NOTE_TRACKS;c++)if(seq_enabled(c))seq_fire(c);
   if(seq_enabled(6))seq_fire(6);}for(c=0;c<SEQ_NOTE_TRACKS;c++)if((expired&(1<<c))&&!seqgateleft[c])seq_off(c);if(page==8)seqflushpending=1;}
  if(padread!=padwrite||!--budget){if(ticks){__critical {seqticks+=ticks;}}break;}
 }
 seq_next_deadline();seq_irq_prepare();editbuffer_reading=0;seqservicing=0;
}
#pragma opt_code_size
uint16_t seq_hit(uint8_t c,uint8_t step,uint8_t pitch){uint16_t i,best=65535,duration=0;uint8_t e[4],note=0;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(e[1]==pitch+1&&e[0]<=step&&(best==65535||e[0]>best)){best=e[0];note=e[1];duration=e[3]?e[3]:256;}}
 return best!=65535&&note==pitch+1&&(uint16_t)step-best<duration?best:65535;
}
void seq_erase(uint8_t c,uint8_t step){uint8_t e[4],fast=0;uint16_t duration=seq_duration_get(c,step);e[0]=step;e[1]=seqpitch[c]+1;e[2]=0;e[3]=duration;if(duration)fast=roll_note_feedback(c,e,1);if(seqplaying&&seqsource[c]==step&&!editbuffer_active())seq_off(c);seq_note_set(c,step,0,0,1);seqdrawvalid=fast;dirty=1;}
void seq_insert(void){uint8_t c=seqtrack,step=seqcursor[c],fast=0,e[4];uint16_t hit=seq_hit(c,step,seqpitch[c]);if(hit!=65535){seq_erase(c,hit);return;}e[0]=step;e[1]=seqpitch[c]+1;e[2]=eval_plotvel[c];e[3]=seqdefaultdur[c];if(seq_event_total()<256)fast=roll_note_feedback(c,e,0);if(!seq_note_set(c,step,seqpitch[c]+1,eval_plotvel[c],seqdefaultdur[c]))fast=0;else if(!seqplaying)seq_plot_audition(c,seqpitch[c],eval_plotvel[c]);seqdrawvalid=fast;dirty=1;}
void eval_seq_clamp_cursor(void) BANKED;
void seq_clamp_cursor(void){eval_seq_clamp_cursor();}
void eval_seq_off_track(uint8_t c) BANKED {if(!editbuffer_reading&&editbuffer_active())return;seq_off(c);}

void seq_track_view(void) BANKED;
void seq_mute(void){mixer_pattern_changed();if(!syncmode){seqirqready=0;seqirqdirty=1;}seqmuted^=1<<seqtrack;if(seqmuted&(1<<seqtrack))seq_off(seqtrack);dirty=1;}
void seq_solo(void){mixer_pattern_changed();uint8_t c;if(!syncmode){seqirqready=0;seqirqdirty=1;}seqsolo^=1<<seqtrack;for(c=0;c<SEQ_TRACKS;c++)if(!seq_audible(c))seq_off(c);dirty=1;}
void seq_meter_edit(uint8_t field,int16_t delta) BANKED;
void seq_edit_value(uint8_t field,int16_t delta){uint8_t c=seqtrack,bars=field==12;uint16_t bar,target;uint16_t step=c==6?65535:seq_hit(c,seqcursor[c],seqpitch[c]),current;int16_t value,lo=1,hi=127;
 if(page==10&&(field==2||field==12)){field=field==2?12:2;bars=field==12;}
 if(bars){bar=(uint16_t)seqbeats*(16/seqdenom);current=seqlength[c];value=delta>0?(current/bar)+delta:((current+bar-1)/bar)+delta;if(value<1)value=1;if(value>256/bar)value=256/bar;target=value*bar;delta=(int16_t)target-current;field=2;}
 if(field==4&&seqhead==5&&c<4){native_velocity_edit(delta);return;}
 if(field==4&&seqhead==5&&c==6){drum_velocity_edit(delta);return;}
 if(field==11){seq_swing_edit(delta);return;}
 if(field==10){int16_t z=(int16_t)seqzoom+delta;seqzoom=z<0?0:z>2?2:z;seq_dimensions();seq_clamp_cursor();seqdrawvalid=0;dirty=1;return;}
 if(field==1){mixer_tempo_edit(delta);return;}
 if(field==9){seqvelocityhidden=delta<0;seq_dimensions();seq_clamp_cursor();seqdrawvalid=0;dirty=1;return;}
 if(field==7||field==8){seq_meter_edit(field,delta);return;}
 if(field==6){value=!!(seqmuted&(1<<c));if((delta>0&&!value)||(delta<0&&value))seq_mute();return;}
 mixer_pattern_changed();
 if(field==2){current=seqlength[c];hi=256;}else if(field==3){current=seqgate[c];hi=100;}else if(field==4)current=page==10||step==65535?seqdefaultvel[c]:seq_velocity_get(c,step);else {current=step==65535?seqdefaultdur[c]:seq_dur(c,step);hi=256;if(c==6)lo=0;}
 value=field==2&&!bars&&(delta>=10||delta<=-10)?(delta>0?(current>128?256:current*2):(current>1?current/2:1)):current+delta;if(value<lo)value=lo;if(value>hi)value=hi;
 if((field==2||field==3)&&!syncmode){seqirqready=0;seqirqdirty=1;}
 if(field==2)seqlength[c]=value;else if(field==3)seqgate[c]=value;else if(field==4){if(page==10||step==65535)seqdefaultvel[c]=value;else {eval_plotvel[c]=value;seq_note_set(c,step,seq_note_get(c,step),value,seq_dur(c,step));}}
 else {if(step!=65535)seq_note_set(c,step,seq_note_get(c,step),seq_velocity_get(c,step),value);seqdefaultdur[c]=value;}
 if(field==3)seqcachedbpm=0;
 /* A length boundary beyond the visible page only changes the header. */
 if((field==2&&value!=current&&(current<(uint16_t)seqbase+seqcols||value<(uint16_t)seqbase+seqcols))||field==5||(field==4&&seqcols==16))seqdrawvalid=0;
 if(field==2){if(seqposition[c]>=value)seqposition[c]%=value;if(seqowned[c]&&seqsource[c]>=value)seq_off(c);seq_clamp_cursor();}dirty=1;
}
/* Resizing shares the real Dpad release latch with move/selection gestures.
   Reaching a tail on another page first positions the cursor there without
   changing its length. Crossing an edge then requires a fresh press. */
extern uint8_t seqgestureblocked,seqgesturepressed;
uint8_t seq_length_step(uint16_t end,uint16_t next) BANKED {uint8_t c=seqtrack,dir=next>end?J_RIGHT:J_LEFT;
 if(next==end||next>=seqlength[c])return 1;
 if(seqgestureblocked&dir)return 0;
 if(end<seqbase||end>=(uint16_t)seqbase+seqcols||
    ((next<seqbase||next>=(uint16_t)seqbase+seqcols)&&(!(seqgesturepressed&dir)||seqcursor[c]!=end))){
  seqcursor[c]=end;seqgestureblocked|=dir;repeatsteps=1;dirty=1;return 0;
 }
 if(next==seqbase||next==(uint16_t)seqbase+seqcols-1){seqgestureblocked|=dir;repeatsteps=1;}
 return 1;
}
uint8_t roll_replace_feedback(uint8_t c,const uint8_t *old,const uint8_t *next,uint16_t index) BANKED;
void seq_drag(int8_t delta){uint8_t c=seqtrack,step,old[4],next[4],fast;uint16_t hit;int16_t length,max;
 if(!seqdrag){hit=seq_hit(c,seqcursor[c],seqpitch[c]);if(hit==65535){seq_insert();hit=seqcursor[c];}seqdragstart=hit;seqdrag=1;}
 step=seqdragstart;max=seqlength[c]-step;length=(int16_t)seq_dur(c,step)+delta;if(length<1)length=1;if(length>max)length=max;
 if(!seq_length_step((uint16_t)step+seq_dur(c,step)-1,(uint16_t)step+length-1))return;
 old[0]=step;old[1]=seq_note_get(c,step);old[2]=seq_velocity_get(c,step);old[3]=seq_dur(c,step);memcpy(next,old,4);next[3]=length;fast=roll_replace_feedback(c,old,next,0);if(!seq_note_set(c,step,next[1],next[2],length))fast=0;seqdefaultdur[c]=length;seqcursor[c]=step+length-1;seqbused=1;seqdrawvalid=fast;dirty=1;
}
void seq_move(uint8_t edge){uint8_t c=seqtrack,e[4],other[4],old[4],fast;uint16_t i,source=65535,dur;int16_t dst,pitch;
 seqamoved=1;if(seqaanchor==65535)return;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(e[1]==seqpitch[c]+1&&e[0]==seqaanchor){source=i;break;}}if(source==65535)return;
 dur=e[3]?e[3]:256;dst=e[0];pitch=e[1];if(edge&J_LEFT)dst--;if(edge&J_RIGHT)dst++;if(edge&J_UP)pitch++;if(edge&J_DOWN)pitch--;
 if(dst<0||dst+dur>seqlength[c]||pitch<SEQ_NOTE_MINIMUM(c)+1||pitch>seq_note_maximum(c)+1)return;
 if(dst!=e[0])for(i=0;i<seq_event_count(c);i++){if(i==source)continue;seq_event_get(c,i,other);if(other[1]&&((!eval_mode(c)&&!evalpatch[c][EV_CHORD_HISTORY])||other[1]==pitch)&&dst<other[0]+(other[3]?other[3]:256)&&other[0]<dst+dur)return;seq_audio();}
 if(seqplaying&&seqsource[c]==e[0]&&!editbuffer_active())seq_off(c);memcpy(old,e,4);e[0]=dst;e[1]=pitch;fast=roll_replace_feedback(c,old,e,source);if(!seq_event_put(c,source,e))fast=0;
 seqaanchor=dst;seqcursor[c]=dst+seqaoffset;seqpitch[c]=pitch-1;seq_clamp_cursor();seqdrawvalid=fast;dirty=1;
}
uint8_t seq_selected_event(uint8_t *e){return e[1]&&seq_group_contains(e[0],e[1]-1);}
void eval_seq_group_move(uint8_t edge) BANKED;
void seq_group_move(uint8_t edge){eval_seq_group_move(edge);}

void eval_seq_group_resize(int8_t delta) BANKED;
void seq_group_resize(int8_t delta){eval_seq_group_resize(delta);}
void seq_group_box(uint8_t edge){uint8_t c=seqtrack;
 seqamoved=1;if((edge&J_LEFT)&&seqcursor[c])seqcursor[c]--;if((edge&J_RIGHT)&&seqcursor[c]+1<seqlength[c])seqcursor[c]++;
 if((edge&J_UP)&&seqpitch[c]<127)seqpitch[c]++;if((edge&J_DOWN)&&seqpitch[c])seqpitch[c]--;
 seq_clamp_cursor();seqgrouptrack=c;seqgroupx0=seqcursor[c]<seqaanchor?seqcursor[c]:seqaanchor;seqgroupx1=seqcursor[c]>seqaanchor?seqcursor[c]:seqaanchor;
 seqgroupy0=seqpitch[c]<seqaoffset?seqpitch[c]:seqaoffset;seqgroupy1=seqpitch[c]>seqaoffset?seqpitch[c]:seqaoffset;seq_clamp_cursor();if(seqdrawvalid)seqdrawvalid=2;dirty=1;
}
uint8_t seq_header_vertical(uint8_t down){uint8_t f=seqfocus;f=down?(f==12?1:f+1):(f==1?12:f-1);while((!experimental_mode&&f==9)||f==3||f==4||f==5)f=down?(f==12?1:f+1):(f==1?12:f-1);return f;}
void seq_record_finish(void) BANKED {uint8_t c=seqrecordtrack;if(c==255)return;seqrecordtrack=255;seqrecordlength=0;seq_off(c);seqdrawvalid=0;dirty=1;}
void seq_record_start(void){uint8_t c=seqtrack,n=seqpitch[c]+1,v=eval_plotvel[c];seq_record_finish();
 if(seqplaying){if(!seq_note_set(c,seqposition[c],n,v,1))return;mixer_pattern_changed();}
 seq_off(c);seqrecordtrack=c;seqrecordstart=seqposition[c];seqrecordvelocity=v;seqrecordlength=seqplaying?1:0;
 seqsource[c]=seqrecordstart;seqowned[c]=n;seqgateleft[c]=0;if(c==TWINK_TRACK)twink_note(1,n-1,v);else event(0x90|c,n-1,mixer_velocity(c,v));seqdrawvalid=0;dirty=1;
}
uint8_t seq_track_page(uint8_t right) BANKED;
uint8_t seq_region_duplicate(void) BANKED;
void seq_popup_input(uint8_t edge) BANKED;
void seq_popup_render(void) BANKED;
uint8_t seq_top_entry(void) BANKED {uint8_t col=seqcursor[seqtrack]-seqbase;uint8_t width=seqtrack==6?136:144;uint16_t x=(seqtrack==6?24:16)+((uint16_t)col*width+width/2)/seqcols;return x<68&&seqtrack!=6?1:x<84?2:x<100?3:4;}
void seq_input(uint8_t p,uint8_t edge) BANKED {uint8_t c=seqtrack,mask=J_UP|J_DOWN|J_LEFT|J_RIGHT;
 if(eval_confirm){eval_input(p,edge);return;}if(genopen){gen_input(p,edge);return;}
 if(seqpopup){seq_popup_input(edge);return;}
 if(seqrecordtrack!=255&&(!(p&J_B)||(p&(J_START|J_SELECT))))seq_record_finish();
 if(edge&J_SELECT){seqselectused=0;seqpopupstep=seqcursor[c];seqpopuppitch=c==6?drumrow:seqpitch[c];}if(edge&J_B){seqbused=0;seqdrag=0;}if(!(p&J_B))seqdrag=0;
 if(p&J_SELECT){seqapending=0;seqdrag=0;if(edge&J_A){seqselectused=1;seq_transport();}if(edge&J_B){seqselectused=seqbused=1;seq_mute();}
  if(edge&(J_LEFT|J_RIGHT)){seqselectused=1;seqtrack=seq_track_page(!(edge&J_LEFT));seq_dimensions();seq_track_view();if(!seqplaying)seqmode=seqtrack==4;if(seqtrack<4){selected=seqtrack==5?4:seqtrack;choice=selected<4?program[selected]:0;}dirty=1;}
  if(edge&(J_UP|J_DOWN)){seqselectused=1;seq_edit_value(10,edge&J_UP?-1:1);}return;
 }
 if((lastpad&J_SELECT)&&!seqselectused){if(page==8&&!seqhead&&!seqfocus&&seqgrouptrack==c){seqpopup=1;seqpopupchoice=seqpopuperror=0;seqselectused=1;seqapending=seqdrag=0;repeatsteps=1;dirty=1;return;}page=page==10?8:10;if(page==8){seq_dimensions();seq_track_view();}seqfocus=page==10?1:0;seqedit=seqhead=0;seqselectused=1;seqdrawvalid=0;dirty=1;return;}
 /* Direction chooses a brush once per A+B hold. */
 if((p&(J_A|J_B))!=(J_A|J_B))seq_brush_reset();
 if(page==8&&!seqhead&&!seqfocus&&(p&(J_A|J_B))==(J_A|J_B)){seq_brush_input(edge);return;}
 if(page==8&&c==6&&seqhead==6){drum_name_input(p,edge);return;}
 if(page==8&&c==6&&seqhead==5){drum_velocity_input(p,edge);return;}
 if(page==8&&seqhead==6){
  if(edge&J_UP){if(seqpitch[c]<127)seqpitch[c]++;seq_clamp_cursor();dirty=1;}
  if(edge&J_DOWN){if(seqpitch[c])seqpitch[c]--;seq_clamp_cursor();dirty=1;}
  if(edge&J_RIGHT){seq_audition_stop();seqhead=0;dirty=1;}
  if(edge&J_LEFT&&seqbase){seqcursor[c]=seqbase-1;seqhead=0;dirty=1;}
  if(edge&J_A){seq_audition_stop();if(c==4&&!monomode)monoenable();seqauditionnote=seqpitch[c]+1;seqauditiontrack=c;if(c==TWINK_TRACK)twink_note(1,seqpitch[c],127);else event(0x90|c,seqpitch[c],mixer_velocity(c,127));}
  if(edge&J_B)seq_record_start();
  return;
 }
 if(page==8&&seqhead==5){
  seqedit=0;
  if(!(p&(J_A|J_B))){if(edge&J_LEFT){seqcursor[c]=seqcursor[c]?seqcursor[c]-1:seqlength[c]-1;dirty=1;}if(edge&J_RIGHT){if((uint16_t)seqcursor[c]+1<seqlength[c])seqcursor[c]++;dirty=1;}}
  if(p&(J_A|J_B)){if(edge&J_UP)seq_edit_value(4,1);if(edge&J_DOWN)seq_edit_value(4,-1);if(edge&J_LEFT)seq_edit_value(4,-10);if(edge&J_RIGHT)seq_edit_value(4,10);}
  else if(edge&J_UP){seqhead=0;dirty=1;}
  else if((edge&J_DOWN)&&c!=6&&seqpitch[c]){seqpitch[c]--;if(seqtop[c])seqtop[c]--;seq_clamp_cursor();dirty=1;}
  return;
 }
 if(page==8&&seqhead){
  if(seqhead==1&&(p&(J_A|J_B))&&(edge&(J_LEFT|J_RIGHT))){seq_audition_stop();seqtrack=seq_track_page(!!(edge&J_RIGHT));seq_dimensions();seq_track_view();seqdrawvalid=0;dirty=1;return;}
  if(c==6&&seqhead==1)seqhead=2;
  if(seqhead==1&&c<3&&(edge&(J_A|J_B))&&!(p&(J_UP|J_DOWN|J_LEFT|J_RIGHT))){eval_set_mode(c,!eval_mode(c));seqbused=1;return;}
  if((edge&J_UP)&&c==6&&!seqedit&&!(p&(J_A|J_B)))return;
  if((edge&J_UP)&&!seqedit&&!(p&(J_A|J_B))){if(seqtop[c]<127)seqtop[c]++;seqpitch[c]=seqtop[c];seq_clamp_cursor();dirty=1;return;}
  if((edge&J_LEFT)&&!((seqhead==1||seqhead==4)&&(p&(J_A|J_B)))){seqhead=seqhead==(c==6?2:1)?4:seqhead-1;seqedit=0;dirty=1;}
  if((edge&J_RIGHT)&&!((seqhead==1||seqhead==4)&&(p&(J_A|J_B)))){seqhead=seqhead==4?(c==6?2:1):seqhead+1;seqedit=0;dirty=1;}
  if(seqhead==2||seqhead==3||seqhead==7){if(edge&(J_A|J_B)){seqbused=1;if(seqhead==7){seqvelocityhidden^=1;seq_dimensions();seq_clamp_cursor();seqdrawvalid=0;dirty=1;}else if(seqhead==2)seq_mute();else seq_solo();}if(edge&J_DOWN){seqhead=0;seqedit=0;dirty=1;}}
  else{if(p&(J_A|J_B)){int8_t d=0;if(edge&J_UP)d++;if(edge&J_DOWN)d--;if((p&(J_A|J_B))&&(edge&J_LEFT))d-=10;if((p&(J_A|J_B))&&(edge&J_RIGHT))d+=10;if(d){if(seqhead==4)seq_edit_value(12,d);else if(c!=6)eval_set_mode(c,d>0?(eval_mode(c)<1?eval_mode(c)+1:eval_mode(c)):(eval_mode(c)?eval_mode(c)-1:0));}}else if(edge&J_DOWN){seqhead=0;dirty=1;}}
  seqbused=1;return;
 }
 if(c==6&&page==8&&!seqfocus){drum_input(p,edge);return;}
 if(seqfocus==6&&(edge&(J_A|J_B))){seq_mute();return;}if(seqfocus==9&&(edge&(J_A|J_B))&&!(p&(J_UP|J_DOWN|J_LEFT|J_RIGHT))){seq_edit_value(9,seqvelocityhidden?1:-1);return;}
 if((p&(J_A|J_B))&&seqfocus){if(edge&J_UP)seq_edit_value(seqfocus,1);if(edge&J_DOWN)seq_edit_value(seqfocus,-1);if(edge&J_LEFT)seq_edit_value(seqfocus,-10);if(edge&J_RIGHT)seq_edit_value(seqfocus,10);return;}
 if(page==10&&!seqfocus)seqfocus=1;
 if(seqfocus){if(edge&J_LEFT){seqfocus=seqfocus==1?12:seqfocus-1;if(seqfocus>=3&&seqfocus<=5)seqfocus=2;dirty=1;}if(edge&J_RIGHT){seqfocus=seqfocus==12?1:seqfocus+1;if(seqfocus>=3&&seqfocus<=5)seqfocus=6;dirty=1;}
  if(edge&(J_UP|J_DOWN)){seqfocus=seq_header_vertical(!!(edge&J_DOWN));dirty=1;}return;
 }
 if(!seqapending&&(edge&J_B)){seqaanchor=seq_hit(c,seqcursor[c],seqpitch[c]);seqapending=seqaanchor==65535?1:2;seqamoved=0;seqaoffset=seqaanchor==65535?0:seqcursor[c]-seqaanchor;
  if(seqapending==1){seq_insert();seqdragstart=seqcursor[c];seqdrag=1;}
 }
 else if(!seqapending&&(edge&J_A)){seqaanchor=seq_hit(c,seqcursor[c],seqpitch[c]);seqapending=seqaanchor==65535?4:3;seqamoved=0;
  if(seqapending==4){seqaanchor=seqcursor[c];seqaoffset=seqpitch[c];}else seqaoffset=seqcursor[c]-seqaanchor;
 }
 if(seqapending){
  if(seqapending==4){if(p&J_A){if(edge&mask)seq_group_box(edge);return;}if(!seqamoved){seqgrouptrack=255;if(seqdrawvalid)seqdrawvalid=2;dirty=1;}seqapending=0;if(!(edge&mask))return;}
  if(seqapending==3){if(p&J_A){if(edge&mask){if(seq_group_contains(seqaanchor,seq_note_get(c,seqaanchor)-1))seq_group_move(edge);else seq_move(edge);}return;}seqapending=0;if(!(edge&mask))return;}
  if(p&J_B){
   if(edge&(J_LEFT|J_RIGHT)){seqamoved=seqbused=1;if(seqapending==2&&seq_group_contains(seqaanchor,seq_note_get(c,seqaanchor)-1))seq_group_resize(edge&J_LEFT?-1:1);else seq_drag(edge&J_LEFT?-1:1);}
   return;
  }
  if(!seqamoved&&seqapending==2)seq_erase(c,seqaanchor);seqapending=0;if(!(edge&mask))return;
 }
 if(edge&J_LEFT){if(!seqcursor[c]){seqhead=6;seqedit=0;}else seqcursor[c]--;dirty=1;}if(edge&J_RIGHT){if((uint16_t)seqcursor[c]+1<seqlength[c])seqcursor[c]++;dirty=1;}
 if(edge&J_UP){if(seqpitch[c]>=seqtop[c]){seqhead=seq_top_entry();seqedit=0;}else if(seqpitch[c]<127)seqpitch[c]++;dirty=1;}if(edge&J_DOWN){if(seqcols==16&&!seqvelocityhidden&&seqpitch[c]+seqrows-1==seqtop[c]){seqhead=5;seqedit=0;}else if(seqpitch[c])seqpitch[c]--;dirty=1;}seq_clamp_cursor();
}
/* Three grid families fit the preview slots; +6 still selects the playhead tile. */
void seq_meterbuild(void) BANKED;
void seq_tiles(void){uint8_t tile,y,lo,hi,buf[16];
 if(seqtilesready)return;
 /* Full-height header switches use the same 5x7 letters as the UI. */
 for(tile=0;tile<8;tile++){for(y=0;y<8;y++){const uint8_t m[7]={17,27,21,21,17,17,17},s[7]={15,16,16,14,1,1,30};uint8_t glyph=y<7?(tile<4?m[y]:s[y])<<2:0;
  lo=(tile&1)?(uint8_t)~glyph:glyph;hi=lo;
  /* Side rails span the full bar; focus brightens the rails. */
  if(tile&2){lo&=0x7E;hi&=0x7E;}else{lo&=0x7E;hi|=0x81;}
  if(y==7){lo=0;hi=tile&2?0:255;}
  buf[y*2]=lo;buf[y*2+1]=hi;}ui_upload_tile(244+tile,buf,0);seq_audio();}
 seqtilesready=1;previewshape=255;
}
void seq_open(void) BANKED {seqpopup=0;seqapending=seqamoved=0;seqdrawvalid=seqdrag=0;seq_tiles();seqselectused=seqbused=1;seqfocus=seqedit=seqhead=0;if(selected==3)selected=0;if(seqtrack==3)seqtrack=0;seqtrack=seqtrack==TWINK_TRACK&&syncmode==SYNC_TWINK?TWINK_TRACK:seqmode?4:seqtrack==6?6:selected==4?5:selected;if(seqtrack==6)drum_init();seq_dimensions();seq_track_view();seq_clamp_cursor();dirty=1;}
uint8_t roll_selection_update(void) BANKED;
extern uint8_t rollcancelled;
extern uint8_t lastseqtrack;
void roll_header_range(void) BANKED;
/* The header is independent of the grid's dynamic tiles. Publish its focus
   and mode before a pending page/scroll repaint, so controls stay visible
   while that repaint is interrupted and retried for incoming input. */
static void seq_header(uint8_t c){
 memset(canvas,96,20);seq_text(0,0,seqshort[c],1);if(c!=6)seq_text(4,0,c==TWINK_TRACK?(twink_ready?"LINK":"WAIT"):eval_mode(c)==1?"ARP":"MONO",seqhead!=1);
 canvas[9]=244+((seqmuted>>c)&1)+(seqhead==2?2:0);canvas[11]=248+((seqsolo>>c)&1)+(seqhead==3?2:0);roll_header_range();
}
static void seq_header_publish(uint8_t c){
 seq_header(c);
 if(memcmp(visible,canvas,20)){
  ui_upload_map(0x9800U,canvas,20);memcpy(visible,canvas,20);
 }
 memcpy(seqscreen,canvas,20);
}
void seq_feedback_cursor(void) BANKED;
void seq_resize_status(void) BANKED;
void seq_render(void) BANKED {
 uint8_t c=seqtrack,backing=0,navigation=seqdrawvalid&&seqrecordtrack!=seqtrack;if(!navopen)lastseqtrack=c;if(!navopen)seq_tiles();if(genopen&&!navopen){gen_render();return;}if(seqpopup&&!navopen){seq_popup_render();return;}seq_dimensions();
 if(seqpreviewpinned&&seqfontdirty&&seqviewtrack==c&&seqviewcols==seqcols)seqbase=seqviewbase;
 /* Choose the first viewport once; subsequent visits retain track-local scroll and cursor state. */
 if(c!=6&&!(seqviewinitialized&(1<<c))){seqviewinitialized|=1<<c;seq_track_view();seqdrawvalid=navigation=0;}seq_clamp_cursor();
 if((c!=6&&seqviewtop!=seqtop[c])||seqviewbase!=seqbase||seqviewcols!=seqcols||seqviewtrack!=c)seqdrawvalid=0;
 if(navopen){seqdrawvalid=0;memcpy(canvas,seqscreen,360);seqflushpending=1;HIDE_SPRITES;return;}
 seq_header_publish(c);
 if(c<4&&!seqdrawvalid)backing=native_edit_feedback();
 seq_resize_status();
 /* A viewport rebuild is deferred during a drag. A retained viewport can
    still update its selection mask without reading or redrawing notes. */
 if(seqeditpreview){
  if(!seqdrawvalid&&!backing){HIDE_SPRITES;return;}
  if(seqdrawvalid==2){if(!roll_selection_update()){seqdrawvalid=0;HIDE_SPRITES;return;}seqdrawvalid=1;seqflushpending=1;}
  seq_feedback_cursor();return;
 }
 if(roll_preview_service()){dirty=1;seq_feedback_cursor();return;}
 if(c<4&&native_edit_service()){seqflushpending=dirty=1;seq_feedback_cursor();return;}
 if(seqdrawvalid==2){if(roll_selection_update()){seqflushpending=1;seqdrawvalid=1;}else seqdrawvalid=0;}
 if(seqdrawvalid){seq_audio();}
 else{roll_feedback_cancel();seqflushpending=1;seq_meterbuild();if(c==6)drum_render();else seq_pixels(navigation);if(rollcancelled){seqflushpending=0;seqdrawvalid=0;dirty=1;return;}seq_audio();memcpy(seqscreen,canvas,360);seqdrawvalid=1;}
 seq_header(c);
 eval_status();if(c==6&&!seqvelocityhidden)drum_velocity_status();
 if(eval_confirm){seq_text(0,7,"DISABLE OTHER MODE?",0);seq_text(0,9,"A CONTINUE B CANCEL",0);}if(seqeventfull)canvas[8]='!'-32+96;/* Header glyphs are static font/M/S tiles, never dynamic grid tiles.
    A header focus change cannot invalidate the grid reference counts. Full
    grid renders still request a recount through rollcache state167. */
 roll_selection_prepare(0);if(memcmp(seqscreen,canvas,20)){seqflushpending=1;memcpy(seqscreen,canvas,20);}seq_audio();seq_resize_status();seq_feedback_cursor();
}


void seq_mixer_mute(uint8_t track,uint8_t solo) BANKED {uint8_t old=seqtrack;seqtrack=track;if(solo)seq_solo();else seq_mute();seqtrack=old;}
void seq_mixer_refresh(void) BANKED {uint8_t c;for(c=0;c<SEQ_TRACKS;c++)if(!seq_audible(c))seq_off(c);drum_mixer_refresh();dirty=1;}

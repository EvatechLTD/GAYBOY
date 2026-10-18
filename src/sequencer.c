#pragma bank 10
#include "api.h"
#include "sequencer.h"
void mixer_pattern_changed(void) BANKED;
/* Zero is a rest; notes 0..127 are stored as 1..128. Patterns are volatile. */

uint16_t seqlength[SEQ_TRACKS]={16,16,16,16,16,16,16};
uint8_t seqdefaultvel[SEQ_TRACKS]={100,100,100,100,100,100,100};
uint16_t seqdefaultdur[SEQ_TRACKS]={1,1,1,1,1,4,0};
uint8_t seqgate[SEQ_TRACKS]={100,100,80,80,80,100,100};
uint8_t seqposition[SEQ_TRACKS],seqcursor[SEQ_TRACKS];
uint8_t seqpitch[SEQ_TRACKS]={60,60,60,60,60,60,60},seqtop[SEQ_TRACKS]={71,71,71,71,71,71,71};
uint8_t seqowned[SEQ_TRACKS],seqsource[SEQ_TRACKS];
uint32_t seqgateleft[SEQ_TRACKS];
uint16_t seqbpm=120;
uint8_t seqvelocityhidden,seqviewinitialized;
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
uint8_t seqgrid[64],seqmarks[64],seqmeterbeats,seqmeterdenom;
uint8_t seqscreen[360],seqdrawvalid,seqdrawplaying,seqdrawpos=255;
uint8_t seqselectused,seqbused,seqtilesready;
uint8_t seqauditionnote,seqauditiontrack;
uint8_t seqapending,seqamoved,seqaoffset;
uint8_t seqpopup;
static uint8_t seqpopupchoice,seqpopupstep,seqpopuppitch,seqpopuperror;
static uint8_t seqlengthpause;
static uint16_t seqlengthpausestart;
uint16_t seqaanchor;
uint8_t seqgrouptrack=255,seqgroupx0,seqgroupx1,seqgroupy0,seqgroupy1;
uint8_t seqrecordtrack=255,seqrecordstart,seqrecordvelocity;
uint16_t seqrecordlength;
uint8_t seqzoom=1,seqbase,seqcols=16,seqrows=17,seqheight=8,seqtilecount,seqtileoverflow;
const char seqshort[7][5]={"P1","P2","WV","NS","M5","W2","DRUM"};
const char seqchannels[7][7]={"PULSE1","PULSE2","WAVE","NOISE","MONO5","WAVE2","DRUM"};
void seq_audio(void){mixfill();if(monomode&&expconfig[0])exp_fill();}
uint8_t seq_group_contains(uint8_t step,uint8_t pitch) BANKED {return seqgrouptrack==seqtrack&&step>=seqgroupx0&&step<=seqgroupx1&&pitch>=seqgroupy0&&pitch<=seqgroupy1;}
/* Keep drawing helpers in the same bank as the roll. */
void seq_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *dst=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*dst++=*s++-32+(inv?96:0);}
void seq_number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits,uint8_t inv){uint8_t i,d,*dst=canvas+(uint16_t)y*20+x;uint16_t place=digits==3?100:digits==2?10:1;for(i=0;i<digits;i++){d=0;while(n>=place){n-=place;d++;}dst[i]=16+d+(inv?96:0);place=place==100?10:1;}}
uint16_t seq_dur(uint8_t c,uint8_t s){return seq_duration_get(c,s); }
uint8_t seq_vel(uint8_t c,uint8_t s){return seq_velocity_get(c,s); }
uint8_t seq_enabled(uint8_t c){return !experimental_mode?(c<4||c==6):seqmode?c==4:c!=4;}
void seq_off(uint8_t c){uint8_t note;if(c==6){drum_stop();return;}note=seqowned[c];seqowned[c]=0;seqgateleft[c]=0;if(note){seq_audio();if(c<2&&!monomode)keyevent(c,note-1,0);else event(0x80|c,note-1,0);seq_audio();}}
void seq_stop(void){uint8_t c;seqrecordtrack=255;seqrecordlength=0;seqplaying=0;for(c=0;c<SEQ_TRACKS;c++)seq_off(c);seqplaying=0;seqclock=seqticks=0;seqdeadline=1;if(!waveengine&&!monomode)TAC_REG=0;dirty=1;}
uint8_t seq_audible(uint8_t c){uint8_t solos=seqsolo&(seqmode?16:experimental_mode?111:79);if(drumsolomask&&!seqmode)solos|=64;return !(seqmuted&(1<<c))&&(!solos||(solos&(1<<c)));}
void seq_gates(void){uint8_t c,busy=seqservicing;if(seqcachedbpm==seqbpm){for(c=0;c<SEQ_TRACKS;c++)if(seqcachedgate[c]!=seqgate[c])break;if(c==SEQ_TRACKS)return;}seqservicing=1;seqstepunits=15360U/seqbpm;for(c=0;c<SEQ_TRACKS;c++){seqgateunits[c]=(seqstepunits*seqgate[c])/100;seqcachedgate[c]=seqgate[c];mixfill();}seqcachedbpm=seqbpm;seqservicing=busy;}
uint32_t seq_gate_length(uint16_t units,uint8_t duration,uint8_t gate) BANKED;
void seq_fire(uint8_t c){
 uint8_t data[4],s,note,v=0,oldvelocity=0,oldlevel=0,level,pan;
 if(c==seqrecordtrack)return;
 if((c==2||c==5)&&waveengine==3&&(mixrunning||drumon[0]|drumon[1]))return;
 if(c==3&&drumnoiseowned)return;
 if(c==6){if(seq_audible(c))drum_fire(seqposition[c]);return;}
 s=seqposition[c];if(!seq_note_event(c,s,data)||!seq_audible(c))return;note=data[1];
 if(seqcachedbpm!=seqbpm)seq_gates();
 /* A native pulse onset replaces the old sequence key without first issuing
    a hardware note-off. Keep live keys, then trigger the replacement once. */
 if(c<2&&!monomode){uint8_t i,j,n=keycount[c];v=mixer_velocity(c,data[2]);
  if(!v)seq_off(c);
  else if(seqowned[c])for(i=0;i<n;i++)if(keystack[c][i]==seqowned[c]-1){for(j=i;j+1<n;j++){keystack[c][j]=keystack[c][j+1];keyvel[c][j]=keyvel[c][j+1];}keycount[c]=n-1;break;}
 }else seq_off(c);
 seqsource[c]=s;seqowned[c]=note;
 if(data[3]==1)seqgateleft[c]=seqgateunits[c];
 else seqgateleft[c]=seq_gate_length(seqstepunits,data[3],seqgate[c]);
 if(!seqgateleft[c])seqgateleft[c]=1;seq_audio();
 if(c<4){param[c][21]=mixer_pan(c);liveparam(c,9);}
 if(c==5){pan=mixer_pan(c);route&=~0x44;if(pan&1)route|=4;if(pan&2)route|=0x40;NR51_REG=route;}
 if(c>=2||monomode){v=data[2];if(c==4){oldvelocity=monosource[10];if(!oldvelocity)v=127;monosource[10]=1;}v=mixer_velocity(c,v);}
 if(c==2&&waveengine!=2){oldlevel=param[2][15];level=v?(v>84?1:v>42?2:3):0;if(level&&oldlevel){level+=oldlevel-1;if(level>3)level=3;}else level=0;param[2][15]=level;}
 /* Internal pulse notes already have a validated channel/type. Keep their
    held-note bookkeeping, without an extra banked MIDI dispatch round trip. */
 if(c<2&&!monomode)keyevent(c,note-1,v);else event(0x90|c,note-1,v);
 if(c==4)monosource[10]=oldvelocity;if(c==2&&waveengine!=2)param[2][15]=oldlevel;
 seq_audio();
}
/* A prepared, same-mode pattern handoff keeps the timer's pending elapsed
   time. Stopping/restarting transport here would lose time on every change. */
void seq_pattern_release(void) BANKED {uint8_t c,busy=seqservicing;seqservicing=1;seqrecordtrack=255;seqrecordlength=0;
 /* Native voices remain audible through the prepared handoff. Incoming
    onsets replace their own voices; incoming rests release here. */
 if(experimental_mode||monomode){for(c=0;c<SEQ_TRACKS;c++)seq_off(c);}
 else{uint8_t e[4];for(c=0;c<SEQ_NOTE_TRACKS;c++)if(!seq_enabled(c)||!seq_audible(c)||!seq_note_event(c,0,e))seq_off(c);drum_stop();}
 seqservicing=busy;}
void seq_pattern_start(void) BANKED {uint8_t c,busy=seqservicing;seqservicing=1;memset(seqposition,0,SEQ_TRACKS);seqdeadline=1;
 if(seqcachedbpm!=seqbpm)seq_gates();mixer_clock_reset();
 if(seq_enabled(6))seq_fire(6);
 for(c=0;c<SEQ_NOTE_TRACKS;c++)if(seq_enabled(c))seq_fire(c);seqservicing=busy;
}
void seq_transport(void) BANKED {uint8_t c,oldmono=monomode;if(seqplaying){seq_stop();return;}seq_stop();
 if(seqmode){if(!monomode)monoenable();}
 else {if(monomode||polymode)panic();monomode=polymode=0;if(oldmono){TAC_REG=waveengine?4:0;route=0;for(c=0;c<4;c++)if(!param[c][9]){if(param[c][21]&1)route|=1<<c;if(param[c][21]&2)route|=0x10<<c;}globals();}}
 memset(seqposition,0,SEQ_TRACKS);seqclock=seqticks=seqfraction=0;if(!(TAC_REG&4)){TMA_REG=240;TIMA_REG=240;IF_REG&=~TIM_IFLAG;TAC_REG=4;}seq_gates();mixer_clock_reset();seqservicing=1;
 /* Configure sample/noise owners before starting the musical clock. This
    avoids starting a wave synth only to steal it for the first drum hit. */
 if(seq_enabled(6))seq_fire(6);
 __critical {seqclock=seqticks=seqfraction=0;seqplaying=1;}
 for(c=0;c<SEQ_NOTE_TRACKS;c++)if(seq_enabled(c))seq_fire(c);seqservicing=0;dirty=1;
}
/* The timer keeps elapsed time even while no event is due. Avoid rescanning
   seven gates on every audio block: wake only for the next gate or step. */
void seq_next_deadline(void){uint8_t c;uint16_t next=(15360U-seqclock+seqbpm-1)/seqbpm;
 for(c=0;c<SEQ_TRACKS;c++)if(seqgateleft[c]&&seqgateleft[c]<next)next=seqgateleft[c];
 if(drumnoiseowned)for(c=0;c<2;c++)if(noiseleft[c]&&noiseleft[c]<next)next=noiseleft[c];
 if(pulsekickleft&&pulsekickleft<next)next=pulsekickleft;seqdeadline=next?next:1;
}
/* Hardware timer time is independent of video refresh. 1024 time units/sec;
   the existing 256 Hz audio-block interrupt contributes four units per tick. */
void seq_frame(void) BANKED {uint8_t c,expired;uint16_t ticks,left,slice;if(!seqplaying||seqservicing)return;seqservicing=1;
 __critical {ticks=seqticks;seqticks=0;}
 while(ticks&&seqplaying){
  slice=ticks>128?128:ticks;left=15360U-seqclock;if(slice*seqbpm>=left){left=(left+seqbpm-1)/seqbpm;if(slice>left)slice=left;}
  expired=0;
  for(c=0;c<SEQ_TRACKS;c++)if(seqgateleft[c]){if(seqgateleft[c]<=slice){
   /* At an adjacent pulse onset, replace the note directly. A rest still
      releases immediately after that boundary has been processed. */
   if(c<2&&!monomode&&seqgateleft[c]==slice&&seqclock+slice*seqbpm>=15360U){seqgateleft[c]=0;expired|=1<<c;}else seq_off(c);
  }else seqgateleft[c]-=slice;}
  if(drumnoiseowned||pulsekickleft)drum_tick(slice);seqclock+=slice*seqbpm;ticks-=slice;
  if(seqclock>=15360U){seqclock-=15360U;
   /* A quantized handoff may service the new pattern while copying its tail.
      Publish any time already elapsed beyond this boundary before that call. */
   if(ticks){__critical {seqticks+=ticks;}}
   if(mixer_boundary()){for(c=0;c<2;c++)if((expired&(1<<c))&&!seqgateleft[c])seq_off(c);break;}
   /* No handoff consumed the published tail. Keep processing it here rather
      than deferring overdue steps until another foreground service call.
      Timer ticks received during the callback remain pending globally. */
   if(ticks){__critical {seqticks-=ticks;}}
   for(c=0;c<SEQ_TRACKS;c++)if(seq_enabled(c)){if(++seqposition[c]>=seqlength[c])seqposition[c]=0;}
   if(seqrecordtrack!=255&&seqrecordlength&&seqrecordlength<seqlength[seqrecordtrack]){seqrecordlength++;if(seq_note_set(seqrecordtrack,seqrecordstart,seqowned[seqrecordtrack],seqrecordvelocity,seqrecordlength))mixer_pattern_changed();if(page==8&&seqtrack==seqrecordtrack){seqdrawvalid=0;dirty=1;}}
   if(seq_enabled(6))seq_fire(6);
   for(c=0;c<SEQ_NOTE_TRACKS;c++)if(seq_enabled(c))seq_fire(c);for(c=0;c<2;c++)if((expired&(1<<c))&&!seqgateleft[c])seq_off(c);if(page==8)seqflushpending=1;}
 }
 seq_next_deadline();seqservicing=0;
}
uint16_t seq_hit(uint8_t c,uint8_t step,uint8_t pitch){uint16_t i,best=65535,duration=0;uint8_t e[4],note=0;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(e[1]&&e[0]<=step&&(best==65535||e[0]>best)){best=e[0];note=e[1];duration=e[3]?e[3]:256;}}
 return best!=65535&&note==pitch+1&&(uint16_t)step-best<duration?best:65535;
}
void seq_erase(uint8_t c,uint8_t step){if(seqplaying&&seqsource[c]==step)seq_off(c);seq_note_set(c,step,0,0,1);seqdrawvalid=0;dirty=1;}
void seq_insert(void){uint8_t c=seqtrack,step=seqcursor[c];uint16_t hit=seq_hit(c,step,seqpitch[c]);if(hit!=65535){seq_erase(c,hit);return;}seq_note_set(c,step,seqpitch[c]+1,seqdefaultvel[c],seqdefaultdur[c]);seqdrawvalid=0;dirty=1;}
void seq_clamp_cursor(void){uint8_t c=seqtrack;if(seqcursor[c]>=seqlength[c])seqcursor[c]=seqlength[c]-1;if(seqtop[c]<seqrows-1)seqtop[c]=seqrows-1;if(seqpitch[c]>seqtop[c])seqtop[c]=seqpitch[c];if(seqpitch[c]+seqrows-1<seqtop[c])seqtop[c]=seqpitch[c]+seqrows-1;}
void seq_mute(void){seqmuted^=1<<seqtrack;if(seqmuted&(1<<seqtrack))seq_off(seqtrack);dirty=1;}
void seq_solo(void){uint8_t c;seqsolo^=1<<seqtrack;for(c=0;c<SEQ_TRACKS;c++)if(!seq_audible(c))seq_off(c);dirty=1;}
void seq_edit_value(uint8_t field,int16_t delta){uint8_t c=seqtrack;uint16_t step=c==6?65535:seq_hit(c,seqcursor[c],seqpitch[c]),current;int16_t value,lo=1,hi=127;
 if(field==4&&seqhead==5&&c<SEQ_NOTE_TRACKS)step=seq_note_get(c,seqcursor[c])?seqcursor[c]:65535;
 if(field==4&&seqhead==5&&c==6){drum_velocity_edit(delta);return;}
 if(field==10){int16_t z=(int16_t)seqzoom+delta;seqzoom=z<0?0:z>3?3:z;seq_dimensions();seq_clamp_cursor();seqdrawvalid=0;dirty=1;return;}
 if(field==1){if(seqplaying)seq_frame();value=(int16_t)seqbpm+delta;seqbpm=value<30?30:value>300?300:value;seqdeadline=1;dirty=1;return;}
 if(field==9&&!experimental_mode)return;
 if(field==9){if((delta>0&&!seqmode)||(delta<0&&seqmode)){uint8_t running=seqplaying;if(running)seq_stop();seqmode=delta>0;seqtrack=seqmode?4:0;seqdrag=0;if(running)seq_transport();}dirty=1;return;}
 if(field==7){seqdrawvalid=0;value=(int16_t)seqbeats+delta;seqbeats=value<1?1:value>12?12:value;dirty=1;return;}
 if(field==8){seqdrawvalid=0;if(delta>0&&seqdenom<16)seqdenom<<=1;if(delta<0&&seqdenom>2)seqdenom>>=1;dirty=1;return;}
 if(field==6){value=!!(seqmuted&(1<<c));if((delta>0&&!value)||(delta<0&&value))seq_mute();return;}
 if(field==2){current=seqlength[c];hi=256;}else if(field==3){current=seqgate[c];hi=100;}else if(field==4)current=page==10||step==65535?seqdefaultvel[c]:seq_velocity_get(c,step);else {current=step==65535?seqdefaultdur[c]:seq_dur(c,step);hi=256;if(c==6)lo=0;}
 value=current+delta;if(value<lo)value=lo;if(value>hi)value=hi;
 if(field==2)seqlength[c]=value;else if(field==3)seqgate[c]=value;else if(field==4){if(page==10||step==65535)seqdefaultvel[c]=value;else seq_note_set(c,step,seq_note_get(c,step),value,seq_dur(c,step));}
 else {if(step!=65535)seq_note_set(c,step,seq_note_get(c,step),seq_velocity_get(c,step),value);seqdefaultdur[c]=value;}
 if(field==3)seqcachedbpm=0;
 if(field==2||field==5||(field==4&&seqcols==16))seqdrawvalid=0;
 if(field==2){if(seqposition[c]>=value)seqposition[c]%=value;if(seqowned[c]&&seqsource[c]>=value)seq_off(c);seq_clamp_cursor();}dirty=1;
}
/* Stop repeat catch-up at the visible edge, then wait for its completed
   redraw before starting a short hold delay. Audio and input keep running. */
uint8_t seq_length_step(uint16_t end,uint16_t next) BANKED {uint16_t edge=(uint16_t)seqbase+seqcols-1,now;
 if(next<=end)return 1;
 if(end==edge&&next>edge){
  repeatsteps=1;
  if(!seqlengthpause){seqlengthpause=1;dirty=1;return 0;}
  if(seqlengthpause==1)return 0;
  __critical {now=sys_time;}
  if((uint16_t)(now-seqlengthpausestart)<15)return 0;
  seqlengthpause=0;
 }else if(next==edge){seqlengthpause=1;repeatsteps=1;}
 return 1;
}
void seq_drag(int8_t delta){uint8_t c=seqtrack,step;uint16_t hit;int16_t length,max;
 if(!seqdrag){hit=seq_hit(c,seqcursor[c],seqpitch[c]);if(hit==65535){seq_insert();hit=seqcursor[c];}seqdragstart=hit;seqdrag=1;}
 step=seqdragstart;max=seqlength[c]-step;length=(int16_t)seq_dur(c,step)+delta;if(length<1)length=1;if(length>max)length=max;
 if(!seq_length_step((uint16_t)step+seq_dur(c,step)-1,(uint16_t)step+length-1))return;
 seq_note_set(c,step,seq_note_get(c,step),seq_velocity_get(c,step),length);seqdefaultdur[c]=length;seqcursor[c]=step+length-1;seqbused=1;seqdrawvalid=0;dirty=1;
}
void seq_move(uint8_t edge){uint8_t c=seqtrack,e[4],other[4];uint16_t i,source=65535,dur;int16_t dst,pitch;
 seqamoved=1;if(seqaanchor==65535)return;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(e[1]&&e[0]==seqaanchor){source=i;break;}}if(source==65535)return;
 dur=e[3]?e[3]:256;dst=e[0];pitch=e[1];if(edge&J_LEFT)dst--;if(edge&J_RIGHT)dst++;if(edge&J_UP)pitch++;if(edge&J_DOWN)pitch--;
 if(dst<0||dst+dur>seqlength[c]||pitch<1||pitch>128)return;
 if(dst!=e[0])for(i=0;i<seq_event_count(c);i++){if(i==source)continue;seq_event_get(c,i,other);if(other[1]&&dst<other[0]+(other[3]?other[3]:256)&&other[0]<dst+dur)return;seq_audio();}
 if(seqplaying&&seqsource[c]==e[0])seq_off(c);e[0]=dst;e[1]=pitch;seq_event_put(c,source,e);
 seqaanchor=dst;seqcursor[c]=dst+seqaoffset;seqpitch[c]=pitch-1;seq_clamp_cursor();seqdrawvalid=0;dirty=1;
}
uint8_t seq_selected_event(uint8_t *e){return e[1]&&seq_group_contains(e[0],e[1]-1);}
void seq_group_move(uint8_t edge){uint8_t c=seqtrack,e[4],other[4],found=0;uint16_t i,j,dur;int8_t dx=0,dy=0;int16_t at,pitch;
 seqamoved=1;if(edge&J_LEFT)dx--;if(edge&J_RIGHT)dx++;if(edge&J_UP)dy++;if(edge&J_DOWN)dy--;
 if((int16_t)seqgroupx0+dx<0||(int16_t)seqgroupx1+dx>=seqlength[c]||(int16_t)seqgroupy0+dy<0||(int16_t)seqgroupy1+dy>127)return;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(!seq_selected_event(e))continue;found=1;at=e[0]+dx;pitch=(int16_t)e[1]+dy;dur=e[3]?e[3]:256;
  if(at<0||at+dur>seqlength[c]||pitch<1||pitch>128)return;
  if(dx)for(j=0;j<seq_event_count(c);j++){seq_event_get(c,j,other);if(other[1]&&!seq_selected_event(other)&&at<other[0]+(other[3]?other[3]:256)&&other[0]<at+dur)return;}seq_audio();
 }if(!found)return;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(!seq_selected_event(e))continue;if(seqplaying&&seqsource[c]==e[0])seq_off(c);e[0]+=dx;e[1]+=dy;seq_event_put(c,i,e);seq_audio();}
 seqgroupx0+=dx;seqgroupx1+=dx;seqgroupy0+=dy;seqgroupy1+=dy;seqaanchor+=dx;seqcursor[c]+=dx;seqpitch[c]+=dy;seq_clamp_cursor();seqdrawvalid=0;dirty=1;
}
void seq_group_resize(int8_t delta){uint8_t c=seqtrack,e[4];uint16_t i;int16_t n;
 seqamoved=seqbused=1;
 if(!seq_length_step(seqaanchor+seq_dur(c,seqaanchor)-1,seqaanchor+seq_dur(c,seqaanchor)-1+delta))return;
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(seq_selected_event(e)){n=(e[3]?e[3]:256)+delta;if(n<1||n>seqlength[c]-e[0])return;}seq_audio();}
 for(i=0;i<seq_event_count(c);i++){seq_event_get(c,i,e);if(seq_selected_event(e)){e[3]=(e[3]?e[3]:256)+delta;seq_event_put(c,i,e);}seq_audio();}
 seqdefaultdur[c]=seq_dur(c,seqaanchor);seqcursor[c]=seqaanchor+seqdefaultdur[c]-1;seqdrawvalid=0;dirty=1;
}
void seq_group_box(uint8_t edge){uint8_t c=seqtrack;
 seqamoved=1;if((edge&J_LEFT)&&seqcursor[c])seqcursor[c]--;if((edge&J_RIGHT)&&seqcursor[c]+1<seqlength[c])seqcursor[c]++;
 if((edge&J_UP)&&seqpitch[c]<127)seqpitch[c]++;if((edge&J_DOWN)&&seqpitch[c])seqpitch[c]--;
 seqgrouptrack=c;seqgroupx0=seqcursor[c]<seqaanchor?seqcursor[c]:seqaanchor;seqgroupx1=seqcursor[c]>seqaanchor?seqcursor[c]:seqaanchor;
 seqgroupy0=seqpitch[c]<seqaoffset?seqpitch[c]:seqaoffset;seqgroupy1=seqpitch[c]>seqaoffset?seqpitch[c]:seqaoffset;seq_clamp_cursor();if(seqdrawvalid)seqdrawvalid=2;dirty=1;
}
uint8_t seq_header_vertical(uint8_t down){uint8_t f=seqfocus;f=down?(f==10?1:f+1):(f==1?10:f-1);while((!experimental_mode&&f==9)||f==3)f=down?(f==10?1:f+1):(f==1?10:f-1);return f;}
void seq_audition_stop(void) BANKED {uint8_t n=seqauditionnote,c=seqauditiontrack;seqauditionnote=0;if(n)event(0x80|c,n-1,0);}
void seq_record_finish(void) BANKED {uint8_t c=seqrecordtrack;if(c==255)return;seqrecordtrack=255;seqrecordlength=0;seq_off(c);seqdrawvalid=0;dirty=1;}
void seq_record_start(void){uint8_t c=seqtrack,n=seqpitch[c]+1,v=seqdefaultvel[c];seq_record_finish();
 if(seqplaying){if(!seq_note_set(c,seqposition[c],n,v,1))return;mixer_pattern_changed();}
 seq_off(c);seqrecordtrack=c;seqrecordstart=seqposition[c];seqrecordvelocity=v;seqrecordlength=seqplaying?1:0;
 seqsource[c]=seqrecordstart;seqowned[c]=n;seqgateleft[c]=0;event(0x90|c,n-1,mixer_velocity(c,v));seqdrawvalid=0;dirty=1;
}
static uint8_t seq_track_neighbor(uint8_t track,uint8_t right){
 if(seqmode)return 4;
 if(!right)return track==0?6:track==6?(experimental_mode?5:3):track==5?3:track-1;
 return track==3?(experimental_mode?5:6):track==5?6:track==6?0:track+1;
}
static uint8_t seq_track_page(uint8_t right){uint8_t next=seqtrack,tries;
 if(!right)return seq_track_neighbor(next,0);
 for(tries=0;tries<7;tries++){next=seq_track_neighbor(next,1);if(seq_event_count(next))return next;if(next==seqtrack)break;}
 return seqtrack;
}
static void seq_popup_input(uint8_t edge){uint8_t ok;
 repeatsteps=1;seqselectused=1;
 if(edge&(J_B|J_SELECT)){seqpopup=0;seqdrawvalid=0;dirty=1;return;}
 if(edge&J_UP)seqpopupchoice=seqpopupchoice?seqpopupchoice-1:2;
 if(edge&J_DOWN)seqpopupchoice=(seqpopupchoice+1)%3;
 if(edge&(J_UP|J_DOWN))seqpopuperror=0;
 if(edge&J_A){ok=seqpopupchoice==2?seq_region_paste(seqpopupstep,seqpopuppitch):seq_region_copy(seqpopupchoice==1);if(ok){seqpopup=0;seqdrawvalid=0;}else seqpopuperror=1;}
 dirty=1;
}
static void seq_popup_render(void){uint8_t y;memcpy(canvas,seqscreen,360);
 for(y=5;y<13;y++)memset(canvas+y*20+2,0,16);
 seq_text(3,5,"SELECTION",0);seq_text(4,7,"COPY",seqpopupchoice==0);seq_text(4,8,"CUT",seqpopupchoice==1);seq_text(4,9,"PASTE",seqpopupchoice==2);
 seq_text(3,11,seqpopuperror?"CAN'T DO THAT":"A OK  B BACK",0);seqflushpending=1;HIDE_SPRITES;
}
void seq_input(uint8_t p,uint8_t edge) BANKED {uint8_t c=seqtrack,mask=J_UP|J_DOWN|J_LEFT|J_RIGHT;
 if(seqpopup){seq_popup_input(edge);return;}
 if(!(p&J_B)||!(p&J_RIGHT)||(p&(J_A|J_SELECT|J_START))||page!=8||seqhead||seqfocus)seqlengthpause=0;
 if(seqrecordtrack!=255&&(!(p&J_B)||(p&(J_START|J_SELECT))))seq_record_finish();
 if(edge&J_SELECT){seqselectused=0;seqpopupstep=seqcursor[c];seqpopuppitch=c==6?drumrow:seqpitch[c];}if(edge&J_B){seqbused=0;seqdrag=0;}if(!(p&J_B))seqdrag=0;
 if(p&J_SELECT){seqapending=0;seqdrag=0;if(edge&J_A){seqselectused=1;seq_transport();}if(edge&J_B){seqselectused=seqbused=1;seq_mute();}
  if(edge&(J_LEFT|J_RIGHT)){seqselectused=1;seqtrack=seq_track_page(!(edge&J_LEFT));if(seqtrack<4||seqtrack==5){selected=seqtrack==5?4:seqtrack;choice=selected<4?program[selected]:0;}dirty=1;}
  if(edge&(J_UP|J_DOWN)){seqselectused=1;seq_edit_value(10,edge&J_UP?-1:1);}return;
 }
 if((lastpad&J_SELECT)&&!seqselectused){if(page==8&&!seqhead&&!seqfocus&&seqgrouptrack==c){seqpopup=1;seqpopupchoice=seqpopuperror=0;seqselectused=1;seqapending=seqdrag=0;repeatsteps=1;dirty=1;return;}page=page==10?8:10;seqfocus=page==10?1:0;seqedit=seqhead=0;seqselectused=1;seqdrawvalid=0;dirty=1;return;}
 if(page==8&&seqhead==6){
  if(edge&J_UP){if(seqpitch[c]<127)seqpitch[c]++;seq_clamp_cursor();dirty=1;}
  if(edge&J_DOWN){if(seqpitch[c])seqpitch[c]--;seq_clamp_cursor();dirty=1;}
  if(edge&J_RIGHT){seq_audition_stop();seqhead=0;dirty=1;}
  if(edge&J_LEFT&&seqbase){seqcursor[c]=seqbase>seqcols?seqbase-seqcols:0;dirty=1;}
  if(edge&J_A){seq_audition_stop();if(c==4&&!monomode)monoenable();seqauditionnote=seqpitch[c]+1;seqauditiontrack=c;event(0x90|c,seqpitch[c],mixer_velocity(c,127));}
  if(edge&J_B)seq_record_start();
  return;
 }
 if(page==8&&seqhead==4&&(p&J_A)&&(edge&(J_LEFT|J_RIGHT))){uint16_t n=edge&J_LEFT?seqlength[c]/2:seqlength[c]*2;if(n<1)n=1;if(n>256)n=256;seq_edit_value(2,(int16_t)n-seqlength[c]);return;}
 if(page==8&&seqhead==5){
  seqedit=0;
  if(edge&J_LEFT){seqcursor[c]=seqcursor[c]?seqcursor[c]-1:seqlength[c]-1;dirty=1;}
  if(edge&J_RIGHT){seqcursor[c]=(seqcursor[c]+1)%seqlength[c];dirty=1;}
  if(p&J_B){if(edge&J_UP)seq_edit_value(4,1);if(edge&J_DOWN)seq_edit_value(4,-1);}
  else if(edge&J_UP){seqhead=0;dirty=1;}
  else if((edge&J_DOWN)&&c!=6&&seqpitch[c]){seqpitch[c]--;if(seqtop[c])seqtop[c]--;seq_clamp_cursor();dirty=1;}
  return;
 }
 if(page==8&&seqhead){
  if((edge&J_UP)&&c==6&&!seqedit&&!(p&J_B))return;
  if((edge&J_UP)&&!seqedit&&!(p&J_B)){if(seqtop[c]<127)seqtop[c]++;seqpitch[c]=seqtop[c];seq_clamp_cursor();dirty=1;return;}
  if((edge&J_LEFT)&&!((seqhead==1||seqhead==4)&&(p&J_B))){seqhead=seqhead==1?4:seqhead==4?7:seqhead==7?3:seqhead-1;seqedit=0;dirty=1;}
  if((edge&J_RIGHT)&&!((seqhead==1||seqhead==4)&&(p&J_B))){seqhead=seqhead==4?1:seqhead==3?7:seqhead==7?4:seqhead+1;seqedit=0;dirty=1;}
  if(seqhead==2||seqhead==3||seqhead==7){if(edge&(J_A|J_B)){seqbused=1;if(seqhead==7){seqvelocityhidden^=1;seq_dimensions();seq_clamp_cursor();seqdrawvalid=0;dirty=1;}else if(seqhead==2)seq_mute();else seq_solo();}if(edge&J_DOWN){seqhead=0;seqedit=0;seqdrawvalid=0;dirty=1;}}
  else{if(edge&J_A){seqedit^=1;dirty=1;}if(seqedit||(p&J_B)){int8_t d=0;if(edge&J_UP)d++;if(edge&J_DOWN)d--;if((p&J_B)&&(edge&J_LEFT))d-=10;if((p&J_B)&&(edge&J_RIGHT))d+=10;if(d){if(seqhead==4)seq_edit_value(2,d);else{int16_t n=(int16_t)seqdefaultvel[c]+d;seqdefaultvel[c]=n<1?1:n>127?127:n;dirty=1;}}}else if(edge&J_DOWN){seqhead=0;seqdrawvalid=0;dirty=1;}}
  seqbused=1;return;
 }
 if(c==6&&page==8&&!seqfocus){drum_input(p,edge);return;}
 if((p&J_B)&&seqfocus){if(edge&J_UP)seq_edit_value(seqfocus,1);if(edge&J_DOWN)seq_edit_value(seqfocus,-1);if(edge&J_LEFT)seq_edit_value(seqfocus,-10);if(edge&J_RIGHT)seq_edit_value(seqfocus,10);return;}
 if(page==10&&!seqfocus)seqfocus=1;
 if(seqfocus){if(edge&J_A){seqedit^=1;dirty=1;}if(edge&J_LEFT){seqfocus=seqfocus==1?10:seqfocus-1;if(!experimental_mode&&seqfocus==9)seqfocus=8;if(seqfocus==3)seqfocus=2;dirty=1;}if(edge&J_RIGHT){seqfocus=seqfocus==10?1:seqfocus+1;if(!experimental_mode&&seqfocus==9)seqfocus=10;if(seqfocus==3)seqfocus=4;dirty=1;}
  if(seqedit){if(edge&J_UP)seq_edit_value(seqfocus,1);if(edge&J_DOWN)seq_edit_value(seqfocus,-1);}else if(edge&(J_UP|J_DOWN)){seqfocus=seq_header_vertical(!!(edge&J_DOWN));dirty=1;}return;
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
 if(edge&J_LEFT){if(seqcursor[c]==seqbase){seqhead=6;seqedit=0;}else seqcursor[c]--;dirty=1;}if(edge&J_RIGHT){seqcursor[c]=(seqcursor[c]+1)%seqlength[c];dirty=1;}
 if(edge&J_UP){if(seqpitch[c]>=seqtop[c]){seqhead=1;seqedit=0;}else if(seqpitch[c]<127)seqpitch[c]++;dirty=1;}if(edge&J_DOWN){if(seqcols==16&&!seqvelocityhidden&&seqpitch[c]+seqrows-1==seqtop[c]){seqhead=5;seqedit=0;}else if(seqpitch[c])seqpitch[c]--;dirty=1;}seq_clamp_cursor();
}
/* Three grid families fit the preview slots; +6 still selects the playhead tile. */
void seq_meterbuild(void){uint8_t i,beat=0,within=0,steps;if(seqmeterbeats==seqbeats&&seqmeterdenom==seqdenom)return;steps=16/seqdenom;for(i=0;i<64;i++){seqgrid[i]=within?64:beat?76:160;seqmarks[i]=within?'.'-32:(beat<9?'1'+beat:'A'+beat-9)-32+96;if(++within==steps){within=0;if(++beat==seqbeats)beat=0;}if(!(i&7))seq_audio();}seqmeterbeats=seqbeats;seqmeterdenom=seqdenom;}
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
void seq_open(void) BANKED {seqpopup=0;seqlengthpause=0;seqapending=seqamoved=0;seqdrawvalid=seqdrag=0;seq_tiles();seqselectused=seqbused=1;seqfocus=seqedit=seqhead=0;seqtrack=seqmode?4:seqtrack==6?6:selected==4?5:selected;if(seqtrack==6)drum_init();seq_dimensions();seq_clamp_cursor();dirty=1;}
void seq_name(uint8_t pitch,char *s){uint8_t n=pitch%12,oct=pitch/12;s[0]="CCDDEFFGGAAB"[n];s[1]=(0x54A&(1U<<n))?'#':' ';if(!oct){s[2]='-';s[3]='1';}else{s[2]='0'+oct-1;s[3]=' ';}s[4]=0;}
void seq_field(uint8_t field,uint8_t x,uint8_t y,const char *label,uint16_t value,uint8_t digits){uint8_t inv=seqfocus==field;seq_audio();seq_text(x,y,label,inv&&(seqedit||(lastpad&J_B)));seq_number(x+3+(field==3||field==6),y,value,digits,inv);}
uint8_t roll_selection_update(void) BANKED;
void seq_render(void) BANKED {
 uint8_t c=seqtrack,navigation=seqdrawvalid&&seqrecordtrack!=seqtrack;if(seqpopup&&!navopen){seq_popup_render();return;}seq_dimensions();
 /* Choose the first viewport once; subsequent visits retain track-local scroll and cursor state. */
 if(c<2&&!(seqviewinitialized&(1<<c))){seqviewinitialized|=1<<c;seqpitch[c]=36+c*12;seqtop[c]=seqpitch[c]+seqrows-1;seqdrawvalid=navigation=0;}
 if((c!=6&&seqviewtop!=seqtop[c])||seqviewbase!=seqbase||seqviewcols!=seqcols||seqviewtrack!=c)seqdrawvalid=0;
 if(navopen){seqdrawvalid=0;memcpy(canvas,seqscreen,360);seqflushpending=1;HIDE_SPRITES;return;}
 if(seqdrawvalid==2){if(roll_selection_update()){seqflushpending=1;memcpy(seqscreen,canvas,360);seqdrawvalid=1;}else seqdrawvalid=0;}
 if(seqdrawvalid){if(c==6&&seqcols==16&&!seqvelocityhidden&&seqviewtop!=drumrow){seqflushpending=1;drum_velocity_render();memcpy(seqscreen,canvas,360);}seq_audio();}
 else{seqflushpending=1;seq_meterbuild();if(c==6)drum_render();else seq_pixels(navigation);seq_audio();memcpy(seqscreen,canvas,360);seqdrawvalid=1;}
 memset(canvas,96,20);seq_text(0,0,seqshort[c],1);seq_text(c==6?5:4,0,"V",1);seq_number(c==6?6:5,0,seqdefaultvel[c],3,seqhead!=1);
 canvas[12]=244+((seqmuted>>c)&1)+(seqhead==2?2:0);canvas[14]=248+((seqsolo>>c)&1)+(seqhead==3?2:0);seq_number(17,0,seqlength[c],3,seqhead!=4);
 seq_text(16,0,"V",!seqvelocityhidden);if(seqhead==7)canvas[15]='>'-32+96;
 mixer_name();if(seqeventfull)canvas[11]='!'-32+96;if(memcmp(seqscreen,canvas,20)){seqflushpending=1;memcpy(seqscreen,canvas,20);}seq_audio();seq_playhead();
 if(seqlengthpause==1){__critical {seqlengthpausestart=sys_time;}seqlengthpause=2;}
}

void seq_settings_render(void) BANKED {
 uint8_t c=seqtrack,i;const char *labels[]={"BPM","LENGTH","GATE %","VELOCITY","DURATION","MUTE","BEATS","BEAT UNIT","MODE H0 M1","ZOOM STEPS"};
 uint16_t values[10];
 seq_audio();memset(canvas,0,sizeof(canvas));memset(canvas,96,20);seq_text(0,0,"SEQ SETTINGS",1);seq_text(0,2,seqchannels[c],0);
 values[0]=seqbpm;values[1]=seqlength[c];values[2]=seqgate[c];values[3]=seqdefaultvel[c];values[4]=seqdefaultdur[c];values[5]=!!(seqmuted&(1<<c));values[6]=seqbeats;values[7]=seqdenom;values[8]=seqmode;values[9]=seqcols;
 for(i=0;i<10;i++){if(i==2||(i==8&&!experimental_mode))continue;seq_audio();seq_text(1,4+i,labels[i],seqfocus==i+1&&(seqedit||(lastpad&J_B)));seq_number(16,4+i,values[i],3,seqfocus==i+1);}
}

void seq_mixer_mute(uint8_t track,uint8_t solo) BANKED {uint8_t old=seqtrack;seqtrack=track;if(solo)seq_solo();else seq_mute();seqtrack=old;}
void seq_mixer_refresh(void) BANKED {uint8_t c;for(c=0;c<SEQ_TRACKS;c++)if(!seq_audible(c))seq_off(c);drum_mixer_refresh();dirty=1;}

#pragma bank 59
#include "api.h"
#include "midi_input.h"
#include "mixer_shared.h"
#include "link_control.h"
/* Native serial: F1/BPM, FA/FC transport, 80..BF numbered 24-PPQN clocks.
   LSDj/Arduinoboy: eight link clock edges per 24-PPQN tick.
   Pulse adapters translate one zero byte to one conditioned output pulse. */
/* Persistent serial state uses otherwise idle high RAM, preserving engine WRAM. */
__at (0xFFDA) uint8_t syncmode;
__at (0xFFDB) uint8_t syncslave;
__at (0xFFDC) uint8_t syncpending;
__at (0xFFDD) uint8_t syncbusy;
__at (0xFF98) volatile uint8_t synctx[32];
extern volatile uint8_t twinktx[32],twink_guard,twink_ended_div;
__at (0xFFD8) volatile uint8_t syncr;
__at (0xFFD9) volatile uint8_t syncw;
extern __at (0xAC6A) uint16_t seqcachedbpm;
extern uint16_t seqclock;
void seq_frame(void) BANKED;
void seq_pattern_release(void) BANKED;
void seq_pattern_start(void) BANKED;
static __at (0xFFDE) uint8_t focus;
static __at (0xFFDF) uint8_t tempo_state;
static __at (0xFFE0) uint8_t tempo_hi;
static __at (0xFFE1) uint8_t beatcount;
static __at (0xFFE2) uint16_t syncalign;
static __at (0xFFE4) uint16_t remainder;
static __at (0xFFE6) uint16_t sentbpm;
static __at (0xFFE8) uint16_t lastpulse;
static __at (0xFFEA) uint16_t beatframe;
static __at (0xFFEC) uint16_t pulsequot;
static __at (0xFFEE) uint16_t pulserem;
static __at (0xFFF0) uint16_t pulsebpm;
/* Selected policy is separate from syncslave, the active wire role.
   0 AUTO, 1 forced MASTER, 2 forced SLAVE. Raw protocols keep manual roles. */
uint8_t syncrole;
static uint8_t native_peer_running;
static uint8_t native_claimed;
static uint16_t native_claim_time;
static uint16_t native_peer_frame;
extern volatile uint8_t link_claiming;
__at (0xFFB8) volatile uint8_t syncirqphase[3];
__at (0xFFBB) volatile uint16_t syncincrement;
__at (0xFFBD) volatile uint8_t synclimit[3];
__at (0xFFC0) volatile uint8_t syncarmed;
__at (0xFFC1) uint8_t syncdivider;
__at (0xFFC2) uint8_t syncsub;
__at (0xFFC3) uint8_t syncreload;
__at (0xFFC4) volatile uint8_t syncdue;
static __at (0xFFC5) uint8_t markerbase;
__at (0xFFC6) volatile uint8_t synctxwait;
__at (0xFFC7) volatile uint8_t synctick;
__at (0xFFC8) volatile uint8_t syncstart;
__at (0xFFC9) volatile uint8_t synctxbyte;
static const char * const modes[]={"OFF","GAYBOY","LSDJ","ARDUBOY","PO","GATE","TWINK"};
static uint16_t frames(void){uint16_t t;__critical {t=sys_time;}return t;}
void link_clock_abort(void) NONBANKED;
void link_clock_decode(uint8_t b,uint8_t delta) NONBANKED;
void sync_init(void) BANKED {memset((void *)0xFF98,0,0x5A);syncrole=native_peer_running=midi_launch_enabled=0;syncmode=0;syncslave=0;}
void sync_control_service(void) BANKED {
 __critical {
  if(syncmode==SYNC_TWINK&&twink_guard&&(uint8_t)(DIV_REG-twink_ended_div)>=8)twink_guard=0;
  if(!synctxwait&&!(SC_REG&0x80)&&!(IF_REG&SIO_IFLAG)&&(syncmode!=SYNC_TWINK||!twink_guard)){
   if(syncmode==SYNC_TWINK&&syncdue){syncdue=0;SB_REG=0x80|synctick;SC_REG=0x81;}
   else if(syncr!=syncw){if(syncmode==1)link_clock_abort();
    if(syncmode==SYNC_TWINK){synctxbyte=twinktx[syncr];}else synctxbyte=synctx[syncr];
    SB_REG=synctxbyte;syncr=(syncr+1)&31;SC_REG=0x81;
   }
  }
 }
}

static void send(uint8_t b){uint8_t next=(syncw+1)&31;
 __critical {if(next==syncr)overflow=1;else {synctx[syncw]=b;syncw=next;}}
 sync_control_service();
}
static uint16_t pulse_units(void){return syncmode==4?30720U:syncmode==5?15360U:2560U;}
/* Only foreground configuration uses multiplication/division. IRQ work is bounded. */
void sync_timer_config(void) BANKED {uint8_t reload=TMA_REG,divide;uint16_t increment;
 if(!syncarmed)return;
 divide=waveengine==3?1:(256U-reload)>>2;if(!divide)divide=1;
 increment=(waveengine==3?183U:64U)*seqbpm;
 __critical {syncreload=reload;syncdivider=divide;syncsub=0;syncincrement=increment;TMA_REG=TIMA_REG=waveengine==3?73:252;}
}
static void tempo(void){uint16_t increment;if(!seqglobalbpm)seqglobalbpm=seqbpm;seqbpm=seqglobalbpm;
 if(sentbpm!=seqbpm){
  increment=(waveengine==3?183U:64U)*seqbpm;
  __critical {syncincrement=increment;}
  if(syncmode==1){send(0xF1);send(seqbpm>>7);send(seqbpm&127);}sentbpm=seqbpm;
 }
}
void sync_pattern(void) BANKED {uint32_t phase,elapsed;uint16_t position,part;uint8_t tick;
 if(syncmode!=1||syncslave||!seqplaying)return;
 /* A paired boundary already sent its marker before patch installation. */
 if(link_pair_phase==6){link_pair_master_launched();return;}
 if(link_pair_phase==5)link_pair_phase=6;
 /* Express beat one in the continuous oscillator epoch, including time
    accumulated while the new pattern was being prepared. */
 if(link_pair_phase==2)link_pair_master_launched();tempo();__critical {phase=syncirqphase[0]|((uint32_t)syncirqphase[1]<<8)|((uint32_t)syncirqphase[2]<<16);tick=synctick;elapsed=seqticks;}
 elapsed=elapsed*seqbpm+seqclock;position=phase>>6;while(elapsed>=2560U){elapsed-=2560U;tick=(tick-1)&63;}part=elapsed;
 if(position<part){tick=(tick-1)&63;position+=2560U;}position-=part;
 /* Bit 6 tags a prepared pair commit without adding a transfer. A stale
    pair must never consume an unrelated later unpaired launch marker. */
 send(0xF2);send(tick|(link_pair_phase==6?64:0));send(position>>7);send(position&127);
}
void sync_transport(uint8_t playing) BANKED {uint32_t limit;uint8_t pending,byte,guard,reply;
 if(syncmode==SYNC_TWINK&&!playing)twink_transport(0);
 if(!playing&&syncmode==1&&!syncslave&&syncarmed){send(0xFC);while(syncr!=syncw||(SC_REG&0x80)||(IF_REG&SIO_IFLAG))sync_control_service();}
 if(syncarmed){__critical {syncarmed=0;syncdue=0;TMA_REG=TIMA_REG=syncreload;}}
 /* Disarm the consumer before clearing its optional bit ring. */
 if(!playing&&syncmode==1){link_clock_abort();if(link_pair_phase)link_reset();}
 remainder=seqbpm-1;syncalign=0;syncpending=0;beatcount=0;lastpulse=beatframe=frames();
 /* Native AUTO idle is externally clocked. A local transport start claims
    the clock; starts dispatched by sync_receive retain the listening role.
    seq_transport calls stop internally before start, so use syncbusy rather
    than the previous role to distinguish the two paths. */
 if(syncmode==1&&!syncrole){
  if(!playing&&syncslave&&native_peer_running)native_peer_frame=frames();
  if(playing&&native_peer_running&&(uint16_t)(frames()-native_peer_frame)>120)native_peer_running=0;
  if(!playing){if(!syncslave){syncslave=1;SB_REG=0;SC_REG=0x80;}}
  else if(!syncbusy){
   /* A button can arrive while the peer's claim is still shifting in.
      Keep the external receiver armed through one complete cable byte,
      then inspect queued claims before changing the clock source. This
      wait runs only on a local AUTO start, never on the musical clock. */
   delay(2);
   pending=rd;
   while(pending!=wr){byte=rx[pending++];
    if(byte==0xF5||byte==0xF7){native_claimed=1;native_claim_time=frames();}
    if(byte==0xF1||byte==0xFA||(byte>=0x80&&byte<0xF0)){native_peer_running=1;native_peer_frame=frames();}
   }
   if(!native_peer_running&&(!native_claimed||(uint16_t)(frames()-native_claim_time)>60)){syncslave=0;SC_REG=0;}
   else if(native_claimed&&!native_peer_running){seqplaying=0;return;}
  }
 }
 if(!syncmode||syncslave||!playing)return;
 /* No musical clock is armed yet. A short explicit claim distinguishes
    simultaneous local starts from ordinary full-duplex byte echoes. */
 if(syncmode==1&&!syncbusy){
  link_reset();link_claiming=1;pending=wr;byte=0;send(0xF5);
  while(syncr!=syncw||(SC_REG&0x80)||(IF_REG&SIO_IFLAG))sync_control_service();
  if(!linkcollision){delay(4);send(0xF7);while(syncr!=syncw||(SC_REG&0x80)||(IF_REG&SIO_IFLAG))sync_control_service();}
  /* A listening peer has now pipelined its nonzero F6 acknowledgement.
     Check an all-zero guard as well: two internal claimants can sample
     only high bits during F5/F7 and otherwise resemble an unplugged cable.
     Keep this check in foreground; the steady serial ISR is unchanged. */
  for(guard=0;guard<8&&!linkcollision;guard++){send(0);while(syncr!=syncw||(SC_REG&0x80)||(IF_REG&SIO_IFLAG))sync_control_service();
   while(pending!=wr){reply=rx[pending++];if(reply==0xF6)byte|=1;if(reply!=0xFF)byte|=2;}
  }
  /* A valid listening peer may resume queued metadata containing zeroes
     after its acknowledgement. Those are not competing clock claims. */
  if(!syncrole&&byte==2)linkcollision=1;
  link_claiming=0;
  if(linkcollision){link_reset();linkstate=4;syncslave=1;seqplaying=0;native_claimed=native_peer_running=0;__critical {rd=wr;SB_REG=0;SC_REG=0x80;}dirty=1;return;}
 }
 limit=(uint32_t)pulse_units()<<6;
 __critical {syncirqphase[0]=syncirqphase[1]=syncirqphase[2]=0;synclimit[0]=limit;synclimit[1]=limit>>8;synclimit[2]=limit>>16;synctick=0;syncstart=syncmode==1;if(syncmode==SYNC_TWINK)syncstart=1;syncarmed=1;synctxwait=0;}
 sync_timer_config();sentbpm=0;tempo();
 if(syncmode==1){send(0xFA);while(syncstart)sync_control_service();}
 if(syncmode==SYNC_TWINK){twink_transport(1);while(syncstart)sync_control_service();}
 __critical {syncirqphase[0]=syncirqphase[1]=syncirqphase[2]=0;synctick=0;seqticks=0;}
 if(syncmode==1)link_begin();
}
uint16_t sync_advance(uint16_t ticks) BANKED {uint16_t result=0,unit,part;uint8_t n;
 if(!syncmode)return ticks;
 if(!syncslave){tempo();return ticks;}
 if(syncmode!=1&&(uint16_t)(frames()-lastpulse)>120){if(seqplaying)seq_transport();return 0;}
 n=syncpending;syncpending=0;unit=pulse_units();
 if(pulsebpm!=seqbpm){pulsequot=unit/seqbpm;pulserem=unit%seqbpm;pulsebpm=seqbpm;}
 while(n--){if(syncalign){part=unit-syncalign;syncalign=0;result+=part/seqbpm;remainder+=part%seqbpm;}else {result+=pulsequot;remainder+=pulserem;}if(remainder>=seqbpm){remainder-=seqbpm;result++;}}
 return result;
}
static uint8_t receive(uint8_t b) {uint16_t bpm,elapsed;uint8_t ppqn;
 if(!syncslave){if(syncmode==1)link_receive(b);return 1;}
 if(syncmode==1){
  if(b==0xF5){native_claimed=1;native_claim_time=frames();return 1;}
  if(b==0xF7)return 1;
  if((b>=0x80&&b<0xF0)||b==0xF8){uint8_t next=b==0xF8?(beatcount+1)&63:b&63,delta=(next-beatcount)&63;beatcount=next;if(!seqplaying){native_peer_running=1;native_peer_frame=frames();}if(tempo_state>=3)return 1;if(seqplaying){if(syncpending+delta<64)syncpending+=delta;else overflow=1;}if(b!=0xF8)link_clock_decode(b,delta);return 1;}
  if(link_receive(b))return 1;
  if(b==0xF2){tempo_state=3;return 1;}
  if(b==0xF1){native_peer_running=1;native_peer_frame=frames();tempo_state=1;return 1;}
  if(tempo_state){
   if(b&128){tempo_state=0;return 1;}
   if(tempo_state==3){markerbase=b;tempo_state=4;return 1;}
   if(tempo_state==1||tempo_state==4){tempo_hi=b;tempo_state=tempo_state+1;return 1;}
   bpm=((uint16_t)tempo_hi<<7)|b;
   if(tempo_state==2){if(bpm>=30&&bpm<=240){seqglobalbpm=seqbpm=bpm;seqcachedbpm=0;dirty=1;}}
   else if(seqplaying&&bpm<2560U){uint8_t clocks=(beatcount-markerbase)&63,busy=seqservicing;uint16_t ticks;seqservicing=1;syncpending=clocks;remainder=seqbpm-1;syncalign=bpm;ticks=sync_advance(0);__critical {seqclock=0;seqticks=ticks;}if(!(markerbase&64)||!link_pair_hold||!link_pair_marker()){seq_pattern_release();seq_pattern_start();}seqservicing=busy;}
   tempo_state=0;return 1;
  }
  if(b==0xFC){native_peer_running=native_claimed=0;if(seqplaying)seq_transport();return 1;}
  if(b==0xFA){native_claimed=0;native_peer_running=1;native_claim_time=native_peer_frame=frames();link_reset();if(seqplaying)seq_transport();seq_transport();return 1;}
  if(b==0xFB){native_peer_running=1;if(!seqplaying)seq_transport();return 1;}
  if(b!=0xF8)return 0;
 }else if(!seqplaying){seq_transport();lastpulse=beatframe=frames();return 1;}
 lastpulse=frames();
 if(!seqplaying)return 1;
 /* Measure a whole quarter note, rather than quantizing each clock to video. */
 if(syncmode!=1){ppqn=syncmode==4?2:syncmode==5?4:24;
  beatcount=beatcount+1;if(beatcount>=ppqn){elapsed=frames()-beatframe;beatframe=frames();beatcount=0;
   if(elapsed){bpm=3584U/elapsed;if(bpm>=30&&bpm<=240){
    /* Pending ticks were converted using the previous estimate. Consume
       them at that tempo before installing the newly measured value. */
    if(bpm!=seqbpm&&seqplaying&&!seqservicing)seq_frame();
    seqglobalbpm=seqbpm=bpm;seqcachedbpm=0;dirty=1;
   }}}}
 if(syncpending<48)syncpending=syncpending+1;else overflow=1;
 return 1;
}
uint8_t sync_receive(uint8_t b) BANKED {uint8_t result;uint16_t ticks;syncbusy=1;result=receive(b);
 if(syncslave&&seqplaying&&syncpending){ticks=sync_advance(0);__critical {seqticks+=ticks;}}
 syncbusy=0;return result;
}
static void drawtext(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
static void drawnumber(uint8_t x,uint8_t y,uint16_t n){char s[4];s[0]='0'+n/100;s[1]='0'+(n/10)%10;s[2]='0'+n%10;s[3]=0;drawtext(x,y,s,0);}
void sync_render(void) BANKED {memset(canvas,0,360);memset(canvas,96,20);drawtext(0,0,"SYNC",1);
 drawtext(1,3,"TYPE",focus==0);drawtext(1,4,modes[syncmode],focus==0);
 drawtext(1,6,"ROLE",focus==1);drawtext(8,6,syncmode==1&&!syncrole?"AUTO":syncslave?"SLAVE":"MASTER",focus==1);
 if(syncmode==1&&!syncrole&&seqplaying)drawtext(8,7,syncslave?"> SLAVE":"> MASTER",0);
 drawtext(1,8,"MIDI LAUNCH",focus==2);drawtext(15,8,midi_launch_enabled?"ON":"OFF",focus==2);
 drawtext(1,10,"GLOBAL BPM",0);drawnumber(13,10,seqglobalbpm?seqglobalbpm:seqbpm);
 drawtext(0,12,"A/B+ARROWS TO EDIT",0);drawtext(0,13,"SELECT+A PLAY / STOP",0);
 if(linkstate==4)drawtext(0,16,"START CLASH - RETRY",0);
 if(syncmode==SYNC_TWINK)drawtext(0,15,twink_ready?"MONOSIMP CONNECTED":"CONNECT MONOSIMP",0);
 else if(syncmode>=4)drawtext(0,15,"PULSE ADAPTER NEEDED",0);
 else if(syncmode==3)drawtext(0,15,"LSDJ SYNC MODE",0);
 else drawtext(0,15,"GAME BOY LINK CABLE",0);
}
void sync_input(uint8_t edge) BANKED {int8_t delta;
 if(edge&(J_UP|J_DOWN)){focus=(focus+(edge&J_UP?2:1))%3;dirty=1;}
 if(focus==2){if(edge&(J_A|J_B|J_LEFT|J_RIGHT)){mixer_midi_launch_set(!midi_launch_enabled);dirty=1;}return;}
 if(edge&J_A){seq_transport();dirty=1;}
 if(!(edge&(J_LEFT|J_RIGHT)))return;
 if(seqplaying)seq_transport();if(syncmode==SYNC_TWINK){twink_panic();while(syncr!=syncw||(SC_REG&0x80)||(IF_REG&SIO_IFLAG))sync_control_service();}delta=edge&J_LEFT?-1:1;
 __critical {remove_SIO(syncmode==1?link_serial_isr:serial_isr);SC_REG=0;IF_REG&=~SIO_IFLAG;syncr=syncw=0;rd=wr;st=count=0;}
 if(!focus)syncmode=(syncmode+(delta<0?6:1))%7;
 else if(syncmode==1)syncrole=(syncrole+(delta<0?2:1))%3;
 else if(syncmode!=SYNC_TWINK)syncslave^=1;
 if(syncmode==SYNC_TWINK)syncslave=0;
 if(syncmode==1){if(syncrole==1)syncslave=0;else syncslave=1;}
 if(syncmode&&syncslave&&mx.magic==0xD3&&!mx.quant)mx.quant=4;
 syncpending=syncalign=remainder=tempo_state=pulsebpm=0;sentbpm=0;
 native_peer_running=native_claimed=0;
 if(syncmode){if(!seqglobalbpm)seqglobalbpm=seqbpm;seqbpm=seqglobalbpm;}
 if(seqtrack==TWINK_TRACK&&syncmode!=SYNC_TWINK)seqtrack=0;twink_reset();
 link_reset();__critical {add_SIO(syncmode==1?link_serial_isr:serial_isr);SB_REG=0;SC_REG=(!syncmode||syncslave)?0x80:0;}dirty=1;
}

void sync_setting_edit(uint8_t row,uint8_t edge) BANKED {uint8_t saved=focus;if(seqplaying)return;focus=row;sync_input(edge);focus=saved;}

/* Coalesce near-simultaneous Play presses with an AUTO remote start. This
   runs only on a local transport press, never on clock or instrument paths. */
uint8_t sync_local_stop_allowed(void) BANKED {
 return syncmode!=1||syncrole||!native_peer_running||(uint16_t)(frames()-native_claim_time)>=6;
}

void sync_ui_input(uint8_t p,uint8_t edge) BANKED {if(!edge)return;int8_t d=0,target,current;
 if((p&J_SELECT)&&(edge&(J_A|J_B))){seq_transport();dirty=1;return;}
 if(focus==2){
  if(!(p&(J_A|J_B))){if(edge&(J_UP|J_DOWN))focus=(focus+(edge&J_UP?2:1))%3;}
  else if(edge&(J_UP|J_DOWN|J_LEFT|J_RIGHT))mixer_midi_launch_set(!!(edge&(J_UP|J_RIGHT)));
  else if(edge&(J_A|J_B))mixer_midi_launch_set(!midi_launch_enabled);
  dirty=1;return;
 }
 if((edge&(J_A|J_B))&&!(p&(J_UP|J_DOWN|J_LEFT|J_RIGHT))&&focus&&syncmode!=1){sync_input(J_RIGHT);return;}
 if(!(p&(J_A|J_B))){if(edge&(J_UP|J_DOWN))focus=(focus+(edge&J_UP?2:1))%3;}
 else{d=edge&J_UP?1:edge&J_DOWN?-1:edge&J_RIGHT?10:edge&J_LEFT?-10:0;if(d){current=!focus?syncmode:syncmode==1?syncrole:syncslave;target=current+d;if(target<0)target=0;if(target>(!focus?6:syncmode==1?2:1))target=!focus?6:syncmode==1?2:1;while(current!=target){sync_input(current<target?J_RIGHT:J_LEFT);current+=current<target?1:-1;}}}
 dirty=1;
}

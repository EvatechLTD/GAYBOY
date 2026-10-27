#pragma bank 5
#pragma opt_code_speed
#include "api.h"
#include "song_mode.h"
#include "song_link.h"
#include "smooth_playback.h"
#include "native_sync.h"
#include "link_control.h"

/* This protocol owns the cable only while a prepared Song transport is armed.
   No song data crosses the cable: each endpoint compiles its own immutable
   arrangement before READY. Steady traffic uses two timestamp bytes, roughly every 32 timer ticks. */
#define BEGIN 0xFD
#define POLL 0xF0
#define ARM 0xFE
#define GO 0xFA
#define STOP 0xFC
#define WAIT 0xD1
#define READY 0xD2
#define FAILED 0xD3
#define ARMED 0xD4
#define STOPPING 0xDC
enum {M_HEADER=1,M_WAIT,M_ARM,M_GO,S_HEADER,S_PREP,S_READY,S_ARM,RUN,ENDING,FAIL,M_PREP,M_ARM_WAIT,S_LISTEN,M_LOCAL_PREP};
uint8_t song_link_active;
typedef struct {
 volatile uint8_t state,reply,transfer,rxat,txat,peer;
 uint8_t smooth,sequence,lastsequence;
 volatile uint16_t since;uint16_t reference,sentframe;
 uint8_t header[10];
 volatile int16_t trim;volatile uint16_t maxerror;
} SongLink;
/* SIM[17] at A3E1 is the noise envelope shadow. Other SIM bytes were unused.
   All SRAM transactions restore bank zero before enabling interrupts. */
__at (0xA3E2) static SongLink wire;
__at (0xA3E9) volatile uint8_t song_link_reload;
__at (0xA3FB) volatile int16_t song_link_trim;
#define W wire
typedef char SongLinkFits[(sizeof(SongLink)<=30)?1:-1];
extern volatile uint16_t song_hwclock,song_hwwait;
extern volatile uint8_t song_actual_done;
extern uint8_t syncrole;
void song_timer(void) NONBANKED;
void editirq_clock_reset(void) NONBANKED;
static uint16_t frame(void){uint16_t n;__critical{n=sys_time;}return n;}
static uint8_t expired(void){uint16_t n;__critical{n=sys_time-W.since;}return n>900;}
static uint8_t checksum(void){uint8_t i,j,c=0;for(i=0;i<9;i++){c^=W.header[i];for(j=0;j<7;j++)c=c&64?((c<<1)^9)&127:(c<<1)&127;}return c;}
static void send(uint8_t b){uint16_t now=song_pattern_mode?DIV_REG:frame();__critical{if(!(SC_REG&0x80)&&!(IF_REG&SIO_IFLAG)){W.sentframe=now;W.transfer=1;SB_REG=b;SC_REG=0x81;}}}
static void quiet(void){NR12_REG=NR22_REG=NR42_REG=8;NR14_REG=NR24_REG=NR44_REG=128;NR30_REG=0;}
static void begin_slave(void){
 native_prepare=0;
 song_link_active=1;memset((void *)&W,0,sizeof(W));W.state=S_HEADER;W.reply=WAIT;W.since=sys_time;syncarmed=syncdue=0;syncslave=1;syncr=syncw;rd=wr;
}
/* Called from SIO. No __critical routines, implicit EI, source scans or UI. */
void song_link_receive(uint8_t b) BANKED {uint8_t timer,base;uint16_t local;
 if(!song_link_active){begin_slave();SB_REG=WAIT;SC_REG=0x80;return;}
 if(!syncslave){
  if(W.state==RUN)return;
  W.peer=b;W.transfer=0;
  if(b==WAIT||b==READY||b==ARMED)W.since=sys_time;
  if(W.state==M_GO){W.state=RUN;W.sequence=W.txat=0;W.reference=0;
   /* Steady song sync is one-way. The master needs no receive interrupts
      after the shared GO edge; they must not preempt its prepared audio. */
   IE_REG&=~SIO_IFLAG;song_go();}
  return;
 }
 /* Rearm immediately; the next byte is never dependent on foreground work. */
 SB_REG=W.reply;SC_REG=0x80;
 if(W.state==RUN&&(b&0xC0)==0x80){
  W.transfer=W.rxat=0;local=song_hwclock;base=song_link_reload;timer=TIMA_REG;
  if((IF_REG&TIM_IFLAG)||timer<base)return;
  /* Timestamp the first byte. The following payload completes its clock
     number; no phase calculation or synthesis runs in this serial IRQ. */
  W.header[0]=b&63;W.header[1]=local;W.header[2]=local>>8;W.header[3]=timer-base;W.header[4]=0;W.header[6]=W.trim;W.header[7]=(uint16_t)W.trim>>8;W.rxat=1;return;
 }
 if(W.state==RUN&&b<128&&W.rxat==1){W.header[5]=b;W.rxat=0;W.transfer=1;return;}
 if(b==POLL||W.state==S_HEADER)W.since=sys_time;
 if(b==STOP){W.state=ENDING;W.reply=STOPPING;song_actual_done=1;quiet();return;}
 if(b==BEGIN&&!song_playing){W.state=S_HEADER;W.rxat=0;W.reply=WAIT;return;}
 if(W.state==S_HEADER){
  if(b&128){W.state=FAIL;return;}
  W.header[W.rxat++]=b;
  if(W.rxat==10){if((W.header[0]!=1&&W.header[0]!=2)||W.header[9]!=checksum()||(W.header[0]==1&&page!=SONG_PAGE))W.state=FAIL;else{song_pattern_mode=W.header[0]==2;W.state=S_PREP;}}
  return;
 }
 if(b==ARM&&W.state==S_READY){W.state=S_ARM;return;}
 if(b==GO&&W.state==S_LISTEN){W.state=RUN;W.lastsequence=0;W.reference=0;W.rxat=W.peer=0;song_go();return;}

}
static void phase_service(void){uint8_t low,high,timer,pending;uint16_t local,amount,reference;int16_t error,trim;
 __critical{low=W.header[0];local=W.header[1]|((uint16_t)W.header[2]<<8);timer=W.header[3];pending=W.header[4];high=W.header[5];trim=W.header[6]|((uint16_t)W.header[7]<<8);W.transfer=0;}
 reference=low|((uint16_t)(high>>2)<<6);local+=pending!=0;
 error=(int16_t)((((reference+1)<<2)+(high&3)-(local<<2)-timer+4096U)&8191U)-4096;
 error-=(int16_t)((uint16_t)W.trim-(uint16_t)trim);
 amount=error<0?-error:error;if(amount>W.maxerror)W.maxerror=amount;
 /* Change one future period by244us. The slave IRQ restores the ordinary
    reload and accounts for the completed trim. Neither TIMA nor DIV is
    written during playback; timer overflow requests are never cleared. */
 __critical{if(TMA_REG==252&&song_link_reload==252){
  if(error>1)TMA_REG=253;
  else if(error< -1)TMA_REG=251;
 }}
}

void pattern_link_request(void) BANKED {if(seqplaying||song_link_active)return;song_pattern_mode=1;song_link_request(1);}
void song_link_request(uint8_t smooth) BANKED {uint32_t start=smooth?0:song_view.cursor&~15UL;uint16_t bpm=seqbpm;uint8_t i;
 if(seqplaying)return;
 native_prepare=0;
 /* Finish any native idle poll before changing ownership of SB/SC. */
 while((SC_REG&0x81)==0x81||IF_REG&SIO_IFLAG);
 __critical{song_link_active=1;syncarmed=syncdue=0;syncr=syncw;rd=wr;SC_REG=0;}
 link_reset();memset((void *)&W,0,sizeof(W));W.smooth=smooth;W.since=frame();
 if(syncrole==2){syncslave=1;W.state=S_LISTEN;W.reply=WAIT;SB_REG=WAIT;SC_REG=0x80;return;}
 syncslave=0;W.state=M_PREP;W.header[0]=song_pattern_mode?2:1;W.header[1]=bpm&127;W.header[2]=bpm>>7;
 for(i=3;i<8;i++){W.header[i]=start&127;start>>=7;}W.header[8]=smooth;W.header[9]=checksum();
 dirty=1;
}
/* Two short bytes describe an arbitrary1024-Hz clock point plus its244us
   fractional phase. Foreground sends only with audio headroom. The receiver
   timestamps byte one; the delayed second byte completes that same stamp.
   No precise foreground wakeup, IRQ send, or master's receive IRQ is needed. */
static void clock_service(void){uint16_t local;uint8_t timer;
 if(SC_REG&0x80)return;
 if(W.txat==1){W.header[1]=DIV_REG;W.txat=2;return;}
 if(W.txat==2){
  if((uint8_t)(DIV_REG-W.header[1])<8)return;
  __critical{if(song_hwwait>2&&!(SC_REG&0x80)&&!(IF_REG&TIM_IFLAG)){SB_REG=W.header[0];SC_REG=0x81;W.txat=0;}}
  return;
 }
 __critical{
  local=song_hwclock;timer=TIMA_REG;
  if((uint16_t)(local-W.reference)>=32&&song_hwwait>2&&timer>=252&&!(SC_REG&0x80)&&!(IF_REG&TIM_IFLAG)){
   W.reference=local;W.header[0]=((local>>6)&31)<<2|(timer&3);W.txat=1;
   SB_REG=0x80|(local&63);SC_REG=0x81;
  }
 }
}

void song_link_finish(void) BANKED {uint16_t since=frame();uint8_t wasplaying=song_playing;
 if(!song_link_active)return;
 if(!syncslave){
  W.state=ENDING;IE_REG|=SIO_IFLAG;while(SC_REG&0x80||IF_REG&SIO_IFLAG);
  send(STOP);while(W.transfer&&((uint16_t)(frame()-since)<4));
 }else{
  TAC_REG=0;quiet();W.reply=STOPPING;
  while(W.state!=ENDING&&(uint16_t)(frame()-since)<4);
 }
 __critical{song_link_active=0;syncarmed=syncdue=0;syncr=syncw;rd=wr;syncslave=1;if(syncrole==1)syncslave=0;SB_REG=0;SC_REG=syncslave?0x80:0;}
 link_reset();
 if(!wasplaying){__critical{TAC_REG=0;remove_TIM(song_timer);remove_TIM(song_slave_timer);remove_TIM(engine_timer);add_TIM(engine_timer);}smooth_playback_preparing=0;song_pattern_mode=0;smooth_playback_update();}
 dirty=1;
}
void song_link_service(void) BANKED {uint16_t bpm;uint32_t start;uint8_t i,prepared;
 if(!song_link_active)return;
 if(W.state==RUN){if(syncslave){if(W.transfer&&song_hwwait>2)phase_service();}else clock_service();return;}
 if(W.state==ENDING&&!song_playing){song_link_finish();return;}
 if(expired()){song_link_finish();song_view.error=11;return;}
 if(syncslave){
  if(W.state==S_PREP){bpm=W.header[1]|((uint16_t)W.header[2]<<7);start=0;for(i=8;i>3;){start=(start<<7)|W.header[--i];}
   prepared=bpm>=30&&bpm<=240&&song_prepare(W.header[8]&1,bpm,start);
   if(W.state!=S_PREP)return; /* STOP/BEGIN may arrive while compiling. */
   if(!prepared){W.state=FAIL;W.reply=FAILED;}
   else {W.state=S_READY;W.reply=READY;}
   /* Publish only the following reply. Writing SB while an externally
      clocked poll is shifting can splice WAIT and READY into FAILED. */
  }else if(W.state==S_ARM){song_status(1);__critical{if(W.state==S_ARM){song_arm();W.state=S_LISTEN;W.reply=ARMED;}}}
  else if(W.state==FAIL){W.reply=FAILED;if(!song_view.error)song_view.error=11;}
  return;
 }
 /* Stopped handshake bytes leave a full video-frame rearm margin. */
 if(W.transfer||SC_REG&0x80||IF_REG&SIO_IFLAG||(song_pattern_mode?(uint8_t)(DIV_REG-W.sentframe)<8:W.sentframe==frame()))return;
 switch(W.state){
 case M_PREP:
  if(song_pattern_mode){W.state=M_HEADER;W.txat=0;send(BEGIN);break;}
  if(!song_prepare(W.smooth,seqbpm,W.smooth?0:song_view.cursor&~15UL)){song_link_finish();return;}
  W.state=M_HEADER;W.since=frame();W.txat=0;send(BEGIN);break;
 case M_HEADER:if(W.txat<10)send(W.header[W.txat++]);else {W.state=song_pattern_mode?M_LOCAL_PREP:M_WAIT;send(POLL);}break;
 case M_LOCAL_PREP:
  if(!song_prepare(1,seqbpm,0)){song_link_finish();return;}
  W.state=M_WAIT;W.since=frame();send(POLL);break;
 case M_WAIT:
  if(W.peer==FAILED){song_link_finish();song_view.error=11;}
  else if(W.peer==READY){W.state=M_ARM_WAIT;send(ARM);}else send(POLL);break;
 case M_ARM_WAIT:
  if(W.peer==ARMED){song_status(1);__critical{song_arm();}W.state=M_GO;send(GO);}else send(POLL);break;
 }
}

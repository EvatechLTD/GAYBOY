#pragma bank 60
#include "api.h"
#include "twink_schedule.h"
/* TWINK v1: F3,type,a,b,CRC7; 80..BF numbered clock, F9 stopped heartbeat,
   FA start, FC stop, FF panic. Reverse A5 identifies TWINK input. */
uint8_t twink_ready;
/* Independent queue: native synctx aliases the retired pulse IRQ flags.
   UI and sequencer housekeeping may still write those flags during play. */
volatile uint8_t twinktx[32];
volatile uint8_t twink_guard,twink_ended_div;
static uint16_t serviced,seen,hello,heartbeat,bpm;
static uint8_t session=1,busy;
static uint8_t crc(uint8_t t,uint8_t a,uint8_t b){uint8_t i,j,c=0,v[3];v[0]=t;v[1]=a;v[2]=b;for(j=0;j<3;j++)for(i=0;i<7;i++){uint8_t top=(c^v[j])&64;c=(c<<1)&127;if(top)c^=9;v[j]<<=1;}return c;}
static uint8_t put(uint8_t b){uint8_t next=(syncw+1)&31;if(next==syncr){overflow=1;return 0;}__critical {twinktx[syncw]=b;syncw=next;}return 1;}
uint8_t twink_queue_message(const uint8_t *data,uint8_t size) BANKED {uint8_t w=syncw,i;if(((syncr-w-1)&31)<size)return 0;for(i=0;i<size;i++){twinktx[w]=data[i];w=(w+1)&31;}__critical{syncw=w;}sync_control_service();return 1;}
static uint8_t packet(uint8_t type,uint8_t a,uint8_t b){uint8_t w=syncw;if(((syncr-w-1)&31)<5){overflow=1;return 0;}twinktx[w]=0xF3;w=(w+1)&31;twinktx[w]=type;w=(w+1)&31;twinktx[w]=a;w=(w+1)&31;twinktx[w]=b;w=(w+1)&31;twinktx[w]=crc(type,a,b);__critical {syncw=(w+1)&31;}return 1;}
/* IRQ consumer: drain one prebuilt byte without depending on a UI pass.
   No __critical calls here: their EI epilogue would nest interrupts. */
void twink_tx_tick(void) BANKED {
 if(twink_guard&&(uint8_t)(DIV_REG-twink_ended_div)>=8)twink_guard=0;
 if(synctxwait||(SC_REG&0x80)||(IF_REG&SIO_IFLAG)||twink_guard)return;
 if(syncdue){syncdue=0;SB_REG=0x80|synctick;SC_REG=0x81;}
 else if(syncr!=syncw){synctxbyte=twinktx[syncr];SB_REG=synctxbyte;syncr=(syncr+1)&31;SC_REG=0x81;}
}
void twink_reset(void) BANKED {twink_ready=0;busy=0;twink_guard=synctxwait=0;session=(session+1)&127;if(!session)session=1;twink_schedule_reset(session);bpm=0;hello=heartbeat=sys_time-120;seen=serviced=sys_time;}
void twink_panic(void) BANKED {if(syncmode!=SYNC_TWINK)return;twink_schedule_stop();seqplaying=0;if(syncarmed){__critical {syncarmed=syncdue=0;TMA_REG=TIMA_REG=syncreload;}}__critical {syncw=syncr;}put(0xFF);sync_control_service();}
void twink_transport(uint8_t playing) BANKED {uint16_t since,current;if(syncmode!=SYNC_TWINK)return;if(!playing){twink_schedule_stop();__critical {syncw=syncr;}put(0xFC);sync_control_service();return;}
 /* A stopped user may have returned from an unsupported patch to native.
    Drain the old session completely before allowing a fresh HELLO reply;
    a stale D1 must not reopen a capability rejection during playback. */
 if(twink_v2_blocked){
  while(syncr!=syncw||(SC_REG&0x80)||(IF_REG&SIO_IFLAG))sync_control_service();
  __critical{rd=wr;}twink_reset();
 }
 /* Ready A5 proves legacy presence, not timed capability. After reconnect
    allow HELLO/response to finish while the local musical clock is held.
    Never attach an epoch-zero scheduled stream to already-running music. */
 if(!twink_v2&&!twink_v2_blocked){
  seqplaying=0;__critical{since=sys_time;}
  do{twink_service();sync_control_service();__critical{current=sys_time;}}
  while(!twink_v2&&!twink_v2_blocked&&(uint16_t)(current-since)<45);
  seqplaying=1;
 }
 if(twink_v2&&twink_schedule_start()){bpm=seqbpm;put(0xFA);sync_control_service();return;}
 packet(1,session,1);packet(2,seqbpm>>7,seqbpm&127);bpm=seqbpm;put(0xFA);sync_control_service();}
void twink_note(uint8_t on,uint8_t pitch,uint8_t velocity) BANKED {if(syncmode!=SYNC_TWINK||!twink_ready)return;if(twink_scheduled&&seqplaying)return;if(!packet(on?3:4,pitch,on?velocity:0))twink_panic();sync_control_service();}
void twink_service(void) BANKED {uint16_t now;if(syncmode!=SYNC_TWINK||busy)return;busy=1;__critical{now=sys_time;}
 if(twink_staging&&twink_received){__critical{twink_received=0;}seen=now;twink_ready=1;if(twink_reply==0xD5){twink_v2_blocked=1;twink_v2=0;}else if(!twink_v2_blocked&&twink_reply==0xD7)twink_v2=3;}
 while(!twink_staging&&rd!=wr){uint8_t b=rx[rd++];if(b<128&&twink_v2&&!twink_v2_blocked){twink_ack=b;seen=now;twink_ready=1;}else if(b>=0xD1&&b<=0xD7){twink_reply=b;if(b==0xD5){twink_v2_blocked=1;twink_v2=0;}else if(!twink_v2_blocked){if(b==0xD7)twink_v2=3;else if(b==0xD6&&twink_v2<2)twink_v2=2;else if(b==0xD1&&!twink_v2)twink_v2=1;}seen=now;twink_ready=1;}else if(b==0xA5){if(!twink_ready){packet(1,session,1);packet(2,seqbpm>>7,seqbpm&127);put(seqplaying?0xFA:0xFC);dirty=1;}seen=now;twink_ready=1;}}
 /* A broken timed stream must stop cleanly, rather than leaving the local
    song running while MS silently waits for a planner that can never catch up. */
 if(twink_scheduled&&(twink_reply==0xD4||twink_reply==0xD5)){uint8_t saved=seqservicing;twink_v2_blocked=1;twink_v2=0;seqservicing=1;if(seqplaying)seq_transport();seqservicing=saved;dirty=1;}
 if(serviced!=now){serviced=now;
  if(twink_ready&&(uint16_t)(now-seen)>120){twink_ready=0;twink_schedule_reset(session);dirty=1;}
  if((uint16_t)(now-hello)>=60){hello=now;if(!twink_v2&&!twink_ready)packet(1,session,1);}
  if(bpm!=seqbpm){if(packet(2,seqbpm>>7,seqbpm&127))bpm=seqbpm;}
  if(!seqplaying&&(uint16_t)(now-heartbeat)>=15){heartbeat=now;put(0xF9);}
 }
 if(twink_ready&&!seqplaying)twink_schedule_probe();twink_schedule_service();sync_control_service();busy=0;
}

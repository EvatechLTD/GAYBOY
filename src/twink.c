#pragma bank 60
#include "api.h"
/* TWINK v1: F3,type,a,b,CRC7; 80..BF numbered clock, F9 stopped heartbeat,
   FA start, FC stop, FF panic. Reverse A5 identifies TWINK input. */
uint8_t twink_ready;
static uint16_t serviced,seen,hello,heartbeat,bpm;
static uint8_t session=1,busy;
static uint8_t crc(uint8_t t,uint8_t a,uint8_t b){uint8_t i,j,c=0,v[3];v[0]=t;v[1]=a;v[2]=b;for(j=0;j<3;j++)for(i=0;i<7;i++){uint8_t top=(c^v[j])&64;c=(c<<1)&127;if(top)c^=9;v[j]<<=1;}return c;}
static uint8_t put(uint8_t b){uint8_t next=(syncw+1)&31;if(next==syncr){overflow=1;return 0;}__critical {synctx[syncw]=b;syncw=next;}return 1;}
static uint8_t packet(uint8_t type,uint8_t a,uint8_t b){uint8_t w=syncw;if(((syncr-w-1)&31)<5){overflow=1;return 0;}synctx[w]=0xF3;w=(w+1)&31;synctx[w]=type;w=(w+1)&31;synctx[w]=a;w=(w+1)&31;synctx[w]=b;w=(w+1)&31;synctx[w]=crc(type,a,b);__critical {syncw=(w+1)&31;}return 1;}
void twink_reset(void) BANKED {twink_ready=0;busy=0;session=(session+1)&127;if(!session)session=1;bpm=0;hello=heartbeat=sys_time-120;seen=serviced=sys_time;}
void twink_panic(void) BANKED {if(syncmode!=SYNC_TWINK)return;seqplaying=0;if(syncarmed){__critical {syncarmed=syncdue=0;TMA_REG=TIMA_REG=syncreload;}}__critical {syncw=syncr;}put(0xFF);sync_control_service();}
void twink_transport(uint8_t playing) BANKED {if(syncmode!=SYNC_TWINK)return;if(!playing){__critical {syncw=syncr;}put(0xFC);sync_control_service();return;}packet(1,session,1);packet(2,seqbpm>>7,seqbpm&127);bpm=seqbpm;put(0xFA);sync_control_service();}
void twink_note(uint8_t on,uint8_t pitch,uint8_t velocity) BANKED {if(syncmode!=SYNC_TWINK||!twink_ready)return;if(!packet(on?3:4,pitch,on?velocity:0))twink_panic();sync_control_service();}
void twink_service(void) BANKED {uint16_t now;if(syncmode!=SYNC_TWINK||busy)return;busy=1;now=sys_time;
 while(rd!=wr){uint8_t b=rx[rd++];if(b==0xA5){if(!twink_ready){packet(1,session,1);packet(2,seqbpm>>7,seqbpm&127);put(seqplaying?0xFA:0xFC);dirty=1;}seen=now;twink_ready=1;}}
 if(serviced!=now){serviced=now;
  if(twink_ready&&(uint16_t)(now-seen)>120){twink_ready=0;dirty=1;}
  if((uint16_t)(now-hello)>=60){hello=now;packet(1,session,1);}
  if(bpm!=seqbpm){if(packet(2,seqbpm>>7,seqbpm&127))bpm=seqbpm;}
  if(!seqplaying&&(uint16_t)(now-heartbeat)>=15){heartbeat=now;put(0xF9);}
 }
 sync_control_service();busy=0;
}

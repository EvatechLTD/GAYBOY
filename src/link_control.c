#pragma bank 63
#include "api.h"
#include "mixer_shared.h"
#include "link_control.h"
#include "mixer_pads.h"
/* F3, body length, type, session low/high, request, payload, CRC7.
   All body bytes are seven-bit clean; real-time clocks may interleave.
   CRC7: polynomial 09, initial zero, MSB first, over length and body. */
#define HELLO 1
#define WELCOME 2
#define STATE 3
#define NAME 4
#define SET 5
#define LAUNCH 6
#define PREPARE 8
#define READY 9
#define NAME_ACK 10
LinkMirror linkmirror;
uint8_t linkstate,link_names_dirty,linkcollision;
uint8_t linkpair,link_pair_hold,link_pair_phase;
uint8_t link_ui_hold;
static uint16_t ui_quiet_since,ui_clock_frame;
static uint8_t ui_clock;
extern uint16_t seqdeadline;
void roll_clear_transition(void) BANKED;
static uint8_t pairslot=255,pair_internal;
static uint16_t pairdeadline;
uint8_t mixer_prepare_busy(void) BANKED;
void mixer_prepare_cancel(void) BANKED;
extern uint8_t seqswingphase;
volatile uint8_t linktx[26],linktxread,linktxsize;
volatile uint8_t linkbits[16],linkbitread,linkbitwrite,linkbitqueued;
static uint8_t linkbitcursor,bitshift,bitcount,bitreceiving,peer_probe;
volatile uint8_t link_peer_capable,link_alive,link_rx_dropped;
volatile uint8_t link_rx_ready;
static uint8_t incoming[24],rxsize,rxread,rxcrc;
static uint16_t session,lastseen,commandepoch,rxstamp,sentframe;
static uint8_t request,waiting,retries,serviceframe;
static uint8_t welcome,state_due,lastrequest,commandtrack,commandfield,commandvalue;
static uint8_t name_pending=255,name_crc,name_ack=255,name_ack_crc;
static uint16_t name_deadline;
static uint8_t nextfield=255,nexttrack,nextvalue;
static uint16_t nextepoch;
static uint8_t applied;
extern uint8_t syncrole;
extern uint8_t mixer_device;
extern uint16_t pattern_generation;

static uint16_t link_frames(void){uint16_t t;__critical {t=sys_time;}return t;}
static void ui_pause(void){link_ui_hold=1;ui_quiet_since=ui_clock_frame=link_frames();ui_clock=*(volatile uint8_t *)0xFFE1;}
static uint8_t crc(uint8_t c,uint8_t b){uint8_t i;for(i=0;i<7;i++){uint8_t top=(c^b)&64;c=(c<<1)&127;if(top)c^=9;b<<=1;}return c;}
static uint8_t idle(void){return linktxread==linktxsize;}
static void packet(uint8_t type,uint8_t payload){uint8_t i,c=0,n=payload+5;
 linktx[0]=0xF3;linktx[1]=n;linktx[2]=type;linktx[3]=session&127;linktx[4]=session>>7;linktx[5]=request;
 for(i=1;i<n+1;i++)c=crc(c,linktx[i]);linktx[n+1]=c;
 __critical {linktxread=0;linktxsize=n+2;}
}
void link_reset(void) BANKED {
 __critical {linktxread=linktxsize=0;memset((void *)linkbits,0,16);linkbitread=linkbitwrite=linkbitqueued=0;}
 linkbitcursor=bitshift=bitcount=bitreceiving=link_peer_capable=peer_probe=0;
 link_alive=link_rx_dropped=0;
 rxsize=rxread=link_rx_ready=welcome=state_due=waiting=0;linkstate=linkcollision=0;
 name_pending=name_ack=255;
 nextfield=255;
 applied=0;
 if(link_pair_phase)mixer_prepare_cancel();link_pair_hold=link_pair_phase=0;pairslot=255;
 link_names_dirty=255;linkmirror.namesvalid=0;linkmirror.quant=255;lastrequest=255;
}
void link_begin(void) BANKED {link_reset();session=(session+1+(uint16_t)DIV_REG+link_frames())&16383;if(!session)session=1;request=0;waiting=1;retries=0;sentframe=link_frames();linkstate=1;}

/* Playback adds NO serial transfers. A negotiated spare bit of existing
   numbered clocks carries the optional bit stream; all six sequence bits
   remain available for the original loss/recovery algorithm. 48..63 keep
   their original byte codes, leaving every essential status unambiguous. */
static void transmit(void){uint8_t budget=16,b;
 if(syncslave)return;
 if(seqplaying){
  if(!link_peer_capable||syncr!=syncw)return;
  while(budget--&&linktxread<linktxsize&&linkbitqueued<16){
   b=(linktx[linktxread]&(128>>linkbitcursor))?2:1;
   __critical {linkbits[linkbitwrite]=b;linkbitwrite=(linkbitwrite+1)&15;linkbitqueued++;}
   if(++linkbitcursor==8){linkbitcursor=0;linktxread++;if(linktxread==linktxsize&&linktx[2]!=NAME_ACK)sentframe=link_frames();}
  }
  return;
 }
 if(!syncrole)return; /* Stopped AUTO peers remain listeners. */
 __critical {if(linktxread<linktxsize&&syncr==syncw&&!syncdue&&!(SC_REG&0x80)&&!(IF_REG&(SIO_IFLAG|TIM_IFLAG|VBL_IFLAG))){SB_REG=linktx[linktxread++];SC_REG=0x81;}}
}
void link_wire_service(void) BANKED {transmit();}
void link_clock_abort(void) NONBANKED {
 if(linktxread<linktxsize||linkbitqueued){linktxread=0;linkbitcursor=0;memset((void *)linkbits,0,16);linkbitread=linkbitwrite=linkbitqueued=0;}
}
void link_clock_decode(uint8_t b,uint8_t delta) NONBANKED {
 uint8_t value;
 if(delta!=1){bitshift=bitcount=bitreceiving=0;if(!link_rx_ready)rxsize=rxread=0;return;}
 if((b&63)>=48)return;
 value=(b>>6)&1;
 if(!bitreceiving){if(!bitshift&&!value)return;bitshift=(bitshift<<1)|value;if(bitshift==0xF3){link_receive(0xF3);bitshift=bitcount=0;bitreceiving=1;}return;}
 bitshift=(bitshift<<1)|value;
 if(++bitcount==8){value=bitshift;bitshift=bitcount=0;link_receive(value);if(link_rx_ready||rxsize==254||!rxsize)bitreceiving=0;}
}
static void state_packet(void){uint8_t i;uint16_t pan=0;
 linktx[6]=mx.slot|(mx.quant<<3)|(applied?64:0);linktx[7]=(mx.pending<8?mx.pending:15)|(drumkit<<4);linktx[8]=seqmuted;linktx[9]=seqsolo;
 for(i=0;i<7;i++)linktx[10+i]=mx.level[i];
 for(i=0;i<7;i++)pan|=(uint16_t)mx.pan[i]<<(i*2);linktx[17]=pan&127;linktx[18]=pan>>7;
 linktx[19]=drummutemask&127;linktx[20]=drummutemask>>7;linktx[21]=drumsolomask&127;linktx[22]=drumsolomask>>7;linktx[23]=pattern_generation&127;linktx[24]=(pattern_generation>>7)&127;
 packet(STATE,19);
}
static void accept(void){uint8_t i,type=incoming[0],id=incoming[3];uint16_t peer=incoming[1]|((uint16_t)incoming[2]<<7);
 if(type==HELLO&&peer&&syncslave&&rxsize==8&&incoming[4]=='G'&&incoming[5]=='B'&&incoming[6]==1){
  if(peer!=session||linkstate!=2){if(link_pair_phase)mixer_prepare_cancel();link_pair_hold=link_pair_phase=0;pairslot=255;session=peer;request=id;linkstate=2;link_names_dirty=255;name_pending=255;lastrequest=255;}
  welcome=1;state_due=1;lastseen=link_frames();return;
 }
 if(peer!=session||!session)return;
 lastseen=link_frames();
 if(!syncslave){
  if(type==WELCOME&&rxsize==8&&incoming[4]=='G'&&incoming[5]=='B'&&incoming[6]==1){linkstate=2;waiting=0;dirty=1;return;}
  if(linkstate!=2)return;
  if(type==READY&&rxsize==6&&id==request&&link_pair_phase==1&&incoming[4]==pairslot){waiting=0;link_pair_phase=2;link_pair_hold=0;dirty=1;return;}
  if(type==NAME&&rxsize==22&&incoming[4]<8){uint8_t s=incoming[4];name_ack=s;name_ack_crc=0;for(i=0;i<16;i++){linkmirror.names[s][i]=incoming[5+i];name_ack_crc=crc(name_ack_crc,incoming[5+i]);}linkmirror.namesvalid|=1<<s;if(page==18&&mixer_device){pad_names_valid=0;dirty=1;}}
  if(type==STATE&&rxsize==24&&((incoming[4]>>3)&7)<=4){uint16_t pan=incoming[15]|((uint16_t)incoming[16]<<7);uint8_t oldslot=linkmirror.slot;
   linkmirror.slot=incoming[4]&7;linkmirror.pending=(incoming[5]&15)<8?(incoming[5]&15):255;linkmirror.kit=(incoming[5]>>4)<6?incoming[5]>>4:0;linkmirror.muted=incoming[6];linkmirror.solo=incoming[7];
   memcpy(linkmirror.level,incoming+8,7);for(i=0;i<7;i++)linkmirror.pan[i]=(pan>>(i*2))&3;
   linkmirror.drummutemask=incoming[17]|((uint16_t)incoming[18]<<7);linkmirror.drumsolomask=incoming[19]|((uint16_t)incoming[20]<<7);
   linkmirror.quant=(incoming[4]>>3)&7;linkmirror.epoch=incoming[21]|((uint16_t)incoming[22]<<7);
   if(id==request&&commandfield!=6){if((incoming[4]&64)&&oldslot==linkmirror.slot&&nextfield<6&&nextepoch==commandepoch)nextepoch=linkmirror.epoch;waiting=0;}if(page==18&&mixer_device)dirty=1;
  }
 }else if(linkstate==2&&type==NAME_ACK&&rxsize==7){if(incoming[4]==name_pending&&incoming[5]==name_crc)name_pending=255;
 }else if(linkstate==2&&(type==SET||type==LAUNCH||type==PREPARE)){
  if(type==SET&&rxsize==10&&incoming[4]<20&&((incoming[5]<2&&incoming[6]<2)||(incoming[4]<7&&incoming[5]==2)||(incoming[4]<7&&incoming[5]==3&&incoming[6]<4)||(incoming[5]==5&&incoming[6]>=1&&incoming[6]<=4))){
   if(id!=lastrequest){applied=0;if((incoming[7]|((uint16_t)incoming[8]<<7))==(pattern_generation&16383)){mixer_remote_apply(incoming[4],incoming[5],incoming[6]);applied=1;}}lastrequest=id;request=id;state_due=1;
  }else if(type==LAUNCH&&rxsize==6&&incoming[4]<8){
   if(id!=lastrequest){ui_pause();mx.openempty=0;mixer_launch_request(incoming[4],0);mx.openempty=0;}lastrequest=id;request=id;state_due=1;
  }else if(type==PREPARE&&rxsize==6&&incoming[4]<8){
   if(id!=lastrequest){ui_pause();mx.openempty=0;pairslot=incoming[4];link_pair_hold=1;link_pair_phase=3;pairdeadline=link_frames();pair_internal=1;mixer_launch_request(pairslot,0);mx.openempty=0;pair_internal=0;}
   else if(link_pair_phase==4)link_pair_phase=3;
   lastrequest=id;request=id;state_due=1;
  }
 }
}
uint8_t link_receive(uint8_t b) BANKED {
 if(!syncslave){/* Clock-only/legacy replies are zero outside frames. */
  /* An established peer returns this idle byte on existing clock transfers.
     Presence therefore survives foreground save/load work without polling. */
  if(!rxsize){
   if(b==0xF4)peer_probe=1;
   else if(peer_probe==1&&b=='G')peer_probe=2;
   else if(peer_probe==2&&b=='B')peer_probe=3;
   else if(peer_probe==3&&b==1){if(linkstate==2||linkstate==3)link_begin();link_peer_capable=1;peer_probe=0;}
   else peer_probe=0;
  }
  if(b==0xF4){if(linkstate==3){link_begin();link_peer_capable=1;}if(linkstate==2)lastseen=link_frames();return 1;}
  /* A delayed slave SIO can echo an essential byte. It is not a role claim;
     contention is detected explicitly while both starts are still idle. */
  if(!rxsize&&b!=0xF3)return 1;
 }else if((b>=0x80&&b<0xF0)||b==0xF8)return 0;
 if(link_rx_ready&&b<128)return 1;
 if(b==0xF3){if(link_rx_ready)return 1;rxsize=255;rxread=0;rxcrc=0;rxstamp=link_frames();return 1;}
 if(b>=0xF0&&b!=0xF3)bitshift=bitcount=bitreceiving=0;
 if(!rxsize)return 0;
 if(b&128){link_rx_ready=rxsize=rxread=0;return syncslave?0:1;}
 if(rxsize==254)return 1; /* Quarantine malformed payload; never MIDI. */
 if((uint16_t)(link_frames()-rxstamp)>3600){rxsize=254;rxread=0;return 1;}
 if(rxsize==255){if(b<5||b>24){rxsize=254;return 1;}rxsize=b;rxcrc=crc(0,b);return 1;}
 if(rxread>=rxsize){rxsize=rxread=0;return 1;}
 incoming[rxread++]=b;
 if(rxread==rxsize){if(rxcrc==b)link_rx_ready=1;else {rxsize=254;rxread=0;}}else rxcrc=crc(rxcrc,b);
 return 1;
}
uint8_t link_command(uint8_t track,uint8_t field,uint8_t value) BANKED {
 /* Queue behind an in-flight packet; service publishes only after it drains. */
 if(syncmode!=1||syncslave||linkstate!=2||linkmirror.quant>4)return 0;
 if(field==4||field==6){if(track>=8)return 0;}else if(field==5){if(value<1||value>4)return 0;}else if(track>=20||field>=4||(field==3&&value>3)||(field<2&&value>1)||value>127)return 0;
 if(waiting){if(field<6){if(nextfield<6&&(nexttrack!=track||nextfield!=field))return 0;nexttrack=track;nextfield=field;nextvalue=value;nextepoch=linkmirror.epoch;return 1;}return 0;}
 commandtrack=track;commandfield=field;commandvalue=value;commandepoch=linkmirror.epoch;request=(request+1)&127;waiting=2;retries=0;sentframe=link_frames();return 1;
}
uint8_t link_target(uint8_t track,uint8_t field) BANKED {
 if(nextfield==field&&nexttrack==track&&nextepoch==linkmirror.epoch)return nextvalue;
 if((waiting&127)==2&&commandfield==field&&commandtrack==track&&commandepoch==linkmirror.epoch)return commandvalue;
 if(track<7){if(field==2)return linkmirror.level[track];if(field==3)return linkmirror.pan[track];return !!((field?linkmirror.solo:linkmirror.muted)&(1U<<track));}
 return !!((field?linkmirror.drumsolomask:linkmirror.drummutemask)&(1U<<(track-7)));
}
uint8_t link_pending(void) BANKED {return waiting||nextfield<6;}
static void ui_release(void){uint16_t ticks;uint8_t clock=*(volatile uint8_t *)0xFFE1;
 if(clock!=ui_clock){ui_clock=clock;ui_clock_frame=link_frames();}
 /* Losing the cable must not trap the UI behind an uncommitted launch.
    Cancel presentation/preparation only; do not reset musical clock phase. */
 if((mx.pending<8||link_pair_phase)&&(uint16_t)(link_frames()-ui_clock_frame)>120){mixer_prepare_cancel();link_pair_hold=link_pair_phase=0;pairslot=255;waiting=0;}

 if(mx.pending<8||link_pair_phase||sparse_install_slot!=255||sparse_journal_retaining()||mixer_prepare_busy()||seqservicing){ui_quiet_since=link_frames();return;}
 __critical {ticks=seqticks;}
 if(seqplaying&&((uint16_t)(link_frames()-ui_quiet_since)<2||ticks>=seqdeadline||syncpending))return;
 link_ui_hold=0;seqdrawvalid=0;seqviewtrack=255;previewshape=255;pad_names_valid=0;mx.padcache=0;
 if(page==8)roll_clear_transition();dirty=1;
}
void link_service(void) BANKED {uint8_t now=(uint8_t)link_frames(),i;
 if(link_alive){__critical {link_alive=0;}lastseen=link_frames();}
 if(linkcollision&&seqplaying){seq_transport();link_reset();linkstate=4;dirty=1;return;}
 if(link_rx_ready){accept();link_rx_ready=rxsize=rxread=0;}
 if(now==serviceframe)return;serviceframe=now;
 if(link_ui_hold)ui_release();
 if(syncmode!=1)return;
 if(!syncslave&&!waiting&&nextfield<6){uint8_t field=nextfield;nextfield=255;if(nextepoch==linkmirror.epoch)link_command(nexttrack,field,nextvalue);}
 if(syncslave&&name_pending<8&&(int16_t)(link_frames()-name_deadline)>=0){link_names_dirty|=1<<name_pending;name_pending=255;}
 if(link_pair_phase&&(uint16_t)(link_frames()-pairdeadline)>1800){mixer_prepare_cancel();link_pair_hold=link_pair_phase=0;pairslot=255;waiting=0;dirty=1;}
 if(linkstate==2&&!syncslave&&(uint16_t)(link_frames()-lastseen)>180){linkstate=3;waiting=0;dirty=1;}
 if(!idle()){transmit();return;}
 if(!syncslave){
  if((waiting&128)&&(uint16_t)(link_frames()-sentframe)>(commandfield==6?900U:600U)){if(++retries>2){waiting=0;linkstate=3;dirty=1;return;}sentframe=link_frames();waiting&=127;}
  if(waiting==1){linktx[6]='G';linktx[7]='B';linktx[8]=1;packet(HELLO,3);waiting|=128;}
  else if(waiting==2){linktx[6]=commandtrack;if(commandfield==4||commandfield==6)packet(commandfield==6?PREPARE:LAUNCH,1);else {linktx[7]=commandfield;linktx[8]=commandvalue;linktx[9]=commandepoch&127;linktx[10]=commandepoch>>7;packet(SET,5);}waiting|=128;}
  else if(name_ack<8){linktx[6]=name_ack;linktx[7]=name_ack_crc;packet(NAME_ACK,2);name_ack=255;}
  else if(!seqplaying&&(linkstate==1||linkstate==2)){linktx[0]=0;linktxsize=1;linktxread=0;}
 }else if(linkstate==2){
  if(welcome){welcome=0;linktx[6]='G';linktx[7]='B';linktx[8]=1;packet(WELCOME,3);}
  else if(link_pair_phase==3&&mx.pending==pairslot&&!mixer_prepare_busy()){linktx[6]=pairslot;packet(READY,1);link_pair_phase=4;}
  else if(state_due||!(now&31)){state_due=0;state_packet();}
  else if(link_names_dirty&&name_pending>=8){char name[17];uint8_t j;for(i=0;i<8;i++)if(link_names_dirty&(1<<i))break;link_names_dirty&=~(1<<i);getname(i,name);name_crc=0;for(j=0;j<16;j++){name[j]&=127;name_crc=crc(name_crc,name[j]);}name_pending=i;/* Include the slow forward ACK at low BPM, and retry dropped replies
     sooner at high BPM. No extra transfers: replies replace idle bytes. */
   name_deadline=link_frames()+36000U/seqbpm+120U;linktx[6]=i;memcpy((void *)(linktx+7),name,16);packet(NAME,17);}
 }
 transmit();
}
uint8_t link_pair_request(uint8_t slot,uint8_t edit) BANKED {
 if(pair_internal)return 0;
 if(syncslave&&link_pair_hold)return 1;
 if(!linkpair||syncmode!=1||syncslave||!seqplaying||(edit&&slot==mx.slot))return 0;
 if(link_pair_phase||!link_command(slot,6,0))return 1;
 pairslot=slot;link_pair_hold=1;link_pair_phase=1;pairdeadline=link_frames();
 if(!mx.quant)mx.quant=4;
 pair_internal=1;mixer_launch_request(slot,edit);pair_internal=0;dirty=1;return 1;
}
void link_pair_master_launched(void) BANKED {if((link_pair_phase==2||link_pair_phase==6)&&mx.slot==pairslot){link_pair_phase=0;pairslot=255;}}
uint8_t link_pair_marker(void) BANKED {
 if(link_pair_phase!=4||!link_pair_hold||mx.pending!=pairslot||mixer_prepare_busy())return 0;
 link_pair_hold=link_pair_phase=0;mx.boundary=0;seqswingphase=0;pair_internal=1;mixer_activate(pairslot,0);pair_internal=0;pairslot=255;state_due=1;return 1;
}

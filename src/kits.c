#pragma bank 37
#include "api.h"
#include "kit_labels.h"
#include "drum_rows.h"
#include "mixer_shared.h"
#include "mixer_drum_names.h"
extern uint8_t noisepatch[2][5],pulsekickpatch[8],seqselectused,globalmod[10];
void mixer_pattern_changed(void) BANKED;
uint8_t kitchoice=1,kitslot;
static uint8_t filemode,filetarget=255,fileorigin=8,contexttrack=255,contextvoice=255;
static uint8_t kitsavedchoice,kitconfirm,kiterror;
#define KIT_BUFFER ((uint8_t *)0xB000)
const char * const kitnames[]={"AMEN ORIGINAL","TR-808","TR-909","TR-707","LINNDRUM","OBERHEIM DMX","SLAP808","SLAM909"};
static const char * const slotnames[]={"KICK","SNARE","CLOSED HAT","OPEN HAT","CLAP","LOW TOM","HIGH TOM","PERCUSSION"};
static const char * const amennames[]={"KK1","KK2","KK3","SC1","SC2","HC1","CL1","KC1","CY1","PSH"};
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){while(*s&&x<20)canvas[y*20+x++]=*s++-32+(inv?96:0);}
void kits_label(uint8_t row,uint8_t *dst) BANKED {memcpy(dst,kitlabels+(uint16_t)row*48,48);}
void drum_file_capture_context(void) BANKED {contexttrack=page==8?seqtrack:255;contextvoice=contexttrack==6&&seqhead==6?DRUM_VOICE_ROW(drumrow):255;}
uint8_t drum_file_context(void) BANKED {return contexttrack==6&&contextvoice==255;}
uint8_t drum_file_sample_context(void) BANKED {return contexttrack==6&&contextvoice<10;}
void drum_file_context_name(uint8_t *name) BANKED {uint8_t i;const char *s;if(contextvoice>=13){memcpy(name,"DRUMS",6);return;}s=mixer_drum_name(drumkit,contextvoice);for(i=0;i<3;i++)name[i]=s[i];name[3]=0;}
static uint16_t checksum(void){uint8_t i;uint16_t sum=0x4b44;for(i=4;i<158;i++)sum=(sum<<1|sum>>15)^KIT_BUFFER[i];return sum;}
static uint8_t kit_valid(void){uint16_t crc;if(memcmp(KIT_BUFFER,"DKT1",4)||KIT_BUFFER[16]>7||KIT_BUFFER[17]!='D'||KIT_BUFFER[18]!=1)return 0;crc=checksum();return KIT_BUFFER[158]==(uint8_t)crc&&KIT_BUFFER[159]==(uint8_t)(crc>>8);}
static uint8_t readkit(uint8_t slot){if(slot>=8)return 0;resident_kit_read(slot,KIT_BUFFER);return kit_valid();}
uint8_t drum_kit_save(uint8_t slot) BANKED {uint16_t crc;if(slot>=8||sparse_enabled!=1)return 0;
 memset(KIT_BUFFER,0,DRUM_KIT_BYTES);memcpy(KIT_BUFFER,"DKT1",4);memcpy(KIT_BUFFER+4,"USER KIT 1",10);KIT_BUFFER[13]='1'+slot;
 KIT_BUFFER[16]=drumkit;drum_map_capture(KIT_BUFFER+17);memcpy(KIT_BUFFER+39,noisepatch,10);memcpy(KIT_BUFFER+49,pulsekickpatch,8);
 memcpy(KIT_BUFFER+57,evalpatch[4],64);memcpy(KIT_BUFFER+121,coarsepitch[4],12);memcpy(KIT_BUFFER+133,&drummutemask,2);memcpy(KIT_BUFFER+135,&drumsolomask,2);KIT_BUFFER[137]=mx.level[6];KIT_BUFFER[138]=mx.pan[6];memcpy(KIT_BUFFER+139,globalmod,10);
 crc=checksum();KIT_BUFFER[158]=crc;KIT_BUFFER[159]=crc>>8;resident_kit_write(slot,KIT_BUFFER);return 1;
}
static void changed(void){eval_moddirty=1;eval_drum_dirty();seqirqdirty=1;seqdrawvalid=0;seqviewtrack=255;previewshape=255;mixer_pattern_changed();dirty=1;}
uint8_t drum_kit_load(uint8_t slot) BANKED {if(!readkit(slot))return 0;
 drum_stop();drumkit=KIT_BUFFER[16];drum_map_restore(KIT_BUFFER+17);memcpy(noisepatch,KIT_BUFFER+39,10);memcpy(pulsekickpatch,KIT_BUFFER+49,8);
 memcpy(evalpatch[4],KIT_BUFFER+57,64);memcpy(coarsepitch[4],KIT_BUFFER+121,12);memcpy(&drummutemask,KIT_BUFFER+133,2);memcpy(&drumsolomask,KIT_BUFFER+135,2);mx.level[6]=KIT_BUFFER[137];mx.pan[6]=KIT_BUFFER[138];memcpy(globalmod,KIT_BUFFER+139,10);changed();return 1;
}
void drum_file_open(uint8_t mode) BANKED {fileorigin=page;filemode=mode;filetarget=contextvoice;kitconfirm=kiterror=0;
 mixer_prepare_cancel();sparse_finish_install();kitsavedchoice=0;kitchoice=drumkit<8?drumkit:1;
 if(mode==2&&filetarget<10){if(DRUM_MAPPED){kitchoice=drumsourcekit[filetarget];kitslot=drumsourceslot[filetarget];}else kitslot=filetarget;if(kitslot>=(kitchoice?8:10))kitslot=0;}
 else kitslot=0;page=23;dirty=1;
}
static void factory_load(void){uint8_t c;static const uint8_t noise[10]={10,0,1,1,1,14,4,2,0,1};static const uint8_t kick[8]={15,48,2,1,1,2,24,1};
 drum_stop();drum_map_factory(kitchoice);memcpy(noisepatch,noise,10);memcpy(pulsekickpatch,kick,8);memset(evalpatch[4],0,64);memset(coarsepitch[4],0,12);
 for(c=4;c<8;c++){evalpatch[c][EV_DIV]=4;evalpatch[c][EV_RETRIGGER]=1;evalpatch[c][EV_MS]=125;}evalpatch[4][0]=evalpatch[4][1]=evalpatch[4][2]=127;drummutemask=drumsolomask=0;mx.level[6]=127;mx.pan[6]=3;changed();
}
static void close(void){drum_stop();page=fileorigin;if(page==8){seqdrawvalid=0;seqviewtrack=255;}seqselectused=1;dirty=1;}
static void kit_number(uint8_t x,uint8_t y,uint8_t n,uint8_t inv){canvas[y*20+x]=16+n+(inv?96:0);}
void kits_render(void) BANKED {uint8_t i,start,n;char name[6];memset(canvas,0,360);memset(canvas,96,20);text(0,0,filemode==2?"LOAD SAMPLE":filemode==1?"SAVE KIT":"LOAD KIT",1);
 if(kitconfirm){text(0,4,"REPLACE USER KIT?",0);kit_number(17,4,kitsavedchoice+1,0);text(2,8,"A REPLACE",0);text(2,10,"B/SELECT CANCEL",0);return;}
 if(filemode==2){text(0,2,"TO CHANNEL",0);name[0]='0'+(filetarget+1)/10;name[1]='0'+(filetarget+1)%10;name[2]=0;text(11,2,name,0);drum_file_context_name((uint8_t *)name);text(15,2,name,0);text(0,4,"SOURCE KIT",0);text(1,6,kitnames[kitchoice],1);text(0,8,"SOURCE SAMPLE",0);text(1,10,kitchoice?slotnames[kitslot]:amennames[kitslot],1);kit_number(18,10,(kitslot+1)/10,1);kit_number(19,10,(kitslot+1)%10,1);text(0,13,"U/D KIT  L/R SAMPLE",0);text(0,15,"A LOAD   B AUDITION",0);}
 else {start=filemode==1?8:kitchoice<8?0:8;for(i=0;i<8;i++){n=start+i;if(n<8){text(1,3+i,kitnames[n],kitchoice==n);}else{text(1,3+i,"USER KIT",filemode==1?kitsavedchoice==i:kitchoice==n);kit_number(10,3+i,i+1,filemode==1?kitsavedchoice==i:kitchoice==n);if(!readkit(i))text(13,3+i,"EMPTY",filemode==1?kitsavedchoice==i:kitchoice==n);}mixfill();}
  text(0,12,filemode==1?"DRUMSYNTH + SAMPLES":"U/D KIT  L/R BANK",0);text(0,13,filemode==1?"ALL CHANNEL ROUTING":"FACTORY / USER KITS",0);text(0,15,filemode==1?"A SAVE":"A LOAD   B AUDITION",0);
 }
 if(kiterror)text(0,16,"EMPTY / INVALID KIT",0);text(0,17,"SELECT BACK",0);
}
void kits_input(uint8_t p,uint8_t edge) BANKED {uint8_t count; (void)p;if(!edge)return;
 if(kitconfirm){if(edge&(J_B|J_SELECT)){kitconfirm=0;dirty=1;return;}if(edge&J_A){if(drum_kit_save(kitsavedchoice))close();else kiterror=1;kitconfirm=0;dirty=1;}return;}
 if(edge&J_SELECT){close();return;}kiterror=0;
 if(filemode==2){if(edge&J_UP)kitchoice=kitchoice?kitchoice-1:7;if(edge&J_DOWN)kitchoice=(kitchoice+1)%8;count=kitchoice?8:10;if(kitslot>=count)kitslot=0;if(edge&J_LEFT)kitslot=kitslot?kitslot-1:count-1;if(edge&J_RIGHT)kitslot=(kitslot+1)%count;
  if(edge&J_B)drum_source_audition(kitchoice,kitslot);
  if(edge&J_A){drum_stop();drum_map_assign(filetarget,kitchoice,kitslot);changed();close();}
 }else if(filemode==1){if(edge&J_UP)kitsavedchoice=kitsavedchoice?kitsavedchoice-1:7;if(edge&J_DOWN)kitsavedchoice=(kitsavedchoice+1)%8;if(edge&J_A){if(readkit(kitsavedchoice))kitconfirm=1;else if(drum_kit_save(kitsavedchoice))close();else kiterror=1;}}
 else {if(edge&J_UP)kitchoice=kitchoice?kitchoice-1:15;if(edge&J_DOWN)kitchoice=(kitchoice+1)%16;if(edge&(J_LEFT|J_RIGHT))kitchoice=kitchoice<8?8:0;
  if(edge&J_B){if(kitchoice<8)drum_source_audition(kitchoice,0);else if(readkit(kitchoice-8))drum_source_audition(KIT_BUFFER[19],KIT_BUFFER[29]);else kiterror=1;}
  if(edge&J_A){if(kitchoice<8){factory_load();close();}else if(drum_kit_load(kitchoice-8))close();else kiterror=1;}
 }dirty=1;
}

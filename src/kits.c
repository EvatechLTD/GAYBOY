#pragma bank 37
#include "api.h"
#include "kit_labels.h"
/* drum_start is local to bank 17; audition through its banked wrapper. */
void kit_audition(uint8_t row) BANKED;
uint8_t kitchoice=1,kitslot;
const char * const kitnames[]={"AMEN ORIGINAL","TR-808","TR-909","TR-707","LINNDRUM","OBERHEIM DMX"};
const char * const slotnames[]={"KICK","SNARE","CLOSED HAT","OPEN HAT","CLAP","LOW TOM","HIGH TOM","PERCUSSION"};
void kit_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){while(*s&&x<20)canvas[y*20+x++]=*s++-32+(inv?96:0);}
void kits_label(uint8_t row,uint8_t *dst) BANKED {memcpy(dst,kitlabels+(uint16_t)row*48,48);}
void kits_render(void) BANKED {uint8_t i;memset(canvas,0,360);memset(canvas,96,20);kit_text(0,0,"KITS",1);for(i=0;i<6;i++){if(i==kitchoice)memset(canvas+(3+i)*20,96,20);kit_text(0,3+i,i==drumkit?"*":" ",i==kitchoice);kit_text(2,3+i,kitnames[i],i==kitchoice);}kit_text(0,10,"A LOAD   B AUDITION",0);kit_text(0,12,"L/R SAMPLE",0);kit_text(0,13,slotnames[kitslot],0);kit_text(0,16,"* LOADED KIT",0);}
void kits_input(uint8_t p,uint8_t edge) BANKED {(void)p;if(edge&J_UP)kitchoice=kitchoice?kitchoice-1:5;if(edge&J_DOWN)kitchoice=(kitchoice+1)%6;if(edge&J_LEFT)kitslot=kitslot?kitslot-1:7;if(edge&J_RIGHT)kitslot=(kitslot+1)%8;if(edge&J_A){drum_stop();drumkit=kitchoice;}if(edge&J_B)kit_audition(kitslot);dirty=1;}

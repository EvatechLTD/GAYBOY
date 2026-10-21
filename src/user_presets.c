#pragma bank 48
#include "api.h"
#include "user_presets.h"
#include "mixer_shared.h"
void resident_user_read(uint16_t o,uint8_t *d,uint16_t n) BANKED;void resident_user_write(uint16_t o,const uint8_t *d,uint16_t n) BANKED;
void mixer_pattern_changed(void) BANKED;extern uint8_t noisepatch[2][5],pulsekickpatch[8];
/* ROM factory bank per drum voice. User SRAM slots and names stay unchanged.
   PK: level,note,duty,fall,sweep time,shift,length,down.
   Noise: level,clock,divisor,7-bit width,fall. All modulation is off. */
typedef struct {char name[9];uint8_t patch[8];} DrumFactory;
static const DrumFactory kickpresets[]={
 {"TR-808", {15,58,2,2,1,3,64,1}},
 {"TR-909", {10,64,2,2,1,3,64,1}},
 {"TR-606", {11,52,2,1,1,3,44,1}},
 {"TR-707", {14,67,2,1,1,2,56,1}},
 {"TR-626", {12,63,1,1,1,2,48,1}},
 {"TR-505", {9,58,2,1,1,2,36,1}},
 {"CR-78",  {8,50,2,1,1,4,32,1}},
 {"LINNDRUM",{15,67,2,1,1,3,60,1}},
 {"DMX",    {15,67,1,1,1,3,60,1}},
 {"SP-1200",{15,64,1,1,1,2,60,1}},
 {"MPC60",  {11,61,2,2,1,3,64,1}},
 {"SIM SDSV",{12,79,2,2,1,5,64,1}},
 {"RIMSHOT",{15,84,0,1,1,1,8,1}}
};
static const DrumFactory hatpresets[]={
 {"CLOSED",  {8,0,1,0,1}},
 {"OPEN",    {15,0,1,0,3}},
 {"606 CH",  {7,0,2,0,1}},
 {"606 OH",  {13,0,2,0,3}},
 {"808 CH",  {8,1,1,1,1}},
 {"808 OH",  {15,1,1,1,3}},
 {"METAL CH",{6,0,3,1,1}},
 {"METAL OH",{14,0,3,1,4}}
};
static const DrumFactory snarepresets[]={
 {"HARD SN", {15,3,2,0,1}},
 {"SOFT SN", {10,4,3,0,2}},
 {"606 SN",  {13,3,3,0,1}},
 {"808 SN",  {15,4,2,0,1}},
 {"909 SN",  {15,2,4,0,1}},
 {"CLAPISH", {14,3,5,0,2}},
 {"RIM TICK",{5,2,4,1,1}},
 {"METAL SN",{15,4,2,1,1}}
};
uint8_t drum_factory_count(uint8_t c) BANKED {return c==7?sizeof(kickpresets)/sizeof(DrumFactory):c==5||c==6?8:0;}
static const DrumFactory *drum_factory(uint8_t c,uint8_t i){return c==7?kickpresets+i:c==5?hatpresets+i:snarepresets+i;}
void drum_factory_name(uint8_t c,uint8_t i,uint8_t *name) BANKED {if(i>=drum_factory_count(c)){memcpy(name,"EMPTY   ",8);name[8]=0;return;}memcpy(name,drum_factory(c,i)->name,9);}
uint8_t drum_factory_load(uint8_t c,uint8_t i) BANKED {if(i>=drum_factory_count(c))return 0;
 memcpy(c==7?pulsekickpatch:noisepatch[c-5],drum_factory(c,i)->patch,c==7?8:5);
 /* Loading a hardware preset must not inherit software pitch/ADSR routes. */
 memset(evalpatch[c],0,16);evalpatch[c][EV_DIV]=4;evalpatch[c][EV_RETRIGGER]=1;evalpatch[c][EV_MS]=125;
 memset(coarsepitch[c],0,3);wavepending=1;eval_drum_dirty();seqirqdirty=1;mixer_pattern_changed();previewshape=255;dirty=1;return 1;}
static uint8_t head(uint8_t slot,uint8_t *h){if(slot>=32)return 0;resident_user_read((uint16_t)slot*64,h,2);return h[0]=='U'&&(h[1]<4||h[1]>=5&&h[1]<=7);}
uint16_t user_preset_reference(uint8_t slot) BANKED {uint8_t h[2];return head(slot,h)?slot:65535U;}
uint8_t user_preset_type(uint8_t slot) BANKED {uint8_t h[2];return head(slot,h)?h[1]:255;}
void user_preset_name(uint8_t slot,uint8_t *n) BANKED {uint8_t h[2];if(head(slot,h))resident_user_read((uint16_t)slot*64+2,n,8);else memcpy(n,"EMPTY   ",8);n[8]=0;}
void user_bank_name(uint8_t bank,uint8_t *n) BANKED {resident_user_read(2048U+bank*8,n,8);if(!n[0]||n[0]==255){memcpy(n,"USER 1  ",8);n[5]='1'+bank;}n[8]=0;}
uint8_t user_preset_rename(uint8_t slot,const uint8_t *n) BANKED {if(slot>=32)return 0;resident_user_write((uint16_t)slot*64+2,n,8);return 1;}
uint8_t user_bank_rename(uint8_t bank,const uint8_t *n) BANKED {if(bank>=4)return 0;resident_user_write(2048U+bank*8,n,8);return 1;}
uint8_t user_preset_remove(uint8_t slot) BANKED {uint8_t z=0;if(slot>=32)return 0;resident_user_write((uint16_t)slot*64,&z,1);return 1;}
uint8_t user_bank_clear(uint8_t bank) BANKED {uint8_t i;if(bank>=4)return 0;for(i=0;i<8;i++)user_preset_remove(bank*8+i);return 1;}
uint8_t user_preset_publish(uint8_t s,uint16_t o,uint8_t c,const uint8_t *n) BANKED {(void)s;(void)o;(void)c;(void)n;return 0;}
uint8_t user_preset_save(uint8_t slot,uint8_t c) BANKED {uint8_t b[64],at=10,old[2];if(slot>=32||c==4||c>7)return 0;memset(b,0,64);b[0]='U';b[1]=c;if(head(slot,old))resident_user_read((uint16_t)slot*64+2,b+2,8);else{memcpy(b+2,"TONE 01 ",8);b[7]='0'+(slot+1)/10;b[8]='0'+(slot+1)%10;}if(c<4){memcpy(b+at,param[c],26);at+=26;if(c<3){memcpy(b+at,finepitch+c,2);at+=2;}}else if(c==7){memcpy(b+at,pulsekickpatch,8);at+=8;}else{memcpy(b+at,noisepatch[c-5],5);at+=5;}memcpy(b+at,evalpatch[c],16);memcpy(b+61,coarsepitch[c],3);resident_user_write((uint16_t)slot*64,b,64);return 1;}
uint8_t user_preset_load(uint8_t slot,uint8_t c) BANKED {uint8_t b[64],at=10;if(slot>=32||c==4||c>7)return 0;resident_user_read((uint16_t)slot*64,b,64);if(b[0]!='U'||!(b[1]==c||b[1]<2&&c<2))return 0;if(c<4){stop(c);memcpy(param[c],b+at,26);at+=26;if(c<3){memcpy(finepitch+c,b+at,2);at+=2;}}else if(c==7){memcpy(pulsekickpatch,b+at,8);at+=8;}else{memcpy(noisepatch[c-5],b+at,5);at+=5;}memcpy(evalpatch[c],b+at,16);memcpy(coarsepitch[c],b+61,3);wavepending=1;eval_drum_dirty();seqirqdirty=1;mixer_pattern_changed();previewshape=255;dirty=1;return 1;}

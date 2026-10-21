#pragma bank 48
#include "api.h"
#include "user_presets.h"
#include "mixer_shared.h"
void resident_user_read(uint16_t o,uint8_t *d,uint16_t n) BANKED;void resident_user_write(uint16_t o,const uint8_t *d,uint16_t n) BANKED;
void mixer_pattern_changed(void) BANKED;extern uint8_t noisepatch[2][5],pulsekickpatch[8];
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

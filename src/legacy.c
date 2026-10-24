#pragma bank 2
#include "api.h"
void seq_native_touch(void) NONBANKED;
#include "presets.h"
void stocktable(uint8_t c,uint8_t n) BANKED {uint8_t i,b=stocktables[n];int8_t *dst=&tables[c][0][0];const int8_t *p=stockpitch[b&3],*s=stockshape[(b>>2)&15],*pan=stockpan[b>>6];for(i=0;i<8;i++){*dst++=*p++;*dst++=(*s+i)&s[1];*dst++=*pan++;}}
/* Neutral APU instruments at boot. Browsing still loads the stock library. */
const uint8_t startupvalues[26]={2,15,0,0,0,0,0,0,0,0,7,0,7,0,0,1,0,0,4,0,3,3,0,0,0,2};
void startup(void) BANKED {uint8_t c,i;for(c=0;c<4;c++){load(c,c*10);memcpy(param[c],startupvalues,26);memset(mods[c],0,6);tablemode[c]=0;tablelen[c]=1;for(i=0;i<8;i++){tables[c][i][0]=0;tables[c][i][1]=c<2?(c?1:2):c==2?6:4;tables[c][i][2]=3;}edited[c]=1;held[c]=255;}
 param[0][1]=param[1][1]=8;param[1][0]=1;param[2][14]=6;param[3][1]=15;param[3][3]=3;master=0x77;route=0xFF;vin=0;globals();}
void enginepitch(void) BANKED {} void enginenote(uint8_t n,uint8_t v,uint8_t o) BANKED {(void)n;(void)v;(void)o;}
void engineoff(uint8_t n) BANKED {(void)n;} void enginesustain(uint8_t on) BANKED {(void)on;}
void engineframe(void) BANKED {} void engineset(uint8_t mode) BANKED {(void)mode;}
void enginestop(void) BANKED {drumenabled=0;if(druminit)drumon[0]=drumon[1]=0;mixready[0]=mixready[1]=mixrunning=mixread=mixwrite=0;NR30_REG=0;}
uint16_t ddsvalue(uint8_t n) BANKED {(void)n;return 0;} uint16_t ddsfine(uint8_t n,uint8_t c) BANKED {(void)n;(void)c;return 0;}
void mixpack(void) __naked {
 __asm
 push bc
 ld a,(_mixwrite)
 swap a
 ld e,a
 ld d,#0
 ld hl,#_mixbuffer
 add hl,de
 ld d,h
 ld e,l
 ld hl,#_mixsamples
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 pop bc
 ret
 __endasm;
}
void legacyfill(void) BANKED {}
__at (0xA400) uint8_t waveimage[16];
static uint8_t wavevalid,waveshape,wavecustom;
void wave(void) BANKED {uint8_t i,shape=param[2][14]&31;const uint8_t *source;if(waveengine==3)return;NR30_REG=0;if(wavevalid&&wavecustom==custom&&(custom?!memcmp(waveimage,customwave,16):waveshape==shape))return;source=custom?customwave:monowaves[shape];for(i=0;i<16;i++)REG(0xff30+i)=waveimage[i]=source[i];waveshape=shape;wavecustom=custom;wavevalid=1;}
void wave_cache_invalidate(void) BANKED {wavevalid=0;wavepending=1;}
void editirq_wave_capture(uint8_t *out) BANKED {memcpy(out,custom?customwave:monowaves[param[2][14]&31],16);}
void stagewave(void) BANKED {seq_native_touch();memcpy(customwave,monowaves[param[2][14]&31],16);}
void drum_enable(void) BANKED {uint8_t pan=mixer_pan(6),level=mixer_velocity(6,127);pcmoutlevel=level?level>84?1:level>42?2:3:0;route&=~0x44;if(pan&1)route|=4;if(pan&2)route|=0x40;NR51_REG=route;drumtail=0;if(waveengine==3)return;wavevalid=0;TAC_REG=0;enginestop();waveengine=3;drumsub=0;TMA_REG=TIMA_REG=73;if(syncarmed)sync_timer_config();IF_REG&=~TIM_IFLAG;TAC_REG=6;NR32_REG=0x20;}

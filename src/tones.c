#pragma bank 39
#pragma opt_code_speed
#include "api.h"
#include "tones.h"
/* Packed saves stay inside each existing 2560-byte slot, below the battery
   magic at offset2500. Decode into a separate cache before the handoff. */
#define PACKED ((uint8_t *)0xB871)
#define RAW ((uint8_t *)0xBA00)
extern uint8_t w2tablemode,w2tablelen,w2tablespeed;
extern int8_t w2tables[8][3];
extern __at (0xAC60) uint8_t noisepatch[2][5];
extern uint8_t pulsekickpatch[8];
static uint16_t bitpos,rawpos;
static uint8_t operation,toneok,savedengine;
/* Optional extension in formerly zero padding. Factory kicks stay all-zero
   on disk, so existing saves and the original416-field layout stay intact. */
#define KICK_EXTENSION 224U
#define KICK_RAW (RAW+464U)
static const uint8_t tonekickfactory[8]={15,48,2,1,1,2,24,1};
static const uint8_t tonekickmax[8]={15,96,3,7,7,7,64,1};
static void kick_pack(void){uint8_t i,sum=0,*p=TONE_PACK+KICK_EXTENSION;if(!memcmp(pulsekickpatch,tonekickfactory,8))return;p[0]='P';p[1]='K';p[2]=1;for(i=0;i<8;i++){p[3+i]=pulsekickpatch[i];sum+=p[3+i];}p[11]=sum^0xA5;}
static uint8_t kick_decode(void){uint8_t i,sum=0,any=0,*p=PACKED+KICK_EXTENSION;for(i=0;i<12;i++)any|=p[i];if(!any){memcpy(KICK_RAW,tonekickfactory,8);return 1;}if(p[0]!='P'||p[1]!='K'||p[2]!=1)return 0;for(i=0;i<8;i++){if(p[3+i]>tonekickmax[i])return 0;sum+=p[3+i];KICK_RAW[i]=p[3+i];}return p[11]==(uint8_t)(sum^0xA5);}
/* Near ABI: value DE, width A, result BC. Walk a packed bit cursor in
   registers, avoiding per-bit C spills and variable shifts. Packing walks
   LSB first; decoding walks the same field backwards into a 16-bit result. */
static uint16_t bits(uint16_t value,uint8_t n) __naked { __asm
 push de
 push af
 ld hl,#_bitpos
 ld c,(hl)
 inc hl
 ld b,(hl)
 ldhl sp,#1
 ld a,(hl)
 add a,c
 ld (_bitpos),a
 ld a,b
 adc a,#0
 ld (_bitpos+1),a
 ld a,(_operation)
 or a,a
 jr z,tone_bits_pack_base$
 ldhl sp,#1
 ld a,(hl)
 dec a
 add a,c
 ld c,a
 ld a,b
 adc a,#0
 ld b,a
 ld hl,#0xb871
 jr tone_bits_pointer$
tone_bits_pack_base$:
 ld hl,#0xbd00
tone_bits_pointer$:
 ld a,c
 and #7
 push af
 srl b
 rr c
 srl b
 rr c
 srl b
 rr c
 add hl,bc
 pop af
 ld b,#1
 or a,a
 jr z,tone_bits_mask_done$
tone_bits_mask$:
 sla b
 dec a
 jr nz,tone_bits_mask$
tone_bits_mask_done$:
 pop af
 ld c,a
 pop de
 ld a,(_operation)
 or a,a
 jr nz,tone_bits_decode$
tone_bits_pack$:
 srl d
 rr e
 jr nc,tone_bits_pack_skip$
 ld a,(hl)
 or a,b
 ld (hl),a
tone_bits_pack_skip$:
 sla b
 jr nz,tone_bits_pack_next$
 ld b,#1
 inc hl
tone_bits_pack_next$:
 dec c
 jr nz,tone_bits_pack$
 ld bc,#0
 ret
tone_bits_decode$:
 ld de,#0
tone_bits_read$:
 sla e
 rl d
 ld a,(hl)
 and a,b
 jr z,tone_bits_read_skip$
 inc e
tone_bits_read_skip$:
 srl b
 jr nz,tone_bits_read_next$
 ld b,#128
 dec hl
tone_bits_read_next$:
 dec c
 jr nz,tone_bits_read$
 ld b,d
 ld c,e
 ret
 __endasm; }

typedef struct {void *destination;uint16_t maximum;uint8_t width,flags;} ToneField;
static const ToneField tonefields[]={
{&param[0][0],3,2,0},
{&param[0][1],15,4,0},
{&param[0][2],1,1,0},
{&param[0][3],7,3,0},
{&param[0][4],7,3,0},
{&param[0][5],1,1,0},
{&param[0][6],7,3,0},
{&param[0][7],63,6,0},
{&param[0][8],1,1,0},
{&param[0][9],1,1,0},
{&param[0][10],7,3,0},
{&param[0][11],1,1,0},
{&param[0][12],7,3,0},
{&param[0][13],1,1,0},
{&param[0][14],15,4,0},
{&param[0][15],3,2,0},
{&param[0][16],255,8,0},
{&param[0][17],1,1,0},
{&param[0][18],15,4,0},
{&param[0][19],1,1,0},
{&param[0][20],7,3,0},
{&param[0][21],3,2,0},
{&param[0][22],1,1,0},
{&param[0][23],1,1,0},
{&param[0][24],1,1,0},
{&param[0][25],24,5,0},
{&program[0],99,7,0},
{&edited[0],1,1,0},
{&mods[0][0],15,4,0},
{&mods[0][1],4,3,0},
{&mods[0][2],3,2,0},
{&mods[0][3],7,3,0},
{&mods[0][4],16,5,0},
{&mods[0][5],63,6,0},
{&tablemode[0],3,2,0},
{&tablelen[0],8,4,2},
{&tables[0][0][0],48,6,4},
{&tables[0][0][1],15,4,0},
{&tables[0][0][2],3,2,0},
{&tables[0][1][0],48,6,4},
{&tables[0][1][1],15,4,0},
{&tables[0][1][2],3,2,0},
{&tables[0][2][0],48,6,4},
{&tables[0][2][1],15,4,0},
{&tables[0][2][2],3,2,0},
{&tables[0][3][0],48,6,4},
{&tables[0][3][1],15,4,0},
{&tables[0][3][2],3,2,0},
{&tables[0][4][0],48,6,4},
{&tables[0][4][1],15,4,0},
{&tables[0][4][2],3,2,0},
{&tables[0][5][0],48,6,4},
{&tables[0][5][1],15,4,0},
{&tables[0][5][2],3,2,0},
{&tables[0][6][0],48,6,4},
{&tables[0][6][1],15,4,0},
{&tables[0][6][2],3,2,0},
{&tables[0][7][0],48,6,4},
{&tables[0][7][1],15,4,0},
{&tables[0][7][2],3,2,0},
{&param[1][0],3,2,0},
{&param[1][1],15,4,0},
{&param[1][2],1,1,0},
{&param[1][3],7,3,0},
{&param[1][4],7,3,0},
{&param[1][5],1,1,0},
{&param[1][6],7,3,0},
{&param[1][7],63,6,0},
{&param[1][8],1,1,0},
{&param[1][9],1,1,0},
{&param[1][10],7,3,0},
{&param[1][11],1,1,0},
{&param[1][12],7,3,0},
{&param[1][13],1,1,0},
{&param[1][14],15,4,0},
{&param[1][15],3,2,0},
{&param[1][16],255,8,0},
{&param[1][17],1,1,0},
{&param[1][18],15,4,0},
{&param[1][19],1,1,0},
{&param[1][20],7,3,0},
{&param[1][21],3,2,0},
{&param[1][22],1,1,0},
{&param[1][23],1,1,0},
{&param[1][24],1,1,0},
{&param[1][25],24,5,0},
{&program[1],99,7,0},
{&edited[1],1,1,0},
{&mods[1][0],15,4,0},
{&mods[1][1],4,3,0},
{&mods[1][2],3,2,0},
{&mods[1][3],7,3,0},
{&mods[1][4],16,5,0},
{&mods[1][5],63,6,0},
{&tablemode[1],3,2,0},
{&tablelen[1],8,4,2},
{&tables[1][0][0],48,6,4},
{&tables[1][0][1],15,4,0},
{&tables[1][0][2],3,2,0},
{&tables[1][1][0],48,6,4},
{&tables[1][1][1],15,4,0},
{&tables[1][1][2],3,2,0},
{&tables[1][2][0],48,6,4},
{&tables[1][2][1],15,4,0},
{&tables[1][2][2],3,2,0},
{&tables[1][3][0],48,6,4},
{&tables[1][3][1],15,4,0},
{&tables[1][3][2],3,2,0},
{&tables[1][4][0],48,6,4},
{&tables[1][4][1],15,4,0},
{&tables[1][4][2],3,2,0},
{&tables[1][5][0],48,6,4},
{&tables[1][5][1],15,4,0},
{&tables[1][5][2],3,2,0},
{&tables[1][6][0],48,6,4},
{&tables[1][6][1],15,4,0},
{&tables[1][6][2],3,2,0},
{&tables[1][7][0],48,6,4},
{&tables[1][7][1],15,4,0},
{&tables[1][7][2],3,2,0},
{&param[2][0],3,2,0},
{&param[2][1],15,4,0},
{&param[2][2],1,1,0},
{&param[2][3],7,3,0},
{&param[2][4],7,3,0},
{&param[2][5],1,1,0},
{&param[2][6],7,3,0},
{&param[2][7],63,6,0},
{&param[2][8],1,1,0},
{&param[2][9],1,1,0},
{&param[2][10],7,3,0},
{&param[2][11],1,1,0},
{&param[2][12],7,3,0},
{&param[2][13],1,1,0},
{&param[2][14],15,4,0},
{&param[2][15],3,2,0},
{&param[2][16],255,8,0},
{&param[2][17],1,1,0},
{&param[2][18],15,4,0},
{&param[2][19],1,1,0},
{&param[2][20],7,3,0},
{&param[2][21],3,2,0},
{&param[2][22],1,1,0},
{&param[2][23],1,1,0},
{&param[2][24],1,1,0},
{&param[2][25],24,5,0},
{&program[2],99,7,0},
{&edited[2],1,1,0},
{&mods[2][0],15,4,0},
{&mods[2][1],4,3,0},
{&mods[2][2],3,2,0},
{&mods[2][3],7,3,0},
{&mods[2][4],16,5,0},
{&mods[2][5],63,6,0},
{&tablemode[2],3,2,0},
{&tablelen[2],8,4,2},
{&tables[2][0][0],48,6,4},
{&tables[2][0][1],15,4,0},
{&tables[2][0][2],3,2,0},
{&tables[2][1][0],48,6,4},
{&tables[2][1][1],15,4,0},
{&tables[2][1][2],3,2,0},
{&tables[2][2][0],48,6,4},
{&tables[2][2][1],15,4,0},
{&tables[2][2][2],3,2,0},
{&tables[2][3][0],48,6,4},
{&tables[2][3][1],15,4,0},
{&tables[2][3][2],3,2,0},
{&tables[2][4][0],48,6,4},
{&tables[2][4][1],15,4,0},
{&tables[2][4][2],3,2,0},
{&tables[2][5][0],48,6,4},
{&tables[2][5][1],15,4,0},
{&tables[2][5][2],3,2,0},
{&tables[2][6][0],48,6,4},
{&tables[2][6][1],15,4,0},
{&tables[2][6][2],3,2,0},
{&tables[2][7][0],48,6,4},
{&tables[2][7][1],15,4,0},
{&tables[2][7][2],3,2,0},
{&param[3][0],3,2,0},
{&param[3][1],15,4,0},
{&param[3][2],1,1,0},
{&param[3][3],7,3,0},
{&param[3][4],7,3,0},
{&param[3][5],1,1,0},
{&param[3][6],7,3,0},
{&param[3][7],63,6,0},
{&param[3][8],1,1,0},
{&param[3][9],1,1,0},
{&param[3][10],7,3,0},
{&param[3][11],1,1,0},
{&param[3][12],7,3,0},
{&param[3][13],1,1,0},
{&param[3][14],15,4,0},
{&param[3][15],3,2,0},
{&param[3][16],255,8,0},
{&param[3][17],1,1,0},
{&param[3][18],15,4,0},
{&param[3][19],1,1,0},
{&param[3][20],7,3,0},
{&param[3][21],3,2,0},
{&param[3][22],1,1,0},
{&param[3][23],1,1,0},
{&param[3][24],1,1,0},
{&param[3][25],24,5,0},
{&program[3],99,7,0},
{&edited[3],1,1,0},
{&mods[3][0],15,4,0},
{&mods[3][1],4,3,0},
{&mods[3][2],3,2,0},
{&mods[3][3],7,3,0},
{&mods[3][4],16,5,0},
{&mods[3][5],63,6,0},
{&tablemode[3],3,2,0},
{&tablelen[3],8,4,2},
{&tables[3][0][0],48,6,4},
{&tables[3][0][1],15,4,0},
{&tables[3][0][2],3,2,0},
{&tables[3][1][0],48,6,4},
{&tables[3][1][1],15,4,0},
{&tables[3][1][2],3,2,0},
{&tables[3][2][0],48,6,4},
{&tables[3][2][1],15,4,0},
{&tables[3][2][2],3,2,0},
{&tables[3][3][0],48,6,4},
{&tables[3][3][1],15,4,0},
{&tables[3][3][2],3,2,0},
{&tables[3][4][0],48,6,4},
{&tables[3][4][1],15,4,0},
{&tables[3][4][2],3,2,0},
{&tables[3][5][0],48,6,4},
{&tables[3][5][1],15,4,0},
{&tables[3][5][2],3,2,0},
{&tables[3][6][0],48,6,4},
{&tables[3][6][1],15,4,0},
{&tables[3][6][2],3,2,0},
{&tables[3][7][0],48,6,4},
{&tables[3][7][1],15,4,0},
{&tables[3][7][2],3,2,0},
{&custom,1,1,0},
{&customwave[0],255,8,0},
{&customwave[1],255,8,0},
{&customwave[2],255,8,0},
{&customwave[3],255,8,0},
{&customwave[4],255,8,0},
{&customwave[5],255,8,0},
{&customwave[6],255,8,0},
{&customwave[7],255,8,0},
{&customwave[8],255,8,0},
{&customwave[9],255,8,0},
{&customwave[10],255,8,0},
{&customwave[11],255,8,0},
{&customwave[12],255,8,0},
{&customwave[13],255,8,0},
{&customwave[14],255,8,0},
{&customwave[15],255,8,0},
{&finepitch[0],65535,16,1},
{&finepitch[1],65535,16,1},
{&finepitch[2],65535,16,1},
{&finepitch[3],65535,16,1},
{&finepitch[4],65535,16,1},
{&w2settings[0],48,6,0},
{&w2settings[1],15,4,0},
{&w2settings[2],120,7,2},
{&w2settings[3],48,6,0},
{&w2settings[4],3,2,0},
{&w2program,99,7,0},
{&w2tablemode,1,1,0},
{&w2tablelen,8,4,2},
{&w2tablespeed,32,6,2},
{&w2tables[0][0],48,6,4},
{&w2tables[0][1],3,2,0},
{&w2tables[0][2],15,4,0},
{&w2tables[1][0],48,6,4},
{&w2tables[1][1],3,2,0},
{&w2tables[1][2],15,4,0},
{&w2tables[2][0],48,6,4},
{&w2tables[2][1],3,2,0},
{&w2tables[2][2],15,4,0},
{&w2tables[3][0],48,6,4},
{&w2tables[3][1],3,2,0},
{&w2tables[3][2],15,4,0},
{&w2tables[4][0],48,6,4},
{&w2tables[4][1],3,2,0},
{&w2tables[4][2],15,4,0},
{&w2tables[5][0],48,6,4},
{&w2tables[5][1],3,2,0},
{&w2tables[5][2],15,4,0},
{&w2tables[6][0],48,6,4},
{&w2tables[6][1],3,2,0},
{&w2tables[6][2],15,4,0},
{&w2tables[7][0],48,6,4},
{&w2tables[7][1],3,2,0},
{&w2tables[7][2],15,4,0},
{&monoset[0][0],4,3,0},
{&monodepth[0][0],5,3,0},
{&monophase[0][0],359,9,1},
{&monoset[0][1],15,4,0},
{&monodepth[0][1],16,5,0},
{&monophase[0][1],359,9,1},
{&monoset[0][2],7,3,0},
{&monodepth[0][2],8,4,0},
{&monophase[0][2],359,9,1},
{&monoset[0][3],7,3,0},
{&monodepth[0][3],8,4,0},
{&monophase[0][3],359,9,1},
{&monoset[0][4],3,2,0},
{&monodepth[0][4],4,3,0},
{&monophase[0][4],359,9,1},
{&monoset[0][5],31,5,0},
{&monodepth[0][5],32,6,0},
{&monophase[0][5],359,9,1},
{&monoset[0][6],2,2,0},
{&monodepth[0][6],3,2,0},
{&monophase[0][6],359,9,1},
{&monoset[1][0],4,3,0},
{&monodepth[1][0],5,3,0},
{&monophase[1][0],359,9,1},
{&monoset[1][1],15,4,0},
{&monodepth[1][1],16,5,0},
{&monophase[1][1],359,9,1},
{&monoset[1][2],7,3,0},
{&monodepth[1][2],8,4,0},
{&monophase[1][2],359,9,1},
{&monoset[1][3],7,3,0},
{&monodepth[1][3],8,4,0},
{&monophase[1][3],359,9,1},
{&monoset[1][4],3,2,0},
{&monodepth[1][4],4,3,0},
{&monophase[1][4],359,9,1},
{&monoset[1][5],31,5,0},
{&monodepth[1][5],32,6,0},
{&monophase[1][5],359,9,1},
{&monoset[1][6],2,2,0},
{&monodepth[1][6],3,2,0},
{&monophase[1][6],359,9,1},
{&monoset[2][0],4,3,0},
{&monodepth[2][0],5,3,0},
{&monophase[2][0],359,9,1},
{&monoset[2][1],3,2,0},
{&monodepth[2][1],4,3,0},
{&monophase[2][1],359,9,1},
{&monoset[2][2],7,3,0},
{&monodepth[2][2],8,4,0},
{&monophase[2][2],359,9,1},
{&monoset[2][3],7,3,0},
{&monodepth[2][3],8,4,0},
{&monophase[2][3],359,9,1},
{&monoset[2][4],32,6,0},
{&monodepth[2][4],32,6,0},
{&monophase[2][4],359,9,1},
{&monoset[2][5],31,5,0},
{&monodepth[2][5],32,6,0},
{&monophase[2][5],359,9,1},
{&monoset[2][6],2,2,0},
{&monodepth[2][6],3,2,0},
{&monophase[2][6],359,9,1},
{&monosource[0],255,8,0},
{&monosource[1],255,8,0},
{&monosource[2],64,7,0},
{&monosource[3],255,8,0},
{&monosource[4],4,3,0},
{&monosource[5],32,6,0},
{&monosource[6],24,5,0},
{&monosource[7],1,1,0},
{&monosource[8],1,1,0},
{&monosource[9],32,6,0},
{&monosource[10],1,1,0},
{&expconfig[0],1,1,0},
{&expconfig[1],1,1,0},
{&expconfig[2],255,8,0},
{&expconfig[3],255,8,0},
{&expconfig[4],64,7,0},
{&expconfig[5],255,8,0},
{&expconfig[6],15,4,0},
{&expconfig[7],3,2,0},
{&expconfig[8],15,4,0},
{&expconfig[9],2,2,0},
{&expconfig[10],31,5,0},
{&expconfig[11],32,6,0},
{&expconfig[12],64,7,0},
{&expconfig[13],32,6,0},
{&expconfig[14],32,6,0},
{&expconfig[15],120,7,0},
{&expconfig[16],15,4,0},
{&expconfig[17],8,4,0},
{&expconfig[18],1,1,0},
{&expconfig[19],1,1,0},
{&expconfig[20],2,2,0},
{&expconfig[21],7,3,0},
{&expconfig[22],7,3,0},
{&expconfig[23],64,7,0},
{&expconfig[24],15,4,0},
{&expconfig[25],12,4,0},
{&expconfig[26],7,3,0},
{&exprelease[0],255,8,0},
{&exprelease[1],255,8,0},
{&exprelease[2],255,8,0},
{&noisepatch[0][0],15,4,0},
{&noisepatch[0][1],15,4,0},
{&noisepatch[0][2],7,3,0},
{&noisepatch[0][3],1,1,0},
{&noisepatch[0][4],7,3,0},
{&noisepatch[1][0],15,4,0},
{&noisepatch[1][1],15,4,0},
{&noisepatch[1][2],7,3,0},
{&noisepatch[1][3],1,1,0},
{&noisepatch[1][4],7,3,0},
{&drumkit,5,3,0},
{&master,255,8,0},
{&vin,255,8,0},
{&arprate,255,8,0},
{&softshape[0],3,2,0},
{&softshape[1],3,2,0},
{&savedengine,2,2,0},
{0,0,0,0}};
/* Field cursors stay in registers between the immutable ROM descriptors.
   Only descriptor/flags/maximum words live on the stack across bit copies. */
static void schema_pack(void) __naked { __asm
 ld a,(0xbcfc)
 or a,a
 jr z,tone_pack_full$
 ld a,(0xbcfe)
 ld l,a
 ld a,(0xbcff)
 ld h,a
 jr tone_pack_field$
tone_pack_full$:
 ld hl,#_tonefields
tone_pack_field$:
 ld a,(hl+)
 ld e,a
 ld a,(hl+)
 ld d,a
 inc hl
 inc hl
 ld a,(hl+)
 or a,a
 jr nz,tone_pack_present$
 ld bc,#-5
 add hl,bc
 jr tone_pack_done$
tone_pack_present$:
 ld c,a
 ld a,(hl+)
 push hl
 push af
 bit 0,a
 jr nz,tone_pack_word$
 bit 2,a
 jr nz,tone_pack_bias$
 ld a,(de)
 ld l,a
 ld h,#0
 jr tone_pack_value$
tone_pack_bias$:
 ld a,(de)
 add a,#24
 ld l,a
 ld h,#0
 jr tone_pack_value$
tone_pack_word$:
 ld a,(de)
 ld l,a
 inc de
 ld a,(de)
 ld h,a
tone_pack_value$:
 ld a,c
 ld e,l
 ld d,h
 call _bits
 pop af
 ld c,#1
 bit 0,a
 jr z,tone_pack_advance$
 inc c
tone_pack_advance$:
 ld hl,#_rawpos
 ld a,(hl)
 add a,c
 ld (hl+),a
 ld c,a
 ld a,(hl)
 adc a,#0
 ld (hl),a
 ld a,c
 and #7
 call z,_mixfill
 pop hl
 ld a,(0xbcfc)
 or a,a
 jr z,tone_pack_field$
 dec a
 ld (0xbcfc),a
 jr nz,tone_pack_field$
tone_pack_done$:
 ld a,l
 ld (0xbcfe),a
 ld a,h
 ld (0xbcff),a
 ret
 __endasm; }
static void schema_decode(void) __naked { __asm
 ld a,(0xbcfc)
 or a,a
 jr z,tone_decode_full$
 ld a,(0xbcfe)
 ld l,a
 ld a,(0xbcff)
 ld h,a
 jr tone_decode_field$
tone_decode_full$:
 ld hl,#_tonefields
tone_decode_field$:
 inc hl
 inc hl
 ld a,(hl+)
 ld c,a
 ld a,(hl+)
 ld b,a
 ld a,(hl+)
 or a,a
 jr nz,tone_decode_present$
 ld bc,#-5
 add hl,bc
 jp tone_decode_done$
tone_decode_present$:
 push bc
 ld c,a
 ld a,(hl+)
 push hl
 push af
 ld a,c
 ld de,#0
 call _bits
 pop af
 pop hl
 pop de
 push hl
 push af
 ld a,e
 sub a,c
 ld a,d
 sbc a,b
 jr nc,tone_decode_max_ok$
 xor a,a
 ld (_toneok),a
tone_decode_max_ok$:
 pop af
 push af
 bit 1,a
 jr z,tone_decode_nonzero_ok$
 ld a,b
 or a,c
 jr nz,tone_decode_nonzero_ok$
 xor a,a
 ld (_toneok),a
tone_decode_nonzero_ok$:
 pop af
 push af
 bit 2,a
 jr z,tone_decode_bias_ok$
 ld a,c
 sub a,#24
 ld c,a
 ld a,b
 sbc a,#0
 ld b,a
tone_decode_bias_ok$:
 ld hl,#_rawpos
 ld a,(hl+)
 ld e,a
 ld d,(hl)
 ld hl,#0xba00
 add hl,de
 ld (hl),c
 pop af
 ld c,#1
 bit 0,a
 jr z,tone_decode_advance$
 inc hl
 ld (hl),b
 inc c
tone_decode_advance$:
 ld hl,#_rawpos
 ld a,(hl)
 add a,c
 ld (hl+),a
 ld c,a
 ld a,(hl)
 adc a,#0
 ld (hl),a
 ld a,c
 and #7
 call z,_mixfill
 pop hl
 ld a,(0xbcfc)
 or a,a
 jp z,tone_decode_field$
 dec a
 ld (0xbcfc),a
 jp nz,tone_decode_field$
tone_decode_done$:
 ld a,l
 ld (0xbcfe),a
 ld a,h
 ld (0xbcff),a
 ret
 __endasm; }
static void schema(void){*(uint8_t *)0xBCFC=0;if(operation)schema_decode();else schema_pack();}
/* Async preparation cursor uses the unused end of the decoded SRAM cache.
   A job owns the serializer until completion or cancellation by its caller. */
#define TONE_CURSOR (*(const ToneField **)0xBCFE)
void tones_pack_begin(void) BANKED {memset(TONE_PACK,0,TONE_SIZE);operation=0;bitpos=rawpos=0;toneok=1;savedengine=waveengine<3?waveengine:0;TONE_CURSOR=tonefields;}
void tones_decode_begin(void) BANKED {operation=1;bitpos=rawpos=0;toneok=1;TONE_CURSOR=tonefields;}
uint8_t tones_step(void) BANKED {
 *(uint8_t *)0xBCFC=8;if(operation)schema_decode();else schema_pack();
 if(TONE_CURSOR->width)return 0;
 if(!toneok||bitpos>TONE_SIZE*8||rawpos>=464)return 2;
 if(operation)return kick_decode()?1:2;
 kick_pack();return 1;
}
void tones_pack(void) BANKED {memset(TONE_PACK,0,TONE_SIZE);operation=0;bitpos=rawpos=0;toneok=1;savedengine=waveengine<3?waveengine:0;schema();kick_pack();}
uint8_t tones_decode(void) BANKED {operation=1;bitpos=rawpos=0;toneok=1;schema();return toneok&&bitpos<=TONE_SIZE*8&&rawpos<464&&kick_decode();}
/* Decode/validate before launch; the boundary only scatters prepared bytes.
   Running schema here repeated range calculations and dozens of banked
   monomax calls with all outgoing voices already released. */
/* ROM scatter list mirrors schema order; no repeated pointer arithmetic
   or generic memcpy setup during the live launch boundary. */
typedef struct {void *destination;uint8_t size;} ToneDestination;
static const ToneDestination tonedest[]={
{&param[0][0],26},
{&program[0],1},
{&edited[0],1},
{&mods[0][0],6},
{&tablemode[0],1},
{&tablelen[0],1},
{&tables[0][0][0],24},
{&param[1][0],26},
{&program[1],1},
{&edited[1],1},
{&mods[1][0],6},
{&tablemode[1],1},
{&tablelen[1],1},
{&tables[1][0][0],24},
{&param[2][0],26},
{&program[2],1},
{&edited[2],1},
{&mods[2][0],6},
{&tablemode[2],1},
{&tablelen[2],1},
{&tables[2][0][0],24},
{&param[3][0],26},
{&program[3],1},
{&edited[3],1},
{&mods[3][0],6},
{&tablemode[3],1},
{&tablelen[3],1},
{&tables[3][0][0],24},
{&custom,1},
{customwave,16},
{finepitch,10},
{w2settings,5},
{&w2program,1},
{&w2tablemode,1},
{&w2tablelen,1},
{&w2tablespeed,1},
{&w2tables[0][0],24},
{&monoset[0][0],1},
{&monodepth[0][0],1},
{&monophase[0][0],2},
{&monoset[0][1],1},
{&monodepth[0][1],1},
{&monophase[0][1],2},
{&monoset[0][2],1},
{&monodepth[0][2],1},
{&monophase[0][2],2},
{&monoset[0][3],1},
{&monodepth[0][3],1},
{&monophase[0][3],2},
{&monoset[0][4],1},
{&monodepth[0][4],1},
{&monophase[0][4],2},
{&monoset[0][5],1},
{&monodepth[0][5],1},
{&monophase[0][5],2},
{&monoset[0][6],1},
{&monodepth[0][6],1},
{&monophase[0][6],2},
{&monoset[1][0],1},
{&monodepth[1][0],1},
{&monophase[1][0],2},
{&monoset[1][1],1},
{&monodepth[1][1],1},
{&monophase[1][1],2},
{&monoset[1][2],1},
{&monodepth[1][2],1},
{&monophase[1][2],2},
{&monoset[1][3],1},
{&monodepth[1][3],1},
{&monophase[1][3],2},
{&monoset[1][4],1},
{&monodepth[1][4],1},
{&monophase[1][4],2},
{&monoset[1][5],1},
{&monodepth[1][5],1},
{&monophase[1][5],2},
{&monoset[1][6],1},
{&monodepth[1][6],1},
{&monophase[1][6],2},
{&monoset[2][0],1},
{&monodepth[2][0],1},
{&monophase[2][0],2},
{&monoset[2][1],1},
{&monodepth[2][1],1},
{&monophase[2][1],2},
{&monoset[2][2],1},
{&monodepth[2][2],1},
{&monophase[2][2],2},
{&monoset[2][3],1},
{&monodepth[2][3],1},
{&monophase[2][3],2},
{&monoset[2][4],1},
{&monodepth[2][4],1},
{&monophase[2][4],2},
{&monoset[2][5],1},
{&monodepth[2][5],1},
{&monophase[2][5],2},
{&monoset[2][6],1},
{&monodepth[2][6],1},
{&monophase[2][6],2},
{monosource,11},
{expconfig,27},
{exprelease,3},
{&noisepatch[0][0],10},
{&drumkit,1},
{&master,1},
{&vin,1},
{&arprate,1},
{softshape,2},
{&savedengine,1},
{0,0}};
static void apply_prepared(void) __naked { __asm
 push bc
 ld de,#0xba00
 ld hl,#_tonedest
tone_scatter_next$:
 ld a,(hl+)
 ld c,a
 ld a,(hl+)
 ld b,a
 ld a,(hl+)
 or a,a
 jr z,tone_scatter_done$
 push hl
 ld h,b
 ld l,c
 ld c,a
tone_scatter_copy$:
 ld a,(de)
 inc de
 ld (hl+),a
 dec c
 jr nz,tone_scatter_copy$
 pop hl
 jr tone_scatter_next$
tone_scatter_done$:
 pop bc
 ret
 __endasm; }
void tones_apply(void) BANKED {uint8_t c,i;apply_prepared();memcpy(pulsekickpatch,KICK_RAW,8);
 memset(phase,0,sizeof(phase));memset(age,0,sizeof(age));memset(stepclock,0,sizeof(stepclock));memset(tablepos,0,sizeof(tablepos));memset(notestep,0,sizeof(notestep));memset(tablerow,0,sizeof(tablerow));
 if(!seqplaying)memset(keycount,0,sizeof(keycount));memset(bend,0,sizeof(bend));memset(held,255,sizeof(held));for(c=0;c<4;c++)wheellast[c]=8192;
 memcpy(monoeffective,monoset,sizeof(monoeffective));
 route=0;for(c=0;c<4;c++)if(!param[c][9]){if(param[c][21]&1)route|=1<<c;if(param[c][21]&2)route|=0x10<<c;}
 /* Native live launches keep the established timer phase and PCM owner. */
 if(!monomode&&(!seqplaying||experimental_mode||(waveengine&&waveengine!=3))){TAC_REG=0;enginestop();waveengine=experimental_mode?savedengine:0;w2enabled=0;TMA_REG=TIMA_REG=waveengine==1?252:240;IF_REG&=~TIM_IFLAG;TAC_REG=(seqplaying||waveengine)?4:0;}
 if(experimental_mode&&!monomode){expwaveon=expconfig[0]||expconfig[1]||exprelease[2]||expconfig[6]!=15||expconfig[7]||expconfig[8]||expconfig[10];expactive=expwaveon||exprelease[0]||exprelease[1];for(i=0;i<EXP_COUNT;i++)if(i!=4&&i!=6&&i!=21&&expconfig[i])expactive=1;}
 wavepending=1;pitchdirty=1;choice=selected<4?program[selected]:0;globals();if(experimental_mode&&monomode)exp_changed();dirty=1;
}

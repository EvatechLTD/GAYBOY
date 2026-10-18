#pragma bank 20
#include "api.h"
const uint8_t drumdata20[]={136};
void drum_fast200(void) BANKED __naked { __asm
 push bc
 ld hl,#0xac42
 ld a,(hl+)
 ld h,(hl)
 ld l,a
 ld de,#_drumdata20
 add hl,de
 ld de,#0xac00
 .rept 16
 ld a,(hl+)
 ld (de),a
 inc e
 .endm
 pop bc
 ret
 __endasm; }
void drum_fast201(void) BANKED __naked { __asm
 push bc
 ld hl,#0xac44
 ld a,(hl+)
 ld h,(hl)
 ld l,a
 ld de,#_drumdata20
 add hl,de
 ld de,#0xac10
 .rept 16
 ld a,(hl+)
 ld (de),a
 inc e
 .endm
 pop bc
 ret
 __endasm; }
void drum_fetch20(uint16_t offset,uint8_t *dst) BANKED {memcpy(dst,drumdata20+offset,16); }

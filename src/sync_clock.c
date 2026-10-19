#include "api.h"
/* Fixed-ROM, interrupt-only clock. Phase uses CPU cycles / 64 times BPM.
   Reloads are selected outside the IRQ; there is no division or bank switch.
   Limits are 0x028000 (24 PPQN), 0x0f0000 (4), or 0x1e0000 (2). */
void sync_clock_isr(void) NONBANKED __naked { __asm
 ldh a,(_synctxwait)
 or a
 jr z,sync_clock_active$
 dec a
 ldh (_synctxwait),a
sync_clock_active$:
 ldh a,(_syncarmed)
 or a
 ret z
 ldh a,(_syncstart)
 or a
 ret nz
 push bc
 ld hl,#_syncirqphase
 ldh a,(_syncincrement)
 add a,(hl)
 ld (hl+),a
 ldh a,(_syncincrement+1)
 adc a,(hl)
 ld (hl+),a
 ld a,(hl)
 adc a,#0
 ld (hl),a
 ld b,a
 ldh a,(_synclimit+2)
 cp a,b
 jr c,sync_clock_due$
 jr nz,sync_clock_done$
 dec hl
 ld b,(hl)
 ldh a,(_synclimit+1)
 cp a,b
 jr c,sync_clock_due$
 jr nz,sync_clock_done$
sync_clock_due$:
 ldh a,(_synctick)
 inc a
 and #63
 ldh (_synctick),a
 ld hl,#_syncirqphase+1
 ldh a,(_synclimit+1)
 ld b,a
 ld a,(hl)
 sub a,b
 ld (hl+),a
 ldh a,(_synclimit+2)
 ld b,a
 ld a,(hl)
 sbc a,b
 ld (hl),a
 ldh a,(#0x0f)
 and #8
 jr nz,sync_clock_pending$
 ldh a,(#0x02)
 bit 7,a
 jr nz,sync_clock_pending$
 ldh a,(_syncmode)
 dec a
 jr nz,sync_clock_raw$
 ldh a,(_synctick)
 or #0x80
 call _link_clock_byte
 jr sync_clock_send$
sync_clock_raw$:
 xor a
sync_clock_send$:
 ldh (#0x01),a
 ld a,#0x81
 ldh (#0x02),a
 jr sync_clock_done$
sync_clock_pending$:
 ldh a,(_syncdue)
 or a
 jr z,sync_clock_record$
 ld a,#1
 ld (_overflow),a
sync_clock_record$:
 ld a,#1
 ldh (_syncdue),a
sync_clock_done$:
 pop bc
 ret
 __endasm; }

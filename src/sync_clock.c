#pragma bank 6
#include "api.h"
extern volatile uint8_t twink_guard,twink_ended_div;
void twink_tx_tick(void) BANKED;
extern uint8_t twink_v2;
void twink_v2_irq(void) BANKED;
void sync_raw_sample(void) BANKED;
/* Fixed-ROM clock; only the negotiated TWINK delivery uses a bank trampoline.
   Phase uses elapsed DIV /16 times64 times BPM, not interrupt invocations.
   Reloads are selected outside the IRQ; there is no division in this kernel.
   Limits are 0x028000 (24 PPQN), 0x0f0000 (4), or 0x1e0000 (2). */
void sync_clock_isr(void) NONBANKED __naked { __asm
 ldh a,(_synctxwait)
 or a
 jr z,sync_clock_active$
 dec a
 ldh (_synctxwait),a
sync_clock_active$:
 ld a,(_sync_raw_ready)
 or a
 jr z,sync_clock_master$
 ldh a,(_syncmode)
 dec a
 ret z
 push bc
 ld e,#b_sync_raw_sample
 ld hl,#_sync_raw_sample
 call ___sdcc_bcall_ehl
 pop bc
 ret
sync_clock_master$:
 ldh a,(_syncarmed)
 or a
 ret z
 ldh a,(_syncstart)
 or a
 jr z,sync_clock_running$
 ; Byte delivery must work during the stopped READY handshake too.
 ldh a,(_syncmode)
 cp #6
 ret nz
 ld a,(_twink_v2)
 or a
 ret z
 push bc
 jr sync_twink_v2_pump$
sync_clock_running$:
 push bc
 ldh a,(_syncmode)
 cp #6
 jr nz,twink_queue_done$
 ld a,(_twink_v2)
 or a
 jr z,twink_v1_queue$
sync_twink_v2_pump$:
 ld e,#b_twink_v2_irq
 ld hl,#_twink_v2_irq
 call ___sdcc_bcall_ehl
 pop bc
 ret
twink_v1_queue$:
 ldh a,(_syncdue)
 or a
 jr nz,twink_queue_pump$
 ldh a,(_syncr)
 ld b,a
 ldh a,(_syncw)
 cp a,b
 jr z,twink_queue_done$
twink_queue_pump$:
 ld e,#b_twink_tx_tick
 ld hl,#_twink_tx_tick
 call ___sdcc_bcall_ehl
twink_queue_done$:
 ; Count elapsed hardware time, not interrupt invocations. APU/VRAM work
 ; can coalesce TIMA requests while DIV continues running. Master-only
 ; lastpulse bytes are free as DIV sample/fraction outside slave mode.
 ldh a,(#0x04)
 ld b,a
 ldh a,(#0xe8)
 ld c,a
 ld a,b
 ldh (#0xe8),a
 sub a,c
 ld b,a
 and #15
 ld c,a
 ldh a,(#0xe9)
 add a,c
 ld c,a
 and #15
 ldh (#0xe9),a
 ld a,b
 swap a
 and #15
 ld b,a
 ld a,c
 and #16
 jr z,sync_clock_elapsed$
 inc b
sync_clock_elapsed$:
 ld a,b
 or a
 jr z,sync_clock_compare$
 ld c,a
 ld hl,#_syncirqphase
sync_clock_sum$:
 ldh a,(_syncincrement)
 add a,(hl)
 ld (hl+),a
 ldh a,(_syncincrement+1)
 adc a,(hl)
 ld (hl+),a
 ld a,(hl)
 adc a,#0
 ld (hl),a
 dec c
 jr z,sync_clock_compare$
 dec hl
 dec hl
 jr sync_clock_sum$
sync_clock_compare$:
 ld hl,#_syncirqphase+2
 ld a,(hl)
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
 ; TWINK grants the receiver 7..8 DIV ticks (427..488 us) to rearm,
 ; including VBlank/input service. Use DIV so stopped polling also works.
 ldh a,(_syncmode)
 cp #6
 jr nz,sync_clock_guard_done$
 ld a,(_twink_guard)
 or a
 jr z,sync_clock_guard_done$
 ld a,(_twink_ended_div)
 ld b,a
 ldh a,(#0x04)
 sub a,b
 cp #8
 jr c,sync_clock_pending$
 xor a
 ld (_twink_guard),a
sync_clock_guard_done$:
 ldh a,(#0x0f)
 and #8
 jr nz,sync_clock_pending$
 ldh a,(#0x02)
 bit 7,a
 jr nz,sync_clock_pending$
 ldh a,(_syncmode)
 cp #6
 jr nz,sync_clock_native$
 ldh a,(_synctick)
 or #0x80
 jr sync_clock_send$
sync_clock_native$:
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

extern const uint8_t drumdata32[];
extern const uint8_t drumdata16[],drumdata19[],drumdata20[];
/* Called only by the interrupt-owned PCM mixer in ROM bank 17. Executing
   from fixed ROM removes nested banked-call wrappers from every sample block. */
void drum_fetch_fast(uint8_t voice) NONBANKED __naked { __asm
 push bc
 ld c,a
 add a,#0x4b
 ld l,a
 ld h,#0xac
 ld b,(hl)
 ld a,c
 add a,a
 add a,#0x42
 ld l,a
 ld a,(hl+)
 ld e,a
 ld d,(hl)
 ld a,b
 cp #32
 jr c,drum_fetch_legacy$
 ld hl,#_drumdata32
 jr drum_fetch_address$
drum_fetch_legacy$:
 cp #19
 jr z,drum_fetch_bank19$
 cp #20
 jr z,drum_fetch_bank20$
 ld hl,#_drumdata16
 jr drum_fetch_address$
drum_fetch_bank19$:
 ld hl,#_drumdata19
 jr drum_fetch_address$
drum_fetch_bank20$:
 ld hl,#_drumdata20
drum_fetch_address$:
 add hl,de
 ld a,c
 swap a
 ld e,a
 ld d,#0xac
 ld a,b
 ldh (#0x90),a
 ld (#0x2000),a
 .rept 16
 ld a,(hl+)
 ld (de),a
 inc e
 .endm
 ld a,#17
 ldh (#0x90),a
 ld (#0x2000),a
 pop bc
 ret
 __endasm; }
void streamblock(void) __naked {
 __asm
 push bc
 ld a,(_mixread)
 swap a
 ld e,a
 ld d,#0
 ld hl,#_mixbuffer
 add hl,de
 ld c,#0x30
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 ld a,(hl+)
 ldh (c),a
 inc c
 pop bc
 ret
 __endasm;
}
/* DDS stays in main; PCM renders its next block after the current upload. */
void drum_timer(void) BANKED;
void input_vblank(void);
void engine_timer(void){uint8_t n;
 sync_clock_isr();
 if(syncarmed){
  if(waveengine!=3&&seqplaying)seqticks++;
  syncsub++;if(syncsub<syncdivider)return;syncsub=0;
 }
 /* Sample after the PCM upload. Delayed VBlank sampling alone can miss a
    one-frame tap; both interrupt producers run without nesting. */
 if(waveengine==3){if(!syncmode&&seqplaying)seq_irq_tick(((uint16_t)seqfraction+183U)>>6);drum_timer();input_vblank();return;}
 if(seqplaying&&!syncarmed&&(!syncmode||!syncslave)){n=64-(TMA_REG>>2);if(!syncmode)seq_irq_tick(n);seqticks+=n;}if(!power)return;
}

#pragma bank 59
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
/* Controlled whole-engine baseline: pulses use the shared foreground
   dispatcher. Keep the packet implementation for the preserved A/B build. */
#define SEQ_PULSE_IRQ_ENABLED 0
extern const uint16_t notes[140];
extern uint8_t seqgate[7],seqrecordtrack;
extern uint16_t seqclock;
uint8_t sparse_first_packet(uint8_t c,uint8_t *regs) BANKED;
uint16_t fine_preview(uint16_t base,uint8_t channel) BANKED;
__at (0xFF98) volatile uint8_t seqirqready;
__at (0xFF99) volatile uint8_t seqirqfired;
__at (0xFF9A) volatile uint16_t seqirqleft;
__at (0xFF9C) uint8_t seqirqstep[2];
__at (0xFF9E) uint8_t seqirqnote[2];
__at (0xFFA0) uint8_t seqirqregs[9];
__at (0xFFA9) uint8_t seqirqpan;
__at (0xFFAA) uint8_t seqirqsuppress;
__at (0xFFAE) uint8_t seqirqdirty;
static __at (0xFFAB) uint8_t panmask;
static __at (0xFFAC) uint16_t bpmcache;
static __at (0xFFAF) uint8_t attackvelocity[2];
static uint8_t packet(uint8_t c,uint8_t note,uint8_t velocity,uint8_t *r){uint8_t *v=param[c],vol,n,frac;uint16_t f,amplitude;int16_t pitch;
 vol=(mx.magic!=0xD3||mx.level[c]==127)?velocity:mixer_velocity(c,velocity);if(!vol)return 0;
 n=note-1;f=notes[n];
 if(bend[c]){pitch=(int16_t)n*128+bend[c];if(pitch<0)pitch=0;if(pitch>16256)pitch=16256;n=pitch>>7;frac=pitch&127;f=notes[n];if(frac)f+=((uint16_t)(notes[n+1]-f)*frac)>>7;}
 if(finepitch[c])f=fine_preview(f,c);
 amplitude=(uint16_t)v[1]*vol;vol=(amplitude+1+(amplitude>>7))>>7;
 if(!c)*r++=(v[4]<<4)|(v[5]<<3)|v[6];
 *r++=(v[0]<<6)|v[7];*r++=!vol&&!v[2]?8:(vol<<4)|(v[2]<<3)|v[3];*r++=f;*r=0x80|(v[8]<<6)|(f>>8);return 1;
}
/* Live controls replace a complete packet atomically. Its deadline stays put.
   If the IRQ already consumed it, the control applies to the following note. */
void seq_irq_refresh(uint8_t c) BANKED {uint8_t bit,note,step,n,regs[5],valid;
 if(!SEQ_PULSE_IRQ_ENABLED)return;
 if(syncmode||c>1)return;bit=1<<c;if(!(seqirqready&bit))return;
 note=seqirqnote[c];step=seqirqstep[c];
 valid=power&&!param[c][9]&&!param[c][22]&&!(seqmuted&bit)&&(!(seqsolo&79)||(seqsolo&bit))&&!drumsolomask;
 if(valid)valid=packet(c,note,attackvelocity[c],regs);
 __critical {if((seqirqready&bit)&&seqirqnote[c]==note&&seqirqstep[c]==step){
  if(!valid)seqirqready&=~bit;
  else for(n=0;n<(c?4:5);n++)seqirqregs[(c?5:0)+n]=regs[n];
 }}
}
/* Lookups and synthesis stay in foreground. Publish only complete attacks.
   Unsupported/live-owned voices keep their existing sequencer path. */
static void prepare(uint8_t launch){uint8_t c,mask=0,bit,*v,e[4],n;uint16_t left,pending,cursor;uint8_t kick=0,drumstep;
 if(!SEQ_PULSE_IRQ_ENABLED)return;
 if(syncmode)return;
 mask=seqirqready;
 if(mask&&!launch){for(c=0;c<2;c++)if(mask&(1<<c)){n=seqposition[c]+1;if(n>=seqlength[c])n=0;if(seqirqstep[c]!=n)break;}if(c==2){seqirqdirty=0;return;}}
 mask=0;
 __critical {mask=seqirqfired;if(!mask)seqirqready=0;}
 if(mask)return;
 seqirqdirty=0;
 if(!seqplaying||experimental_mode||monomode||polymode||!power||(!launch&&seqeventcache==2)||(!launch&&mx.pending!=255)||(!launch&&seqclock>=seqthreshold))return;
 seqirqpan=panmask=0;
 drumstep=seqposition[6]+(launch?0:1);if(drumstep>=seqlength[6])drumstep=0;cursor=0;
 if(launch&&sparse_enabled)kick=sparse_first_kick();else kick=2;
 if(kick==2){kick=0;while(seq_event_next_step(6,drumstep,&cursor,e))if(e[1]==13&&e[2]){kick=1;break;}}
 for(c=0;c<2;c++){
  bit=1<<c;v=param[c];
  if(seqrecordtrack==c||v[9]||v[22]||keycount[c]>1||(keycount[c]&&(!seqowned[c]||keystack[c][0]!=seqowned[c]-1))||(c==0&&(pulsekickleft||kick)))continue;
  if((seqmuted&bit)||((seqsolo&79)&&!(seqsolo&bit))||drumsolomask)continue;
  n=seqposition[c]+(launch?0:1);if(n>=seqlength[c])n=0;
  if(!seq_note_event(c,n,e))continue;
  if(!(launch&&sparse_enabled&&sparse_first_packet(c,seqirqregs+(c?5:0))))if(!packet(c,e[1],e[2],seqirqregs+(c?5:0)))continue;
  seqirqstep[c]=n;seqirqnote[c]=e[1];attackvelocity[c]=e[2];mask|=bit;
 }
 if(!mask)return;
 if(launch){__critical {seqirqleft=0;bpmcache=seqbpm;seqirqready=mask;seq_irq_tick(0);}return;}
 left=(seqthreshold-seqclock+seqbpm-1)/seqbpm;
 __critical {pending=seqticks;if(left>pending){seqirqleft=left-pending;bpmcache=seqbpm;seqirqready=mask;}}
}
void seq_irq_prepare(void) BANKED {prepare(0);}
/* At a launch, batch beat-one attacks before gate setup and PCM dispatch.
   The normal dispatcher later acknowledges these attacks without retriggering. */
void seq_irq_launch(void) BANKED {prepare(1);}
/* The interrupt only counts elapsed units and writes prepared registers.
   No bank switch, pattern access, division or sequencer reentry. */
void seq_irq_tick(uint8_t elapsed) NONBANKED __naked {
#if SEQ_PULSE_IRQ_ENABLED
 __asm
 ld e,a
 ldh a,(_syncmode)
 or a
 ret nz
 ld a,(_seqplaying)
 or a
 ret z
 ldh a,(_seqirqready)
 or a
 ret z
 push bc
 ld b,a
 ld hl,#_bpmcache
 ld a,(_seqbpm)
 cp a,(hl)
 jr nz,seq_irq_cancel$
 inc hl
 ld a,(_seqbpm+1)
 cp a,(hl)
 jr nz,seq_irq_cancel$
 ldh a,(_seqirqleft)
 sub a,e
 ld c,a
 ldh a,(_seqirqleft+1)
 sbc a,#0
 jr c,seq_irq_fire$
 ldh (_seqirqleft+1),a
 or a,c
 jr z,seq_irq_fire$
 ld a,c
 ldh (_seqirqleft),a
 jr seq_irq_done$
seq_irq_fire$:
 xor a
 ldh (_seqirqready),a
 ld a,b
 ldh (_seqirqfired),a
 ld hl,#_seqirqregs
 bit 0,b
 jr z,seq_irq_p2$
 ld a,(hl+)
 ldh (#0x10),a
 ld a,(hl+)
 ldh (#0x11),a
 ld a,(hl+)
 ldh (#0x12),a
 ld a,(hl+)
 ldh (#0x13),a
 ld a,(hl)
 ldh (#0x14),a
seq_irq_p2$:
 bit 1,b
 jr z,seq_irq_route$
 ld hl,#_seqirqregs+5
 ld a,(hl+)
 ldh (#0x16),a
 ld a,(hl+)
 ldh (#0x17),a
 ld a,(hl+)
 ldh (#0x18),a
 ld a,(hl)
 ldh (#0x19),a
seq_irq_route$:
 jr seq_irq_done$
seq_irq_cancel$:
 xor a
 ldh (_seqirqready),a
seq_irq_done$:
 pop bc
 ret
 __endasm;
#else
 __asm
 ret
 __endasm;
#endif
}

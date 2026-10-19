#pragma bank 62
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
#include "tones.h"
#include "seq_native_types.h"

/* Separate packet: preparing an incoming pad never replaces the outgoing
   lookahead, held notes, mixer state, fine-tuning cache, or PCM sources. */
__at (0xA200) NativeStep seqlaunchstep;
__at (0xA600) static uint8_t buildphase;
__at (0xA601) static uint8_t launchslot;
__at (0xA602) static uint16_t launchidentity;
__at (0xA604) static uint16_t drumcursor;
__at (0xA606) static uint8_t launchdrums;
__at (0xA607) static uint8_t launchinstalled;
#define STEP (&seqlaunchstep)
#define FULL ((uint8_t *)0xB5A0)
#define FIRST ((uint8_t *)0xB590)
#define FIRST_OTHER ((uint8_t *)0xB7D0)
#define FIRST_DRUM ((uint8_t *)0xB7E0)
extern const uint16_t notes[140];
uint16_t fine_preview_value(uint16_t base,int16_t value) BANKED;
uint32_t seq_gate_length(uint16_t units,uint8_t duration,uint8_t gate) BANKED;
void seq_native_sample_value(const uint8_t *event,uint8_t *out,uint8_t kit,uint16_t bpm) BANKED;
static uint16_t word(const uint8_t *p){return p[0]|((uint16_t)p[1]<<8);}
static uint8_t native_note(uint8_t c,uint8_t step,uint8_t *e){step;memcpy(e,c<2?FIRST+c*4:FIRST_OTHER+(c-2)*4,4);return !!e[1];}
static uint8_t native_drum(uint16_t *cursor,uint8_t *e){if(*cursor>=launchdrums)return 0;memcpy(e,FIRST_DRUM+(*cursor)*4,4);(*cursor)++;return 1;}
#include "seq_native_calc.h"

void seq_native_launch_begin(uint8_t slot,uint8_t count,uint8_t overflow) BANKED {uint8_t c;
 buildphase=255;launchinstalled=0;
 if(overflow||slot>=8||experimental_mode||monomode||polymode||w2enabled||(waveengine!=0&&waveengine!=3)||!power)return;
 memset(STEP,0,sizeof(*STEP));launchslot=slot;launchidentity=sparse_slots[slot];launchdrums=count;drumcursor=0;
 STEP->slot=slot;STEP->bpm=seqglobalbpm?seqglobalbpm:word(FULL+75);STEP->units=15360U/STEP->bpm;
 STEP->muted=FULL[70];STEP->solo=FULL[71];STEP->drummute=word(FULL+77);STEP->drumsolo=word(FULL+79);
 memcpy(STEP->mix,FULL+56,14);memcpy(STEP->gates,FULL+49,4);
 for(c=0;c<4;c++)memcpy(STEP->params[c],TONE_CACHED_RAW+c*60,26);
 STEP->wavecustom=TONE_CACHED_RAW[240];memcpy(STEP->waveinput,TONE_CACHED_RAW+241,16);memcpy(STEP->fine,TONE_CACHED_RAW+257,6);
 memcpy(STEP->noiseinput,TONE_CACHED_RAW+425,10);STEP->kit=TONE_CACHED_RAW[435];memcpy(STEP->kickinput,TONE_CACHED_RAW+442,8);
 buildphase=1;
}
/* 0 pending, 1 ready, 2 unsupported: unsupported launches retain the existing
   complete foreground path rather than publishing a partial drum batch. */
uint8_t seq_native_launch_service(void) BANKED {
 if(buildphase>=1&&buildphase<=4){voice(buildphase-1);buildphase++;}
 else if(buildphase==5)drums();
 else if(buildphase==6){if(STEP->mask&4)wavebytes();finish_registers();buildphase=7;}
 return buildphase==7?1:buildphase==255?2:0;
}
/* Only the validated cached-tone installation grants a single-use ticket.
   A stopped pad selection or a same-pad retrigger cannot reuse stale notes. */
void seq_native_launch_installed(uint8_t slot) BANKED {
 launchinstalled=seqplaying&&buildphase==7&&slot==launchslot&&slot<8&&launchidentity==sparse_slots[slot];
}
/* Both packets are aligned protected bank-zero allocations. Copy a bounded
   384-byte slot without the general memcpy's per-byte count bookkeeping. */
typedef char launch_packet_fits[(sizeof(NativeStep)<=384)?1:-1];
static void copy_packet(void) __naked {__asm
 ld de,#0xa200
 ld hl,#0xa000
 ld b,#24
launch_copy_group$:
 .rept 16
 ld a,(de)
 inc e
 ld (hl+),a
 .endm
 ld a,e
 or a
 jr nz,launch_copy_next$
 inc d
launch_copy_next$:
 dec b
 jr nz,launch_copy_group$
 ret
 __endasm;}
uint8_t seq_native_launch_copy(uint8_t slot) BANKED {
 if(!launchinstalled)return 0;launchinstalled=0;
 if(buildphase!=7||page!=18||slot!=launchslot||slot>=8||launchidentity!=sparse_slots[slot]||STEP->bpm!=seqbpm)return 0;
 copy_packet();buildphase=0;return 1;
}

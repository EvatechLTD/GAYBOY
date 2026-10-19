#pragma bank 61
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"

/* Native playback never uses the experimental delay. Its protected bank-zero
   allocation holds the next complete step, independently of UI page scratch.
   Nothing in this file allocates battery storage or enters a banked IRQ path. */
extern uint16_t pattern_generation,seqclock,seqdeadline;
extern uint8_t seqgate[7],seqrecordtrack;
extern const uint16_t notes[140];
extern uint32_t noiseleft[2];
extern __at (0xAC54) uint8_t noiselevel[2];
extern uint8_t noisepatch[2][5],pulsekickpatch[8],drumsamplevoice[2],pcmoutlevel;
extern __at (0xAC42) uint16_t drumpos[2];
extern __at (0xAC46) uint16_t drumend[2];
extern __at (0xAC4A) uint8_t drumlast;
extern __at (0xAC4B) uint8_t drumbankvoice[2];
extern __at (0xAC58) uint8_t drumnoisetail;
extern uint8_t drumtail;
extern uint16_t finebase[5];
extern uint8_t finemode[5],finevalid[5];
uint16_t fine_preview(uint16_t base,uint8_t c) BANKED;
uint32_t seq_gate_length(uint16_t units,uint8_t duration,uint8_t gate) BANKED;
void seq_native_sample(const uint8_t *event,uint8_t *out) BANKED;

#include "seq_native_types.h"
typedef char native_step_fits[(sizeof(NativeStep)<=512)?1:-1];
__at (0xA000) NativeStep seqnativestep;
#define STEP (&seqnativestep)
/* The fixed hardware writer consumes only these explicitly laid-out bytes. */
#define HW ((volatile uint8_t *)0xA400)
/* 0 mask, 1 release, 2 route-mask, 3 route-bits, 4..22 voice registers,
   23..38 wave RAM. P1 offset4, P2 offset9, wave offset13, noise offset18. */
volatile uint8_t seqnativepending;
uint16_t seqnativehits,seqnativemisses;
uint8_t seqnativefallback;
static uint8_t nativedirty=1;
static uint8_t buildphase,building,configuration_valid;
static uint16_t drumcursor;
void seq_native_hardware(void) NONBANKED;

static uint8_t eligible(void){return !experimental_mode&&!monomode&&!polymode&&!w2enabled&&(waveengine==0||waveengine==3)&&seqrecordtrack==255&&power;}
uint16_t fine_preview_value(uint16_t base,int16_t value) BANKED;
void seq_native_sample_value(const uint8_t *event,uint8_t *out,uint8_t kit,uint16_t bpm) BANKED;
uint8_t seq_native_launch_copy(uint8_t slot) BANKED;
static uint8_t native_note(uint8_t c,uint8_t step,uint8_t *e){return seq_note_event(c,step,e);}
static uint8_t native_drum(uint16_t *cursor,uint8_t *e){return seq_event_next_step(6,STEP->steps[6],cursor,e);}
#include "seq_native_calc.h"
static uint8_t native_valid(void);
static void finish(void){finish_registers();buildphase=native_valid()?7:0;if(buildphase==7)nativedirty=0;}

static uint8_t native_valid(void){
 if(!eligible()||STEP->generation!=pattern_generation||STEP->bpm!=seqbpm||STEP->slot!=mx.slot||STEP->muted!=seqmuted||STEP->solo!=seqsolo||STEP->kit!=drumkit||STEP->drummute!=drummutemask||STEP->drumsolo!=drumsolomask)return 0;
 if(configuration_valid&&!nativedirty)return 1;
 return !memcmp(STEP->params,param,104)&&!memcmp(STEP->gates,seqgate,4)&&!memcmp(STEP->fine,finepitch,6)&&!memcmp(STEP->bend,bend,6)&&STEP->wavecustom==custom&&!memcmp(STEP->waveinput,customwave,16)&&!memcmp(STEP->noiseinput,noisepatch,10)&&!memcmp(STEP->kickinput,pulsekickpatch,8)&&(mx.magic!=0xD3||!memcmp(STEP->mix,mx.level,14));
}
static void begin(uint8_t current){uint8_t c;uint16_t left;
 memset(STEP->voice,0,sizeof(STEP->voice));STEP->samplecount=STEP->mask=STEP->release=STEP->routebits=STEP->routemask=STEP->noisechanged=STEP->kick=0;
 if(!configuration_valid||!native_valid()){
 STEP->generation=pattern_generation;STEP->bpm=seqbpm;STEP->units=15360U/seqbpm;STEP->slot=mx.slot;STEP->muted=seqmuted;STEP->solo=seqsolo;STEP->kit=drumkit;STEP->drummute=drummutemask;STEP->drumsolo=drumsolomask;
 memcpy(STEP->params,param,104);memcpy(STEP->gates,seqgate,4);memcpy(STEP->fine,finepitch,6);memcpy(STEP->bend,bend,6);STEP->wavecustom=custom;memcpy(STEP->waveinput,customwave,16);memcpy(STEP->noiseinput,noisepatch,10);memcpy(STEP->kickinput,pulsekickpatch,8);
 if(mx.magic==0xD3)memcpy(STEP->mix,mx.level,14);else{memset(STEP->mix,127,7);memset(STEP->mix+7,3,7);}
 configuration_valid=1;nativedirty=0;
 }
 for(c=0;c<7;c++){STEP->steps[c]=seqposition[c];if(!current&&++STEP->steps[c]>=seqlength[c])STEP->steps[c]=0;}
 left=current?0:(seqthreshold-seqclock+seqbpm-1)/seqbpm;
 for(c=0;c<2;c++){STEP->noisegate[c]=noiseleft[c]>left?noiseleft[c]-left:0;STEP->noisevelocity[c]=noiselevel[c];}
 STEP->kickgate=pulsekickleft>left?pulsekickleft-left:0;
 drumcursor=0;buildphase=1;
}
static void quantum(void){if(buildphase>=1&&buildphase<=4){voice(buildphase-1);buildphase++;}else if(buildphase==5)drums();else if(buildphase==6){if(STEP->mask&4)wavebytes();finish();}}

void seq_native_prepare(void) BANKED {uint8_t c,busy;
 if(building||!seqplaying||!eligible()||seqnativepending)return;
 if(buildphase==7){if(!nativedirty&&STEP->generation==pattern_generation&&STEP->bpm==seqbpm&&STEP->slot==mx.slot)return;if(native_valid()){nativedirty=0;return;}buildphase=0;}
 if(buildphase==255)return;
 for(c=0;c<4;c++)if(keycount[c]&&(!seqowned[c]||keycount[c]!=1||keystack[c][0]!=seqowned[c]-1)){buildphase=0;return;}
 building=1;busy=seqservicing;seqservicing=1;
 if(!buildphase)begin(0);else quantum();
 seqservicing=busy;building=0;
}
void seq_native_reset(void) BANKED {buildphase=0;seqnativepending=0;configuration_valid=0;nativedirty=1;}
void seq_native_launch(void) BANKED {
 if(!eligible()||building||!seq_native_launch_copy(mx.slot))return;
 STEP->generation=pattern_generation;
 /* Copy is granted only by the immediately preceding immutable cached-tone
    installation. Avoid re-comparing the entire just-installed patch at the
    musical boundary; retain the live scalar and tuning/gate guards. */
 configuration_valid=1;nativedirty=0;
 if(native_valid()&&!memcmp(STEP->gates,seqgate,4)&&!memcmp(STEP->fine,finepitch,6)&&!memcmp(STEP->bend,bend,6)){buildphase=7;}
 else{configuration_valid=0;buildphase=0;}
}
void seq_native_launch_clear(void) NONBANKED {if(!experimental_mode)*(volatile uint8_t *)0xA607=0;}
void seq_native_touch(void) NONBANKED {nativedirty=1;}
/* Establish transport time only after the cold first step is calculated. */
void seq_native_prime(void) BANKED {
 if(!eligible()||building)return;
 building=1;begin(1);
 while(buildphase&&buildphase!=7&&buildphase!=255)quantum();
 building=0;
}


#define ADOPT_NATIVE(C) do { \
v=&STEP->voice[C]; \
  if((C==2&&waveengine==3)||(C==3&&(STEP->noisegate[0]||STEP->noisegate[1]))){seqowned[C]=0;seqgateleft[C]=0;keycount[C]=0;held[C]=255;if(C==3)active[C]=0;break;} \
  if(v->note&&v->velocity){seqowned[C]=v->note;seqsource[C]=seqposition[C];seqgateleft[C]=v->gate;keycount[C]=1;keystack[C][0]=v->note-1;keyvel[C][0]=v->velocity; \
   held[C]=basepitch[C]=livepitch[C]=v->note-1;velocity[C]=v->velocity;phase[C]=age[C]=stepclock[C]=0;active[C]=!(STEP->params[C][9]||STEP->params[C][22]);if(C<3){polyowner[(C<3)?C:0]=0;finebase[C]=v->base;finemode[C]=finevalid[C]=0;if(finepitch[C])fine_apply(v->base,C,0);STEP->fine[(C<3)?C:0]=finepitch[C];} \
   tablepos[C]=tablemode[C]==3?notestep[C]++%tablelen[C]:0;tablerow[C]=tablepos[C];liveduty[C]=STEP->params[C][0];param[C][21]=STEP->params[C][21]=STEP->mix[7+C]; \
  }else if(release&(1<<C)){seqowned[C]=0;seqgateleft[C]=0;keycount[C]=0;held[C]=255;active[C]=0;} \
  \
} while(0)

uint8_t seq_native_fire(uint8_t expired) BANKED {uint8_t c,i,mask,release,ons,last=drumlast,busy;NativeVoice *v;NativeSample *sample,*targets[2]={0,0};
 seqnativefallback=0;
 if(!eligible()||building){seqnativefallback=1;return 0;}
 /* Never overwrite a published step during foreground catch-up. At most
    two ordinary PCM IRQs finish its first source block and shared attack. */
 while(seqnativepending){}
 for(c=0;c<4;c++)if(keycount[c]&&(!seqowned[c]||keycount[c]!=1||keystack[c][0]!=seqowned[c]-1)){seqnativefallback=16+c;return 0;}
 building=1;busy=seqservicing;seqservicing=1;
 if(!buildphase||buildphase==255||memcmp(STEP->steps,seqposition,4)||STEP->steps[6]!=seqposition[6]||!native_valid()){
  seqnativemisses++;begin(1);
 }else seqnativehits++;
 /* If the foreground reached the deadline part-way through preparation,
    finish the remaining phases instead of throwing away completed work. */
 while(buildphase&&buildphase!=7&&buildphase!=255)quantum();
 if(buildphase!=7){seqnativefallback=32;buildphase=0;seqservicing=busy;building=0;return 0;}
 /* New PCM sources must be in place before their next block is rendered.
    Keep all other attacks queued until that block is actually uploaded. */
 if(STEP->samplecount){if(waveengine!=3)drum_enable();drumenabled=1;drumtail=0;ons=(drumon[0]?1:0)|(drumon[1]?2:0);last=drumlast;
  for(i=0;i<STEP->samplecount;i++){c=!(ons&1)?0:!(ons&2)?1:last^1;last=c;ons|=1<<c;targets[c]=&STEP->sample[i];}
  c=STEP->mix[6];pcmoutlevel=c?c>84?1:c>42?2:3:0;pan(2,6);
 }
 mask=STEP->mask;release=STEP->release|expired;
 if(waveengine==3){if(STEP->samplecount||mixrunning||drumon[0]||drumon[1]){mask&=~4;release&=~4;pan(2,6);}else if(mask&4){TAC_REG=0;waveengine=0;w2enabled=0;TMA_REG=TIMA_REG=240;if(syncarmed)sync_timer_config();IF_REG&=~TIM_IFLAG;TAC_REG=4;}}
 if(STEP->noisegate[0]||STEP->noisegate[1]){mask&=~8;release&=~8;pan(3,6);}
 if(STEP->kickgate){mask&=~1;release&=~1;pan(0,6);}
 /* Publish the complete register image before setting its pending flag. */
 seqnativepending=0;HW[0]=mask;HW[1]=release&~mask;
 memcpy((void *)(HW+4),STEP->voice[0].regs,5);memcpy((void *)(HW+9),STEP->voice[1].regs+1,4);memcpy((void *)(HW+13),STEP->voice[2].regs,5);memcpy((void *)(HW+18),STEP->voice[3].regs,4);memcpy((void *)(HW+23),STEP->waveform,16);
 if(STEP->noisechanged){memcpy((void *)(HW+18),STEP->noisereg,4);HW[0]|=8;pan(3,6);}
 if(STEP->kick){memcpy((void *)(HW+4),STEP->kickreg,5);HW[0]|=1;pan(0,6);}
 HW[2]=STEP->routemask;HW[3]=STEP->routebits;
 HW[39]=(STEP->params[0][22]?1:0)|(STEP->params[1][22]?2:0);
 memcpy((void *)(HW+40),STEP->steps,4);
 /* The IRQ must never see a new source before its matching attack packet.
    Build all bytes first, then install at most two source records and arm
    their shared commit in one bounded interrupt window. */
 if(STEP->samplecount){__critical {
  for(c=0;c<2;c++)if(targets[c]){sample=targets[c];drumsamplevoice[c]=sample->sample;drumbankvoice[c]=sample->bank;drumpos[c]=sample->start;drumend[c]=sample->end;drumon[c]=1;}
  drumlast=last;drumtail=0;mixrunning=1;active[2]=1;seqnativepending=2;
 }}else if(waveengine==3){
  /* Keep native-only steps on the same PCM block pipeline as sample steps;
     otherwise every sample hit shifts the other voices by two blocks. */
  seqnativepending=2;
 }else{__critical {seq_native_hardware();}}
 ADOPT_NATIVE(0);ADOPT_NATIVE(1);ADOPT_NATIVE(2);ADOPT_NATIVE(3);
 if(STEP->noisechanged){for(c=0;c<2;c++){noiseleft[c]=STEP->noisegate[c];noiselevel[c]=STEP->noisevelocity[c];}drumnoiseowned=1;drumnoisetail=0;}
 if(STEP->kick){pulsekickleft=STEP->kickgate;active[0]=0;}
 buildphase=0;seqservicing=busy;building=0;return 1;
}

/* Fixed-ROM only, bounded register writes. SRAM bank zero is guaranteed at
   every interruptible point by the existing cartridge I/O windows. */
void seq_native_hardware(void) NONBANKED __naked {__asm
 push bc
 ld hl,#0xa400
 ld b,(hl)
 inc hl
 ld c,(hl)
 bit 0,c
 jr z,native_release_p2$
 ld a,(0xa427)
 and #1
 jr z,native_release_p1_bias$
 xor a
 ldh (#0x12),a
 jr native_release_p2$
native_release_p1_bias$:
 ld a,#8
 ldh (#0x12),a
 ld a,#0x80
 ldh (#0x14),a
native_release_p2$:
 bit 1,c
 jr z,native_release_wave$
 ld a,(0xa427)
 and #2
 jr z,native_release_p2_bias$
 xor a
 ldh (#0x17),a
 jr native_release_wave$
native_release_p2_bias$:
 ld a,#8
 ldh (#0x17),a
 ld a,#0x80
 ldh (#0x19),a
native_release_wave$:
 bit 2,c
 jr z,native_release_noise$
 xor a
 ldh (#0x1a),a
native_release_noise$:
 bit 3,c
 jr z,native_route$
 xor a
 ldh (#0x21),a
native_route$:
 ld a,(0xa402)
 cpl
 ld c,a
 ld a,(_route)
 and c
 ld c,a
 ld a,(0xa403)
 or c
 ld (_route),a
 ldh (#0x25),a
 bit 2,b
 jr z,native_p1$
 xor a
 ldh (#0x1a),a
 ld hl,#0xa417
 .irp ofs,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
 ld a,(hl+)
 ldh (#0x30+ofs),a
 .endm
native_p1$:
 bit 0,b
 jr z,native_p2$
 ld hl,#0xa404
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
native_p2$:
 bit 1,b
 jr z,native_wave$
 ld hl,#0xa409
 ld a,(hl+)
 ldh (#0x16),a
 ld a,(hl+)
 ldh (#0x17),a
 ld a,(hl+)
 ldh (#0x18),a
 ld a,(hl)
 ldh (#0x19),a
native_wave$:
 bit 2,b
 jr z,native_noise$
 ld hl,#0xa40d
 ld a,(hl+)
 ldh (#0x1a),a
 ld a,(hl+)
 ldh (#0x1b),a
 ld a,(hl+)
 ldh (#0x1c),a
 ld a,(hl+)
 ldh (#0x1d),a
 ld a,(hl)
 ldh (#0x1e),a
native_noise$:
 bit 3,b
 jr z,native_done$
 ld hl,#0xa412
 ld a,(hl+)
 ldh (#0x20),a
 ld a,(hl+)
 ldh (#0x21),a
 ld a,(hl+)
 ldh (#0x22),a
 ld a,(hl)
 ldh (#0x23),a
native_done$:
 pop bc
 ret
 __endasm; }

void seq_native_pcm_tick(void) NONBANKED {
 if(!seqnativepending)return;
 if(!seqplaying||experimental_mode||monomode){seqnativepending=0;return;}
 if(--seqnativepending)return;
 seq_native_hardware();
}
void seq_native_cancel_voice(uint8_t c) NONBANKED {if(seqnativepending&&c<4&&!(c==0&&pulsekickleft)&&!(c==2&&waveengine==3)&&!(c==3&&drumnoiseowned))HW[0]&=~(1<<c);}

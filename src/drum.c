#pragma bank 17
#pragma opt_code_speed
#include "api.h"
#include "seq_live_note.h"
#include "mod_bypass.h"
#include "mixer_shared.h"
#include "drum_rows.h"
uint8_t roll_note_feedback(uint8_t c,const uint8_t *e,uint8_t erase) BANKED;
uint16_t roll_drum_onset(uint8_t step,uint8_t row) BANKED;
uint16_t roll_drum_hit(uint8_t step,uint8_t row) BANKED;
void roll_drum_erase_handles(uint16_t deleted) BANKED;
extern __at (0xA500) uint32_t fastrowbits[13];
extern __at (0xA534) uint16_t fastoverlap;
extern __at (0xA800) uint16_t fastcells[13][32];
extern __at (0xA540) uint8_t fastcoverorigin[13][32];
extern uint8_t globalmod[10];
void seq_native_touch(void) NONBANKED;
#include "drum_samples.h"
extern const uint16_t notes[140];
extern uint8_t kickreleasing,expzvolume[2];
uint8_t eval_drum_pan(uint8_t c) BANKED;
/* Protected bank-zero control gap; keep the 1024-byte WRAM reserve. */
__at (0xAC59) uint32_t pulsekickleft;
uint8_t pulsekickpatch[8];
const uint8_t kickfactory[8]={15,48,2,1,1,2,24,1};
const uint8_t kickmax[8]={15,96,3,7,7,7,64,1};
const char * const kicknames[]={"LEVEL","PITCH","DUTY","FALL RATE","SWEEP TIME","SWEEP SHIFT","LENGTH","SWEEP DIR"};
/* Exact division by127 for envelope products; no software divider per hit. */
static uint8_t drum_scale(uint16_t value){uint8_t q=value>>7;return q+((uint8_t)((value&127)+q)>=127);}
/* P1 keeps its logical note/gate while PK owns the hardware. Restore the
   current sequence note only while its original gate is still open. */
void eval_audio_resume_pulse1(void) BANKED;
void kick_stop(void){uint8_t e[4];if(!pulsekickleft)return;pulsekickleft=0;kickreleasing=0;eval_note(7,0);NR12_REG=8;NR14_REG=0x80;route=(route&~0x11)|(param[0][21]&1?1:0)|(param[0][21]&2?0x10:0);NR51_REG=route;
 if(experimental_mode&&!monomode&&(active[0]||mono_owned&1)){eval_audio_resume_pulse1();return;}
 if(seqplaying&&!monomode&&seqowned[0]&&seqgateleft[0]){

  if(!seq_note_event(0,seqsource[0],e))return;
  param[0][21]=mixer_pan(0);liveparam(0,9);play(0,seqowned[0]-1,mixer_velocity(0,e[2]));
 }
}
extern uint8_t evalkickvelocity;
void kick_start(uint8_t vel,uint32_t gate){evalkickvelocity=vel;kickreleasing=0;uint16_t f=eval_drum_pitch(7,notes[pulsekickpatch[1]]);eval_note(7,1);uint8_t pan=eval_drum_pan(7),vol=drum_scale((uint16_t)eval_drum_level(7,pulsekickpatch[0])*vel);uint16_t length=(uint16_t)pulsekickpatch[6]*4;if(!length)length=4;pulsekickleft=gate<length?gate:length;if(!experimental_mode)active[0]=0;NR10_REG=(pulsekickpatch[4]<<4)|(pulsekickpatch[7]<<3)|pulsekickpatch[5];NR11_REG=(eval_drum_duty(7,pulsekickpatch[2])<<6)|((64-pulsekickpatch[6])&63);NR12_REG=(vol<<4)|(MOD_LEVEL(7)?8:pulsekickpatch[3]);expzvolume[0]=vol;NR13_REG=f;NR14_REG=(!mod_bypass&&globalmod[3]?0x80:0xC0)|(f>>8);route=(route&~0x11)|(pan&1?1:0)|(pan&2?0x10:0);NR51_REG=route;}
uint8_t drumpackmask;
/* Upper delay allocation was twice the maximum selectable delay. Reserve its
   unused 2 KiB for the kit pattern and PCM state; no SD writes or extra RAM. */
__at (0xAC00) uint8_t drumraw[2][16];
__at (0xAC20) uint8_t drumgain[2][16];
__at (0xAC40) uint8_t drumon[2];
__at (0xAC42) uint16_t drumpos[2];
__at (0xAC46) uint16_t drumend[2];
__at (0xAC4A) uint8_t drumlast;
__at (0xAC4B) uint8_t drumbankvoice[2];
uint32_t noiseleft[2];
uint8_t drumreleasing[2],kickreleasing;
__at (0xAC54) uint8_t noiselevel[2];
__at (0xAC56) uint16_t drumserial;
__at (0xAC60) uint8_t noisepatch[2][5];
extern __at (0xBA00) uint8_t rollrow[320];
extern __at (0xBB40) uint8_t rollbackground[320];
extern __at (0xBC80) uint8_t rollx[41];
__at (0xAD80) uint8_t drumleft[192];
__at (0xAE40) uint8_t drumright[192];
__at (0xAF00) uint8_t drumnext[192];
__at (0xAFC0) uint8_t drumheads[13];
uint8_t drumkit=1;
uint8_t drummapkit=255,drumsourcekit[10],drumsourceslot[10],drumsourcebank[10];
uint16_t drumsourceoffset[10],drumsourcelength[10];
void drum_map_factory(uint8_t kit) BANKED {uint8_t i;if(kit>7)kit=1;drumkit=kit;for(i=0;i<10;i++){drumsourcekit[i]=kit;drumsourceslot[i]=i;drumsourcebank[i]=(kit?kitbank[kit-1]:amenbank)[i];drumsourceoffset[i]=(kit?kitoffset[kit-1]:amenoffset)[i];drumsourcelength[i]=(kit?kitlength[kit-1]:amenlength)[i];}drummapkit=kit;}
void drum_map_assign(uint8_t dest,uint8_t kit,uint8_t sample) BANKED {if(dest>=10||kit>7||sample>=(kit?8:10))return;if(!DRUM_MAPPED)drum_map_factory(drumkit);drumsourcekit[dest]=kit;drumsourceslot[dest]=sample;drumsourcebank[dest]=(kit?kitbank[kit-1]:amenbank)[sample];drumsourceoffset[dest]=(kit?kitoffset[kit-1]:amenoffset)[sample];drumsourcelength[dest]=(kit?kitlength[kit-1]:amenlength)[sample];}
void drum_map_capture(uint8_t *out) BANKED {if(!DRUM_MAPPED)drum_map_factory(drumkit);out[0]='D';out[1]=1;memcpy(out+2,drumsourcekit,10);memcpy(out+12,drumsourceslot,10);}
void drum_map_restore(const uint8_t *in) BANKED {uint8_t i;if(DRUM_MAPPED&&in[0]=='D'&&in[1]==1&&!memcmp(drumsourcekit,in+2,10)&&!memcmp(drumsourceslot,in+12,10))return;drum_map_factory(drumkit);if(in[0]!='D'||in[1]!=1)return;for(i=0;i<10;i++)if(in[2+i]>7||in[12+i]>=10||in[2+i]&&in[12+i]>=8){/* Factory rows 9/10 are intentional silent placeholders. */if(in[2+i]!=drumkit||in[12+i]!=i)return;}for(i=0;i<10;i++){uint8_t k=in[2+i],s=in[12+i];drumsourcekit[i]=k;drumsourceslot[i]=s;drumsourcebank[i]=(k?kitbank[k-1]:amenbank)[s];drumsourceoffset[i]=(k?kitoffset[k-1]:amenoffset)[s];drumsourcelength[i]=(k?kitlength[k-1]:amenlength)[s];}}
uint8_t drumenabled,drumrow,druminit,drumsynthrow,drumsynthvoice;
uint16_t drumanchor=65535U;
uint8_t drumbused,drumnoiseowned;
/* Spare byte between drumserial and noisepatch in cartridge RAM. */
__at (0xAC58) uint8_t drumnoisetail;
uint16_t drummutemask,drumsolomask;
uint8_t drumsamplevoice[2];
uint8_t drum_audible(uint8_t row){uint16_t bit=1U<<row;return !(drummutemask&bit)&&(!drumsolomask||(drumsolomask&bit));}
const uint8_t noisemax[5]={15,15,7,1,7};
/* Wide-noise hat and snare, both with a quick decay. */
const uint8_t noisefactory[2][5]={{15,0,1,0,1},{15,4,2,0,1}};
const char * const drumnoisenames[]={"LEVEL","CLOCK SHIFT","DIVISOR","METALLIC","FALL RATE"};
void drum_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
void drum_num(uint8_t x,uint8_t y,uint8_t n,uint8_t inv){uint8_t hundreds=0,tens=0;while(n>=100){hundreds++;n-=100;}while(n>=10){tens++;n-=10;}canvas[y*20+x]=16+hundreds+(inv?96:0);canvas[y*20+x+1]=16+tens+(inv?96:0);canvas[y*20+x+2]=16+n+(inv?96:0);}
void drum_init(void) BANKED {ENABLE_RAM_MBC5;SWITCH_RAM_MBC5(0);if(druminit)return;pulsekickleft=0;memset(noiseleft,0,8);drumnoisetail=0;memcpy(noisepatch,noisefactory,10);memcpy(pulsekickpatch,kickfactory,8);drumserial=0;drumlast=0;druminit=1;}
/* Keep CH4's DAC bias stable when silencing, just as for the pulse voices.
   A zero-volume trigger is required to latch silence on DMG hardware. */
static void drum_noise_silence(void){NR42_REG=8;NR44_REG=0x80;drumnoisetail=0;}
/* A normal gate ends logical ownership, but lets a decaying hardware envelope
   finish. Constant-volume patches must be explicitly silenced. Never restart
   the shared noise generator merely because one of its logical voices ends. */
void eval_audio_resume_noise(void) BANKED;
static void drum_noise_release(uint8_t force){
 if(!noiseleft[0]&&!noiseleft[1]&&(drumnoiseowned||(force&&drumnoisetail))){
  if(force||!(NR42_REG&7))drum_noise_silence();else drumnoisetail=1;
  drumnoiseowned=0;
  if(experimental_mode&&active[3])eval_audio_resume_noise();
 }
}
void drum_stop(void) BANKED {if(!druminit)return;kick_stop();drumon[0]=drumon[1]=0;if(waveengine==3){drumtail=1;mixrunning=0;if(!experimental_mode)active[2]=0;mixready[0]=mixready[1]=0;NR30_REG=0;}noiseleft[0]=noiseleft[1]=0;memset(drumreleasing,0,2);if(drumnoiseowned||drumnoisetail)drum_noise_silence();drumnoiseowned=0;}
void drum_noise(void){uint8_t i,n=0,pan,v[5],a=!!noiseleft[0],b=!!noiseleft[1];if(!a&&!b){drum_noise_release(0);return;}
 for(i=0;i<5;i++){v[i]=a&&b?(noisepatch[0][i]+noisepatch[1][i]+1)>>1:noisepatch[b?1:0][i];}
 if(a&&b)n=drum_scale(((uint16_t)eval_drum_level(5,noisepatch[0][0])*noiselevel[0]+(uint16_t)eval_drum_level(6,noisepatch[1][0])*noiselevel[1]+127)>>1);else n=drum_scale((uint16_t)eval_drum_level(b?6:5,v[0])*noiselevel[b?1:0]);
 NR41_REG=0;NR42_REG=n?((n<<4)|(MOD_LEVEL(b?6:5)?8:v[4])):8;expzvolume[1]=n;NR43_REG=eval_drum_pitch(b?6:5,(v[1]<<4)|(v[3]<<3)|v[2]);NR44_REG=0x80;pan=eval_drum_pan(b?6:5);route=(route&~0x88)|((pan&1)?8:0)|((pan&2)?0x80:0);NR51_REG=route;drumnoiseowned=1;drumnoisetail=0;
}
void drum_tick(uint16_t ticks) BANKED {uint8_t i,changed=0;if(!druminit)return;if(pulsekickleft){if(pulsekickleft<=ticks){if(!kickreleasing&&MOD_LEVEL(7)&&globalmod[3]){kickreleasing=1;pulsekickleft=(uint16_t)globalmod[3]*17;eval_note(7,0);}else kick_stop();}else pulsekickleft-=ticks;}for(i=0;i<2;i++)if(noiseleft[i]){if(noiseleft[i]<=ticks){if(!drumreleasing[i]&&MOD_LEVEL(5+i)&&globalmod[3]){drumreleasing[i]=1;noiseleft[i]=(uint16_t)globalmod[3]*17;eval_note(5+i,0);}else{noiseleft[i]=0;drumreleasing[i]=0;eval_note(5+i,0);changed=1;}}else noiseleft[i]-=ticks;}if(changed){if(noiseleft[0]||noiseleft[1])drum_noise();else drum_noise_release(0);}}
void drum_mixer_refresh(void) BANKED {uint8_t i,pan;if(!drum_audible(12))kick_stop();for(i=0;i<2;i++){if(drumon[i]&&!drum_audible(drumsamplevoice[i])){__critical {drumon[i]=0;}}if(!drum_audible(10+i))noiseleft[i]=0;}drum_noise_release(1);pan=mixer_pan(6);route=(route&~0x88)|((pan&1)?8:0)|((pan&2)?0x80:0);NR51_REG=route;}
/* ROM lookup keeps sample-gate conversion off the live onset divider. */
static const uint16_t drumstepsamples[271]={5730,5545,5371,5209,5055,4911,4775,4645,4523,4407,4297,4192,4092,3997,3906,3820,3736,3657,3581,3508,3438,3370,3305,3243,3183,3125,3069,3015,2963,2913,2865,2818,2772,2728,2685,2644,2604,2565,2527,2491,2455,2421,2387,2354,2322,2292,2261,2232,2203,2175,2148,2122,2096,2071,2046,2022,1998,1975,1953,1931,1910,1889,1868,1848,1828,1809,1790,1772,1754,1736,1719,1701,1685,1668,1652,1637,1621,1606,1591,1577,1562,1548,1534,1521,1507,1494,1481,1469,1456,1444,1432,1420,1409,1397,1386,1375,1364,1353,1342,1332,1322,1312,1302,1292,1282,1273,1263,1254,1245,1236,1227,1219,1210,1202,1193,1185,1177,1169,1161,1153,1146,1138,1130,1123,1116,1109,1101,1094,1087,1081,1074,1067,1061,1054,1048,1041,1035,1029,1023,1017,1011,1005,999,993,987,982,976,971,965,960,955,949,944,939,934,929,924,919,914,909,904,900,895,890,886,881,877,872,868,863,859,855,850,846,842,838,834,830,826,822,818,814,810,807,803,799,795,792,788,784,781,777,774,770,767,764,760,757,753,750,747,744,740,737,734,731,728,725,722,719,716,713,710,707,704,701,698,695,693,690,687,684,682,679,676,674,671,668,666,663,661,658,656,653,651,648,646,643,641,639,636,634,631,629,627,625,622,620,618,616,613,611,609,607,605,603,601,598,596,594,592,590,588,586,584,582,580,578,576,574,573};
uint16_t drum_step_samples(void){uint16_t q;if(seqbpm>=30&&seqbpm<=300)return drumstepsamples[seqbpm-30];q=17190U/seqbpm;return q*10+((17190U-q*seqbpm)*10)/seqbpm;}
uint8_t drum_auto(uint8_t sample){uint16_t samples=drum_step_samples();uint8_t dur=(drumlength[sample]*2+samples-1)/samples;return dur?dur:1;}
static void drum_start_source(uint8_t sample,uint8_t bank,uint16_t offset,uint16_t length){uint8_t c,pan;
 drum_enable();if(!drumenabled){drumenabled=1;drumon[0]=drumon[1]=0;}c=!drumon[0]?0:!drumon[1]?1:drumlast^1;drumlast=c;
 pan=mixer_pan(6);route=(route&~0x44)|((pan&1)?4:0)|((pan&2)?0x40:0);NR51_REG=route;
 __critical {drumsamplevoice[c]=sample;drumpos[c]=offset;drumbankvoice[c]=bank;drumend[c]=offset+length;drumon[c]=1;drumtail=0;mixrunning=1;if(!experimental_mode)active[2]=1;}
}
void drum_start(uint8_t sample,uint8_t vel,uint8_t dur){(void)vel;(void)dur;drum_start_source(sample,drumbank[sample],drumoffset[sample],drumlength[sample]);}
void drum_source_audition(uint8_t kit,uint8_t sample) BANKED {if(kit>7||sample>=(kit?8:10))return;drum_start_source(sample,(kit?kitbank[kit-1]:amenbank)[sample],(kit?kitoffset[kit-1]:amenoffset)[sample],(kit?kitlength[kit-1]:amenlength)[sample]);}
/* PCM stores two samples per byte. Cap the source at the plotted gate;
   longer notes still stop naturally at the end of the sample. */
uint16_t drum_play_length(uint8_t sample,uint8_t duration){uint32_t bytes=(uint32_t)drum_step_samples()*(duration?duration:256U)/2;return bytes<drumlength[sample]?(uint16_t)bytes:drumlength[sample];}
/* Precompute source addresses outside the attack deadline. Flat six-byte
   record: sample, ROM bank, start LE16, end LE16. */
void seq_native_sample_value(const uint8_t *e,uint8_t *out,uint8_t kit,uint16_t bpm) BANKED {
 uint8_t sample=e[1]-1,mapped=kit==drumkit&&DRUM_MAPPED;uint16_t start=(mapped?drumsourceoffset:kit?kitoffset[kit-1]:amenoffset)[sample],length=(mapped?drumsourcelength:kit?kitlength[kit-1]:amenlength)[sample],samples,q;uint32_t bytes;
 if(bpm>=30&&bpm<=300)samples=drumstepsamples[bpm-30];else{q=17190U/bpm;samples=q*10+((17190U-q*bpm)*10)/bpm;}
 if(e[3]==1)bytes=samples>>1;else if(e[3]==2)bytes=samples;else if(e[3]==4)bytes=(uint32_t)samples<<1;else if(e[3]==8)bytes=(uint32_t)samples<<2;else bytes=(uint32_t)samples*(e[3]?e[3]:256U)/2;
 length=start+(bytes<length?(uint16_t)bytes:length);
 out[0]=sample;out[1]=(mapped?drumsourcebank:kit?kitbank[kit-1]:amenbank)[sample];out[2]=start;out[3]=start>>8;out[4]=length;out[5]=length>>8;
}
void seq_native_sample(const uint8_t *e,uint8_t *out) BANKED {seq_native_sample_value(e,out,drumkit,seqbpm);}

void drum_fire(uint8_t step) BANKED {
 uint8_t e[4],sample,c,pending=0,ons,last,changed=0,banks[2],samples[2];uint16_t cursor=0,starts[2],ends[2],step_samples=0,step_units;uint32_t bytes;
 extern uint16_t seqstepunits,seqcachedbpm;
 if(!step&&seqeventcache==2&&(*(uint8_t *)0xACCF&64))return;
 step_units=seqcachedbpm==seqbpm?seqstepunits:15360U/seqbpm;
 drum_init();ons=(drumon[0]?1:0)|(drumon[1]?2:0);last=drumlast;
 while(seq_event_next_step(6,step,&cursor,e)){
  if(!step&&seqeventcache==2&&(*(uint8_t *)0xACCF&128))cursor=seqeventcounts[6];
  if(!e[1]||!drum_audible(e[1]-1)||!eval_drum_allowed(cursor-1))continue;
  if(e[1]<=10){if(!pending){drum_enable();if(!drumenabled){drumenabled=1;ons=0;}}
   if((ons&3)==3)continue;c=!(ons&1)?0:1;last=c;ons|=1<<c;pending|=1<<c;
   if(!step_samples)step_samples=drum_step_samples();
   sample=e[1]-1;samples[c]=sample;starts[c]=drumoffset[sample];
   /* Exact common durations avoid a general 32-bit multiply at the onset.
      Cast before shifting so unusual out-of-range tempos cannot overflow. */
   if(e[3]==1)bytes=step_samples>>1;
   else if(e[3]==2)bytes=step_samples;
   else if(e[3]==4)bytes=(uint32_t)step_samples<<1;
   else if(e[3]==8)bytes=(uint32_t)step_samples<<2;
   else bytes=(uint32_t)step_samples*(e[3]?e[3]:256U)/2;
   ends[c]=starts[c]+(bytes<drumlength[sample]?(uint16_t)bytes:drumlength[sample]);banks[c]=drumbank[sample];
  }else if(e[1]<=12){c=e[1]-11;drumreleasing[c]=0;if(drumreleasing[c^1]){noiseleft[c^1]=0;drumreleasing[c^1]=0;}eval_note(5+c,1);noiseleft[c]=(uint32_t)step_units*(e[3]?e[3]:256U);noiselevel[c]=mixer_velocity(6,e[2]);changed=1;}else if(e[1]==13)kick_start(mixer_velocity(6,e[2]),(uint32_t)step_units*(e[3]?e[3]:256U));
 }
 if(pending){__critical {
  if(pending&1){drumsamplevoice[0]=samples[0];drumpos[0]=starts[0];drumend[0]=ends[0];drumbankvoice[0]=banks[0];drumon[0]=1;}
  if(pending&2){drumsamplevoice[1]=samples[1];drumpos[1]=starts[1];drumend[1]=ends[1];drumbankvoice[1]=banks[1];drumon[1]=1;}
  /* The PCM IRQ may have finished the old voices while these attacks were
     prepared. Publish their running state and clear that stale tail together. */
  drumlast=last;drumtail=0;mixrunning=1;if(!experimental_mode)active[2]=1;
 }}if(changed)drum_noise();
}
/* Native-rate, direct PCM: no oscillator, pitch, envelope or DDS processing.
   Single hits retain full amplitude. Overlaps average independently per nibble.
   Latch activity before fetching so the final block also keeps its full level. */
void drum_pack(void) __naked { __asm
 push bc
 ld a,(_mixwrite)
 swap a
 ld e,a
 ld d,#0
 ld hl,#_mixbuffer
 add hl,de
 ld d,h
 ld e,l
 ld a,(_drumpackmask)
 cp #3
 jr z,drum_pack_pair$
 ld hl,#0xac00
 cp #2
 jr nz,drum_pack_single$
 ld hl,#0xac10
drum_pack_single$:
 .rept 16
 ld a,(hl+)
 ld (de),a
 inc de
 .endm
 pop bc
 ret
drum_pack_pair$:
 ld a,(0xac00)
 ld b,a
 ld a,(0xac10)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac01)
 ld b,a
 ld a,(0xac11)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac02)
 ld b,a
 ld a,(0xac12)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac03)
 ld b,a
 ld a,(0xac13)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac04)
 ld b,a
 ld a,(0xac14)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac05)
 ld b,a
 ld a,(0xac15)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac06)
 ld b,a
 ld a,(0xac16)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac07)
 ld b,a
 ld a,(0xac17)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac08)
 ld b,a
 ld a,(0xac18)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac09)
 ld b,a
 ld a,(0xac19)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac0a)
 ld b,a
 ld a,(0xac1a)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac0b)
 ld b,a
 ld a,(0xac1b)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac0c)
 ld b,a
 ld a,(0xac1c)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac0d)
 ld b,a
 ld a,(0xac1d)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac0e)
 ld b,a
 ld a,(0xac1e)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 ld a,(0xac0f)
 ld b,a
 ld a,(0xac1f)
 ld c,a
 xor a,b
 and #0xee
 rrca
 ld l,a
 ld a,c
 and b
 add a,l
 ld (de),a
 inc de
 pop bc
 ret
 __endasm; }
/* One 11712-cycle timer period equals 183/64 sequencer milliseconds.
   Keep the clock and upload in assembly so foreground note events have room. */
void streamblock(void);
void drum_timer(void) BANKED __naked { __asm
 push bc
 ; Allow only fixed-bank serial completion to preempt PCM work. This rearms
 ; external-clock reception before the peer next byte; audio/timer work
 ; cannot recursively enter the mixer.
 ldh a,(#0xff)
 push af
 and #8
 ldh (#0xff),a
 ei
 ld a,(_seqplaying)
 or a
 jr z,drum_timer_clocked$
 ld a,(_syncmode)
 or a
 jr z,drum_timer_local_clock$
 ld a,(_syncslave)
 or a
 jr nz,drum_timer_clocked$
drum_timer_local_clock$:
 ld a,(_seqfraction)
 add a,#183
 ld b,a
 and #63
 ld (_seqfraction),a
 ld a,b
 swap a
 rrca
 rrca
 and #3
 ld hl,#_seqticks
 add a,(hl)
 ld (hl+),a
 jr nc,drum_timer_clocked$
 inc (hl)
drum_timer_clocked$:
 call _seq_native_pcm_tick
 ld a,(_power)
 or a
 jp z,drum_timer_done$
 ld a,(_mixrunning)
 or a
 jp z,drum_timer_done$
 ld a,(_mixread)
 ld e,a
 ld d,#0
 ld hl,#_mixready
 add hl,de
 ld a,(hl)
 or a
 jr nz,drum_timer_upload$
 ld a,(_drumtail)
 or a
 jr z,drum_timer_prime$
 xor a
 ld (_mixrunning),a
 ld a,(_experimental_mode)
 or a
 jr nz,drum_keep_wave$
 xor a
 ld (_active+2),a
drum_keep_wave$:
 xor a
 ldh (#0x1a),a
 jp drum_timer_done$
drum_timer_prime$:
 xor a
 ldh (#0x1a),a
 call _drum_irq
 jp drum_timer_done$
drum_timer_upload$:
 ; Prepare every register and pointer before disconnecting the channel.
 ld a,(_pcmoutlevel)
 swap a
 add a,a
 ldh (#0x1c),a
 ; Divider 176 fits all 32 reads inside the measured active window.
 ld a,#0x50
 ldh (#0x1d),a
 ld a,(_mixread)
 swap a
 ld e,a
 ld d,#0
 ld hl,#_mixbuffer
 add hl,de
 ; CH3 is disconnected only for the short DAC-off upload and retrigger.
 ldh a,(#0x25)
 push af
 and #0xbb
 ldh (#0x25),a
 xor a
 ldh (#0x1a),a
 .irp ofs,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
 ld a,(hl+)
 ldh (#0x30+ofs),a
 .endm
 ld a,#0x80
 ldh (#0x1a),a
 ld a,#0x87
 ldh (#0x1e),a
 pop af
 ldh (#0x25),a
 ld a,(_mixread)
 ld e,a
 ld d,#0
 ld hl,#_mixready
 add hl,de
 ld (hl),#0
 xor #1
 ld (_mixread),a
 ld hl,#_engineblocks
 inc (hl)
 jr nz,drum_timer_counted$
 inc hl
 inc (hl)
drum_timer_counted$:
 call _drum_irq
drum_timer_done$:
 di
 pop af
 ldh (#0xff),a
 pop bc
 ret
 __endasm; }
/* Interrupt-owned producer: one prepared block follows the previous upload.
   Foreground code never enters this function, so rendering cannot starve PCM. */
void drum_irq(void) BANKED __naked { __asm
 push bc
 ld a,(0xac40)
 ld b,a
 ld a,(0xac41)
 or a,b
 jr nz,drum_irq_fill$
 ld a,#1
 ld (_drumtail),a
 pop bc
 ret
drum_irq_fill$:
 ld a,(_mixread)
 ld (_mixwrite),a
 call _drum_mix
 ld a,(_mixread)
 ld e,a
 ld d,#0
 ld hl,#_mixready
 add hl,de
 ld (hl),#1
 pop bc
 ret
 __endasm; }
void drum_fetch_fast(uint8_t voice) NONBANKED;
void drum_mix(void) BANKED __naked { __asm
 push bc
 ld a,(0xac41)
 add a,a
 ld b,a
 ld a,(0xac40)
 or b
 ld (_drumpackmask),a
 ld a,(0xac40)
 or a
 jr z,drum_quiet0$
 ld a,#0
 call _drum_fetch_fast
 ld hl,#0xac42
 ld a,(hl+)
 add a,#16
 ld c,a
 ld a,(hl)
 adc a,#0
 ld b,a
 ld (hl-),a
 ld (hl),c
 ld hl,#0xac46
 ld a,c
 sub a,(hl)
 ld a,b
 inc hl
 sbc a,(hl)
 jr c,drum_done0$
 xor a
 ld (0xac40),a
 jr drum_done0$
drum_quiet0$:
 ld hl,#0xac00
 ld a,#0x88
 .rept 16
 ld (hl+),a
 .endm
drum_done0$:
 ld a,(0xac41)
 or a
 jr z,drum_quiet1$
 ld a,#1
 call _drum_fetch_fast
 ld hl,#0xac44
 ld a,(hl+)
 add a,#16
 ld c,a
 ld a,(hl)
 adc a,#0
 ld b,a
 ld (hl-),a
 ld (hl),c
 ld hl,#0xac48
 ld a,c
 sub a,(hl)
 ld a,b
 inc hl
 sbc a,(hl)
 jr c,drum_done1$
 xor a
 ld (0xac41),a
 jr drum_done1$
drum_quiet1$:
 ld hl,#0xac10
 ld a,#0x88
 .rept 16
 ld (hl+),a
 .endm
drum_done1$:
 call _drum_pack
 pop bc
 ret
 __endasm; }
uint16_t drum_duration(const uint8_t *e){return e[3]?e[3]:256U;}
uint16_t drum_find(uint8_t step,uint8_t row){uint16_t i,count=seq_event_count(6),best=65535U;uint8_t e[4],start=0;i=roll_drum_hit(step,row);if(i==65535U)return i;if(i!=65534U&&i!=65535U&&i<count&&seq_event_get(6,i,e)&&e[1]==DRUM_VOICE_ROW(row)+1&&step>=e[0]&&(uint16_t)step<e[0]+drum_duration(e))return i;for(i=0;i<count;i++)if(seq_event_get(6,i,e)&&e[1]==DRUM_VOICE_ROW(row)+1&&step>=e[0]&&(uint16_t)step<e[0]+drum_duration(e)){if(e[0]==step)return i;if(best==65535U||e[0]>=start){best=i;start=e[0];}}return best;}

void drum_erase(uint16_t index,uint8_t row){uint8_t e[4],fast=0;(void)row;eval_message=0;if(index!=65535U){if(seq_event_get(6,index,e))fast=roll_note_feedback(6,e,1);seq_event_erase(6,index);if(fast)roll_drum_erase_handles(index);}seqdrawvalid=fast;dirty=1;}
void drum_age_sync(void) BANKED {}
/* The event pool's insertion order is the plot age. */
uint8_t roll_drum_group_refresh(int8_t dx,int8_t dy,int8_t resize) BANKED;
void roll_edit_batch(uint8_t enabled) BANKED;
uint8_t roll_group_add(uint8_t c,const uint8_t *e,uint16_t index) BANKED;
uint8_t roll_replace_feedback(uint8_t c,const uint8_t *old,const uint8_t *next,uint16_t index) BANKED;
uint16_t drum_plot(uint8_t step,uint8_t row,uint16_t dur,uint8_t vel,uint16_t age){uint16_t i,t,end,newest,count,replace=age?age-1:65535U;uint8_t e[4],old[4],voices,fast=0;
 if(row>12||step>=seqlength[6])return 65535U;
 if(!dur)dur=row>=3?drum_auto(DRUM_VOICE_ROW(row)):1;
 end=(uint16_t)step+dur;if(end>seqlength[6])end=seqlength[6];dur=end-step;if(!dur)return 65535U;
 if(row<3){i=drum_find(step,row);if(i!=65535U&&i!=replace){seq_event_get(6,i,e);if(e[0]==step){drum_erase(i,row);if(replace!=65535U&&i<replace)replace--;}}}
 e[0]=step;e[1]=DRUM_VOICE_ROW(row)+1;e[2]=vel;e[3]=(uint8_t)dur;if(replace!=65535U&&seq_event_get(6,replace,old))fast=roll_replace_feedback(6,old,e,replace);if(replace==65535U&&seq_event_total()<256)fast=roll_note_feedback(6,e,0);if(!seq_event_put(6,replace,e)){seqdrawvalid=0;return 65535U;}seqdrawvalid=fast;dirty=1;return replace==65535U?seq_event_count(6)-1:replace;
}
void drum_insert(void){uint16_t n=drum_find(seqcursor[6],drumrow),dur=seqdefaultdur[6];if(n!=65535U){drum_erase(n,drumrow);return;}if(!dur)dur=drumrow>=3?drum_auto(DRUM_VOICE_ROW(drumrow)):1;n=drum_plot(seqcursor[6],drumrow,dur,eval_plotvel[6],0);eval_message=n!=65535U&&!seqdrawvalid&&!eval_drum_allowed(n)?1:0;if(n!=65535U&&!seqplaying)seq_plot_audition(6,drumrow,eval_plotvel[6]);dirty=1;}
void drum_brush_erase(void) BANKED {uint8_t e[4];uint16_t n=roll_drum_onset(seqcursor[6],drumrow),cursor=0;
 if(n==65534U){n=65535U;while(seq_event_next_step(6,seqcursor[6],&cursor,e))if(e[1]==DRUM_VOICE_ROW(drumrow)+1){n=cursor-1;break;}}
 if(n!=65535U)drum_erase(n,drumrow);
}
void drum_brush_plot(void) BANKED {uint8_t e[4];uint16_t n=roll_drum_onset(seqcursor[6],drumrow),cursor=0;if(n==65534U){while(seq_event_next_step(6,seqcursor[6],&cursor,e))if(e[1]==DRUM_VOICE_ROW(drumrow)+1)return;}else if(n!=65535U)return;n=drum_plot(seqcursor[6],drumrow,seqdefaultdur[6],eval_plotvel[6],0);eval_message=n!=65535U&&!seqdrawvalid&&!eval_drum_allowed(n)?1:0;if(n!=65535U&&!seqplaying)seq_plot_audition(6,drumrow,eval_plotvel[6]);dirty=1;}

uint8_t drum_selected_event(const uint8_t *e){return seqgrouptrack==6&&e[1]&&e[0]>=seqgroupx0&&e[0]<=seqgroupx1&&DRUM_VIEW_ROW(e[1]-1)>=seqgroupy0&&DRUM_VIEW_ROW(e[1]-1)<=seqgroupy1;}
uint8_t drum_group_size(int8_t delta){uint16_t i,t,count=seq_event_count(6);uint8_t e[4],old[4],voices,pcm=0,fast=seqdrawvalid;int16_t d;
 for(i=0;i<count;i++){seq_event_get(6,i,e);if(drum_selected_event(e)){if(e[1]<=10)pcm=1;d=drum_duration(e)+delta;if(d<1||d>seqlength[6]-e[0])return 0;}}
 for(i=0;i<count;i++){seq_event_get(6,i,e);if(drum_selected_event(e)){e[3]=(uint8_t)(drum_duration(e)+delta);seq_event_put(6,i,e);}if(!(i&7))service();}seqdrawvalid=roll_drum_group_refresh(0,0,delta);return 1;
}
uint8_t drum_group_move(int8_t dx,int8_t dy){uint16_t i,j,count=seq_event_count(6),selected=0;uint8_t e[4],other[4],old[4],fast=seqdrawvalid;int16_t dst,row;
 if((int16_t)seqgroupx0+dx<0||seqgroupx1+dx>=seqlength[6]||(int16_t)seqgroupy0+dy<0||seqgroupy1+dy>12)return 0;
 for(i=0;i<count;i++){seq_event_get(6,i,e);if(!drum_selected_event(e))continue;dst=e[0]+dx;row=DRUM_VIEW_ROW(e[1]-1)+dy;if(e[1]<=10){if(row<3)return 0;}else if(row>=3)return 0;if(dst+drum_duration(e)>seqlength[6])return 0;selected++;
 }
 if(selected<count)for(i=0;i<count;i++){seq_event_get(6,i,e);if(!drum_selected_event(e))continue;dst=e[0]+dx;row=DRUM_VIEW_ROW(e[1]-1)+dy;
  for(j=0;j<count;j++){seq_event_get(6,j,other);if(drum_selected_event(other)||!other[1])continue;if((row>=3&&other[1]<=10)||(other[1]==DRUM_VOICE_ROW(row)+1)){if(dst<(uint16_t)other[0]+drum_duration(other)&&other[0]<dst+drum_duration(e))return 0;}}
 }
 for(i=0;i<count;i++){seq_event_get(6,i,e);if(drum_selected_event(e)){e[0]+=dx;e[1]=DRUM_VOICE_ROW(DRUM_VIEW_ROW(e[1]-1)+dy)+1;seq_event_put(6,i,e);}if(!(i&7))service();}seqdrawvalid=roll_drum_group_refresh(dx,dy,0)?2:0;seqgroupx0+=dx;seqgroupx1+=dx;seqgroupy0+=dy;seqgroupy1+=dy;return 1;
}
uint8_t seq_top_entry(void) BANKED;
void drum_input(uint8_t p,uint8_t edge) BANKED {uint8_t s=seqcursor[6],row=drumrow,e[4];uint16_t n,dur;int16_t dst,r;drum_init();
 if(!seqapending&&(edge&J_B)){drumbused=seqamoved=0;drumanchor=drum_find(s,row);seqapending=drumanchor==65535U?2:1;if(seqapending==2){drum_insert();drumanchor=drum_find(s,row);}}
 else if(!seqapending&&(edge&J_A)){drumanchor=drum_find(s,row);seqapending=drumanchor==65535U?4:3;seqamoved=0;if(seqapending==4){seqaanchor=s;seqaoffset=row;}}
 if(seqapending&&!(p&(seqapending>=3?J_A:J_B))){if(seqapending==4&&!seqamoved){seqgrouptrack=255;if(seqdrawvalid)seqdrawvalid=2;dirty=1;}if(seqapending==1&&!seqamoved)drum_erase(drumanchor,row);seqapending=0;if(!(edge&(J_UP|J_DOWN|J_LEFT|J_RIGHT)))return;}
 if(seqapending){
  if(seqapending==4){if(edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN)){if((edge&J_LEFT)&&s)s--;if((edge&J_RIGHT)&&(uint16_t)s+1<seqlength[6])s++;if((edge&J_UP)&&row)row--;if((edge&J_DOWN)&&row<12)row++;seqcursor[6]=s;drumrow=row;seqgrouptrack=6;seqgroupx0=s<seqaanchor?s:seqaanchor;seqgroupx1=s>seqaanchor?s:seqaanchor;seqgroupy0=row<seqaoffset?row:seqaoffset;seqgroupy1=row>seqaoffset?row:seqaoffset;seqamoved=1;if(seqdrawvalid)seqdrawvalid=2;dirty=1;}return;}
  n=drumanchor;if(n==65535U||!seq_event_get(6,n,e))return;
  if(drum_selected_event(e)&&((seqapending==3&&(edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN)))||(seqapending!=3&&(edge&(J_LEFT|J_RIGHT))))){int8_t dx=(edge&J_RIGHT?1:0)-(edge&J_LEFT?1:0),dy=(edge&J_DOWN?1:0)-(edge&J_UP?1:0);seqamoved=drumbused=1;if(seqapending==3){if(drum_group_move(dx,dy)){seqcursor[6]+=dx;drumrow+=dy;if(!seqplaying)seq_live_current(0);}}else {dur=drum_duration(e);if(!seq_length_step((uint16_t)e[0]+dur-1,(uint16_t)e[0]+dur-1+dx))return;if(drum_group_size(dx)){seqcursor[6]=e[0]+dur+dx-1;if(!seqplaying)seq_live_current(1);}}dirty=1;return;}
  dur=drum_duration(e);
  if(seqapending!=3){if(!(edge&(J_LEFT|J_RIGHT)))return;seqamoved=drumbused=1;dst=dur+(edge&J_RIGHT?1:-1);if(dst<1)dst=1;if(dst>seqlength[6]-e[0])dst=seqlength[6]-e[0];if(dst==dur)return;if(!seq_length_step((uint16_t)e[0]+dur-1,(uint16_t)e[0]+dst-1))return;s=e[0];drumanchor=drum_plot(s,row,dst,e[2],n+1);if(drumanchor!=65535U){seq_event_get(6,drumanchor,e);dur=drum_duration(e);seqdefaultdur[6]=dur;seqcursor[6]=s+dur-1;}}
  else if(edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN)){seqamoved=drumbused=1;dst=e[0];r=row;if(edge&J_LEFT)dst--;if(edge&J_RIGHT)dst++;if(edge&J_UP)r--;if(edge&J_DOWN)r++;if(dst<0||dst+dur>seqlength[6]||r<0||r>12)return;drumanchor=drum_plot(dst,r,dur,e[2],n+1);seqcursor[6]=dst;drumrow=r;}else return;
  if(!seqplaying&&drumanchor!=65535U)seq_live_current(seqapending!=3);dirty=1;return;
 }
 if(edge&J_LEFT){if(!s){seqhead=6;seqedit=0;}else seqcursor[6]=s-1;}if((edge&J_RIGHT)&&(uint16_t)s+1<seqlength[6])seqcursor[6]=s+1;if(edge&J_UP){if(row==0)seqhead=seq_top_entry();else drumrow--;}if(edge&J_DOWN){if(row<12)drumrow++;}if(edge&(J_UP|J_DOWN|J_LEFT|J_RIGHT))dirty=1;
}
void drum_synth_render(void) BANKED {eval_render();}
void drum_synth_input(uint8_t p,uint8_t edge) BANKED {eval_input(p,edge);}

uint16_t drum_clip_plot(uint8_t step,uint8_t row,uint16_t dur,uint8_t vel) BANKED {uint16_t length=seqlength[6],n;seqlength[6]=256;n=drum_plot(step,row,dur,vel,0);seqlength[6]=length;return n;}

void drum_plot_audition(uint8_t row,uint8_t vel) BANKED {
 drum_init();if(row>=3){drum_start(DRUM_VOICE_ROW(row),vel,1);return;}
 if(row==2){kick_start(vel,65535UL);return;}
 drumreleasing[row]=0;eval_note(5+row,1);noiseleft[row]=65535UL;noiselevel[row]=vel;drum_noise();
}
void kit_audition(uint8_t row) BANKED {drum_start(row,127,1);}


/* Deadline calculation shares the roomy drum bank; transport owns its state. */
extern uint16_t seqclock,seqdeadline;
extern uint8_t seqgate[SEQ_TRACKS];
extern __at (0xAC6A) uint16_t seqcachedbpm;
extern __at (0xAC6C) uint16_t seqstepunits;
void seq_next_deadline(void) BANKED {uint8_t c;uint16_t next,step;
 if(seqclock>=seqthreshold)next=1;
 else if(seqswing==50&&seqcachedbpm==seqbpm&&seqclock<seqbpm)next=seqstepunits+(15360U-seqstepunits*seqbpm>seqclock);
 else next=(seqthreshold-seqclock+seqbpm-1)/seqbpm;
 step=next;
 for(c=0;c<SEQ_TRACKS;c++)if(seqgateleft[c]&&seqgateleft[c]<next){
  /* Full pulse gates rounded one unit short still occupy their whole step. */
  if(c<4&&!experimental_mode&&!monomode&&seqgate[c]==100&&seqgateleft[c]+1==step)continue;
  next=seqgateleft[c];
 }
 if(drumnoiseowned)for(c=0;c<2;c++)if(noiseleft[c]&&noiseleft[c]<next)next=noiseleft[c];
 if(pulsekickleft&&pulsekickleft<next)next=pulsekickleft;{step=eval_arp_wait();if(step<next)next=step;}seqdeadline=next?next:1;
}

void drum_synth_audition(void) BANKED {drum_init();if(drumsynthvoice==2)kick_start(100,256);else {drumreleasing[drumsynthvoice]=0;eval_note(5+drumsynthvoice,1);noiseleft[drumsynthvoice]=256;noiselevel[drumsynthvoice]=100;drum_noise();}dirty=1;}

#pragma bank 48
#pragma opt_code_speed
#include "api.h"
#include "mod_bypass.h"
#include "lfo_irq.h"
extern uint8_t globalmod[10],lphase,tablemode[4];
/* One entry per four phase units. Coefficients are independent of note pitch,
   so new sequencer/arp attacks require no table rebuild. */
typedef struct {int8_t semitone,fine;} LfoPoint;
static LfoPoint points[3][64];
static uint8_t previousnote[3],previouscontrol[3],previouswave[3],waves[64];
volatile uint8_t lfo_irq_mask;
static uint8_t keys[3][5],shape=255,frame,playing=255,clockkey=255,ratekey,divkey,timingkey;
static uint16_t bpmkey,phasefraction,stepfraction,lastpitch[3];
static uint8_t stepwhole,tickfraction,preparing,prepared_state=255,prepared_blocked;
static uint16_t prepared_generation;
extern uint16_t pattern_generation;
uint16_t lfo_irq_updates;
uint8_t lfo_irq_owned(uint8_t c) NONBANKED {return c<3&&seqplaying&&(lfo_irq_mask&(1<<c));}
uint8_t lfo_irq_active(void) NONBANKED {return seqplaying&&lfo_irq_mask;}
void lfo_irq_note(uint8_t c) NONBANKED {
 uint8_t ie;if(!lfo_irq_owned(c))return;ie=IE_REG;IE_REG=0;lastpitch[c]=65535U;
 if(!globalmod[9]){lphase=0;phasefraction=0;tickfraction=0;}IE_REG=ie;
}
/* Native voices have neither bend nor detune here. Coarse modulation is a
   semitone lookup in the existing fixed-ROM pitch table, not period scaling. */
uint16_t lfo_irq_pitch(uint8_t c,uint16_t note) NONBANKED __naked {
 c;note;
 __asm
  ; SDCC register ABI: channel A, note DE, result BC.
  ld h,a
  ld l,#0
  srl h
  rr l
  cp #2
  jr nz,90101$
  ld a,e
  add a,#12
  ld e,a
  jr nc,90101$
  inc d
90101$:
  ld a,(_lphase)
  srl a
  and a,#0x7e
  add a,l
  ld l,a
  jr nc,90102$
  inc h
90102$:
  ld bc,#_points
  add hl,bc
  ld a,(hl+)
  ld c,a
  rlca
  sbc a,a
  ld b,a
  ld a,(hl)
  push af
  ld h,d
  ld l,e
  add hl,bc
  bit 7,h
  jr z,90103$
  ld hl,#0
  jr 90105$
90103$:
  ld a,h
  or a,a
  jr nz,90104$
  ld a,l
  cp #140
  jr c,90105$
90104$:
  ld hl,#139
90105$:
  add hl,hl
  ld bc,#_notes
  add hl,bc
  ld a,(hl+)
  ld c,a
  ld b,(hl)
  pop af
  ld e,a
  rlca
  sbc a,a
  ld d,a
  ld h,b
  ld l,c
  add hl,de
  bit 7,h
  jr z,90106$
  ld bc,#0
  ret
90106$:
  ld a,h
  cp #8
  jr c,90107$
  ld bc,#2047
  ret
90107$:
  ld b,h
  ld c,l
  ret
 __endasm;
}
void lfo_irq_tick(uint8_t elapsed) NONBANKED {
 uint8_t n;int16_t accrued;uint16_t before,f;uint8_t wave;
 if(!lfo_irq_mask||!power||!seqplaying){tickfraction=0;return;}
 /* Elapsed is1024Hz. Bound register work to128Hz; phase arithmetic stays256Hz. */
 /* Round a 1024Hz elapsed sample to the nearest 128Hz quantum. A
    one-unit signed residual avoids alternating 3/1 timer periods when DIV
    sampling straddles an integer boundary during drawing. No clock drift:
    the early unit is repaid by the following elapsed sample. */
 accrued=(int8_t)tickfraction+elapsed;
 if(accrued<7){tickfraction=accrued;return;}
 n=(accrued+1)>>3;tickfraction=accrued-(n<<3);n<<=1;
 while(n--){before=phasefraction;phasefraction+=stepfraction;lphase+=stepwhole+(phasefraction<before);}
 wave=waves[lphase>>2];
#define LFO_VOICE(C,BIT,LOW,HIGH,BUSY) do { \
 if((lfo_irq_mask&BIT)&&active[C]&&!(BUSY)&&!(mono_owned&BIT)) { \
  if(lastpitch[C]==65535U||previousnote[C]!=basepitch[C]||previouscontrol[C]!=param[C][8]||previouswave[C]!=wave) { \
   previouswave[C]=wave;previousnote[C]=basepitch[C];previouscontrol[C]=param[C][8]; \
   f=lfo_irq_pitch(C,basepitch[C]); \
   if(f!=lastpitch[C]){lastpitch[C]=f;LOW=f;HIGH=(param[C][8]<<6)|(f>>8);lfo_irq_updates++;} \
  } \
 } \
} while(0)
 LFO_VOICE(0,1,NR13_REG,NR14_REG,pulsekickleft);
 LFO_VOICE(1,2,NR23_REG,NR24_REG,0);
 LFO_VOICE(2,4,NR33_REG,NR34_REG,waveengine||evalwaveactive);
#undef LFO_VOICE

}
static int8_t signal(uint8_t phase){uint8_t n;static const uint8_t sine[17]={0,6,12,19,24,30,36,41,45,49,53,56,59,61,63,64,64};
 switch(globalmod[4]){case 1:return (phase>>1)-64;case 2:return phase<128?64:-64;case 3:return (int8_t)((phase&0xC0)*73+37)/2;case 4:n=phase&63;if(phase&64)n=64-n;n=sine[n>>2];return phase&128?-(int8_t)n:n;default:return phase<128?(int16_t)phase-64:191-(int16_t)phase;}
}
static int8_t amount(int8_t depth,int8_t wave){int16_t v=(int16_t)depth*wave;return v<0?-((-v)>>6):v>>6;}
static void prepare(uint8_t force){
 uint8_t c,i,bit,want=0,key[5],changed=shape!=globalmod[4],div=globalmod[6],oldmask=lfo_irq_mask;int8_t wave;uint32_t denominator,numerator,q;
 if(mod_bypass){lfo_irq_mask=0;return;}
 if(!force&&frame==(uint8_t)sys_time&&playing==seqplaying)return;
 frame=sys_time;playing=seqplaying;
 if(!seqplaying||!power||monomode||polymode||!SYNC_EVENT_IRQ){lfo_irq_mask=0;return;}
 if(clockkey!=globalmod[7]||ratekey!=globalmod[5]||divkey!=div||timingkey!=globalmod[8]||bpmkey!=seqbpm){
  if(globalmod[7]){if(div>16)div=16;denominator=globalmod[8]==1?160:globalmod[8]==2?360:240;
   if(div<=8)numerator=(uint32_t)seqbpm<<(8-div);else{numerator=seqbpm;denominator<<=div-8;}
   q=(numerator<<16)/denominator;
  }else q=(uint32_t)globalmod[5]*15360UL;
  __critical{stepwhole=q>>16;stepfraction=q;}
  clockkey=globalmod[7];ratekey=globalmod[5];divkey=globalmod[6];timingkey=globalmod[8];bpmkey=seqbpm;
 }
 for(c=0,bit=1;c<3;c++,bit<<=1){
  if(finepitch[c]||bend[c]||tablemode[c]||mono_owned&bit)continue;
  if(!(evalpatch[c][EV_DEPTH]&&(evalpatch[c][EV_SOURCES]&1))&&!(coarsepitch[c][1]&&coarsepitch[c][2]))continue;
  if(evalpatch[c][EV_DEPTH]&&!(evalpatch[c][EV_SOURCES]&1)||coarsepitch[c][1]&&!coarsepitch[c][2])continue;
  key[0]=evalpatch[c][EV_DEPTH];key[1]=evalpatch[c][EV_SOURCES];memcpy(key+2,coarsepitch[c],3);
  if(changed||!(oldmask&bit)||memcmp(keys[c],key,5)){
   __critical{lfo_irq_mask&=~bit;}
   for(i=0;i<64;i++){
    wave=signal(i<<2);waves[i]=wave;points[c][i].fine=amount((int8_t)key[0],wave);
    points[c][i].semitone=(int8_t)key[2]+amount((int8_t)key[3],wave);
    if(!(i&7))mixfill();
   }
   memcpy(keys[c],key,5);lastpitch[c]=65535U;
  }
  want|=bit;
 }
 shape=globalmod[4];__critical{lfo_irq_mask=want;}
}

/* Note painting changes the event generation; unchanged playback does not
   need three fresh modulation keys every video frame. Ownership predicates
   use direct fixed-lane reads and still react without a settings generation. */
void lfo_irq_prepare(uint8_t force) BANKED {
 uint8_t state,blocked;uint16_t generation;
 if(preparing)return;
 state=(seqplaying?1:0)|(power?2:0)|((monomode||polymode)?4:0)|((!SYNC_EVENT_IRQ)?8:0)|(mod_bypass?16:0);
 blocked=mono_owned;
 if(finepitch[0]||bend[0]||tablemode[0])blocked|=1;
 if(finepitch[1]||bend[1]||tablemode[1])blocked|=2;
 if(finepitch[2]||bend[2]||tablemode[2])blocked|=4;
 generation=pattern_generation;
 if(!force&&prepared_state==state&&prepared_blocked==blocked&&prepared_generation==generation)return;
 preparing=1;prepare(1);preparing=0;
 prepared_state=state;prepared_blocked=blocked;prepared_generation=generation;
}

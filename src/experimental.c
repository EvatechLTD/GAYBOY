#pragma bank 3
#include "api.h"
#include "experimental.h"
/* Every effect is bypassed initially. ADSR times and note echo times use frames. */
uint8_t expconfig[EXP_COUNT]={0,0,0,0,64,0,15,0,0,0,0,0,0,0,0,0,0,0,0,0,0,7,0,0,0,0,0};
uint8_t exprelease[3],expactive,expwaveon,expecho,exppan,expoutlevel;
int16_t expoffset[3];
volatile uint8_t exppending;
volatile uint16_t expblocks,expdrops;
uint8_t expenv[3],expstage[3],expfrom[3],expzvolume[2],expdirty=1;
uint16_t expwaveclock,expclock[3],exptime,expphase,expchorus,expslew=240,expfraction,expechogate;
uint8_t expampmap[16],expbase[32];
uint8_t expcache[16],expwave[32],expframes[32],expstamp[8],expechonote[16],expechovol[16],expechopan[16],expechonext;
uint16_t expechodue[16];
uint8_t expechoon[16];
uint16_t exppcmphase[2],exppcmstep[2],expdelaypos,expdelaylength,exptail;
int8_t expfilter1,expfilter2;
uint8_t expindex,expnibble,expdelayenabled;
uint16_t expoutptr;
__at (0xDA00) int8_t expalpha[256];
__at (0xDB00) int8_t expreslut[256];
__at (0xDC00) uint8_t expinterp[256];
__at (0xDD00) int8_t expfeedback[256];
/* Leave DE00-DFFF for nested live-launch calls and timer IRQ stack frames. */
__at (0xD900) int8_t expwet[256];
__at (0xD840) int8_t explut[32];
__at (0xA000) int8_t expdelay[2048];
int16_t expclip(int16_t x,int16_t lo,int16_t hi){return x<lo?lo:x>hi?hi:x;}
uint8_t exp_sample(uint8_t *wave,uint8_t i){uint8_t x=wave[i>>1];return i&1?x&15:x>>4;}
void exp_gain(uint8_t c,uint8_t level){uint8_t n;if(monovol[c]==level)return;monovol[c]=level;active[c]=!!level;
 if(expconfig[19]){n=(level-expzvolume[c])&15;while(n--)REG(c?0xff17:0xff12)=8;expzvolume[c]=level;}
 else{REG(c?0xff17:0xff12)=(level<<4)|8;REG(c?0xff19:0xff14)=0x80|(pitchvalue(c)>>8);}
}
void exp_envelope(uint8_t c,uint16_t ticks){uint8_t stage=expstage[c],target;uint16_t duration,elapsed;if(!stage)return;
 if(stage==3){expenv[c]=(c==2&&!expconfig[1])?64:expconfig[4];return;}
 duration=(uint16_t)(stage==4?exprelease[c]:stage==1?expconfig[2]:expconfig[3])*4;
 target=stage==1?64:stage==2?expconfig[4]:0;
 if(c==2&&!expconfig[1]&&stage<3){expenv[c]=64;expstage[c]=3;return;}
 elapsed=expclock[c]+ticks;
 if(!duration||elapsed>=duration){expenv[c]=target;expclock[c]=0;expfrom[c]=target;expstage[c]=stage==4?0:stage+1;}
 else{expclock[c]=elapsed;expenv[c]=expfrom[c]+(((int16_t)target-expfrom[c])*(((uint16_t)elapsed<<6)/duration))/64;}
}
void exp_wavebuild(void){uint8_t cut,frac,shape=monovalue(2,5),res=expconfig[7],bank,i,j,a,b,shift,level=monovalue(2,1),gain,rebuild;uint16_t address,target;uint8_t stamp[8];int16_t brightness=expconfig[6]*16,mod=0;int16_t phase;
 if(expconfig[9]==1)mod=(int16_t)expenv[2]*expconfig[8]/4;
 if(expconfig[9]==2)mod=(int16_t)monolfo(0)*expconfig[8]/4;
 brightness=expclip(brightness+mod,0,240);target=brightness;
 if(!expconfig[26])expslew=target;else if(expslew<target)expslew+=((target-expslew)>>expconfig[26])+1;else if(expslew>target)expslew-=((expslew-target)>>expconfig[26])+1;
 cut=expslew>>4;frac=expslew&15;bank=5+(res>>1);i=shape;
 if(shape==3){bank+=2;i=monovalue(2,4)-1;}
 address=((uint16_t)(res&1)<<13)+((uint16_t)i<<8)+((uint16_t)cut<<4);
 phase=(expphase>>2)&255;phase=phase<128?phase-64:191-phase;
 shift=expconfig[11]?((uint16_t)(phase+64)*expconfig[10])>>7:expconfig[10];
 stamp[0]=shape;stamp[1]=monovalue(2,4);stamp[2]=expslew;stamp[3]=res;stamp[4]=shift;stamp[5]=expenv[2];stamp[6]=monovel;stamp[7]=level;
 if(!expdirty&&!memcmp(stamp,expstamp,8))return;if(expconfig[0])exp_fill();rebuild=expdirty||memcmp(stamp,expstamp,5);memcpy(expstamp,stamp,8);
 gain=expconfig[1]||exprelease[2]||expconfig[0]?expenv[2]:64;if(monosource[10])gain=((uint16_t)gain*monovel)/127;exp_maps(frac,gain);
 if(rebuild){exp_fetch(bank,address,expframes);if(cut<15)exp_fetch(bank,address+16,expframes+16);else memcpy(expframes+16,expframes,16);
  for(i=0;i<32;i++){if(i==16&&expconfig[0])exp_fill();a=expinterp[(exp_sample(expframes,i)<<4)|exp_sample(expframes+16,i)];if(expconfig[10]){j=(i+shift)&31;b=expinterp[(exp_sample(expframes,j)<<4)|exp_sample(expframes+16,j)];a=(a+b+1)>>1;}expbase[i]=a;}}
 expoutlevel=level;
 for(i=0;i<32;i++){a=expampmap[expbase[i]];expwave[i]=a;explut[i]=level?(int16_t)((uint16_t)((int16_t)a-8)<<level):0;}

}
void exp_pcm_pitch(void){uint8_t c,n,f;int16_t pitch;uint16_t step;
 for(c=0;c<2;c++){pitch=(int16_t)basepitch[2]*128+bend[2]+expoffset[c];pitch=expclip(pitch,0,83*128);n=pitch>>7;f=pitch&127;step=ddsnotes[n]*4;if(n<83)step+=((uint16_t)(ddsnotes[n+1]-ddsnotes[n])*f)>>5;exppcmstep[c]=step;}
}
void exp_pitch(void) BANKED {exp_pcm_pitch();}
void exp_waveapply(void) BANKED {uint8_t i,a;uint16_t f;
 exp_wavebuild();if(expconfig[0]){if(expdirty)exp_pcm_pitch();expdirty=0;return;}
 if(!monodown&&!expstage[2]){NR30_REG=0;monovol[2]=active[2]=0;return;}
 for(i=0;i<16;i++){a=(expwave[2*i]<<4)|expwave[2*i+1];if(a!=expcache[i])expdirty=1;expcache[i]=a;}
 if(!expdirty)return;expdirty=0;NR30_REG=0;for(i=0;i<16;i++)REG(0xff30+i)=expcache[i];f=pitchvalue(2);NR32_REG=monovalue(2,1)?(4-monovalue(2,1))<<5:0;NR33_REG=f;NR30_REG=0x80;NR34_REG=0x80|(f>>8);monovol[2]=monovalue(2,1);active[2]=!!monovol[2];
}
void exp_reset(void) BANKED {uint8_t c;exppending=0;expecho=0;expechogate=0;exptail=0;exptime=0;for(c=0;c<3;c++){expoffset[c]=0;expstage[c]=expenv[c]=0;expclock[c]=0;}memset(expechoon,0,16);mixready[0]=mixready[1]=mixread=mixwrite=mixrunning=0;expfilter1=expfilter2=0;expdelaypos=0;if(expconfig[0])memset(expdelay,0,2048);}
void exp_note(uint8_t note) BANKED {uint8_t c,i,level=expconfig[16];uint16_t due;
 if(expconfig[0])exp_fill();
 for(c=expconfig[0]?2:0;c<3;c++){expstage[c]=1;expenv[c]=expfrom[c]=0;expclock[c]=0;exp_envelope(c,0);if(expstage[c]==2)exp_envelope(c,0);}
 if(expconfig[19])for(c=0;c<2;c++){expzvolume[c]=0;REG(c?0xff17:0xff12)=8;REG(c?0xff19:0xff14)=0x80|(pitchvalue(c)>>8);monovol[c]=0;}
 if(!expconfig[0]&&expconfig[15]&&level){level=((uint16_t)level*monovel)/127;due=exptime;for(i=0;i<expconfig[17];i++){c=expechonext++&15;due+=(uint16_t)expconfig[15]*4;expechoon[c]=1;expechodue[c]=due;expechonote[c]=note;expechovol[c]=level;expechopan[c]=(i&1)?2:0;level=(level*3)>>2;}}
 if(!expconfig[0])expdirty=1;
 if(expconfig[0]){basepitch[2]=monopitch(2,note);exp_pcm_pitch();mixrunning=1;exptail=0;}
}
uint8_t exp_off(void) BANKED {uint8_t c,mask=0,level,steps;uint16_t pace;
 for(c=0;c<3;c++)if(exprelease[c]&&((c==2&&expwaveon)||(c<2&&monovol[c]&&monostage[c]!=4))){expfrom[c]=expenv[c];if(c<2&&!expconfig[19]){level=monovol[c];if(monostage[c]==1||monostage[c]==2){pace=(uint16_t)monovalue(c,monostage[c]==1?2:3)*60;steps=pace?monoticks[c]/pace:level;if(steps>level)steps=level;level=monostage[c]==1?steps:level-steps;}expfrom[c]=((uint16_t)level*64)/monovol[c];}expstage[c]=4;expenv[c]=expfrom[c];expclock[c]=0;monostage[c]=6;mask|=1<<c;}
 else {expstage[c]=0;expenv[c]=0;}
 if(expconfig[0]){exp_wavebuild();if(expconfig[23]&&expconfig[24])exptail=(uint16_t)expconfig[23]*32*(expconfig[25]?8:1);else exptail=0;}
 return mask;
}
void exp_update(uint16_t ticks){uint8_t c,i,level,oldenv=expenv[2];int16_t cents,offset;
 exptime+=ticks;expphase+=(uint16_t)expconfig[11]*ticks;expchorus+=(uint16_t)expconfig[14]*ticks;
 for(c=expconfig[0]?2:0;c<3;c++){if(c==2||expconfig[19]||expstage[c]==4)exp_envelope(c,ticks);if(c<2&&((expconfig[19]&&monodown)||monostage[c]==6)){
  level=(((uint16_t)monovalue(c,1)*monovel)/127)*expenv[c]/64;exp_gain(c,level);if(!expstage[c]&&!level){monostage[c]=4;stop(c);}
 }}
 if(expconfig[12]||expconfig[13]||expoffset[0]||expoffset[1]){cents=((expchorus>>2)&255);cents=cents<128?cents-64:191-cents;cents=(cents*expconfig[13])/64+expconfig[12];offset=(cents*128)/100;
 if(expoffset[0]!=-offset||expoffset[1]!=offset){expoffset[0]=-offset;expoffset[1]=offset;updatepitch(0);if(!expconfig[15])updatepitch(1);if(expconfig[0])exp_pcm_pitch();}}
 if(!expconfig[0]&&expconfig[15])for(i=0;i<16;i++)if(expechoon[i]&&(int16_t)(exptime-expechodue[i])>=0){expechoon[i]=0;expecho=1;exppan=expechopan[i];held[1]=expechonote[i];basepitch[1]=monopitch(1,held[1]);monovol[1]=expechovol[i];active[1]=1;monostage[1]=3;monopulse(1,0);expechogate=60;if(expconfig[18]){uint8_t routepan=expechopan[i];NR51_REG=(NR51_REG&0xDD)|(routepan==0?0x20:2);}}
 if(expechogate){if(ticks>=expechogate){expechogate=0;expecho=0;monovol[1]=0;stop(1);}else expechogate-=ticks;}
 expwaveclock+=ticks;if(expwaveon&&(monodown||expstage[2])&&(oldenv!=expenv[2]||expdirty||((expconfig[8]||expconfig[11])&&expwaveclock>=(expconfig[0]?30:15)))){expwaveclock=0;exp_waveapply();}
 if(!monocount&&!modtail&&!expstage[0]&&!expstage[1]&&!expstage[2]){monodown=0;if(!expconfig[0]){monovol[2]=0;stop(2);}}
 if(!expconfig[0])monoroute();
}
void exp_frame(void) BANKED {if(!expactive)return;if(!expconfig[0]&&!expconfig[20])exp_update((uint16_t)frameadvance*4);}
void exp_service(void) BANKED {uint8_t ticks=exppending,shift;if(!ticks)return;__critical{exppending-=ticks;}shift=expconfig[0]?6:expconfig[20]==1?7:8;expfraction+=(uint16_t)ticks*240;exp_update(expfraction>>shift);expfraction&=(1U<<shift)-1;}
uint8_t expoldengine,expoldcontrol,expoldzombie,expolddelay;
void exp_changed(void) BANKED {uint8_t i,on=0,wasactive=expactive,restart=expoldengine!=expconfig[0]||expoldcontrol!=expconfig[20]||expoldzombie!=expconfig[19];exprelease[2]=expconfig[5];expwaveon=expconfig[0]||expconfig[1]||exprelease[2]||expconfig[6]!=15||expconfig[7]||expconfig[8]||expconfig[10];
 for(i=0;i<EXP_COUNT;i++)if(i!=4&&i!=6&&i!=21&&expconfig[i])on=1;expactive=on||expwaveon||exprelease[0]||exprelease[1];
 if(restart||wasactive!=expactive){TAC_REG=0;exp_reset();TMA_REG=expconfig[0]?192:expconfig[20]==1?224:240;TIMA_REG=TMA_REG;if(syncarmed)sync_timer_config();IF_REG&=~TIM_IFLAG;if(monomode&&expactive&&(expconfig[0]||expconfig[20]))TAC_REG=4;}
 if(expconfig[0]&&!expoldengine){ENABLE_RAM_MBC5;SWITCH_RAM_MBC5(0);memset(expdelay,0,2048);NR12_REG=NR22_REG=0;}
 if(expconfig[15]!=expolddelay){memset(expechoon,0,16);expecho=0;monovol[1]=0;stop(1);expolddelay=expconfig[15];}
 if(expconfig[0])exp_tables();
 expoldengine=expconfig[0];expoldcontrol=expconfig[20];expoldzombie=expconfig[19];expdelaylength=(uint16_t)expconfig[23]*32;expdirty=1;dirty=1;
 if(monocount&&(restart||!wasactive)){uint8_t note=monokeys[monocount-1];exp_note(note);for(i=0;i<3;i++)monoapply(i);}
 else if(monodown){if(expwaveon)exp_waveapply();else monoapply(2);}
}
/* Fixed-time DDS lookup, interruptible; phase table lives at D840. */
void exp_oscillators(void) __naked {
 __asm
 push bc
 ld hl,#_exppcmphase
 ld a,(hl+)
 ld h,(hl)
 ld l,a
 ld a,(_exppcmstep)
 ld e,a
 ld a,(_exppcmstep+1)
 ld d,a
 ld bc,#_mixsamples
 ld a,#32
 ld (_mixcounter),a
exp_osc0$:
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #31
 ld l,a
 set 6,l
 ld h,#0xd8
 ld a,(hl)
 ld (bc),a
 inc bc
 pop hl
 ld a,(_mixcounter)
 dec a
 ld (_mixcounter),a
 jr nz,exp_osc0$
 ld a,l
 ld (_exppcmphase),a
 ld a,h
 ld (_exppcmphase+1),a
 ld a,(_expconfig+12)
 ld l,a
 ld a,(_expconfig+13)
 or l
 jr z,exp_osc_done$
 ld hl,#_exppcmphase+2
 ld a,(hl+)
 ld h,(hl)
 ld l,a
 ld a,(_exppcmstep+2)
 ld e,a
 ld a,(_exppcmstep+3)
 ld d,a
 ld bc,#_mixsamples
 ld a,#32
 ld (_mixcounter),a
exp_osc1$:
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #31
 ld l,a
 set 6,l
 ld h,#0xd8
 ld a,(hl)
 ld l,a
 ld a,(bc)
 add a,l
 sra a
 ld (bc),a
 inc bc
 pop hl
 ld a,(_mixcounter)
 dec a
 ld (_mixcounter),a
 jr nz,exp_osc1$
 ld a,l
 ld (_exppcmphase+2),a
 ld a,h
 ld (_exppcmphase+3),a
exp_osc_done$:
 pop bc
 ret
 __endasm;
}
/* Two low-pass poles, bounded resonance, signed PCM delay and wet/feedback
   lookup tables. All sample arithmetic stays eight-bit on the DMG. */
void exp_kernel(void) __naked {
 __asm
 push bc
 ld a,#0
 ld (_expindex),a
exp_kernel_loop$:
 ld a,(_expindex)
 ld e,a
 ld d,#0
 ld hl,#_mixsamples
 add hl,de
 ld a,(hl)
 ld b,a
 ld a,(_expfilter2)
 xor #128
 ld l,a
 ld h,#0xdb
 ld a,(hl)
 ld c,a
 ld a,b
 sub c
 call exp_clamp$
 ld b,a
 ld a,(_expfilter1)
 ld c,a
 ld a,b
 sub c
 xor #128
 ld l,a
 ld h,#0xda
 ld a,(hl)
 add a,c
 ld (_expfilter1),a
 ld b,a
 ld a,(_expfilter2)
 ld c,a
 ld a,b
 sub c
 xor #128
 ld l,a
 ld h,#0xda
 ld a,(hl)
 add a,c
 ld (_expfilter2),a
 ld b,a
 ld a,(_expdelayenabled)
 or a
 jr z,exp_kernel_pack$
 ld a,(_expdelaypos)
 ld l,a
 ld a,(_expdelaylength)
 ld c,a
 ld a,l
 sub c
 ld l,a
 ld a,(_expdelaylength+1)
 ld c,a
 ld a,(_expdelaypos+1)
 sbc a,c
 and #7
 add a,#0xa0
 ld h,a
 ld a,(hl)
 ld c,a
 xor #128
 ld l,a
 ld h,#0xdd
 ld a,(hl)
 add a,b
 call exp_clamp$
 ld d,a
 ld a,(_expdelaypos)
 ld l,a
 ld a,(_expdelaypos+1)
 and #7
 add a,#0xa0
 ld h,a
 ld (hl),d
 ld hl,#_expdelaypos
 inc (hl)
 jr nz,exp_delay_advance$
 inc hl
 inc (hl)
 ld a,(hl)
 and #7
 ld (hl),a
exp_delay_advance$:
 ld a,c
 sub b
 xor #128
 ld l,a
 ld h,#0xd9
 ld a,(hl)
 add a,b
 ld b,a
exp_kernel_pack$:
 ld a,b
 sra a
 sra a
 sra a
 add a,#8
 ld b,a
 ld a,(_expindex)
 and #1
 jr nz,exp_kernel_write$
 ld a,b
 swap a
 ld (_expnibble),a
 jr exp_kernel_next$
exp_kernel_write$:
 ld a,(_expoutptr)
 ld l,a
 ld a,(_expoutptr+1)
 ld h,a
 ld a,(_expnibble)
 or b
 ld (hl+),a
 ld a,l
 ld (_expoutptr),a
 ld a,h
 ld (_expoutptr+1),a
exp_kernel_next$:
 ld hl,#_expindex
 inc (hl)
 ld a,(hl)
 cp #32
 jp nz,exp_kernel_loop$
 pop bc
 ret
exp_clamp$:
 bit 7,a
 jr nz,exp_clamp_negative$
 cp #64
 ret c
 ld a,#63
 ret
exp_clamp_negative$:
 cp #192
 ret nc
 ld a,#192
 ret
 __endasm;
}
void exp_fill(void) BANKED {uint8_t slot=mixwrite;
 if(!expconfig[0]||!mixrunning||mixready[slot])return;
 exp_oscillators();expoutptr=(uint16_t)(mixbuffer+(slot<<4));exp_kernel();
 mixready[slot]=1;mixwrite=slot^1;
 if(!monodown&&!expstage[2]){if(exptail>32)exptail-=32;else{exptail=0;mixrunning=0;NR30_REG=0;}}
}

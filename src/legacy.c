#pragma bank 2
#include "api.h"
#include "presets.h"
void stocktable(uint8_t c,uint8_t n) BANKED {uint8_t i,b=stocktables[n];int8_t *dst=&tables[c][0][0];const int8_t *p=stockpitch[b&3],*s=stockshape[(b>>2)&15],*pan=stockpan[b>>6];for(i=0;i<8;i++){*dst++=*p++;*dst++=(*s+i)&s[1];*dst++=*pan++;}}
/* Neutral APU instruments at boot. Browsing still loads the stock library. */
const uint8_t startupvalues[26]={2,10,0,0,0,0,0,0,0,0,7,0,7,0,0,2,0,0,4,0,3,3,0,0,0,2};
void startup(void) BANKED {uint8_t c,i;for(c=0;c<4;c++){load(c,c*10);memcpy(param[c],startupvalues,26);memset(mods[c],0,6);tablemode[c]=0;tablelen[c]=1;for(i=0;i<8;i++){tables[c][i][0]=0;tables[c][i][1]=c<2?(c?1:2):c==2?0:4;tables[c][i][2]=3;}edited[c]=1;held[c]=255;}
 param[1][0]=1;param[3][1]=8;param[3][3]=3;master=0x77;route=0xFF;vin=0;globals();}
/* Two DDS oscillators at 8192 samples/sec, packed into 32-sample blocks.
   No note/envelope state is changed at a block boundary. */
uint16_t ddsraw(uint8_t note,int16_t bendvalue){int16_t pitch=(int16_t)note*128+bendvalue;uint8_t n,f;uint16_t v;if(pitch<0)pitch=0;if(pitch>13696)pitch=13696;n=pitch>>7;f=pitch&127;v=ddsnotes[n];if(f&&n<107)v+=((uint16_t)(ddsnotes[n+1]-v)*f)>>7;return v;}
uint16_t ddsvalue(uint8_t note) BANKED {uint16_t v=ddsraw(note,bend[2]);return monomode?v:fine_apply(v,2,1);}
uint16_t ddsfine(uint8_t note,uint8_t c) BANKED {return fine_apply(ddsraw(note,0),c,1);}
uint16_t fastvalue(uint8_t note){int16_t pitch=(int16_t)note+bend[2]/128;uint16_t f;if(pitch<0)pitch=0;if(pitch>127)pitch=127;f=1024+notes[pitch]/2;return fine_apply(f,2,0);}
const uint8_t softfactory[16][32]={{0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0},{0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,3,3,3,3,2,2,2,2,1,1,1,1,0,0,0,0},{0,0,0,1,1,1,2,2,3,3,3,4,4,4,5,5,5,5,4,4,4,3,3,3,2,2,1,1,1,0,0,0},{0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,7,7,6,6,5,5,4,4,3,3,2,2,1,1,0,0},{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1},{0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,3},{0,0,0,0,0,0,1,1,1,1,1,1,2,2,2,2,3,3,3,3,3,3,4,4,4,4,4,4,5,5,5,5},{0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6,7,7,7,7},{1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},{3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},{5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},{7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},{0,0,1,0,1,0,1,0,1,1,0,1,0,1,0,1,1,1,0,1,0,1,0,1,0,0,1,0,1,0,1,0},{0,1,3,1,3,0,2,0,3,2,0,2,0,3,1,3,2,3,1,3,1,2,0,2,1,0,2,0,2,1,3,1},{0,2,5,1,5,0,3,0,4,4,1,3,0,4,1,5,3,5,2,4,2,3,0,3,1,1,4,0,3,1,4,2},{0,3,7,2,7,0,4,1,6,5,1,4,1,6,2,7,4,7,3,6,3,4,0,5,2,1,5,0,5,2,6,3}};
const uint8_t softgain[4][16]={{0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1},{0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3},{0,0,0,1,1,1,2,2,3,3,3,4,4,4,5,5},{0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7}};
void softtable(uint8_t c){uint8_t i,a,level=softvel[c]>>5,s=softshape[c];const uint8_t *gain;
 if(s<3||!custom){memcpy(softlut[c],softfactory[(s<<2)+level],32);return;}
 gain=softgain[level];for(i=0;i<16;i++){a=customwave[i];softlut[c][i*2]=gain[a>>4];softlut[c][i*2+1]=gain[a&15];}
}
void fastbuild(void){uint8_t i,n=0,bank=fastbank^1;for(i=0;i<8;i++)if(faston[i])fastfreq[bank][n++]=fastvalue(fastnote[i]);fastcount[bank]=n;fastbank=bank;}
void enginepitch(void) BANKED {if(waveengine==1)fastbuild();else if(waveengine==2)pitchdirty=1;}
void enginestop(void) BANKED {uint8_t i;drumenabled=0;if(druminit)drumon[0]=drumon[1]=0;for(i=0;i<2;i++)softon[i]=softheld[i]=softowned[i]=0;for(i=0;i<8;i++)faston[i]=fastdown[i]=0;fastcount[0]=fastcount[1]=0;mixready[0]=mixready[1]=mixrunning=mixread=mixwrite=0;NR30_REG=0;}
void enginesync(void){uint8_t i,on=0;if(waveengine==3)return;if(waveengine==1){for(i=0;i<8;i++)on|=faston[i];}else on=softon[0]|softon[1]|(drumenabled?(drumon[0]|drumon[1]):0);active[2]=on;if(!on){mixrunning=0;mixready[0]=mixready[1]=mixread=mixwrite=0;NR30_REG=0;} }
void enginenote(uint8_t note,uint8_t vel,uint8_t owner) BANKED {uint8_t i,c;
 if(waveengine==3||!power||param[2][9]||param[2][17]||param[2][22])return;
 if(waveengine==1){for(c=0;c<8;c++)if(!faston[c])break;if(c==8)c=fastnext;fastnext=(c+1)&7;fastnote[c]=note;faston[c]=fastdown[c]=1;fastbuild();
 if(!active[2]){wave();wavepending=0;NR30_REG=0x80;NR32_REG=param[2][15]<<5;NR33_REG=fastvalue(note);NR34_REG=0x80|(fastvalue(note)>>8);} }
 else {c=softnext;if(w2enabled&&!owner)c=0;for(i=0;i<(w2enabled&&!owner?1:2);i++){c=w2enabled&&!owner?0:(softnext+i)&1;if(!softon[c])break;}if(i==(w2enabled&&!owner?1:2))c=w2enabled&&!owner?0:softnext;softnext=c^1;softnote[c]=note;softvel[c]=vel;softphase[c]=softage[c]=0;softheld[c]=softon[c]=1;softowned[c]=owner;softstep[c]=ddsvalue(note);softtable(c);wavepending=0;mixrunning=1;if(!(TAC_REG&4))TAC_REG=4;}
 active[2]=1;held[2]=note;basepitch[2]=note;velocity[2]=vel;livepitch[2]=note;
}
void engineoff(uint8_t note) BANKED {uint8_t i;if(waveengine==3)return;if(waveengine==1){for(i=0;i<8;i++)if(faston[i]&&fastnote[i]==note){fastdown[i]=0;if(!sustain[2])faston[i]=0;}fastbuild();}else for(i=0;i<2;i++)if(softon[i]&&softowned[i]!=2&&softnote[i]==note){softheld[i]=0;if(!sustain[2])softon[i]=0;}enginesync();}
void enginesustain(uint8_t on) BANKED {uint8_t i;if(waveengine==3)return;sustain[2]=on;if(!on){if(waveengine==1){for(i=0;i<8;i++)if(!fastdown[i])faston[i]=0;fastbuild();}else for(i=0;i<2;i++)if(!softheld[i]&&softowned[i]!=2)softon[i]=0;}enginesync();}
void engineframe(void) BANKED {uint8_t i;if(waveengine==3){if(!mixrunning)active[2]=0;return;}w2_frame();if(waveengine==2){for(i=0;i<2;i++)if(softon[i]){if(softage[i]<255)softage[i]=((uint16_t)softage[i]+frameadvance)>255?255:softage[i]+frameadvance;if(!monomode&&softowned[i]!=2&&mods[2][5]&&softage[i]>=mods[2][5])softon[i]=0;}enginesync();}}
void engineset(uint8_t mode) BANKED {if(mode>2)mode=2;if(waveengine==mode)return;panic();monomode=0;TAC_REG=0;waveengine=mode;w2enabled=0;engineblocks=mixunderruns=0;fastpos=fastclock=0;softnext=0;
 TMA_REG=mode==1?252:240;TIMA_REG=TMA_REG;IF_REG&=~TIM_IFLAG;if(mode)TAC_REG=4;dirty=1;
}
void mixrender(void) __naked {
 __asm
 push bc
 ld a,(_softon+0)
 or a
 jp z,soft_off_0$
 ld hl,#_softphase+0
 ld a,(hl+)
 ld h,(hl)
 ld l,a
 ld a,(_softstep+0)
 ld e,a
 ld a,(_softstep+1)
 ld d,a
 ld bc,#_mixsamples
 ld a,#4
 ld (_mixcounter),a
soft_loop_0$:
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld (bc),a
 inc bc
 pop hl
 ld a,(_mixcounter)
 dec a
 ld (_mixcounter),a
 jp nz,soft_loop_0$
 ld a,l
 ld (_softphase+0),a
 ld a,h
 ld (_softphase+1),a
 jp soft_done_0$
soft_off_0$:
 ld hl,#_mixsamples
 ld b,#32
soft_center_0$:
 ld a,#4
 ld (hl+),a
 dec b
 jr nz,soft_center_0$
soft_done_0$:
 ld a,(_softon+1)
 or a
 jp z,soft_off_1$
 ld hl,#_softphase+2
 ld a,(hl+)
 ld h,(hl)
 ld l,a
 ld a,(_softstep+2)
 ld e,a
 ld a,(_softstep+3)
 ld d,a
 ld bc,#_mixsamples
 ld a,#4
 ld (_mixcounter),a
soft_loop_1$:
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 add a,#32
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld l,a
 ld a,(bc)
 add a,l
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 add a,#32
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld l,a
 ld a,(bc)
 add a,l
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 add a,#32
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld l,a
 ld a,(bc)
 add a,l
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 add a,#32
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld l,a
 ld a,(bc)
 add a,l
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 add a,#32
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld l,a
 ld a,(bc)
 add a,l
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 add a,#32
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld l,a
 ld a,(bc)
 add a,l
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 add a,#32
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld l,a
 ld a,(bc)
 add a,l
 ld (bc),a
 inc bc
 pop hl
 add hl,de
 push hl
 ld a,h
 rrca
 rrca
 rrca
 and #0x1f
 add a,#32
 ld l,a
 ld h,#0xd8
 ld a,(hl)
 ld l,a
 ld a,(bc)
 add a,l
 ld (bc),a
 inc bc
 pop hl
 ld a,(_mixcounter)
 dec a
 ld (_mixcounter),a
 jp nz,soft_loop_1$
 ld a,l
 ld (_softphase+2),a
 ld a,h
 ld (_softphase+3),a
 jp soft_done_1$
soft_off_1$:
 ld hl,#_mixsamples
 ld b,#32
soft_center_1$:
 ld a,(hl)
 add a,#4
 ld (hl+),a
 dec b
 jr nz,soft_center_1$
soft_done_1$:
 pop bc
 ret
 __endasm;
}
void mixpack(void) __naked {
 __asm
 push bc
 ld a,(_mixwrite)
 swap a
 ld e,a
 ld d,#0
 ld hl,#_mixbuffer
 add hl,de
 ld d,h
 ld e,l
 ld hl,#_mixsamples
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 ld a,(hl+)
 swap a
 ld b,a
 ld a,(hl+)
 or b
 ld (de),a
 inc de
 pop bc
 ret
 __endasm;
}
void legacyfill(void) BANKED {uint8_t slot=mixwrite;
 if(waveengine!=2||mixready[slot]||!mixrunning)return;
 if(pitchdirty){bendupdate(2);pitchdirty=0;softstep[0]=ddsvalue(softnote[0]);if(softowned[1]!=2)softstep[1]=ddsvalue(softnote[1]);}
 mixrender();mixpack();mixready[slot]=1;mixwrite=slot^1;
}

void wave(void) BANKED {uint8_t i,a,b,s=param[2][14];if(waveengine==3)return;NR30_REG=0;for(i=0;i<16;i++){a=(i*2+s)&31;b=(a+1)&31;
 switch(s&3){case 0:a=a<16?a:31-a;b=b<16?b:31-b;break;case 1:a>>=1;b>>=1;break;case 2:a=a<16?15:0;b=b<16?15:0;break;default:a=(a*7^(a>>1))&15;b=(b*7^(b>>1))&15;}
 REG(0xff30+i)=custom?customwave[i]:(a<<4)|b;}}
/* MIDI waveform edits are staged in RAM until the next real note trigger. */
void stagewave(void) BANKED {uint8_t i,a,b,s=param[2][14];for(i=0;i<16;i++){a=(i*2+s)&31;b=(a+1)&31;
 switch(s&3){case 0:a=a<16?a:31-a;b=b<16?b:31-b;break;case 1:a>>=1;b>>=1;break;case 2:a=a<16?15:0;b=b<16?15:0;break;default:a=(a*7^(a>>1))&15;b=(b*7^(b>>1))&15;}
 customwave[i]=(a<<4)|b;}}

void w2_start(uint8_t note,uint8_t vel) BANKED {
 uint8_t was=active[2],oldnote=held[2],oldvel=velocity[2];if(waveengine==3)return;
 if(waveengine!=2){enginestop();waveengine=2;TMA_REG=240;TIMA_REG=240;IF_REG&=~TIM_IFLAG;TAC_REG=4;param[2][15]=1;}
 if(!w2enabled){w2enabled=1;if(was&&oldnote!=255)enginenote(oldnote,oldvel,0);}
 softon[1]=softheld[1]=1;softowned[1]=2;softnote[1]=note;softvel[1]=vel;softage[1]=0;softphase[1]=0;softstep[1]=ddsfine(note,4);mixrunning=1;active[2]=1;
}

void drum_enable(void) BANKED {uint8_t pan=mixer_pan(6),level=mixer_velocity(6,127);pcmoutlevel=level?level>84?1:level>42?2:3:0;route&=~0x44;if(pan&1)route|=4;if(pan&2)route|=0x40;NR51_REG=route;drumtail=0;if(waveengine==3)return;TAC_REG=0;enginestop();waveengine=3;w2enabled=0;drumsub=0;TMA_REG=TIMA_REG=73;IF_REG&=~TIM_IFLAG;TAC_REG=6;NR32_REG=0x20;}

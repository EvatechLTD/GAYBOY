/* Packet calculations shared by live lookahead and incoming launch lookahead.
   Each translation unit supplies STEP, native_note/native_drum and cursors.
   These functions never apply a patch or write the APU. */
static uint8_t audible(uint8_t c){uint8_t solo=STEP->solo&79;if(STEP->drumsolo)solo|=64;return !(STEP->muted&(1<<c))&&(!solo||(solo&(1<<c)));}
static uint8_t scale(uint16_t n){uint8_t q=n>>7;return q+((uint8_t)((n&127)+q)>=127);}
static uint8_t native_velocity(uint8_t c,uint8_t v){return STEP->mix[c]==127?v:scale((uint16_t)v*STEP->mix[c]+63);}
/* Most patterns use short power-of-two durations. Avoid the software
   32-bit multiplier on every voice in that common case. Zero means 256. */
static uint32_t native_duration(uint16_t units,uint8_t duration){
 switch(duration){case 1:return units;case 2:return (uint32_t)units<<1;case 4:return (uint32_t)units<<2;case 8:return (uint32_t)units<<3;case 16:return (uint32_t)units<<4;case 0:return (uint32_t)units<<8;default:return (uint32_t)units*duration;}
}
static void pan(uint8_t c,uint8_t source){uint8_t mask=(1<<c)|(0x10<<c),p=STEP->mix[7+source];if(c==source&&STEP->params[c][9])p=0;STEP->routemask|=mask;STEP->routebits&=~mask;if(p&1)STEP->routebits|=mask&15;if(p&2)STEP->routebits|=mask&240;}
/* Constant channel expansion avoids expensive dynamic array addressing on
   the DMG CPU; all four channels still share the same calculation. */
#define PREPARE_NATIVE(C) do { \
uint8_t e[4],n,frac,*p=STEP->params[C],vol,level;uint16_t f=0,base=0,units=STEP->units;int16_t pitch;NativeVoice *v=&STEP->voice[C]; \
 if(!audible(C)||!native_note(C,STEP->steps[C],e))break; \
 v->note=e[1];v->velocity=native_velocity(C,e[2]);if(!v->velocity){STEP->release|=1<<C;break;} \
 v->gate=native_duration(units,e[3]);if(!v->gate)v->gate=1; \
 if(C<3){if(!STEP->bend[C])base=notes[e[1]-1+(C==2?12:0)];else{pitch=(int16_t)(e[1]-1)*128+STEP->bend[C];if(pitch<0)pitch=0;if(pitch>16256)pitch=16256;n=(pitch>>7)+(C==2?12:0);frac=pitch&127;base=notes[n];if(frac&&n<139)base+=((uint16_t)(notes[n+1]-base)*frac)>>7;}f=STEP->fine[C]?fine_preview_value(base,STEP->fine[C]):base;} \
 v->base=base;level=experimental_mode&&evalpatch[C][EV_LEVEL_MODE]==128?15:p[1];vol=((uint16_t)level*v->velocity+1+(((uint16_t)level*v->velocity)>>7))>>7; \
 if(C<2){v->regs[0]=(p[4]<<4)|(p[5]<<3)|p[6];v->regs[1]=(p[0]<<6)|p[7];v->regs[2]=experimental_mode&&evalpatch[C][EV_LEVEL_MODE]==128?(vol<<4)|8:!vol&&!p[2]?8:(vol<<4)|(p[2]<<3)|p[3];v->regs[3]=f;v->regs[4]=0x80|(p[8]<<6)|(f>>8);} \
 else if(C==2){level=v->velocity>84?1:v->velocity>42?2:3;if(experimental_mode&&evalpatch[C][EV_LEVEL_MODE]==128){}else if(p[15]){level+=p[15]-1;if(level>3)level=3;}else level=0;v->regs[0]=p[17]?0:0x80;v->regs[1]=p[16];v->regs[2]=level<<5;v->regs[3]=f;v->regs[4]=0x80|(p[8]<<6)|(f>>8);} \
 else {v->regs[0]=p[7];v->regs[1]=experimental_mode&&evalpatch[C][EV_LEVEL_MODE]==128?(vol<<4)|8:(vol<<4)|(p[2]<<3)|p[3];v->regs[2]=(p[18]<<4)|(p[19]<<3)|p[20];v->regs[3]=0x80|(p[8]<<6);} \
 if(p[9]||p[22])STEP->release|=1<<C;else STEP->mask|=1<<C; \
 pan(C,C); \
} while(0)
static void voice(uint8_t c){switch(c){
 case 0:PREPARE_NATIVE(0);break;
 case 1:PREPARE_NATIVE(1);break;
 case 2:PREPARE_NATIVE(2);break;
 case 3:PREPARE_NATIVE(3);break;
}}
/* Exact images of the native generator for all 32 phase/shape inputs. */
static const uint8_t nativewaves[32][16]={
 {1,35,69,103,137,171,205,239,254,220,186,152,118,84,50,16},
 {1,18,35,52,69,86,103,120,137,154,171,188,205,222,239,240},
 {255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255},
 {78,25,44,179,130,213,232,247,198,145,164,59,10,93,96,127},
 {69,103,137,171,205,239,254,220,186,152,118,84,50,16,1,35},
 {35,52,69,86,103,120,137,154,171,188,205,222,239,240,1,18},
 {255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255},
 {44,179,130,213,232,247,198,145,164,59,10,93,96,127,78,25},
 {137,171,205,239,254,220,186,152,118,84,50,16,1,35,69,103},
 {69,86,103,120,137,154,171,188,205,222,239,240,1,18,35,52},
 {255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255},
 {130,213,232,247,198,145,164,59,10,93,96,127,78,25,44,179},
 {205,239,254,220,186,152,118,84,50,16,1,35,69,103,137,171},
 {103,120,137,154,171,188,205,222,239,240,1,18,35,52,69,86},
 {255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255},
 {232,247,198,145,164,59,10,93,96,127,78,25,44,179,130,213},
 {254,220,186,152,118,84,50,16,1,35,69,103,137,171,205,239},
 {137,154,171,188,205,222,239,240,1,18,35,52,69,86,103,120},
 {0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,0},
 {198,145,164,59,10,93,96,127,78,25,44,179,130,213,232,247},
 {186,152,118,84,50,16,1,35,69,103,137,171,205,239,254,220},
 {171,188,205,222,239,240,1,18,35,52,69,86,103,120,137,154},
 {0,0,0,0,0,255,255,255,255,255,255,255,255,0,0,0},
 {164,59,10,93,96,127,78,25,44,179,130,213,232,247,198,145},
 {118,84,50,16,1,35,69,103,137,171,205,239,254,220,186,152},
 {205,222,239,240,1,18,35,52,69,86,103,120,137,154,171,188},
 {0,0,0,255,255,255,255,255,255,255,255,0,0,0,0,0},
 {10,93,96,127,78,25,44,179,130,213,232,247,198,145,164,59},
 {50,16,1,35,69,103,137,171,205,239,254,220,186,152,118,84},
 {239,240,1,18,35,52,69,86,103,120,137,154,171,188,205,222},
 {0,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0},
 {96,127,78,25,44,179,130,213,232,247,198,145,164,59,10,93}
};
static void wavebytes(void){memcpy(STEP->waveform,STEP->wavecustom?STEP->waveinput:nativewaves[STEP->params[2][14]&31],16);}

static void drums(void){uint8_t e[4],row,n;uint16_t units=STEP->units;uint32_t gate;
 if(!audible(6)){buildphase=6;return;}
 /* One matching event per service; repeated calls finish a bounded batch. */
 if(!native_drum(&drumcursor,e)){buildphase=6;return;}
 if(!e[1]||e[1]>13)return;row=e[1]-1;if((STEP->drummute&(1U<<row))||(STEP->drumsolo&&!(STEP->drumsolo&(1U<<row))))return;
 if(e[1]<=10){n=STEP->samplecount;if(n>=16){buildphase=255;return;}seq_native_sample_value(e,(uint8_t *)&STEP->sample[n],STEP->kit,STEP->bpm);STEP->samplecount++;return;}
 gate=native_duration(units,e[3]);
 if(e[1]<=12){n=e[1]-11;STEP->noisegate[n]=gate;STEP->noisevelocity[n]=native_velocity(6,e[2]);STEP->noisechanged=1;}
 else{uint16_t length=(uint16_t)STEP->kickinput[6]*4;if(!length)length=4;STEP->kickgate=gate<length?gate:length;STEP->kick=1;STEP->kickreg[2]=(scale((uint16_t)STEP->kickinput[0]*native_velocity(6,e[2]))<<4)|STEP->kickinput[3];}
}
static void finish_registers(void){uint8_t i,p[5],a=!!STEP->noisegate[0],b=!!STEP->noisegate[1],vol;uint16_t f;
 if(STEP->noisechanged){for(i=0;i<5;i++)p[i]=a&&b?(STEP->noiseinput[i]+STEP->noiseinput[5+i]+1)>>1:STEP->noiseinput[(b?5:0)+i];
 if(a&&b)vol=scale(((uint16_t)STEP->noiseinput[0]*STEP->noisevelocity[0]+(uint16_t)STEP->noiseinput[5]*STEP->noisevelocity[1]+127)>>1);else vol=scale((uint16_t)p[0]*STEP->noisevelocity[b?1:0]);
 STEP->noisereg[0]=0;STEP->noisereg[1]=vol?(vol<<4)|p[4]:8;STEP->noisereg[2]=(p[1]<<4)|(p[3]<<3)|p[2];STEP->noisereg[3]=0x80;
 }
 if(STEP->kick){f=notes[STEP->kickinput[1]];STEP->kickreg[0]=(STEP->kickinput[4]<<4)|(STEP->kickinput[7]<<3)|STEP->kickinput[5];STEP->kickreg[1]=(STEP->kickinput[2]<<6)|((64-STEP->kickinput[6])&63);STEP->kickreg[3]=f;STEP->kickreg[4]=0xC0|(f>>8);}
}

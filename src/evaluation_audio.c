#pragma bank 19
#include "api.h"
#include "evaluation.h"
#include "mixer_shared.h"
extern uint8_t globalmod[10],pulsekickpatch[8],noisepatch[2][5],expzvolume[2];
extern uint32_t noiseleft[2];extern uint8_t drumreleasing[2],kickreleasing;
extern __at (0xAC54) uint8_t noiselevel[2];
uint8_t evalwavefx[27],evalwaveactive,evalsecondon,evalsecondmask,evalkickvelocity;
static uint8_t pulsevolume[4];
static uint8_t bound(int16_t v,uint8_t hi){return v<0?0:v>hi?hi:v;}
void eval_wave_enter(void) BANKED {} void eval_wave_leave(void) BANKED {}
void eval_wave_defaults(void) BANKED {memset(evalwavefx,0,27);}
void eval_wave_save(uint8_t *out) BANKED {memset(out,0,27);}
uint8_t *eval_mono_fx(void) BANKED {return expconfig;}
uint8_t eval_wave_value(uint8_t id) BANKED {(void)id;return 0;}
void eval_second_lut(void) BANKED {}
uint16_t eval_poly_pitch(uint8_t note) BANKED {return notes[note];}
uint16_t eval_pitch(uint8_t c,uint16_t base) BANKED {int16_t v;if(c>=3)return base;v=(int16_t)base+eval_amount(c,0);return v<0?0:v>2047?2047:v;}

static uint8_t level(uint8_t c,uint8_t base,uint8_t vel){uint8_t v=evalpatch[c][EV_LEVEL_MODE]==128?(c==2?3:15):base;v=(uint16_t)v*vel/127;if(evalpatch[c][EV_LEVEL_MODE]==128)v=(uint16_t)v*eval_signal(0,0)/64;return v;}
uint8_t eval_attack_volume(uint8_t c,uint8_t vel) BANKED {return level(c,param[c][1],vel);}
void eval_audio_note(uint8_t c) BANKED {if(c<4)pulsevolume[c]=level(c,c==2?(param[2][15]?4-param[2][15]:0):param[c][1],velocity[c]);}
uint8_t eval_audio_release(uint8_t c) BANKED {if(c>=4)return 0;eval_note(c,0);return active[c]&&evalpatch[c][EV_LEVEL_MODE]==128&&globalmod[3];}
void eval_audio_reset(void) BANKED {memset(pulsevolume,0,4);voice_reset();}
static void applylevel(uint8_t c){uint8_t n,v=level(c,c==2?(param[2][15]?4-param[2][15]:0):param[c][1],velocity[c]);if(v==pulsevolume[c])return;if(c==2)NR32_REG=(v?4-v:0)<<5;else if(c<2){n=(v-pulsevolume[c])&15;while(n--)REG(c?0xff17:0xff12)=8;}else{NR42_REG=(v<<4)|8;NR44_REG=128;}pulsevolume[c]=v;}
void eval_audio_frame(void) BANKED {uint8_t c,n,v;uint16_t f;for(c=0;c<4;c++){if(!active[c])continue;if(c==0&&pulsekickleft||c==2&&waveengine==3||c==3&&drumnoiseowned)continue;if(evalpatch[c][EV_DEPTH]&&c<3)updatepitch(c);else if(c==3&&evalpatch[c][EV_DEPTH])NR43_REG=eval_drum_pitch(3,(param[3][18]<<4)|(param[3][19]<<3)|param[3][20]);if(evalpatch[c][EV_LEVEL_MODE]==128){applylevel(c);if(!keycount[c]&&!eval_signal(0,0))active[c]=0;}}
 if(pulsekickleft){if(evalpatch[7][EV_DEPTH]){f=eval_drum_pitch(7,notes[pulsekickpatch[1]]);NR13_REG=f;NR14_REG=f>>8;}if(evalpatch[7][EV_LEVEL_MODE]==128){v=(uint16_t)eval_drum_level(7,pulsekickpatch[0])*evalkickvelocity/127;n=(v-expzvolume[0])&15;while(n--)NR12_REG=8;expzvolume[0]=v;}}
 if(drumnoiseowned&&(noiseleft[0]||noiseleft[1])){c=noiseleft[1]?6:5;if(!(noiseleft[0]&&noiseleft[1])&&evalpatch[c][EV_DEPTH])NR43_REG=eval_drum_pitch(c,(noisepatch[c-5][1]<<4)|(noisepatch[c-5][3]<<3)|noisepatch[c-5][2]);if(!(noiseleft[0]&&noiseleft[1])&&evalpatch[c][EV_LEVEL_MODE]==128){v=(uint16_t)eval_drum_level(c,noisepatch[c-5][0])*noiselevel[c-5]/127;if(v!=expzvolume[1]){NR42_REG=(v<<4)|8;NR44_REG=128;expzvolume[1]=v;}}}}
uint16_t eval_drum_pitch(uint8_t c,uint16_t base) BANKED {int16_t v=base+(int16_t)(evalpatch[c][EV_FINE]|((uint16_t)evalpatch[c][EV_FINE+1]<<8))+eval_amount(c,0);return v<0?0:v>(c==7?2047:255)?(c==7?2047:255):v;}
uint8_t eval_drum_level(uint8_t c,uint8_t base) BANKED {return evalpatch[c][EV_LEVEL_MODE]==128?(uint16_t)15*eval_signal(0,0)/64:base;}
uint8_t eval_drum_duty(uint8_t c,uint8_t base) BANKED {(void)c;return base;}
uint8_t eval_drum_pan(uint8_t c) BANKED {uint8_t p=evalpatch[c][EV_PAN];return (p&128?p&3:3)&mixer_pan(6);}
void eval_audio_resume_channel(uint8_t c) BANKED {uint16_t f;uint8_t v;if(c>=2||!active[c])return;f=pitchvalue(c);v=level(c,param[c][1],velocity[c]);if(!c)NR10_REG=(param[0][4]<<4)|(param[0][5]<<3)|param[0][6];REG(c?0xff16:0xff11)=(param[c][0]<<6)|param[c][7];REG(c?0xff17:0xff12)=(v<<4)|(evalpatch[c][EV_LEVEL_MODE]==128?8:(param[c][2]<<3)|param[c][3]);REG(c?0xff18:0xff13)=f;REG(c?0xff19:0xff14)=128|(f>>8);pulsevolume[c]=v;}
void eval_audio_resume_pulse1(void) BANKED {eval_audio_resume_channel(0);}
void eval_audio_resume_wave(void) BANKED {uint16_t f;uint8_t v;if(!active[2]||mixrunning||drumon[0]||drumon[1])return;TAC_REG=0;waveengine=0;TMA_REG=TIMA_REG=240;IF_REG&=~TIM_IFLAG;v=level(2,param[2][15]?4-param[2][15]:0,velocity[2]);f=pitchvalue(2);NR30_REG=0;wave();NR30_REG=128;NR32_REG=(v?4-v:0)<<5;NR33_REG=f;NR34_REG=128|(f>>8);route=(route&~0x44)|(param[2][21]&1?4:0)|(param[2][21]&2?0x40:0);NR51_REG=route;if(seqplaying)TAC_REG=4;}
void eval_audio_resume_noise(void) BANKED {uint8_t v;if(!active[3]||drumnoiseowned)return;v=level(3,param[3][1],velocity[3]);NR42_REG=(v<<4)|(evalpatch[3][EV_LEVEL_MODE]==128?8:(param[3][2]<<3)|param[3][3]);NR43_REG=eval_drum_pitch(3,(param[3][18]<<4)|(param[3][19]<<3)|param[3][20]);NR44_REG=128;route=(route&~0x88)|(param[3][21]&1?8:0)|(param[3][21]&2?0x80:0);NR51_REG=route;pulsevolume[3]=v;}

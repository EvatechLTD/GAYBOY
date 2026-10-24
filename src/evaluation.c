#pragma bank 42
#pragma opt_code_speed
#include "api.h"
#include "smooth_playback.h"
#include "mod_bypass.h"
#include "lfo_irq.h"
extern uint32_t noiseleft[2];
#include "evaluation.h"
#include "tones.h"
#include "mixer_shared.h"
#include "tones.h"
void mixer_pattern_changed(void) BANKED;
uint8_t evalpatch[8][16],eval_hidden=128,eval_row,eval_col,eval_tab;
uint8_t eval_confirm,eval_pending,eval_target;
uint8_t eval_plotvel[7]={127,127,127,127,127,127,127};
static uint8_t env,stage,from,modheld;
uint8_t lphase;
/* Durations are bytes; a retained clock is always strictly below duration. */
static uint8_t eclock;
uint8_t mod_bypass;
uint8_t globalmod[10]={0,0,64,0,0,0,8,1,0,0};
static uint32_t lfoclock;
static uint16_t lfobpm;
static uint8_t lfodiv,lfotiming,lfoincrement;
static uint32_t lfoperiod,lfofraction,lforemainder;
uint8_t eval_lfousers,eval_envusers,eval_moddirty=1;
uint16_t eval_modgeneration;
extern uint16_t pattern_generation;
__at (0xD860) uint8_t chord[3][16];
__at (0xD8B0) uint8_t arpindex[3];
__at (0xD8B5) uint8_t arpnote[3];
__at (0xD8BA) uint8_t arpcount[3];
__at (0xD8BF) uint8_t arpcycle[3];
__at (0xD8C4) uint8_t arpvel[3];
__at (0xD8D0) uint32_t arpclock[3];
__at (0xD8C9) uint8_t arpstride[3];
__at (0xD8E4) uint8_t arpfirstvel[3][4];
static const uint8_t bitmasks[8]={1,2,4,8,16,32,64,128};
static uint16_t randomstate=0xACE1;
typedef struct {uint8_t bits[16],vel[4],count,next,step,valid,onset;uint16_t duration;} EvalChord;

static uint8_t evalinitialized,chordnext[3];
static uint16_t arpremaining[3],arp_bpm;
/* Prepared chord/rate data: common four-note arps never search pitch bits. */
uint8_t arpfirstnotes[3][4];
uint8_t arp_active_mask;
uint16_t arpfirstfreq[3][4];
static uint32_t arpperiod[3],arpwhole[3];
static uint16_t arpscale[3],arpratebpm[3],arpremainder[3];
static uint8_t arpratekey[3][5];
static uint16_t arprategeneration[3];
void arp_irq_cancel(uint8_t c) NONBANKED;
void arp_irq_reset(void) NONBANKED;
uint8_t arp_irq_owned(uint8_t c) NONBANKED;
uint8_t arp_irq_valid(uint8_t c) NONBANKED;
uint8_t arp_irq_continue(uint8_t c) BANKED;
uint8_t arp_irq_pattern_owned(uint8_t c) NONBANKED;
uint8_t arp_irq_prepare(uint8_t c,uint32_t period,uint16_t scale,uint16_t steps) BANKED;
extern uint8_t eval_prepare_due,editbuffer_reading;
extern uint16_t seqclock;
static EvalChord loopchord[3];
static uint16_t loopgeneration[3],looplength[3];
void eval_chord_dirty(uint8_t c) BANKED {if(c<3){loopchord[c].valid=0;chordnext[c]=255;arpremaining[c]=0;eval_prepare_due&=~bitmasks[c];}}
/* Snapshot edits alter future onsets, not the chord currently sounding.
   Retain its natural next boundary and find any earlier newly edited onset.
   In particular, do not clear arp clocks, indices or IRQ ownership here. */
void eval_chord_refresh(uint8_t c) BANKED {
 uint16_t i,count,next,at;uint8_t e[4],position;
 if(c<3)loopchord[c].valid=0;
 if(c>=3||(!eval_mode(c)&&!evalpatch[c][EV_CHORD_HISTORY]))return;
 if(chordnext[c]==255)return;
 position=seqposition[c];next=chordnext[c]?chordnext[c]:seqlength[c];
 if(next<=position)next=seqlength[c];
 count=seq_event_count(c);
 for(i=0;i<count;i++){seq_event_get(c,i,e);at=e[0];if(e[1]&&at>position&&at<next)next=at;if((i&3)==3)mixfill();}
 chordnext[c]=next>=seqlength[c]?0:(uint8_t)next;
}
uint8_t eval_message,eval_prepare_due;
extern uint8_t drumsynthvoice;
extern uint16_t seqstepunits;
extern uint8_t seqgate[7];
uint32_t seq_gate_length(uint16_t units,uint8_t duration,uint8_t gate) BANKED;
void eval_audio_reset(void) BANKED;
static void eval_runtime_reset(void){memset(loopchord,0,sizeof(loopchord));arp_active_mask=0;arp_irq_reset();memset(arpperiod,0,sizeof(arpperiod));eval_audio_reset();
 eval_lfousers=eval_envusers=0;eval_moddirty=1;
 eval_prepare_due=0;memset(chordnext,0,sizeof(chordnext));memset(arpremaining,0,sizeof(arpremaining));env=stage=from=lphase=eclock=modheld=0;lfoclock=0;lfobpm=0;memset(chord,0,sizeof(chord));memset(arpcount,0,3);
 if(!evalinitialized){memset(arpclock,0,sizeof(arpclock));memset(arpindex,0,3);evalinitialized=1;}
}
void eval_defaults(void) BANKED {uint8_t c;mod_bypass=0;memset(evalpatch,0,sizeof(evalpatch));memset(coarsepitch,0,24);
 for(c=0;c<8;c++){evalpatch[c][EV_DIV]=4;evalpatch[c][EV_RETRIGGER]=1;evalpatch[c][EV_MS]=125;evalpatch[c][EV_LEVEL_MODE]=0;}
 /* Removed Mono patch bytes hold the three independent synth mixer gains. */
 evalpatch[4][0]=evalpatch[4][1]=evalpatch[4][2]=127;
 globalmod[0]=globalmod[1]=globalmod[3]=globalmod[4]=globalmod[5]=globalmod[8]=globalmod[9]=0;globalmod[2]=64;globalmod[6]=8;globalmod[7]=1;eval_wave_defaults();eval_runtime_reset();
}
void eval_load_object(uint16_t object) BANKED {(void)object;}
void eval_capture(uint8_t *out) BANKED {memset(out,0,EVAL_BYTES);out[0]='S';out[1]=1;memcpy(out+2,evalpatch,128);memcpy(out+130,globalmod,10);}
void eval_restore(const uint8_t *in) BANKED {uint8_t c;uint16_t ms;if(in[0]!='S'||in[1]!=1)return;if(!memcmp(evalpatch,in+2,128)&&!memcmp(globalmod,in+130,10))return;memcpy(evalpatch,in+2,128);memcpy(globalmod,in+130,10);for(c=0;c<3;c++){if(evalpatch[c][EV_DIV]<(evalpatch[c][EV_TIMING]==1?4:3))evalpatch[c][EV_DIV]=evalpatch[c][EV_TIMING]==1?4:3;ms=evalpatch[c][6]|((uint16_t)evalpatch[c][7]<<8);if(ms<63)ms=63;if(ms>1000)ms=1000;evalpatch[c][6]=ms;evalpatch[c][7]=ms>>8;}eval_runtime_reset();eval_drum_dirty();seqirqdirty=1;}
uint8_t eval_instrument(void) BANKED {return page==17?5+drumsynthvoice:page==7?4:selected;}
uint8_t eval_mode(uint8_t c) BANKED {return c<3&&evalpatch[c][EV_MODE]==1;}
uint8_t eval_visible(uint8_t c) BANKED {return c==TWINK_TRACK?syncmode==SYNC_TWINK:c!=3&&c!=4&&!(eval_hidden&(1<<c));}
uint8_t native_mode_feedback(uint8_t c) BANKED;
void eval_set_mode(uint8_t c,uint8_t mode) BANKED {if(c>=3)return;evalpatch[c][EV_MODE]=mode?1:0;evalpatch[c][EV_CHORD_HISTORY]=1;arpremaining[c]=0;eval_seq_off(c);if(!native_mode_feedback(c))seqdrawvalid=0;seqirqready=0;seqirqdirty=1;mixer_pattern_changed();dirty=1;}
int8_t eval_signal(uint8_t c,uint8_t source) BANKED {uint8_t phase=lphase,n;(void)c;static const uint8_t sine[17]={0,6,12,19,24,30,36,41,45,49,53,56,59,61,63,64,64};if(!source)return env;switch(globalmod[4]){case 1:return (phase>>1)-64;case 2:return phase<128?64:-64;case 3:return (int8_t)((phase&0xC0)*73+37)/2;case 4:n=phase&63;if(phase&64)n=64-n;n=sine[n>>2];return phase&128?-(int8_t)n:n;default:return phase<128?(int16_t)phase-64:191-(int16_t)phase;}}
int8_t eval_amount(uint8_t c,uint8_t destination) BANKED {int16_t value;uint8_t source;if(mod_bypass||c>=8||destination>1)return 0;value=(int8_t)(destination?coarsepitch[c][1]:evalpatch[c][EV_DEPTH]);if(!value)return 0;source=destination?coarsepitch[c][2]:evalpatch[c][EV_SOURCES]&1;value*=eval_signal(0,source);return value<0?-((-value)>>6):value>>6;}
static uint8_t route_sources(uint8_t c){uint8_t sources=0;if(mod_bypass)return 0;
 if(evalpatch[c][EV_DEPTH])sources|=evalpatch[c][EV_SOURCES]&1?1:2;
 if(coarsepitch[c][1])sources|=coarsepitch[c][2]?1:2;
 if(MOD_LEVEL(c))sources|=2;
 return sources;
}
static void envelope_start(void){if(!globalmod[0]&&!globalmod[1]){stage=3;env=from=globalmod[2];}else if(!globalmod[0]){stage=2;env=from=64;}else{stage=1;env=from=0;}eclock=0;}
void eval_note(uint8_t c,uint8_t on) BANKED {uint8_t mask,sources;if(mod_bypass||c>=8||c==4)return;mask=bitmasks[c];
 if(on){if(lfo_irq_mask)lfo_irq_note(c);sources=route_sources(c);if((sources&1)&&!globalmod[9])lphase=0;if(sources&2){modheld|=mask;envelope_start();}}
 else{if(!(modheld&mask))return;modheld&=~mask;if(modheld)return;stage=globalmod[3]?4:0;from=env;eclock=0;if(!stage)env=0;}
}
/* Settings masks include both modulation destinations. Activity/ownership is
   checked separately each frame; a configured but silent route does no work. */
void eval_mod_configure(void) BANKED {uint8_t c,bit,sources,oldheld=modheld,oldlfo=eval_lfousers,oldenv=eval_envusers,users=0;
 eval_lfousers=eval_envusers=0;
 if(mod_bypass){eval_modgeneration=pattern_generation;eval_moddirty=0;return;}
 for(c=0;c<8;c++)if(c!=3&&c!=4){bit=bitmasks[c];sources=route_sources(c);if(sources&1)eval_lfousers|=bit;if(sources&2)eval_envusers|=bit;}
 if(!eval_lfousers||!oldlfo){lphase=0;lfoclock=0;lfobpm=0;}
 modheld&=eval_envusers;
 if(!eval_envusers)env=stage=from=eclock=0;
 else if(oldheld&&!modheld){stage=globalmod[3]?4:0;from=env;eclock=0;if(!stage)env=0;}
 if(active[0]&&!pulsekickleft)users|=1;if(active[1])users|=2;
 if(active[2]&&waveengine!=3)users|=4;if(active[3]&&!drumnoiseowned)users|=8;
 if(drumnoiseowned){if(noiseleft[0])users|=32;if(noiseleft[1])users|=64;}if(pulsekickleft)users|=128;
 users&=eval_envusers&~oldenv;
 if(users){modheld|=users;envelope_start();}
 eval_modgeneration=pattern_generation;eval_moddirty=0;
}
/* This is a transport-independent performance switch, not pattern data. */
void eval_mod_enable(uint8_t enabled) BANKED {
 uint8_t c,next=!enabled;if(next==mod_bypass)return;
 __critical{mod_bypass=next;if(next)lfo_irq_mask=0;}
 for(c=0;c<3;c++)arp_irq_cancel(c);
 eval_moddirty=1;seqirqdirty=1;eval_mod_configure();
 eval_mod_refresh_audio();seq_irq_prepare();dirty=1;
}
/* Configure exact quotient/remainder only when musical settings change.
   Retrigger resets lphase, retaining the original musical fractional phase. */
static void lfo_advance(void){uint8_t div=globalmod[6],frames=frameadvance,increment;uint32_t numerator;
 if(globalmod[7]){
  if(div>16)div=16;
  if(lfobpm!=seqbpm||lfodiv!=div||lfotiming!=globalmod[8]){
   lfobpm=seqbpm;lfodiv=div;lfotiming=globalmod[8];
   lfoperiod=lfotiming==1?9600UL:lfotiming==2?21600UL:14400UL;
   if(div<=8){numerator=(uint32_t)seqbpm<<(16-div);lforemainder=((lfoclock%lfoperiod)<<(16-div))%lfoperiod;}
   else{lfoperiod<<=div-8;numerator=(uint32_t)seqbpm<<8;lforemainder=((lfoclock%lfoperiod)<<8)%lfoperiod;}
   if(div<=8&&numerator>lfoperiod*128UL){lfoincrement=128;lfofraction=0;}
   else{lfoincrement=numerator/lfoperiod;lfofraction=numerator%lfoperiod;}
  }
  /* Binary accumulation bounds a long gap to eight iterations. Both the
     integer increment and its fraction double together, retaining every carry. */
  if(frames>8){
   lfoclock+=(uint32_t)seqbpm*frames;if(lfoclock>=22118400UL)lfoclock-=22118400UL;
   numerator=lfofraction;increment=lfoincrement;
   while(frames){
    if(frames&1){lphase+=increment;lforemainder+=numerator;if(lforemainder>=lfoperiod){lforemainder-=lfoperiod;lphase++;}}
    frames>>=1;if(!frames)break;
    increment<<=1;numerator<<=1;if(numerator>=lfoperiod){numerator-=lfoperiod;increment++;}
   }
   return;
  }
  while(frames--){
   increment=lfoincrement;lforemainder+=lfofraction;
   if(lforemainder>=lfoperiod){lforemainder-=lfoperiod;increment++;}
   lphase+=increment;lfoclock+=seqbpm;if(lfoclock>=22118400UL)lfoclock-=22118400UL;
  }
 }else{
  lfobpm=0;lphase+=(uint16_t)globalmod[5]*frames;
  lfoclock+=(uint32_t)seqbpm*frames;if(lfoclock>=22118400UL)lfoclock-=22118400UL;
 }
}
static void envelope_advance(void){uint8_t target,duration;uint16_t ticks;
 if(stage==3){env=globalmod[2];return;}if(!stage)return;duration=globalmod[stage==1?0:stage==2?1:3];target=stage==1?64:stage==2?globalmod[2]:0;ticks=eclock+frameadvance;
 if(!duration||ticks>=duration){env=from=target;eclock=0;stage=stage==4?0:stage+1;}else{eclock=ticks;env=from+((int16_t)target-from)*ticks/duration;}
}
void eval_frame(void) BANKED {lfo_advance();envelope_advance();}
void eval_mod_frame(uint8_t needed) BANKED {if(mod_bypass)return;if(needed&1){if(lfo_irq_active())lfobpm=0;else lfo_advance();}if(needed&2)envelope_advance();}
static uint8_t randbyte(void){randomstate^=randomstate<<7;randomstate^=randomstate>>9;randomstate^=randomstate<<8;return randomstate;}
/* ROM lookup avoids walking every pitch bit on time-critical arp attacks. */
static const uint8_t chord_bits[256]={0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4,1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8};
static const uint8_t chord_first[256]={0,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,4,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,5,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,4,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,6,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,4,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,5,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,4,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,7,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,4,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,5,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,4,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,6,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,4,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,5,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0,4,0,1,0,2,0,1,0,3,0,1,0,2,0,1,0};
static uint8_t nth(uint8_t c,uint8_t index){uint8_t byte,value,count;if(index<4)return arpfirstnotes[c][index];for(byte=0;byte<16;byte++){value=chord[c][byte];count=chord_bits[value];if(index>=count){index-=count;continue;}while(index--)value&=value-1;return (byte<<3)+chord_first[value];}return 0;}
static uint8_t arp_next(uint8_t c){uint8_t count=arpcount[c],p=arpindex[c],n=0,order=evalpatch[c][EV_ORDER];
 if(count<2)return 0;
 switch(order){case 1:n=count-1-(p%count);break;
 case 2:case 4:n=p%(count*2-2);if(n>=count)n=count*2-2-n;if(order==4)n=count-1-n;break;
 case 3:n=randbyte()%count;break;
 case 5:n=p%count;n=n&1?count-1-(n>>1):n>>1;break;
 case 6:n=p%count;n=n&1?(count-1)/2+(n+1)/2:(count-1)/2-n/2;break;
 case 7:n=randbyte()%(count-1);if(n>=arpnote[c])n++;break;
 case 8:/* An affine permutation visits every note once per shuffle cycle. */
  if(!p){uint8_t a,b,t;arpcycle[c]=randbyte()%count;do{arpstride[c]=1+randbyte()%(count-1);a=count;b=arpstride[c];while(b){t=a%b;a=b;b=t;}}while(a!=1);}n=(arpcycle[c]+p*arpstride[c])%count;break;
 case 9:n=arpnote[c];if(randbyte()&1){if(n+1<count)n++;}else if(n)n--;break;
 case 10:n=p%(count*2-2);if(n>=count)n=count*2-2-n;n=n&1?count-1-(n>>1):n>>1;break;
 default:n=p%count;break;}
 arpindex[c]=(p+1)%((order==2||order==4||order==10)?count*2-2:count);arpnote[c]=n;return n;
}
extern uint8_t tablemode[4];
/* Ordinary native arps retrigger the same APU registers as play(), while
   prepared frequencies avoid pitch/FX dispatch. Modulated/shared voices keep
   the general path and its envelope/ownership semantics. */
uint8_t arp_native_sound(uint8_t c,uint8_t note,uint8_t vel,uint8_t index){uint8_t *v,mask,vol;uint16_t f,amp;
 if(c>=3||index>=4||!power||monomode||polymode||tablemode[c]||bend[c]||finepitch[c]||coarsepitch[c][0]||(!mod_bypass&&(coarsepitch[c][1]||evalpatch[c][EV_DEPTH]))||MOD_LEVEL(c)||(mono_owned&(1<<c))||c==0&&pulsekickleft||c==2&&(waveengine||evalwaveactive||keycount[2]>1))return 0;
 v=param[c];if(v[9]||v[22]||c==2&&v[17])return 0;
 if(c==2&&!vel){NR30_REG=0;active[2]=keycount[2]=0;return 1;}
 if(!syncmode&&!seqservicing&&c<2){__critical{seqirqready&=~(1<<c);seqirqfired&=~(1<<c);}seqirqdirty=1;}
 f=arpfirstfreq[c][index];mask=(1<<c)|(16<<c);route&=~mask;if(v[21]&1)route|=mask&15;if(v[21]&2)route|=mask&240;NR51_REG=route;
 phase[c]=age[c]=stepclock[c]=tablepos[c]=tablerow[c]=0;held[c]=basepitch[c]=livepitch[c]=note;velocity[c]=vel;active[c]=keycount[c]=1;keystack[c][0]=note;keyvel[c][0]=vel;liveduty[c]=v[0];
 amp=(uint16_t)v[1]*vel;vol=(amp+1+(amp>>7))>>7;
 if(c==0){NR10_REG=(v[4]<<4)|(v[5]<<3)|v[6];NR11_REG=(v[0]<<6)|v[7];NR12_REG=!vol&&!v[2]?8:(vol<<4)|(v[2]<<3)|v[3];NR13_REG=f;NR14_REG=128|(v[8]<<6)|(f>>8);}
 else if(c==1){NR21_REG=(v[0]<<6)|v[7];NR22_REG=!vol&&!v[2]?8:(vol<<4)|(v[2]<<3)|v[3];NR23_REG=f;NR24_REG=128|(v[8]<<6)|(f>>8);}
 else{wave();wavepending=0;NR30_REG=128;NR31_REG=v[16];NR32_REG=v[15]<<5;NR33_REG=f;NR34_REG=128|(v[8]<<6)|(f>>8);}
 eval_audio_note(c);return 1;
}
static uint8_t startup_mask,startup_note[3][3];
static void sound(uint8_t c,uint8_t note,uint8_t vel,uint8_t index){if(c>=4)return;if(smooth_playback_preparing&&!seqplaying&&c<3){startup_mask|=1<<c;startup_note[c][0]=note;startup_note[c][1]=vel;startup_note[c][2]=index;return;}if(arp_native_sound(c,note,vel,index))return;if(c<2){uint8_t mask=c?0x22:0x11;route&=~mask;if(param[c][21]&1)route|=mask&15;if(param[c][21]&2)route|=mask&240;NR51_REG=route;keycount[c]=1;keystack[c][0]=note;keyvel[c][0]=vel;play(c,note,vel);}else event(0x90|c,note,vel);}
void eval_seq_off(uint8_t c) BANKED {if(c>=3)return;startup_mask&=~(1<<c);arp_active_mask&=~bitmasks[c];arp_irq_cancel(c);chordnext[c]=0;eval_prepare_due&=~bitmasks[c];arpcount[c]=0;memset(chord[c],0,16);if(!c&&eval_mode(0)==2){keyevent(1,held[1],0);seqowned[1]=0;} }
static void prepare_chord(uint8_t c,uint8_t position,EvalChord *out){uint16_t i,count,duration,remaining=1,at;uint8_t data[4],*e,low[4],rank,j,n,onset=0,total=0,*cursor;out->next=(uint8_t)seqlength[c];count=seq_event_count(c);memset(out->bits,0,16);memset(low,255,4);for(i=0;i<count;i++){seq_event_get(c,i,data);e=data;duration=e[3]?e[3]:256;{uint16_t next=out->next?out->next:256,end=e[0]+duration;if(e[0]>position&&e[0]<next)next=e[0];if(end>position&&end<next)next=end;out->next=next;}if(e[1]&&e[0]<=position&&(uint16_t)position<e[0]+duration){n=e[1]-1;if(!(out->bits[n>>3]&bitmasks[n&7])){total++;for(rank=0;rank<4&&n>low[rank];rank++);if(rank<4){for(j=3;j>rank;j--){low[j]=low[j-1];out->vel[j]=out->vel[j-1];}low[rank]=n;out->vel[rank]=e[2];if(!rank)remaining=duration-(position-e[0]);}}out->bits[n>>3]|=bitmasks[n&7];if(e[0]==position)onset=1;mixfill();}if((i&3)==3)mixfill();}
 if(out->next>=seqlength[c])out->next=0;out->count=total;out->duration=remaining;out->step=position;out->valid=1;out->onset=onset; }
void eval_seq_prepare(void) BANKED {}

uint8_t eval_seq_fire(uint8_t c) BANKED {uint16_t duration;uint8_t n,index=0,changed,vel=100,mode,previous;EvalChord current,*ready=&current;
 if(c>=3)return 0;if(seqplaying&&(startup_mask&(1<<c))){startup_mask&=~(1<<c);sound(c,startup_note[c][0],startup_note[c][1],startup_note[c][2]);return 1;}if(!eval_mode(c)&&!evalpatch[c][EV_CHORD_HISTORY])return 0;if(c==1&&eval_mode(0)==2)return 1;
 if(arp_irq_pattern_owned(c))return 1;
 previous=arpcount[c];if(chordnext[c]!=255&&chordnext[c]!=seqposition[c])return previous||eval_mode(c)?1:0;
 if(!seqposition[c]&&editbuffer_reading&&loopchord[c].valid&&loopgeneration[c]==pattern_generation&&looplength[c]==seqlength[c])memcpy(ready,&loopchord[c],sizeof(EvalChord));
 else{prepare_chord(c,seqposition[c],ready);if(!seqposition[c]&&editbuffer_reading){memcpy(&loopchord[c],ready,sizeof(EvalChord));loopgeneration[c]=pattern_generation;looplength[c]=seqlength[c];}}
 chordnext[c]=ready->next;changed=memcmp(ready->bits,chord[c],16)!=0;mode=eval_mode(c);
 if(mode&&ready->count)arp_active_mask|=bitmasks[c];else arp_active_mask&=~bitmasks[c];
 if(!changed&&ready->onset&&!memcmp(arpfirstvel[c],ready->vel,4)&&arp_irq_continue(c)){if(evalpatch[c][EV_RETRIGGER])arpclock[c]=0;return 1;}
 if(!changed&&arpcount[c]&&!ready->onset)return 1;
 arp_irq_cancel(c);
 memcpy(chord[c],ready->bits,16);memcpy(arpfirstvel[c],ready->vel,4);arpcount[c]=ready->count;
 {uint8_t byte,value,rank=0,note;for(byte=0;byte<16&&rank<4;byte++){value=chord[c][byte];while(value&&rank<4){note=(byte<<3)+chord_first[value];arpfirstnotes[c][rank]=note;arpfirstfreq[c][rank++]=notes[note+(c==2?12:0)];value&=value-1;}}}
 if(!arpcount[c]){if(seqowned[c]){if(c==4){monocount=0;monorelease();}else keyevent(c,seqowned[c]-1,0);seqowned[c]=0;}if(!c&&mode==2){stop(1);seqowned[1]=0;}return 1;}
 if(!mode&&arpcount[c]==1&&previous<=1){arpcount[c]=0;return 0;}
 if(mode==1&&!evalpatch[c][EV_RETRIGGER]&&previous)return 1;
 n=nth(c,0);vel=arpfirstvel[c][0];duration=ready->duration;
 if(evalpatch[c][EV_RETRIGGER]){arpindex[c]=arpnote[c]=0;arpclock[c]=0;arpremaining[c]=0;}
 if(mode==1){index=evalpatch[c][EV_RETRIGGER]?arp_next(c):arpnote[c]%arpcount[c];n=nth(c,index);vel=index<4?arpfirstvel[c][index]:vel;}
 arpvel[c]=vel;sound(c,n,mixer_velocity(c,vel),index);seqowned[c]=n+1;seqgateleft[c]=mode==1?0:seqgate[c]==100?(uint32_t)seqstepunits*duration:seq_gate_length(seqstepunits,(uint8_t)duration,seqgate[c]);
 return 1;
}
static uint32_t arp_period(uint8_t c,uint16_t *scale){uint8_t *p=evalpatch[c],division,key[5];int16_t value=0;uint32_t threshold;
 if(arpperiod[c]&&arpratebpm[c]==seqbpm&&arprategeneration[c]==pattern_generation){*scale=arpscale[c];return arpperiod[c];}
 key[0]=p[EV_CLOCK];key[1]=p[EV_DIV];key[2]=p[EV_TIMING];key[3]=p[6];key[4]=p[7];
 if(arpratebpm[c]==seqbpm&&!memcmp(arpratekey[c],key,5)){arprategeneration[c]=pattern_generation;*scale=arpscale[c];return arpperiod[c];}
 if(!p[EV_CLOCK]){value+=p[EV_DIV];division=value<(p[EV_TIMING]==1?4:3)?(p[EV_TIMING]==1?4:3):value>16?16:value;threshold=960UL<<division;*scale=seqbpm;if(p[EV_TIMING]==1)threshold=threshold*2/3;else if(p[EV_TIMING]==2)threshold=threshold*3/2;}
 else {int32_t ms=((uint16_t)p[6]|((uint16_t)p[7]<<8))+(int32_t)value;if(ms<63)ms=63;if(ms>1000)ms=1000;threshold=(uint32_t)ms*1024;*scale=1000;}
 arprategeneration[c]=pattern_generation;memcpy(arpratekey[c],key,5);arpratebpm[c]=seqbpm;arpscale[c]=*scale;arpperiod[c]=threshold;arpwhole[c]=threshold/(*scale);arpremainder[c]=threshold%(*scale);arpremaining[c]=0;return threshold;
}
/* Keep the large division/catch-up frame out of native and idle polling. */
static uint16_t arp_foreground_wait(uint8_t c){uint16_t scale,wait;uint32_t period,left;
 period=arp_period(c,&scale);if(arp_irq_owned(c))return 65535;
 if(arpremaining[c])return arpremaining[c];
 if(arpclock[c]<scale)left=arpwhole[c]+(arpremainder[c]>arpclock[c]);
 else{left=period>arpclock[c]?period-arpclock[c]:1;left=left<65000UL?((uint16_t)left+scale-1)/scale:(left+scale-1)/scale;}
 wait=left>65535UL?65535:(uint16_t)left;if(!wait)wait=1;arpremaining[c]=wait;return wait;
}
uint16_t eval_arp_wait(void) BANKED {uint8_t c;uint16_t next=65535,wait;
 if(!experimental_mode||!arp_active_mask)return next;
 if(arp_bpm!=seqbpm){arp_bpm=seqbpm;memset(arpremaining,0,sizeof(arpremaining));}
 for(c=0;c<3;c++)if((arp_active_mask&bitmasks[c])&&!arp_irq_valid(c)){wait=arp_foreground_wait(c);if(wait<next)next=wait;}
 return next;
}
/* Publish timer ownership after foreground catch-up has consumed its local
   ticks. The preparer accounts for IRQ time accumulated during packet work. */
void eval_arp_prepare(void) BANKED {uint8_t c;uint16_t scale;uint32_t period;
 if(!experimental_mode||(!seqplaying&&!smooth_playback_preparing))return;
 for(c=0;c<3;c++)if(evalpatch[c][EV_MODE]==1&&arpcount[c]&&!arp_irq_valid(c)&&chordnext[c]!=255){if(evalpatch[c][EV_ORDER]==3||evalpatch[c][EV_ORDER]==7||evalpatch[c][EV_ORDER]==8||evalpatch[c][EV_ORDER]==9)continue;period=arp_period(c,&scale);if(arp_irq_prepare(c,period,scale,chordnext[c]?chordnext[c]-seqposition[c]:seqlength[c]-seqposition[c]))arpremaining[c]=0;}
}
static void arp_foreground_tick(uint8_t c,uint16_t ticks){uint16_t scale;uint32_t period;
 if(arpremaining[c]>ticks){arpremaining[c]-=ticks;return;}arpremaining[c]=0;
 period=arpperiod[c];if(!period)period=arp_period(c,&scale);
 if(arpclock[c]>=period){arpclock[c]-=period;if(arpclock[c]>=period)arpclock[c]%=period;
  if(arpcount[c]&&!(seqplaying&&evalpatch[c][EV_RETRIGGER]&&(uint32_t)seqclock+(uint16_t)(ticks*seqbpm)>=seqthreshold&&chordnext[c]==(uint8_t)(seqposition[c]+1>=seqlength[c]?0:seqposition[c]+1))){
   uint8_t index,note,vel;index=arp_next(c);note=nth(c,index);vel=index<4?arpfirstvel[c][index]:arpvel[c];sound(c,note,mixer_velocity(c,vel),index);seqowned[c]=note+1;
  }
 }
}
void eval_seq_tick(uint16_t ticks) BANKED {uint8_t c;uint32_t period;
 if(!experimental_mode||!arp_active_mask)return;
 for(c=0;c<3;c++)if(arp_active_mask&bitmasks[c]){
  arpclock[c]+=evalpatch[c][EV_CLOCK]?(uint32_t)ticks*1000:(uint16_t)(ticks*seqbpm);
  if(arp_irq_owned(c)){period=arpperiod[c];if(arpclock[c]>=period){arpclock[c]-=period;if(arpclock[c]>=period)arpclock[c]%=period;}}
  else arp_foreground_tick(c,ticks);
 }
}
static uint8_t drumallowed[32],drumdirty=1,drumnativesafe;
void seq_native_touch(void) NONBANKED;
void eval_drum_dirty(void) BANKED {drumdirty=1;}
void eval_drum_prepare(void) BANKED {uint8_t occupied[4][32],e[4],group,mask,allowed;uint16_t i,t,end,count;
 if(!drumdirty)return;drumnativesafe=1;memset(occupied,0,sizeof(occupied));memset(drumallowed,0,32);count=seq_event_count(6);
 for(i=0;i<count;i++){seq_event_get(6,i,e);if(!e[1])continue;group=e[1]<=10?0:e[1]<=12?2:3;end=(uint16_t)e[0]+(e[3]?e[3]:256U);if(end>256)end=256;allowed=1;
  for(t=e[0];t<end;t++){mask=bitmasks[t&7];if(group==0?((occupied[0][t>>3]&mask)&&(occupied[1][t>>3]&mask)):(group!=2&&(occupied[group][t>>3]&mask))){allowed=0;break;}}
  if(!allowed)drumnativesafe=0;
  if(allowed){drumallowed[i>>3]|=bitmasks[i&7];for(t=e[0];t<end;t++){mask=bitmasks[t&7];if(group==0){if(occupied[0][t>>3]&mask)occupied[1][t>>3]|=mask;else occupied[0][t>>3]|=mask;}else occupied[group][t>>3]|=mask;}}
  if(!(i&7))mixfill();
 }drumdirty=0;seq_native_touch();
}
uint8_t eval_drum_allowed(uint16_t index) BANKED {eval_drum_prepare();return index<256&&!!(drumallowed[index>>3]&bitmasks[index&7]);}


/* Silent startup warmup: populate packets while musical time is stopped. */
void eval_seq_startup_prepare(void) BANKED {uint8_t c,solos=seqsolo&95;if(drumsolomask)solos|=64;
 startup_mask=0;for(c=0;c<3;c++)if(eval_mode(c)==1&&!(seqmuted&(1<<c))&&(!solos||(solos&(1<<c))))eval_seq_fire(c);
 eval_arp_prepare();
}

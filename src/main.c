#include <gb/gb.h>
#include <gbdk/console.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "api.h"
#include "notes.h"
#define REG(a) (*(volatile uint8_t *)(a))
volatile uint8_t rx[256],wr,rd,overflow;
uint8_t param[4][26],program[4],held[4],velocity[4],active[4],sustain[4];
extern uint8_t edited[4],lastcc,lastvalue,midiage,livepitch[4],liveduty[4];
uint8_t selected=0,choice=0,dirty=1,lastpad=0,st=0,first=0,count=0;
uint8_t basepitch[4],keycount[4],keystack[4][8],keyvel[4][8];
uint8_t mods[4][6],phase[4],age[4],stepclock[4];
uint16_t lastframe;
uint8_t frameadvance=1;
/* Capture transitions even while banked rendering spans several frames.
   Non-nested VBlank/PCM interrupts write padwrite; only main writes padread. */
volatile uint8_t padqueue[32],padwrite,padread;
volatile uint8_t padsampled;
void input_vblank(void){uint8_t p=joypad(),next=(padwrite+1)&31;
 if(p!=padsampled&&next!=padread){padqueue[padwrite]=p;padwrite=next;padsampled=p;}
}
uint8_t tablemode[4],tablelen[4],tablepos[4],notestep[4],tablerow[4];
int8_t tables[4][8][3];
uint8_t customwave[16],custom=0;
uint16_t rawfreq[3];
int16_t bend[4];
uint16_t wheellast[4]={8192,8192,8192,8192};
uint8_t wavepending;
uint8_t polymode,polyowner[3],polynext,polysustain,polyprogram;
uint8_t master=0x77,route=0xff,power=1,vin=0;
const uint8_t limits[26]={3,15,1,7,7,1,7,63,1,1,7,1,7,1,15,3,255,1,15,1,7,3,1,1,1,24};
#include "engine_state.h"
#include "mono_state.h"
void serial_isr(void) { uint8_t b=SB_REG,n=wr+1; SB_REG=0; SC_REG=0x80; if(n==rd) overflow=1; else {rx[wr]=b;wr=n;} }
void globals(void) {NR52_REG=power?0x80:0; if(power){NR50_REG=master|(monomode?0:vin);NR51_REG=route;}}
void panic_audio(void) BANKED;
void panic(void){panic_audio();}
const int8_t arp[5][4]={{0,0,0,0},{0,4,7,12},{0,3,7,12},{0,7,12,7},{0,12,0,-12}};
/* This path never writes a trigger, envelope register or macro counter. */
uint16_t pitchvalue(uint8_t c){uint8_t ph=phase[c]?phase[c]-1:0,n,frac;int16_t pitch,f,delta;
 if(!monomode&&!bend[c]&&(!experimental_mode||!(mods[c][1]|mods[c][3]|mods[c][4]|tablemode[c]))){
  n=basepitch[c];livepitch[c]=n;if(c==2)n+=12;return fine_apply(notes[n],c,0);
 }
 pitch=(int16_t)basepitch[c]*128+bend[c]+(monomode?expoffset[c]:0);
 if(experimental_mode&&!(monomode&&c<3)){
  if(mods[c][1])pitch+=(int16_t)arp[mods[c][1]%5][ph&3]*128;
  if(tablemode[c])pitch+=(int16_t)tables[c][tablerow[c]][0]*128;
 }
 if(pitch<0)pitch=0;if(pitch>16256)pitch=16256;n=pitch>>7;frac=pitch&127;livepitch[c]=n;
 if(c==2)n+=12;f=notes[n];if(frac&&n<139)f+=((uint16_t)(notes[n+1]-notes[n])*frac)>>7;
 if(!experimental_mode)return fine_apply(f,c,0);if(monomode&&c<3)return f;
 if(mods[c][3]){delta=(int16_t)mods[c][3]*((ph&7)<4?(ph&3):3-(ph&3));if(ph&8)delta=-delta;f+=delta;}
 if(mods[c][4])f+=((int16_t)mods[c][4]-8)*(int16_t)age[c];if(f<0)f=0;if(f>2047)f=2047;return fine_apply(f,c,0);
}
void updatepitch(uint8_t c){uint16_t f,base;if(c>2||!active[c])return;if(c==2&&monomode&&expconfig[0]){exp_pitch();return;}if(c==2&&waveengine){enginepitch();return;}f=pitchvalue(c);base=c==0?0xff13:c==1?0xff18:0xff1d;REG(base)=f;REG(base+1)=(param[c][8]<<6)|(f>>8);}

void liveparam(uint8_t c,uint8_t i){uint8_t *v=param[c];if(c==0&&pulsekickleft)return;if(c==2&&waveengine==3)return;
 /* DMG envelope/initial-volume writes are latched only by the next note.
    Writing NRx2 live invokes model-dependent zombie behavior. */
 if(i==1||i==2||i==3)return;
 if(i==0&&c<2){liveduty[c]=v[0];REG(c?0xff16:0xff11)=(v[0]<<6)|v[7];}
 else if(i>=4&&i<=6&&c==0)NR10_REG=(v[4]<<4)|(v[5]<<3)|v[6];
 else if(i==7){if(c==0)NR11_REG=(liveduty[c]<<6)|v[7];else if(c==1)NR21_REG=(liveduty[c]<<6)|v[7];else if(c==3)NR41_REG=v[7];}
 else if(i==8){if(c<3)updatepitch(c);else NR44_REG=v[8]<<6;}
 else if(i==9){uint8_t mask=(1<<c)|(0x10<<c);route&=~mask;if(!v[9]){if(v[21]&1)route|=1<<c;if(v[21]&2)route|=0x10<<c;}NR51_REG=route;}
 else if(i==14&&c==2){custom=0;wavepending=1;}
 else if(i==15&&c==2)NR32_REG=v[15]<<5;
 else if(i==16&&c==2)NR31_REG=v[16];
 else if(i==17&&c==2){if(v[17])stop(c);}
 else if(i>=18&&i<=20&&c==3)NR43_REG=(v[18]<<4)|(v[19]<<3)|v[20];
 else if(i==25)bendupdate(c);
}
void play(uint8_t c,uint8_t note,uint8_t vel){uint8_t *v=param[c],vol;uint16_t f,amplitude;
 if(c==0&&pulsekickleft)return;
 if(c==2&&waveengine){if(waveengine!=3)enginenote(note,vel,0);return;}
 if(c<3)polyowner[c]=0;
 if(!power)return;phase[c]=age[c]=stepclock[c]=0;held[c]=note;basepitch[c]=note;velocity[c]=vel;active[c]=1;tablepos[c]=tablemode[c]==3?(notestep[c]++%tablelen[c]):0;livepitch[c]=note;liveduty[c]=v[0];
 tablerow[c]=tablepos[c];if(c<3)f=pitchvalue(c);else f=0;amplitude=(uint16_t)v[1]*vel;/* Exact floor(x/127), x <= 15*127. */vol=(amplitude+1+(amplitude>>7))>>7;
 if(c<2){uint16_t base=c?0xff16:0xff11;if(!c)NR10_REG=(v[4]<<4)|(v[5]<<3)|v[6];
 REG(base)=(v[0]<<6)|v[7];REG(base+1)=!vol&&!v[2]?8:(vol<<4)|(v[2]<<3)|v[3];REG(base+2)=(uint8_t)f;REG(base+3)=0x80|(v[8]<<6)|(f>>8);
 }else if(c==2){wave();wavepending=0;NR30_REG=v[17]?0:0x80;NR31_REG=v[16];NR32_REG=v[15]<<5;NR33_REG=(uint8_t)f;NR34_REG=0x80|(v[8]<<6)|(f>>8);
 }else{NR41_REG=v[7];NR42_REG=(vol<<4)|(v[2]<<3)|v[3];NR43_REG=(v[18]<<4)|(v[19]<<3)|v[20];NR44_REG=0x80|(v[8]<<6);}
 if(v[9]||v[22])stop(c);
}
void load(uint8_t c,uint8_t n){keycount[c]=0;stop(c);if(c<3)polyowner[c]=0;memcpy(param[c],patch(n)->v,26);memcpy(mods[c],patch(n)->mod,6);phase[c]=age[c]=stepclock[c]=0;tablemode[c]=patch(n)->tconfig&3;tablelen[c]=(patch(n)->tconfig>>2)+1;stocktable(c,patch(n)->table);tablepos[c]=notestep[c]=0;program[c]=n;held[c]=255;bend[c]=0;wheellast[c]=8192;route&=~((1<<c)|(0x10<<c));if(param[c][21]&1)route|=1<<c;if(param[c][21]&2)route|=0x10<<c;NR51_REG=route;edited[c]=0;if(c==2)custom=0;dirty=1;}
void cc(uint8_t c,uint8_t n,uint8_t x){uint8_t i,v,mask;lastcc=n;lastvalue=x;edited[c]=1;dirty=1;
 if(n==120||n==123){keycount[c]=0;stop(c);held[c]=255;return;}if(n==64){if(c==2&&waveengine){enginesustain(x>=64);return;}sustain[c]=x>=64;if(!sustain[c]&&held[c]==255)stop(c);return;}
 if(!experimental_mode&&((n>=112&&n<=126)||n==118||n==119))return;
 if(n==122){if(waveengine==3)return;engineset(((uint16_t)x*3)>>7);return;}if(n==124){arprate=x>>4;return;}if(n==125||n==126){softshape[n-125]=x>>5;return;}
 if(n>=112&&n<=117){i=n-112;mods[c][i]=((uint16_t)x*(i==0?16:i==1?5:i==2?4:i==3?8:i==4?17:64))>>7;return;}
 if(n==118){tablemode[c]=x>>5;return;}if(n==119){tablelen[c]=(x>>4)+1;return;}
 if(n<41||n>119)return;
 if(n>=70&&n<=101){i=n-70;if(!custom){stagewave();custom=1;}mask=customwave[i>>1];v=x>>3;customwave[i>>1]=(i&1)?((mask&0xf0)|v):((mask&15)|(v<<4));wavepending=1;return;}
 if(n==67||n==68){if(c==2&&waveengine)return;if(c<3){if(n==67)rawfreq[c]=(rawfreq[c]&0x780)|x;else rawfreq[c]=(rawfreq[c]&127)|((uint16_t)(x>>3)<<7);if(c==0){if(!pulsekickleft){NR13_REG=rawfreq[c];NR14_REG=(param[c][8]<<6)|(rawfreq[c]>>8);}}else if(c==1){NR23_REG=rawfreq[c];NR24_REG=(param[c][8]<<6)|(rawfreq[c]>>8);}else{NR33_REG=rawfreq[c];NR34_REG=(param[c][8]<<6)|(rawfreq[c]>>8);}}return;}
 if(n==69){if(x>=64)play(c,held[c]==255?basepitch[c]:held[c],velocity[c]?velocity[c]:127);return;}
 if(n==102){if(x<100)load(c,x);return;}
 if(n==103){panic();return;}
 if(n>=104&&n<=106){v=x>>4;if(n==104)master=(master&0x70)|v;else if(n==105)master=(master&7)|(v<<4);else vin=(x>=64)?0x88:0;globals();return;}
 if(n==107){power=x>=64;globals();return;}
 if(n>=108&&n<=111){c=n-108;mask=(1<<c)|(0x10<<c);route&=~mask;if(x&1)route|=1<<c;if(x&2)route|=0x10<<c;globals();return;}
 if(n>66)return;i=n-41;v=((uint16_t)x*(limits[i]+1))>>7;param[c][i]=v;
 if(i==21){mask=(1<<c)|(0x10<<c);route&=~mask;if(v&1)route|=1<<c;if(v&2)route|=0x10<<c;globals();}
 else if(i>=10&&i<=13){if(i==10)master=(master&0x70)|v;if(i==11)vin=(vin&0x80)|(v?8:0);if(i==12)master=(master&7)|(v<<4);if(i==13)vin=(vin&8)|(v?128:0);globals();}
 else if(i==14){custom=0;wavepending=1;}
 else if(i==23){sustain[c]=v;if(!v&&held[c]==255)stop(c);}
 else if(i==24){if(v)stop(c);}
 else if(i==22){if(v)stop(c);}
 else liveparam(c,i);
}
void polyload(uint8_t n){uint8_t c;for(c=0;c<3;c++)load(c,n);polyprogram=n;polynext=polysustain=0;
 /* A pulse patch uses a square wave for its third oscillator. */
 if(patch(n)->voice!=2){param[2][14]=2;param[2][15]=1;tablemode[2]=0;}polymode=1;dirty=1;
}
void polynote(uint8_t note,uint8_t vel){uint8_t i,c=polynext;
 if(waveengine==1){sustain[2]=polysustain;enginenote(note,vel,1);polyowner[2]=1;return;}
 if(waveengine==2){for(i=0;i<4;i++){c=(polynext+i)&3;if(c<2?!active[c]:!softon[c-2])break;}if(i==4)c=polynext&3;
 if(c<2){play(c,note,vel);polyowner[c]=1;sustain[c]=polysustain;}else{softnext=c-2;sustain[2]=polysustain;enginenote(note,vel,1);polyowner[2]=1;}polynext=(c+1)&3;return;}
for(i=0;i<3;i++){c=(polynext+i)%3;if(!active[c])break;}
 if(i==3)c=polynext;play(c,note,vel);polyowner[c]=1;sustain[c]=polysustain;polynext=(c+1)%3;
}
void polyevent(uint8_t t,uint8_t a,uint8_t b){uint8_t c;if(waveengine==3)return;polymode=1;dirty=1;
 if(t==0x90&&b){polynote(a,b);return;}
 if(t==0x80||(t==0x90&&!b)){if(waveengine)engineoff(a);for(c=0;c<(waveengine?2:3);c++)if(polyowner[c]&&held[c]==a){held[c]=255;if(!polysustain)stop(c);}return;}
 if(t==0xc0){if(a<100)polyload(a);return;}
 if(t==0xe0){for(c=0;c<3;c++){wheellast[c]=((uint16_t)b<<7)|a;if(c==2&&waveengine==2)pitchdirty=1;else bendupdate(c);}return;}
 if(t!=0xb0)return;
 if(a==102){if(b<100)polyload(b);return;}
 if(a==64){polysustain=b>=64;for(c=0;c<3;c++)if(polyowner[c])cc(c,a,b);return;}
 for(c=0;c<3;c++)cc(c,a,b);
}
#include "engine_stream.h"
#include "mono.h"
/* Keep direct mono channels sounding when the newest held key is released. */
void keyevent(uint8_t c,uint8_t note,uint8_t vel){uint8_t i,j,n=keycount[c],last=n?keystack[c][n-1]:255;for(i=0;i<n;i++)if(keystack[c][i]==note){for(j=i;j+1<n;j++){keystack[c][j]=keystack[c][j+1];keyvel[c][j]=keyvel[c][j+1];}n--;break;}
 if(vel){if(n==8){for(j=0;j<7;j++){keystack[c][j]=keystack[c][j+1];keyvel[c][j]=keyvel[c][j+1];}n--;}keystack[c][n]=note;keyvel[c][n++]=vel;keycount[c]=n;play(c,note,vel);}
 else {keycount[c]=n;if(last!=note)return;if(n)play(c,keystack[c][n-1],keyvel[c][n-1]);else {held[c]=255;if(!sustain[c])stop(c);}}}
void midi(uint8_t b){midiage=12;if(b>=0xf8)return;if(b&128){count=0;st=b<0xf0?b:0;return;}if(!st)return;
 if((st&0xe0)==0xc0){event(st,b,0);return;}if(!count){first=b;count=1;}else{event(st,first,b);count=0;}}
/* Frame-clock macros update pitch/duty without retriggering hardware envelopes. */
void service(void){uint8_t b;uint16_t now,delta;mixfill();while(rd!=wr){b=rx[rd++];midi(b);mixfill();}__critical {now=sys_time;}if(lastframe!=now){delta=now-lastframe;frameadvance=delta>255?255:delta;lastframe=now;if(experimental_mode)modulate();if(midiage)midiage--;}}
void exp_fetch(uint8_t bank,uint16_t offset,uint8_t *dst) NONBANKED {uint8_t saved=CURRENT_BANK;SWITCH_ROM(bank);memcpy(dst,(const void *)(0x4000+offset),16);SWITCH_ROM(saved);}
extern uint16_t seqdeadline;
void mixer_prepare_service(void) BANKED;
void mixfill(void){if(rd!=wr){uint8_t b=rx[rd++];midi(b);}if(monomode&&expactive){exp_service();if(expconfig[0])exp_fill();}else if(waveengine==2&&mixrunning&&!mixready[mixwrite]){legacyfill();if(!mixready[mixwrite])legacyfill();}if(seqplaying&&!seqservicing&&seqticks>=seqdeadline)seq_frame();}
/* Intro audio can interrupt graphics in any ROM bank. Restore that bank before
   returning; the normal workstation timer is installed after the intro exits. */
void intro_audio_tick(void);
void intro_timer(void){uint8_t saved=CURRENT_BANK;SWITCH_ROM(21);intro_audio_tick();SWITCH_ROM(saved);}
void main(void){uint8_t p,edge,frame=0;intro_run();DISPLAY_OFF;NR52_REG=0x80;globals();startup();drum_init();mixer_boot();navblocked=1;navchoice=8;lastpad=J_START;ui_init();DISPLAY_ON;
 disable_interrupts();padsampled=lastpad;add_VBL(input_vblank);add_SIO(serial_isr);add_TIM(engine_timer);SB_REG=0;SC_REG=0x80;set_interrupts(VBL_IFLAG|SIO_IFLAG|TIM_IFLAG);enable_interrupts();
 lastframe=sys_time;{uint16_t inputframe=sys_time;uint8_t end;while(1){service();mixer_prepare_service();if(inputframe!=sys_time||padread!=padwrite){__critical{inputframe=sys_time;end=padwrite;p=padsampled;}
 if(padread==end){ui_input(p,0);lastpad=p;}
 else while(padread!=end){p=padqueue[padread];padread=(padread+1)&31;edge=p&~lastpad;ui_input(p,edge);lastpad=p;service();}
 if(dirty||(page!=8&&page<18&&!(++frame&(page>=7?1:3)))){dirty=0;ui_render();}ui_flush();}
 }
}
}

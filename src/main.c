#include <gb/gb.h>
#include <gbdk/console.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "api.h"
#include "link_control.h"
#include "mixer_shared.h"
#include "notes.h"
#define REG(a) (*(volatile uint8_t *)(a))
volatile uint8_t rx[256],wr,rd,overflow;
extern volatile uint8_t link_rx_ready,link_peer_capable;
extern volatile uint8_t linkbitqueued;
void link_wire_service(void) BANKED;
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
const uint8_t limits[26]={3,15,1,7,7,1,7,63,1,1,7,1,7,1,31,3,255,1,15,1,7,3,1,1,1,24};
#include "engine_state.h"
#include "mono_state.h"
void serial_isr(void) { uint8_t b=SB_REG,n=wr+1; if(syncmode&&!syncslave){
 if(syncstart&&synctxbyte==0xFA)syncstart=0;synctxwait=3;if(waveengine==3&&syncdivider==1)synctxwait=1;
 if(syncdue){syncdue=0;SB_REG=syncmode==1?(0x80|synctick):0;SC_REG=0x81;}return;
 } SB_REG=0; SC_REG=0x80; if(n==rd) overflow=1; else {rx[wr]=b;wr=n;} }
void globals(void) {NR52_REG=power?0x80:0; if(power){NR50_REG=master|(monomode?0:vin);NR51_REG=route;}}
void panic_audio(void) BANKED;
void seq_native_prepare(void) BANKED;
void seq_native_cancel_voice(uint8_t c) BANKED;
void seq_native_touch(void) NONBANKED;
void panic(void){panic_audio();}
const int8_t arp[5][4]={{0,0,0,0},{0,4,7,12},{0,3,7,12},{0,7,12,7},{0,12,0,-12}};
/* This path never writes a trigger, envelope register or macro counter. */
uint16_t pitchvalue(uint8_t c){uint8_t n,frac;int16_t pitch=(int16_t)basepitch[c]*128+bend[c],f;if(pitch<0)pitch=0;if(pitch>16256)pitch=16256;n=pitch>>7;frac=pitch&127;livepitch[c]=n;if(c==2)n+=12;f=notes[n];if(frac&&n<139)f+=((uint16_t)(notes[n+1]-f)*frac)>>7;return eval_pitch(c,fine_apply(f,c,0));}
void updatepitch(uint8_t c){uint16_t f,base;seq_native_touch();if(c>2||!active[c]||c==0&&pulsekickleft||experimental_mode&&(mono_owned&(1<<c)))return;if(c==2&&(monomode||evalwaveactive)&&expconfig[0]){exp_pitch();return;}if(c==2&&waveengine){enginepitch();return;}f=pitchvalue(c);base=c==0?0xff13:c==1?0xff18:0xff1d;REG(base)=f;REG(base+1)=(param[c][8]<<6)|(f>>8);}

void liveparam(uint8_t c,uint8_t i){uint8_t *v=param[c];if(c==0&&pulsekickleft||experimental_mode&&c<3&&(mono_owned&(1<<c)))return;if(c==2&&waveengine==3)return;
 /* DMG envelope/initial-volume writes are latched only by the next note.
    Writing NRx2 live invokes model-dependent zombie behavior. */
 if(i==1||i==2||i==3)return;
 if(i==0&&c<2){liveduty[c]=v[0];REG(c?0xff16:0xff11)=(v[0]<<6)|v[7];}
 else if(i>=4&&i<=6&&c==0)NR10_REG=(v[4]<<4)|(v[5]<<3)|v[6];
 else if(i==7){if(c==0)NR11_REG=(liveduty[c]<<6)|v[7];else if(c==1)NR21_REG=(liveduty[c]<<6)|v[7];else if(c==3)NR41_REG=v[7];}
 else if(i==8){if(c<3)updatepitch(c);else NR44_REG=v[8]<<6;}
 else if(i==9){uint8_t mask=(1<<c)|(0x10<<c);route&=~mask;if(!v[9]){if(v[21]&1)route|=1<<c;if(v[21]&2)route|=0x10<<c;}NR51_REG=route;}
 else if(i==14&&c==2){custom=0;wavepending=1;}
 else if(i==15&&c==2)NR32_REG=(evalpatch[2][EV_LEVEL_MODE]==128?(3*eval_signal(0,0)/64?4-3*eval_signal(0,0)/64:0):v[15])<<5;
 else if(i==16&&c==2)NR31_REG=v[16];
 else if(i==17&&c==2){if(v[17])stop(c);}
 else if(i>=18&&i<=20&&c==3)NR43_REG=(v[18]<<4)|(v[19]<<3)|v[20];
 else if(i==25)bendupdate(c);
}
uint8_t eval_attack_volume(uint8_t c,uint8_t vel) BANKED;
void play(uint8_t c,uint8_t note,uint8_t vel){uint8_t *v=param[c],vol;uint16_t f,amplitude;
 if(!seqservicing)seq_native_cancel_voice(c);
 if(!syncmode&&!seqservicing&&c<2){__critical {seqirqready&=~(1<<c);seqirqfired&=~(1<<c);}seqirqdirty=1;}
 if(c==2&&waveengine&&!(experimental_mode&&waveengine==3)){enginenote(note,vel,0);return;}
 if(c<3)polyowner[c]=0;
 if(!power)return;phase[c]=age[c]=stepclock[c]=0;held[c]=note;basepitch[c]=note;velocity[c]=vel;active[c]=1;tablepos[c]=tablemode[c]==3?(notestep[c]++%tablelen[c]):0;livepitch[c]=note;liveduty[c]=v[0];if(experimental_mode)eval_note(c==1&&eval_mode(0)==2?0:c,1);if(c==0&&pulsekickleft||experimental_mode&&(c<3&&(mono_owned&(1<<c))||c==2&&waveengine==3||c==3&&drumnoiseowned)){eval_audio_note(c);return;}
 tablerow[c]=tablepos[c];if(c<3)f=pitchvalue(c);else f=0;amplitude=(uint16_t)v[1]*vel;/* Exact floor(x/127), x <= 15*127. */vol=(amplitude+1+(amplitude>>7))>>7;if(experimental_mode&&c!=2)vol=eval_attack_volume(c,vel);
 if(c<2){uint16_t base;if(!syncmode&&(seqirqsuppress&(1<<c))){if(v[9]||v[22])stop(c);return;}base=c?0xff16:0xff11;if(!c)NR10_REG=(v[4]<<4)|(v[5]<<3)|v[6];
 REG(base)=(v[0]<<6)|v[7];REG(base+1)=experimental_mode&&evalpatch[c==1&&eval_mode(0)==2?0:c][EV_LEVEL_MODE]==128?(vol<<4)|8:!vol&&!v[2]?8:(vol<<4)|(v[2]<<3)|v[3];REG(base+2)=(uint8_t)f;REG(base+3)=0x80|(v[8]<<6)|(f>>8);
 }else if(c==2){if(1){wave();wavepending=0;NR30_REG=v[17]?0:0x80;NR31_REG=v[16];NR32_REG=(evalpatch[2][EV_LEVEL_MODE]==128?(3*eval_signal(0,0)/64?4-3*eval_signal(0,0)/64:0):v[15])<<5;NR33_REG=(uint8_t)f;NR34_REG=0x80|(v[8]<<6)|(f>>8);}
 }else{NR41_REG=v[7];NR42_REG=experimental_mode&&evalpatch[3][EV_LEVEL_MODE]==128?(vol<<4)|8:(vol<<4)|(v[2]<<3)|v[3];NR43_REG=(v[18]<<4)|(v[19]<<3)|v[20];NR44_REG=0x80|(v[8]<<6);}
 if(v[9]||v[22])stop(c);else eval_audio_note(c);
}
void cc_apply(uint8_t c,uint8_t n,uint8_t x) BANKED;
void cc(uint8_t c,uint8_t n,uint8_t x){cc_apply(c,n,x);seq_native_touch();if(!syncmode)seq_irq_refresh(c);}
void eval_polyload(uint8_t n) BANKED;
void polyload(uint8_t n){eval_polyload(n);}
void polynote(uint8_t n,uint8_t v){(void)n;(void)v;}
void polyevent(uint8_t t,uint8_t a,uint8_t b){(void)t;(void)a;(void)b;}
extern uint8_t seqnativeautoarm,seqnativelaunchfired;
void seq_native_schedule_tick(uint8_t elapsed) BANKED;
void input_vblank_native(void){input_vblank();if(seqnativeautoarm)seq_native_schedule_tick((((seqfraction+9)&63)+183U)>>6);}
#define input_vblank input_vblank_native
#include "engine_stream.h"
#undef input_vblank
#include "mono.h"
/* Keep direct mono channels sounding when the newest held key is released. */
void keyevent(uint8_t c,uint8_t note,uint8_t vel){uint8_t i,j,n=keycount[c],last=n?keystack[c][n-1]:255;for(i=0;i<n;i++)if(keystack[c][i]==note){for(j=i;j+1<n;j++){keystack[c][j]=keystack[c][j+1];keyvel[c][j]=keyvel[c][j+1];}n--;break;}
 if(vel){if(n==8){for(j=0;j<7;j++){keystack[c][j]=keystack[c][j+1];keyvel[c][j]=keyvel[c][j+1];}n--;}keystack[c][n]=note;keyvel[c][n++]=vel;keycount[c]=n;play(c,note,vel);}
 else {keycount[c]=n;if(last!=note)return;if(n)play(c,keystack[c][n-1],keyvel[c][n-1]);else {held[c]=255;if(!sustain[c])stop(c);}}}
void midi(uint8_t b){if(syncmode&&sync_receive(b))return;midiage=12;if(b>=0xf8)return;if(b&128){count=0;st=b<0xf0?b:0;return;}if(!st)return;
 if((st&0xe0)==0xc0){event(st,b,0);return;}if(!count){first=b;count=1;}else{event(st,first,b);count=0;}}
/* Frame-clock macros update pitch/duty without retriggering hardware envelopes. */
uint8_t seq_native_supported(void) BANKED;
void service_frame(void) BANKED;
void roll_feedback_service(void) BANKED;
void service(void){uint8_t b,budget=8;mixfill();while(rd!=wr&&budget--&&!seqnativelaunchfired){b=rx[rd++];midi(b);mixfill();}if(lastframe!=sys_time)service_frame();}
void exp_fetch(uint8_t bank,uint16_t offset,uint8_t *dst) NONBANKED {uint8_t saved=CURRENT_BANK;SWITCH_ROM(bank);memcpy(dst,(const void *)(0x4000+offset),16);SWITCH_ROM(saved);}
extern uint16_t seqdeadline;
void mixer_prepare_service(void) BANKED;
void sparse_prepare_service(void) BANKED;
void eval_seq_prepare(void) BANKED;
extern uint8_t eval_prepare_due;
extern uint8_t mixer_layout_dirty;
void mixer_layout_service(void) BANKED;
void mixer_poll_input(void) BANKED;
void eval_audio_resume_wave(void) BANKED;
void mixfill(void){if(voice_owner_busy){if(waveengine!=3&&expconfig[0])exp_fill();return;}if(page==18&&!navopen&&padread!=padwrite)mixer_poll_input();if(syncarmed&&syncmode==1&&link_peer_capable&&linkbitqueued<8&&linktxread<linktxsize)link_wire_service();if(syncarmed&&!seqnativelaunchfired&&syncr!=syncw&&!synctxwait)sync_control_service();if(rd!=wr&&!seqnativelaunchfired&&!syncbusy&&(!syncmode||!seqservicing||(syncmode==1&&!syncslave))){uint8_t b=rx[rd++];midi(b);} /* Retire a bounded part of the incoming installation before catching up
    musical time. Otherwise repeated cartridge scans can keep the scheduler
    busy forever and prevent the foreground installer from making progress.
    The guard also prevents nested I/O yields from reentering this service. */
 if(seqplaying&&!seqservicing&&seqeventcache>=2){seqservicing=1;sparse_service();seqservicing=0;}
 if((rd==wr||seqnativelaunchfired||(syncmode==1&&!syncslave))&&seqplaying&&!seqservicing&&seqticks>=seqdeadline)seq_frame();
 
 if(waveengine==3&&drumtail&&!mixrunning&&!drumon[0]&&!drumon[1])eval_audio_resume_wave();
 if(padread==padwrite&&sparse_enabled==1&&seqplaying&&!seqservicing&&(page==18||link_ui_hold))sparse_prepare_service();}
/* Intro audio can interrupt graphics in any ROM bank. Restore that bank before
   returning; the normal workstation timer is installed after the intro exits. */
void intro_audio_tick(void);
void intro_timer(void){uint8_t saved=CURRENT_BANK;SWITCH_ROM(21);intro_audio_tick();SWITCH_ROM(saved);}
void mixer_fader_service(void) BANKED;
void main(void){uint8_t p,edge,frame=0;sync_init();intro_run();DISPLAY_OFF;NR52_REG=0x80;globals();drum_init();startup();eval_defaults();ui_loading_begin();mixer_boot();navblocked=1;navchoice=8;lastpad=J_START;ui_init();DISPLAY_ON;
 disable_interrupts();padsampled=lastpad;add_VBL(input_vblank);add_SIO(link_serial_isr);add_TIM(engine_timer);SB_REG=0;SC_REG=0x80;set_interrupts(VBL_IFLAG|SIO_IFLAG|TIM_IFLAG);enable_interrupts();
 /* Preparation runs on Mixer; its private journal commit (phase18 atACB4)
    also finishes off-page. Avoid an idle bank round-trip on other pages. */
 *(uint8_t *)0xA427=0;lastframe=sys_time;{uint16_t inputframe=sys_time;uint8_t end;while(1){service();if(sparse_enabled)sparse_service();else if(page==18||link_ui_hold||*(volatile uint8_t *)0xACB4==18)mixer_prepare_service();if(inputframe!=sys_time||padread!=padwrite){__critical{inputframe=sys_time;end=padwrite;p=padsampled;}
 if(syncmode>1&&syncslave&&seqplaying)sync_advance(0);
 if(syncmode==1)link_service();
 if(mixer_layout_dirty&&!seqplaying)mixer_layout_service();
 if(padread==end){if(!link_ui_hold){ui_input(p,0);if(p&&page!=18)seq_native_touch();}lastpad=p;}
 else while(padread!=padwrite){p=padqueue[padread];padread=(padread+1)&31;edge=p&~lastpad;if(!link_ui_hold||((p&J_SELECT)&&(edge&J_START))){ui_input(p,edge);if(page!=18)seq_native_touch();}lastpad=p;service();}
 if(!syncmode&&seqplaying&&!seqservicing&&seqirqdirty&&!seqirqready&&!seqirqfired){seqservicing=1;seq_irq_prepare();seqservicing=0;}
 /* Settings pages change on input. Periodic refresh is only for live views. */
 if(!link_ui_hold){if(!(page==18&&seqplaying&&sparse_enabled&&mx.pending<8)&&(dirty||(!navopen&&(page==0||page==9)&&!(++frame&3)))){dirty=0;ui_render();}ui_flush();if(page==8)roll_feedback_service();else if(page==18)mixer_fader_service();}}
 }
}
}

#pragma bank 12
#include "api.h"
#include "mixer_shared.h"
#include "midi_input.h"
void seq_native_touch(void) NONBANKED;
#include "tones.h"
void mixer_pattern_changed(void) BANKED;
void seq_native_launch_clear(void) BANKED;
void midi_event(uint8_t s,uint8_t a,uint8_t b) BANKED {if(!mixer_midi(s,a,b))event(s,a,b);}
void event(uint8_t s,uint8_t a,uint8_t b) BANKED {uint8_t c=s&15,t=s&0xf0;if(c==3)return;if(c==1&&!monomode&&eval_mode(0)==2&&(t==0x90||t==0x80))return;if(t==0xb0||t==0xc0)mixer_pattern_changed();if(!experimental_mode&&c>3)return;if(waveengine==3&&(c==2||c==5)&&!experimental_mode){
 if(mixrunning||drumon[0]|drumon[1]||t!=0x90||!b)return;
 TAC_REG=0;enginestop();waveengine=0;TMA_REG=TIMA_REG=240;if(syncarmed)sync_timer_config();IF_REG&=~TIM_IFLAG;if(seqplaying)TAC_REG=4;
 }if(!experimental_mode&&c==3&&drumnoiseowned&&(t==0x90||t==0x80))return;if(c>=4)return;if(monomode)return;
 if(c==2&&waveengine&&!(experimental_mode&&waveengine==3)&&(t==0x90||t==0x80)){if(t==0x90&&b)enginenote(a,b,0);else engineoff(a);return;}
 if(t==0x90||t==0x80)keyevent(c,a,t==0x90?b:0);
 else if(t==0xe0){seq_native_launch_clear();seq_native_touch();wheellast[c]=((uint16_t)b<<7)|a;if(c==2&&waveengine==2)pitchdirty=1;else bendupdate(c);}
 else if(t==0xb0)cc(c,a,b);else if(t==0xc0&&a<100){load(c,a);if(c==selected)choice=a;}
}

/* Elapsed VBlank time keeps acceleration consistent, with quick grid repeats. */
/* Samples of 8 + 20*log2(1 + seconds*2), in level units per second.
   Interpolate at quarter-second intervals; retain fractional steps so slow
   renders do not interrupt a held fader or discard its elapsed time. */
static const uint8_t mixrates[17]={8,20,28,34,40,44,48,51,54,57,60,62,64,66,68,70,71};
static uint16_t mixphase;
uint8_t ui_repeat(uint8_t p,uint8_t edge) BANKED {uint8_t axis,interval,resetmask=J_A|J_B|J_SELECT|J_START;uint16_t now,elapsed,steps;__critical{now=sys_time;}repeatsteps=1;
 if((p&(J_A|J_B))&&(page==1||page==2||page==5||page==6||page==7||page==9||page==10||page==16||page==17||page==27)){axis=p&(J_UP|J_DOWN|J_LEFT|J_RIGHT);if((p&J_SELECT)||!axis||(axis&(axis-1))){repeataxis=0;return edge;}}
 else if(page==8||page==9||page==10){axis=p&(J_UP|J_DOWN|J_LEFT|J_RIGHT);if((p&J_SELECT)||!axis||(axis&(axis-1))){repeataxis=0;return edge;}}
 else if(page==7){axis=p&(J_UP|J_DOWN);resetmask|=J_LEFT|J_RIGHT;if((!(p&J_B)&&!monoedit)||(p&J_SELECT)||(axis!=J_UP&&axis!=J_DOWN)){repeataxis=0;return edge;}}
 else if(page==18){axis=p&(J_UP|J_DOWN);resetmask|=J_LEFT|J_RIGHT;if(!(p&(J_A|J_B))||(p&J_SELECT)||(axis!=J_UP&&axis!=J_DOWN)){repeataxis=0;return edge;}}
 else{axis=p&(J_LEFT|J_RIGHT);resetmask|=J_UP|J_DOWN;if(!(page==1||page==2||page==5||page==6)||(axis!=J_LEFT&&axis!=J_RIGHT)){repeataxis=0;return edge;}}
 if(navopen||(p&J_START)||(edge&resetmask)){repeataxis=0;mixphase=0;return edge;}
 if(axis!=repeataxis||(edge&axis)){repeataxis=axis;repeatstart=repeatlast=now;mixphase=0;return edge;}
 elapsed=now-repeatstart;
 if(page==18||(page==8&&seqhead==5&&(p&(J_A|J_B)))){uint8_t rate,index;
  if(elapsed>=240)rate=71;
  else{index=elapsed/15;rate=mixrates[index]+(uint16_t)(mixrates[index+1]-mixrates[index])*(elapsed%15)/15;}
  steps=now-repeatlast;if(steps>60)steps=60;repeatlast=now;
  mixphase+=steps*rate;steps=mixphase/60;if(steps>8)steps=8;
  mixphase-=steps*60;
  if(steps){repeatsteps=steps;edge|=axis;}return edge;
 }
 if(page==8&&!seqhead){if(elapsed<8)return edge;interval=elapsed<24?4:elapsed<48?2:1;}
 else{if(elapsed<18)return edge;interval=elapsed<60?8:elapsed<120?3:1;}
 if((uint16_t)(now-repeatlast)>=interval){if(repeatlast==repeatstart){repeatlast=now;steps=1;}else{steps=(uint16_t)(now-repeatlast)/interval;if(steps>8){steps=8;repeatlast=now;}else repeatlast+=steps*interval;}repeatsteps=steps;edge|=axis;}return edge;
}

void mixer_pattern_changed(void) BANKED;
extern uint8_t seqrecordtrack;
void seq_record_finish(void) BANKED;
/* During a drag the resident data remains authoritative for hit testing,
   but drawing keeps the published notes until every direction is released. */
uint8_t seqeditpreview,seqpreviewdirty,seqpreviewpinned;
uint8_t seqgestureblocked,seqgesturepressed;
static uint8_t seqgesturepage;
uint8_t roll_preview_finish(void) BANKED;
/* A427 is dedicated input state; B4E3 overlaps the retained grid tiles. */
void ui_input(uint8_t p,uint8_t edge) BANKED {uint8_t i,head=seqhead,gesture,tracking,c=seqtrack,oldcursor,oldpitch,oldtop,oldbase,stop;int16_t top;*(uint8_t *)0xA427=1;if(sparse_enabled&&edge&&!(page==18&&!navopen&&mx.focus>=30&&mx.focus<38&&!(p&(J_A|J_B|J_START|J_SELECT))))sparse_finish_install();if(seqrecordtrack!=255&&(!(p&J_B)||page!=8||navopen||(p&(J_START|J_SELECT))))seq_record_finish();
 seqgesturepressed=edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN);
 gesture=page==8&&!navopen&&!seqhead&&!seqfocus&&seqapending&&
  !(p&(J_START|J_SELECT))&&((p&(J_A|J_B))==J_A||(p&(J_A|J_B))==J_B);
 tracking=gesture||(page==8&&!navopen&&!seqfocus&&(!seqhead||seqhead==6)&&!(p&(J_A|J_B|J_START|J_SELECT)));
 if(!tracking){seqgestureblocked=seqgesturepage=0;}
 if(!(p&(J_LEFT|J_RIGHT|J_UP|J_DOWN)))seqgestureblocked=0;
 if(seqgesturepage&&seqdrawvalid&&seqfontdirty&&seqviewtrack==c&&seqviewbase==seqbase&&(c==6||seqviewtop==seqtop[c])){seqgesturepage=0;__critical{repeatstart=repeatlast=sys_time;}}
 edge=ui_repeat(p,edge);
 if(tracking){edge&=~seqgestureblocked;
  if(seqgesturepage){edge&=~(J_LEFT|J_RIGHT|J_UP|J_DOWN);__critical{repeatstart=repeatlast=sys_time;}}
 }
 /* A slow paint/drag must not turn elapsed repeat time into eight expensive
    edits before the next input edge can be handled. Keep real queued edges;
    bound only synthetic held-button catch-up and discard its time debt. */
 if(page==8&&!navopen&&!seqhead&&!seqfocus&&(p&(J_A|J_B))&&repeatsteps>2){repeatsteps=2;__critical{repeatlast=sys_time;}}
 seqeditpreview=page==8&&!navopen&&!seqhead&&!seqfocus&&seqapending&&seqapending!=4&&
  !(p&(J_START|J_SELECT))&&((p&(J_A|J_B))==J_A||(p&(J_A|J_B))==J_B)&&
  (p&(J_UP|J_DOWN|J_LEFT|J_RIGHT));
 /* A fresh edge crossing explicitly permits drawing the destination page.
    Until it is published, discard synthetic repeat debt from that hold. */
 seqpreviewpinned=0;if(seqgesturepage)seqeditpreview=0;
 if(!seqeditpreview&&seqpreviewdirty){seqpreviewdirty=0;seqdrawvalid=roll_preview_finish();dirty=1;}
 for(i=0;i<repeatsteps;i++){uint8_t retained=seqdrawvalid;oldcursor=seqcursor[c];oldpitch=c==6?drumrow:seqpitch[c];oldtop=seqtop[c];oldbase=seqbase;mixfill();/* Only value gestures can change a tone; grid mutations mark themselves. */if(edge&&!navopen&&!(p&(J_START|J_SELECT))&&page!=8&&(page<18||page==23)&&(p&(J_A|J_B)))mixer_pattern_changed();ui_action(p,edge);
  if(seqeditpreview){seqpreviewdirty=1;if(retained)seqdrawvalid=seqgrouptrack==seqtrack?2:1;}
  if(tracking){stop=0;
   if(c!=6&&seqpitch[c]!=oldpitch){
    if(gesture&&(edge&J_UP)&&seqpitch[c]>oldtop){top=(int16_t)oldtop+seqrows;seqtop[c]=top>127?127:top;seqgesturepage=1;}
    if(gesture&&(edge&J_DOWN)&&(int16_t)seqpitch[c]<(int16_t)oldtop-seqrows+1){top=(int16_t)oldtop-seqrows;seqtop[c]=top<(c==2?24:36)+seqrows-1?(c==2?24:36)+seqrows-1:top;seqgesturepage=1;}
    /* Ordinary one-row octave scrolling keeps its retained fast path. Stop
       on arrival at an edge, but do not relatch every retained scroll row. */
    if(gesture||seqtop[c]==oldtop){
     if((edge&J_UP)&&seqpitch[c]==seqtop[c])stop|=J_UP;
     if((edge&J_DOWN)&&(int16_t)seqpitch[c]==(int16_t)seqtop[c]-seqrows+1)stop|=J_DOWN;
    }
   }else if(c==6&&drumrow!=oldpitch){if((edge&J_UP)&&!drumrow)stop|=J_UP;if((edge&J_DOWN)&&drumrow==12)stop|=J_DOWN;}
   if(seqcursor[c]!=oldcursor){
    if((seqcursor[c]/seqcols)*seqcols!=oldbase){seqbase=(seqcursor[c]/seqcols)*seqcols;seqgesturepage=1;}
    if((edge&J_LEFT)&&seqcursor[c]==seqbase)stop|=J_LEFT;
    if((edge&J_RIGHT)&&(uint16_t)seqcursor[c]+1==seqbase+seqcols)stop|=J_RIGHT;
   }
   seqgestureblocked|=stop;
   if(seqgesturepage){seqdrawvalid=seqeditpreview=0;dirty=1;stop=1;}
   if(stop||(edge&seqgestureblocked)){__critical{repeatstart=repeatlast=sys_time;}break;}
  }
  /* A grid-repeat batch ends at the focus boundary. Its remaining UPs must
     not become header scrolling or carry accelerated repeat debt into it. */
  if(page==8&&!navopen&&!(p&(J_A|J_B))&&(!head)!=(!seqhead)){
   __critical{repeatstart=repeatlast=sys_time;}break;
  }
 }*(uint8_t *)0xA427=0;}

/* Durations are one byte (zero means256); avoid a generic32-bit multiply
   in the real-time onset path. Validated tempo/gate bounds fit24 bits. */
static uint32_t gate_multiply(uint32_t value,uint8_t count){uint32_t total=0;while(count){if(count&1)total+=value;count>>=1;if(count)value<<=1;}return total;}
uint32_t seq_gate_length(uint16_t units,uint8_t duration,uint8_t gate) BANKED {uint32_t total=duration?gate_multiply(units,duration):(uint32_t)units<<8;(void)gate;return total?total:1;}

void load(uint8_t c,uint8_t n) BANKED {seq_native_touch();keycount[c]=0;stop(c);memcpy(param[c],patch(n)->v,26);memset(mods[c],0,6);phase[c]=age[c]=stepclock[c]=0;tablemode[c]=0;tablelen[c]=(patch(n)->tconfig>>2)+1;stocktable(c,patch(n)->table);tablepos[c]=notestep[c]=0;program[c]=n;held[c]=255;bend[c]=0;wheellast[c]=8192;route&=~((1<<c)|(0x10<<c));if(param[c][21]&1)route|=1<<c;if(param[c][21]&2)route|=0x10<<c;NR51_REG=route;edited[c]=0;if(c==2)custom=0;seq_irq_refresh(c);dirty=1;}

void eval_polyload(uint8_t n) BANKED {(void)n;}
void eval_polyevent(uint8_t t,uint8_t a,uint8_t b) BANKED {(void)t;(void)a;(void)b;}

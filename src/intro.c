#pragma bank 21
#include "api.h"
#include <gb/cgb.h>
#include "intro_assets.h"
void intro_demo(uint8_t frame,uint8_t base) BANKED;
void intro_cracks(uint8_t stage,uint8_t mood,uint8_t load) BANKED;
void zoom0(uint8_t frame) BANKED;
void zoom1(uint8_t frame) BANKED;
void zoom2(uint8_t frame) BANKED;

/* Boot-only scene; no page number or runtime navigation route points here. */
uint8_t introactive, introready, introbar, introstep;
uint16_t introframe;
uint8_t zoombuffer,introfade;
volatile uint8_t intro_audio_running,intro_audio_song,intro_audio_scene;
volatile uint16_t intro_audio_ticks,intro_scene_ticks;
static uint16_t audio_clock;
void intro_timer(void);
/* Two-bar harmonic reductions; leads are newly composed for this ROM.
   District opening: C / F / Am / Am, two beats per chord.
   Heights main progression: F / C / Bb / F C (2/2/2/1/1 beats).
   Root tables advance once per quarter note; melodies once per eighth. */
static const uint8_t roots[8]={36,36,41,41,45,45,45,45};
static const uint8_t melody[2][8]={
 {67,64,0,72,69,65,76,72},
 {76,0,72,71,69,64,67,0}
};
static const uint8_t happyroots[8]={41,41,36,36,46,46,41,36};
static const uint8_t happymelody[2][8]={
 {81,77,72,0,76,79,84,79},
 {74,77,82,0,81,77,76,72}
};
/* Four bars: 95 -> 128 BPM, arriving at the second cue without a tempo jump. */
static const uint16_t train_rate[64]={380,382,384,386,388,390,392,394,396,398,400,403,405,407,409,411,413,415,417,419,421,424,426,428,430,432,434,436,438,440,442,444,447,449,451,453,455,457,459,461,463,465,468,470,472,474,476,478,480,482,484,486,488,491,493,495,497,499,501,503,505,507,509,512};
static const uint16_t train_swing[64]={3072,3023,2974,2925,2876,2828,2779,2730,2681,2633,2584,2535,2486,2438,2389,2340,2291,2243,2194,2145,2096,2048,1999,1950,1901,1852,1804,1755,1706,1657,1609,1560,1511,1462,1414,1365,1316,1267,1219,1170,1121,1072,1024,975,926,877,828,780,731,682,633,585,536,487,438,390,341,292,243,195,146,97,48,0};
static const uint8_t arpmajor[]={0,4,7,12}, arpminor[]={0,3,7,12};
static void pulse(uint8_t channel,uint8_t note,uint8_t volume){
 uint16_t f=notes[note];uint16_t reg=channel?0xff16:0xff11;
 REG(reg)=0x40;REG(reg+1)=(volume<<4)|1;
 REG(reg+2)=f;REG(reg+3)=0x80|(f>>8);
}
void intro_drum(uint8_t envelope,uint8_t timbre){NR41_REG=0;NR42_REG=envelope;NR43_REG=timbre;NR44_REG=0x80;}
static void percussion(uint8_t snare){intro_drum(snare?0x72:0x31,snare?0x37:0x15);}
static void happymusic(void){
 uint8_t b=introbar&1,s=introstep,n,r=happyroots[(b<<2)+(s>>2)];uint16_t f;
 if(introfade<4&&!(s&1)){n=happymelody[b][s>>1];if(n)pulse(0,n,7);}
 if(introfade<3&&(s&1))pulse(1,r+12+arpmajor[s&3],3);
 if(introfade<2&&(!(s&3)||s==6||s==14)){
  n=r;f=notes[n+12];
  NR30_REG=0x80;NR32_REG=0x40;NR33_REG=f;NR34_REG=0x80|(f>>8);
 }
 if(introfade<2&&(s&3)==2)NR32_REG=0x60;
 if(introfade<1){
 if(s==0||s==8)intro_drum(0x61,0x64);
 else if(s==4||s==12)percussion(1);else if(s&1)percussion(0);
 }
 if(++introstep==16){introstep=0;introbar=(introbar+1)&15;}
}
static void music(void){
 uint8_t b=introbar&1,s=introstep,n,offset,r=roots[(b<<2)+(s>>2)];uint16_t f;
 if(!(s&1)){n=melody[b][s>>1];if(n)pulse(0,n,7);}
 /* First two bars are melody alone. The MPC introduces the full rhythm. */
 if(!intro_audio_scene)goto advance;
 offset=(b?arpminor:arpmajor)[s&3];
 if(s&1)pulse(1,r+24+offset,3);
 if(!(s&3)||s==6||s==15){
  n=r+(s==15?7:0);f=notes[n+12];
  NR30_REG=0x80;NR32_REG=0x40;NR33_REG=f;NR34_REG=0x80|(f>>8);
 }
 if((s&3)==2)NR32_REG=0x60;
 if(intro_audio_scene==2){
  /* Tonal kick shares the downbeat with the noise snare, never delayed. */
  if(!(s&3)){pulse(1,24,8);NR21_REG=0x80;}
  if(s==4||s==12)intro_drum(0x72,0x37);
  else if(!(s&3))intro_drum(0x81,0x65);
  else if((s&3)==2)intro_drum(0x52,0x15);
 }else{
  if(s==0||s==6||s==10)intro_drum(0x71,0x65);
  else if(s==4||s==12)percussion(1);else if(s&1)percussion(0);
 }
advance:
 if(++introstep==16){introstep=0;introbar=(introbar+1)&15;}
}
/* Called from the fixed-bank timer trampoline. No video work or banked calls. */
void intro_audio_step(void){
 if(!introstep){
  if(!intro_audio_song){
   if(introbar==2&&intro_audio_scene==0){intro_audio_scene=1;intro_scene_ticks=0;}
   else if(introbar==4&&intro_audio_scene==1){intro_audio_scene=2;intro_scene_ticks=0;}
   else if(introbar==8&&intro_audio_scene==2){intro_audio_scene=3;intro_scene_ticks=0;intro_audio_song=2;introbar=0;}
  }else if(introbar==2&&intro_audio_scene==3){intro_audio_scene=4;intro_scene_ticks=0;}
  else if(intro_audio_scene==4&&!(introbar&1)&&introfade<4){
   introfade++;
   if(introfade==1)NR42_REG=0;
   else if(introfade==2)NR32_REG=0;
   else if(introfade==3)NR22_REG=0;
   else NR12_REG=0;
  }
 }
 if(intro_audio_song==2)happymusic();else music();
}
void intro_audio_tick(void){
 uint16_t threshold;uint8_t position;
 if(!intro_audio_running)return;
 intro_audio_ticks++;if(intro_scene_ticks!=65535)intro_scene_ticks++;
 /* Keep the final effects running indefinitely, without replaying the reveal.
    16384 ticks is an exact multiple of the raster, pulse and blink periods. */
 if(intro_audio_scene==4&&intro_scene_ticks==65535)intro_scene_ticks-=16384;
 /* 256 Hz hardware time: exact mean BPM, independent of LCD and drawing. */
 if(intro_audio_scene==2){
  position=(((introbar-4)<<4)+introstep-1)&63;
  audio_clock+=train_rate[position];
  threshold=(introstep&1)?15360+train_swing[position]:15360-train_swing[position];
 }else{
  audio_clock+=intro_audio_song==2?512:380;
  threshold=intro_audio_song==2?15360:(introstep&1)?18432:12288;
 }
 if(audio_clock>=threshold){audio_clock-=threshold;intro_audio_step();}
}
static void audio_start(void){
 disable_interrupts();TAC_REG=0;
 intro_audio_song=intro_audio_scene=introfade=0;intro_audio_ticks=intro_scene_ticks=audio_clock=0;
 intro_audio_running=1;add_TIM(intro_timer);TMA_REG=TIMA_REG=240;
 IF_REG&=~TIM_IFLAG;set_interrupts(VBL_IFLAG|TIM_IFLAG);TAC_REG=4;enable_interrupts();
}
static void audio_stop(void){
 disable_interrupts();intro_audio_running=0;TAC_REG=0;
 remove_TIM(intro_timer);IF_REG&=~TIM_IFLAG;set_interrupts(VBL_IFLAG);enable_interrupts();
}
static void intro_map(uint8_t x,uint8_t y,uint8_t width,uint8_t height,const uint8_t *map){
 uint8_t row,col,buf[20];for(row=0;row<height;row++){for(col=0;col<width;col++)buf[col]=(*map++)+zoombuffer;set_bkg_tiles(x,y+row,width,1,buf);}
}
static void face(uint8_t mood){
 uint8_t row;
 for(row=4;row<9;row++){
  intro_map(4,row,4,1,intro_faces[mood]+(uint16_t)row*20+4);
  intro_map(12,row,4,1,intro_faces[mood]+(uint16_t)row*20+12);
 }
 for(row=8;row<14;row++)intro_map(6,row,8,1,intro_faces[mood]+(uint16_t)row*20+6);
}
static void overlay(uint8_t stage,uint8_t prompt){
 uint8_t base=zoombuffer^128;
 if(prompt){set_bkg_data(base+60,20,intro_prompt[stage]);intro_map(0,16,20,1,intro_prompt_map);}
 else{
  if(stage==3){uint8_t i;static const uint8_t blank[16]={0};for(i=0;i<60;i++)set_bkg_data(base+i,1,blank);}
  else set_bkg_data(base,60,intro_logo[stage]);
  intro_map(0,0,20,3,intro_logo_map);
 }
}
void intro_run(void) BANKED {
 uint8_t mood=255,next,i,pad,previous=joypad(),logophase=255,promptphase=255,rasterphase=255,faceinit=0,lastzoom=255,cracks=0,damage_started=0,scene;uint16_t reveal,sceneclock,lasttick,delta,ticks,effectclock=0,fuzz=0xace1;
 static const uint8_t basswave[16]={0x89,0xab,0xcd,0xee,0xff,0xee,0xdc,0xba,0x98,0x65,0x43,0x21,0x00,0x12,0x34,0x67};
 introactive=1;introready=introbar=introstep=zoombuffer=0;introframe=0;
 DISPLAY_OFF;HIDE_SPRITES;BGP_REG=0xe4;
 if(_cpu==CGB_TYPE){set_bkg_palette_entry(0,0,RGB(22,30,23));set_bkg_palette_entry(0,3,RGB(2,7,6));}
 NR52_REG=0x80;NR50_REG=0x55;NR51_REG=0xf7;NR10_REG=0;NR30_REG=0;
 NR12_REG=NR22_REG=NR32_REG=NR42_REG=0;
 for(i=0;i<16;i++)REG(0xff30+i)=basswave[i];
 cinema_frame(0);music();audio_start();lasttick=sys_time;
 while(1){
  wait_vbl_done();delta=sys_time-lasttick;lasttick=sys_time;if(!delta)delta=1;
  introframe+=delta;
  pad=joypad();if(pad&J_START)break;
  __critical {scene=intro_audio_scene;ticks=intro_scene_ticks;}
  if(scene<4){cinema_frame(((uint16_t)scene<<10)+(scene==2?ticks>>2:ticks>>1));previous=joypad();continue;}
  sceneclock=((uint32_t)ticks*15)>>6;
  if(sceneclock<=72){
   HIDE_WIN;HIDE_SPRITES;
   next=sceneclock?(sceneclock-1)>>2:0;
   if(next!=lastzoom){if(next<6)zoom0(next);else if(next<12)zoom1(next-6);else zoom2(next-12);lastzoom=next;}
   previous=joypad();continue;
  }
  if(!faceinit){
   faceinit=1;
   zoombuffer^=128;
   /* Signed tile IDs wrap at 128; individual uploads keep the maps intact. */
   for(i=0;i<INTRO_TILES;i++)set_bkg_data(zoombuffer+i,1,intro_tiles+(uint16_t)i*16);
   intro_map(0,0,20,18,intro_faces[0]);
  }
  if(effectclock<600){BGP_REG=0xe4;SCX_REG=SCY_REG=0;}
  reveal=sceneclock-72;
  if(reveal<60)next=0;else if(reveal<68)next=1;
  else if(reveal<130)next=2;else if(reveal<200)next=6;
  else if(reveal<270)next=3;else if(reveal<345)next=5;
  else if(reveal<410)next=4;else{static const uint8_t expressions[8]={0,2,6,3,5,4,0,1};next=expressions[(reveal/90)&7];}
  if(next!=mood){if(!cracks)face(next);mood=next;if(cracks)intro_cracks(cracks,mood,0);}
  /* Local face time: logo starts at 1 s, prompt starts at 1.5 s. */
  reveal=sceneclock-72;
  if(reveal>=60){
   if(reveal<84){next=(reveal-60)/8;if(next>2)next=2;
    if(next!=logophase){overlay(next,0);logophase=next;}
   }else if(reveal>=180){
    next=reveal<188?2:reveal<196?1:reveal<204?0:3;
    if(next!=logophase){overlay(next,0);logophase=next;}
   }else{
    next=((reveal-84)/8)&7;
    if(next!=rasterphase){intro_demo(next,zoombuffer^128);rasterphase=next;}
   }
  }
  if(reveal>=90){
   /* Two one-second pulses with slow fades, then permanent silence. */
   uint16_t phase=(reveal-90)%360;
   next=reveal>=510?3:phase<12?0:phase<24?1:phase<36?2:phase<48?1:phase<60?0:3;
   if(next!=promptphase){overlay(next,1);promptphase=next;}
   if(next==2)introready=1;
  }
  /* Wait five seconds after the score ends, then ten seconds between faults. */
  if(!damage_started){
   if(introfade<4)effectclock=0;
   else{effectclock+=delta;if(effectclock>=300){damage_started=1;effectclock=600;}}
  }else effectclock+=delta;
  if(effectclock>=618){
   effectclock=0;SCX_REG=SCY_REG=0;BGP_REG=0xe4;NR12_REG=NR22_REG=NR42_REG=0;NR10_REG=0;NR51_REG=0xf7;
   if(_cpu==CGB_TYPE){set_bkg_palette_entry(0,0,RGB(22,30,23));set_bkg_palette_entry(0,3,RGB(2,7,6));}
   if(cracks<10)cracks++;
   intro_cracks(cracks,mood,1);
  }else if(effectclock>=600){
   uint8_t fault[20];
   SCX_REG=(effectclock&1)?12:244;SCY_REG=(effectclock&2)?4:252;
   BGP_REG=(effectclock&2)?0x1b:0xe4;
   if(_cpu==CGB_TYPE){set_bkg_palette_entry(0,0,(effectclock&2)?RGB(31,0,7):RGB(0,31,31));set_bkg_palette_entry(0,3,RGB(31,31,31));}
   for(i=0;i<20;i++)fault[i]=zoombuffer+(i*7+(effectclock&7)*13)%INTRO_TILES;
   set_bkg_tiles(0,3,20,1,fault);set_bkg_tiles(0,10,20,1,fault);
   if(effectclock-delta<600||!(effectclock%3)){
    fuzz=(fuzz>>1)^((fuzz&1)?0xb400:0);
    NR51_REG=0xff;
    NR10_REG=0x10|((fuzz>>5)&0x6f);NR11_REG=(fuzz&3)<<6;NR12_REG=0xa1;
    NR13_REG=fuzz;NR14_REG=0x80|((fuzz>>8)&7);
    NR21_REG=((fuzz>>2)&3)<<6;NR22_REG=0x81;NR23_REG=fuzz>>4;NR24_REG=0x80|((fuzz>>11)&7);
    NR41_REG=0;NR42_REG=0xc1|((fuzz>>8)&0x30);NR43_REG=(fuzz>>3)&0x7f;NR44_REG=0x80;
   }
  }

  pad=joypad();if(introready&&(pad&J_START)&&!(previous&J_START))break;previous=pad;
  /* Saturate scene time after the reveal; music and blink keep looping. */
  if(introframe==5000)introframe=2200;
 }
 audio_stop();DISPLAY_OFF;HIDE_WIN;NR52_REG=0;introactive=0;
}

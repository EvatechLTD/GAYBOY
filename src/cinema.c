#pragma bank 28
#include "api.h"
void cinema0(uint8_t line,uint8_t count,uint8_t load) BANKED;
void cinema1(uint8_t line,uint8_t count,uint8_t load) BANKED;
void cinema2(uint8_t line,uint8_t count,uint8_t load) BANKED;
void cinema5(uint8_t line,uint8_t count,uint8_t load) BANKED;
void cinema1_motion(uint8_t step,uint8_t phase) BANKED;
void cinema0_motion(uint8_t frame) BANKED;
void cinema0_react(uint8_t emotion) BANKED;
void cinema2_motion(uint8_t frame) BANKED;
void cinema2_ride(uint16_t frame) BANKED;
void cinema5_motion(uint8_t frame) BANKED;
void cinema5_stars(uint8_t frame) BANKED;
extern uint8_t introstep,introbar;
static void train_frame(uint16_t time){
 uint8_t variant;static uint16_t previous;static uint8_t previousvariant=255;
 if(time<4||time-previous>=2){
  previous=time;
  if(time<240)variant=0;
  else if(time<400)variant=1+((time>>1)&1);
  else if(time<480)variant=3+(time-400)/12;
  else variant=9;
  if(variant!=previousvariant){cinema2_motion(variant);previousvariant=variant;}
 }
 cinema2_ride(time);
}
static uint8_t current_scene=255,caption_line=255,caption_count=255,current_emotion=255;
static void caption(uint8_t scene,uint16_t time){
 uint8_t line=0,limit,count;uint16_t letters=0;
 if(scene==3){limit=0;} /* Caption-free living handheld close-up. */
 else if(scene==2&&introbar>=6){line=1;limit=28;letters=28;}
 else{
  limit=scene==0?19:scene==1?27:22;
  if(time>=(scene==2?30:40))letters=(time-(scene==2?30:40))/3;
 }
 count=letters>limit?limit:letters;
 if(line==caption_line&&count==caption_count)return;
 /* Commit before the banked call; a completed line holds until its next card. */
 caption_line=line;caption_count=count;
 if(scene==0)cinema0(0,count,0);else if(scene==1)cinema1(0,count,0);else if(scene==2)cinema2(line,count,0);else cinema5(line,count,0);
}
/* Text, picture animation and sound have separate clocks and state. */
void cinema_frame(uint16_t frame) BANKED {
 uint8_t scene,emotion;uint16_t time;
 /* The audio timer supplies two-bar scene IDs and a local 128 Hz art clock. */
 scene=frame>>10;time=frame&1023;
 if(scene!=current_scene){
  current_scene=scene;caption_line=caption_count=0;
  if(scene==0)cinema0(0,0,1);else if(scene==1)cinema1(0,0,1);else if(scene==2)cinema2(0,0,1);else cinema5(0,0,1);
 }
 caption(scene,time);
 if(scene==0){
  if(!(frame&7))cinema0_motion((frame>>3)&3);
  emotion=time<190?0:time<400?1:2;
  if(emotion!=current_emotion){current_emotion=emotion;cinema0_react(emotion);}
 }
 if(scene==1&&!(frame&3))cinema1_motion((introstep+15)&15,frame>>2);
 if(scene==2)train_frame(time);
 if(scene==3&&!(time&7)){cinema5_motion(time%140<12);cinema5_stars(time);}
}

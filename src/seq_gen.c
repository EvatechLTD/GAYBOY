#pragma bank 61
#include "api.h"
#include "ui_fields.h"
#include "drum_rows.h"
#include "mixer_drum_names.h"
#include "gen_music.h"
#include "resident.h"
void seq_track_view(void) BANKED;
extern uint8_t seqbeats,seqdenom;
extern void mixer_pattern_changed(void) BANKED;
extern void seq_clear_release(uint8_t track) BANKED;
/* Preview owns the existing track clipboard. Settings occupy renderer scratch. */
uint8_t genopen;
__at (0xAFF0) uint8_t genrow;
__at (0xAFF1) uint8_t genpreview;
__at (0xAFF2) uint8_t generror;
__at (0xAFF3) uint8_t gentype;
__at (0xAFF4) uint8_t genprogression;
__at (0xAFF5) uint8_t genroot;
__at (0xAFF6) uint8_t genscale;
__at (0xAFF7) uint8_t genhits;
__at (0xAFF8) uint8_t gencontour;
__at (0xAFF9) uint8_t genregister;
__at (0xAFFA) uint16_t genseed;
__at (0xAFFC) uint8_t genrhythm;
__at (0xAFFD) uint8_t genlength;
__at (0xAFFE) uint8_t genvariation;
__at (0xAFFF) uint8_t genchange;
uint8_t genvoice,genrotation,genaccent,genintro;
static const char *rhythms[]={"QUARTER","EIGHTH","SIXTEENTH","OFFBEAT","TRESILLO","BACKBEAT","EUCLID","CHANGES"};
static const char *lengths[]={"1/16","1/8","1/4","1/2","1/1","TO NEXT"};
static const char *variations[]={"NONE","LOW","MEDIUM","HIGH"};
static void gen_text(uint8_t x,uint8_t y,const char *s,uint8_t inv){while(*s&&x<20)canvas[(uint16_t)y*20+x++]=*s++-32+(inv?96:0);}
static void gen_number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits,uint8_t inv){uint16_t place=digits==3?100:10;uint8_t d;while(digits--){d=(n/place)%10;canvas[(uint16_t)y*20+x++]=16+d+(inv?96:0);place/=10;}}
void gen_cancel(void) BANKED {if(!genopen)return;if(genpreview)seq_paste();genopen=genpreview=0;seq_dimensions();seq_track_view();seqdrawvalid=0;dirty=1;}
static uint8_t gen_selected(const uint8_t *e){return e[0]<seqlength[seqtrack]&&(seqtrack!=6||e[1]==genvoice);}
static uint8_t candidate(uint16_t step,uint8_t voice,uint8_t *e){
 uint16_t bar=gen_bar_steps(seqbeats,seqdenom),phase=step%bar;uint8_t notes[3];
 if(!gen_rhythm_onset(step,bar,genrhythm,genhits,genrotation,genchange))return 0;
 e[0]=step;e[2]=seqdefaultvel[seqtrack];if(!e[2])e[2]=100;
 if(seqtrack==6){
  e[1]=genvoice;
  if(genaccent&&((genaccent==1&&phase%(16/seqdenom))||(genaccent==2&&phase%4!=2)||(genaccent==3&&phase))){e[2]=(uint16_t)e[2]*3/4;if(!e[2])e[2]=1;}
  e[2]=gen_drum_variation(e[2],step,genvariation,genseed);
 }else if(gentype==3&&seqtrack<3){
  gen_chord_notes(step,bar,genprogression,genchange,genroot,genscale,genregister,gencontour,genvariation,genseed,notes);
  e[1]=notes[voice];
 }else e[1]=gen_pitch(step,bar,gentype,genprogression,genchange,gencontour,genvariation,genroot,genscale,genregister,genseed);
 e[3]=gen_duration(step,seqlength[seqtrack],bar,genrhythm,genhits,genrotation,genlength,genchange);return 1;
}
static void generate(void){uint16_t i,n,needed=0,removed=0;uint8_t e[4],busy,voice,voices=seqtrack<3&&gentype==3?3:1;
 n=seq_event_count(seqtrack);
 for(i=0;i<n;i++){seq_event_get(seqtrack,i,e);if(gen_selected(e))removed++;mixfill();}
 for(i=0;i<seqlength[seqtrack];i++)needed+=candidate(i,0,e)*voices;
 if(seq_event_total()-removed+needed>RESIDENT_NOTES){generror=1;return;}
 busy=seqservicing;seqservicing=1;seq_clear_release(seqtrack);
 i=n;while(i){seq_event_get(seqtrack,--i,e);if(gen_selected(e))seq_event_erase(seqtrack,i);mixfill();}
 for(i=0;i<seqlength[seqtrack];i++){for(voice=0;voice<voices;voice++)if(candidate(i,voice,e))seq_event_put(seqtrack,SEQ_EVENT_APPEND,e);mixfill();}
 if(voices==3)evalpatch[seqtrack][EV_CHORD_HISTORY]=1;
 seqservicing=busy;if(seqplaying)seq_frame();genpreview=1;generror=0;seqdrawvalid=0;mixer_pattern_changed();
}
void gen_open(void) BANKED {
 if(seq_event_total()>RESIDENT_NOTES){seqeventfull=1;dirty=1;return;}
 /* drumrow is the highlighted name even while velocity sliders are hidden. */
 genvoice=DRUM_VOICE_ROW(drumrow)+1;
 seqgrouptrack=255;seq_copy();gentype=genprogression=0;genroot=9;genscale=1;
 genhits=5;gencontour=3;genregister=3;genseed=1;genrhythm=1;genlength=0;
 genchange=2;genvariation=genrotation=genaccent=0;
 genopen=genintro=1;genrow=generror=genpreview=0;generate();dirty=1;
}
static uint8_t apply_row(void){return seqtrack==6?7:12;}
static void apply_current(void){if(!genpreview||generror)return;genopen=genpreview=0;page=8;seqhead=seqfocus=0;seq_dimensions();seq_track_view();seqdrawvalid=0;}
void gen_input(uint8_t p,uint8_t edge) BANKED {
 int16_t value;uint8_t *cell=0,max=0,min=0,changed=0,row=genrow,k=apply_row();
 if(!edge)return;
 if(edge&J_SELECT){gen_cancel();return;}
 if(!(p&(J_A|J_B))){if(edge&(J_UP|J_DOWN))genintro=0;if(edge&J_UP)genrow=genrow?genrow-1:k+1;if(edge&J_DOWN)genrow=(genrow+1)%(k+2);}
 row=genrow;
 if(seqtrack==6){switch(row){
 case 0:cell=&genrhythm;max=6;break;case 1:cell=&genlength;max=5;break;
 case 2:cell=&genhits;min=0;max=gen_bar_steps(seqbeats,seqdenom)>255?255:gen_bar_steps(seqbeats,seqdenom);break;
 case 3:cell=&genrotation;max=gen_bar_steps(seqbeats,seqdenom)-1;break;
 case 4:cell=&genaccent;max=3;break;case 5:cell=&genvariation;max=3;break;
 }}else {switch(row){
 case 0:cell=&gentype;max=seqtrack<3?3:2;break;case 1:cell=&genroot;max=11;break;
 case 2:cell=&genscale;max=3;break;case 3:cell=&genprogression;max=3;break;
 case 4:cell=&genchange;max=4;break;case 5:cell=&genrhythm;max=7;break;
 case 6:cell=&genlength;max=5;break;case 7:cell=&gencontour;max=gentype==3?2:4;break;
 case 8:cell=&genvariation;max=3;break;case 9:cell=&genregister;max=7;break;
 case 10:cell=&genhits;max=gen_bar_steps(seqbeats,seqdenom)>255?255:gen_bar_steps(seqbeats,seqdenom);break;
 }}
 /* Disabled fields explain their dependency instead of editing an unseen value. */
 if(cell==&genhits&&genrhythm!=6)cell=0;
 if((p&(J_A|J_B))&&(edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN))){
  value=edge&(J_UP|J_RIGHT)?1:-1;
  if(cell){value+=*cell;*cell=value<min?max:value>max?min:value;changed=1;}
  else if(row==k-1&&((seqtrack!=6&&gentype!=3)||genvariation)){genseed=(genseed+1000+value)%1000;changed=1;}
 }
 if(changed){
  genintro=0;
  /* A held chord gives the instrument arp time to visit all three notes. */
  if(cell==&gentype&&gentype==3){genrhythm=7;genlength=5;gencontour=0;}
  generate();
 }
 if(edge&(J_A|J_B|J_START)){if(row==k)apply_current();else if(row==k+1)gen_cancel();}
 dirty=1;
}
/* Show controls once at entry, then explain the highlighted field. */
static void gen_help(void){
 const char *tip=0,*detail=0;
 uint8_t k=apply_row();
 if(genintro)tip="A/B EDIT SELECT BACK";
 else if(genrow==k)tip="APPLY THESE NOTES";
 else if(genrow==k+1)tip="RESTORE ENTRY NOTES";
 else if(seqtrack==6){switch(genrow){
  case 0:tip="WHERE HITS START";break;
  case 1:tip="MAX HIT HOLD TIME";detail="STOPS AT NEXT ATTACK";break;
  case 2:tip=genrhythm==6?"HITS IN EACH BAR":"SELECT EUCLID FIRST";break;
  case 3:tip="SHIFT RHYTHM STEPS";break;
  case 4:tip="CHOOSE STRONG HITS";break;
  case 5:tip="VARY HIT STRENGTH";break;
  case 6:tip=genvariation?"REPEATABLE VARIATION":"ENABLE VARIATION";if(!genvariation)detail="SEED NEEDS VARIATION";break;
 }}else {switch(genrow){
  case 0:tip=gentype==3?"STACK THREE NOTES":gentype==2?"WRITE AN ARP LINE":gentype==1?"FOLLOW CHORD ROOTS":"MELODY OVER CHORDS";if(gentype==3)detail="USE INSTRUMENT ARP";break;
  case 1:tip="TONIC / HOME NOTE";break;
  case 2:
   tip=genscale==0?"MAJOR SCALE NOTES":genscale==1?"NATURAL MINOR SCALE":genscale==2?"MINOR WITH RAISED 6":"FIVE MINOR NOTES";
   if(gentype==3&&genscale==2&&genprogression==0)detail="TONIC TRIAD IS SAME";
   if(gentype==3&&genscale==3)detail="PENT USES MIN CHORDS";
   break;
  case 3:tip="CHORD ROOT SEQUENCE";break;
  case 4:tip="TIME BETWEEN CHORDS";break;
  case 5:tip="WHERE NOTES START";break;
  case 6:tip="MAX NOTE HOLD TIME";detail="STOPS AT NEXT ATTACK";break;
  case 7:tip=gentype==3?"CHORD INVERSION":"SHAPE OF NOTE MOTION";break;
  case 8:tip=gentype==3?"VARY INVERSIONS":"VARY PHRASE ENDINGS";if(gentype!=3)detail="AFTER FIRST 2 BARS";break;
  case 9:tip="BASE PITCH REGISTER";break;
  case 10:tip=genrhythm==6?"HITS IN EACH BAR":"SELECT EUCLID FIRST";break;
  case 11:tip=gentype!=3||genvariation?"REPEATABLE VARIATION":"ENABLE VARIATION";if(gentype==3&&!genvariation)detail="SEED NEEDS VARIATION";break;
 }
 if(!genintro&&(genrow==3||genrow==4)&&genprogression&&seqlength[seqtrack]<=gen_chord_steps(gen_bar_steps(seqbeats,seqdenom),genchange))detail="CHORD RATE TOO LONG";
 }
 if(generror)detail="FULL: NO CHANGE";
 if(detail)gen_text(0,16,detail,0);
 if(tip)gen_text(0,17,tip,0);
}
void gen_render(void) BANKED {
 uint8_t i,k=apply_row();const char *s=0;
 const char *labels[]={"ROLE","KEY","SCALE","CHORDS","CHANGE","RHYTHM","LENGTH","CONTOUR","VARIATION","OCTAVE","HITS","SEED","APPLY","CANCEL"};
 const char *drumlabels[]={"RHYTHM","LENGTH","HITS","ROTATE","ACCENT","VARIATION","SEED","APPLY","CANCEL"};
 const char *roles[]={"MELODY","BASS","ARP LINE","CHORD"},*names[]={"MAJOR","MINOR","DORIAN","MIN PENT"};
 const char *roots[]={"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
 const char *progressions[]={"HOLD I","I-IV","I-V-VI-IV","II-V-I"};
 const char *changes[]={"1/4","1/2","1 BAR","2 BARS","4 BARS"};
 const char *contours[]={"REPEAT","RISE","FALL","ARCH","STEPS"};
 const char *voicings[]={"ROOT","1ST INV","2ND INV"};
 const char *accents[]={"FLAT","BEATS","OFFBEAT","BAR START"};
 const char *tracks[]={"PULSE1","PULSE2","WAVE","NOISE","MONO5","WAVE2","DRUM"};
 memset(canvas,0,360);memset(canvas,96,20);gen_text(0,0,"LIVE PREVIEW",1);
 gen_text(0,1,seqtrack==6?mixer_drum_name(drumkit,genvoice-1):tracks[seqtrack],0);
 for(i=0;i<k+2;i++){
  if(i>=k){field_text(11,i+2,9,i==k?"APPLY":"CANCEL",genrow==i,0);continue;}
  gen_text(0,i+2,seqtrack==6?drumlabels[i]:(gentype==3&&i==7)?"VOICING":labels[i],0);
  s=0;
  if(seqtrack==6){switch(i){
   case 0:s=rhythms[genrhythm];break;case 1:s=lengths[genlength];break;
   case 2:if(genrhythm==6)field_number(11,i+2,9,genhits,genrow==i);else s="--";break;
   case 3:field_number(11,i+2,9,genrotation,genrow==i);break;
   case 4:s=accents[genaccent];break;case 5:s=variations[genvariation];break;
   case 6:if(genvariation)field_number(11,i+2,9,genseed,genrow==i);else s="VAR OFF";break;
  }}else {switch(i){
   case 0:s=roles[gentype];break;case 1:s=roots[genroot];break;case 2:s=names[genscale];break;
   case 3:s=progressions[genprogression];break;case 4:s=changes[genchange];break;
   case 5:s=rhythms[genrhythm];break;case 6:s=lengths[genlength];break;
   case 7:s=gentype==3?voicings[gencontour]:contours[gencontour];break;case 8:s=variations[genvariation];break;
   case 9:field_number(11,i+2,9,genregister,genrow==i);break;
   case 10:if(genrhythm==6)field_number(11,i+2,9,genhits,genrow==i);else s="--";break;
   case 11:if(gentype!=3||genvariation)field_number(11,i+2,9,genseed,genrow==i);else s="VAR OFF";break;
  }}
  if(s)field_text(11,i+2,9,s,genrow==i,0);
 }
 gen_help();seqflushpending=1;HIDE_SPRITES;
}

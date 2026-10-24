#include "smooth_playback.h"
#include "song_mode.h"
extern __at (0xA433) uint8_t mixerfontdirty;
#include "user_presets.h"
#include "tones.h"
#include "seq_live_note.h"
/* Tile UI: 20x18, original 5x7 type, inverted chrome, differential VRAM writes. */
#include "ui_tiles.h"
void seq_audition_stop(void) BANKED;
extern uint8_t seqselectused,genrow;
void mixer_prepare_cancel(void) BANKED;
void mixer_view_capture(void) BANKED;
uint8_t canvas[360],visible[360],flushrow,page,cursor[8],edited[4],lastcc,lastvalue,midiage;
__at (0xACF8) uint8_t ui_transition_hidden;
__at (0xACF9) uint8_t ui_font_upload_pending;
__at (0xACFE) uint8_t ui_loading_active;
__at (0xACFF) uint8_t ui_loading_step;
/* Never switch off the LCD or mask interrupts: only hide its background while
   a different page reuses the same tile graphics. Reveal after map publication. */
void ui_transition_begin(void) BANKED {if(!ui_transition_hidden){HIDE_BKG;HIDE_SPRITES;ui_transition_hidden=1;}}
uint8_t sticky_start;
uint8_t auditionvoice=255,navopen,navchoice,navcategory,navblocked,repeataxis,repeatsteps,monoedit;
uint8_t lastseqtrack=6;
uint16_t repeatstart,repeatlast;
uint8_t livepitch[4],liveduty[4],tablefield;
uint8_t graytiles[64];
/* MONOSYNTH preview and deferred font uploads are page-local scratch. The
   roll and incoming pattern cache already own this region on other pages.
   ui_render publishes deferred fonts in the same iteration's ui_flush,
   before another preparation quantum can reuse it. Keep this out of WRAM
   so engines retain 1280 bytes of headroom below their fixed lookup tables. */
__at (0xB000) uint8_t wavepixels[1280];
uint8_t previewshape=255,previewwidth=255;

const char graychars[]="0123456789ACDEIKLNRSTUY";
const char * const expnames[]={"ENGINE","WAVE ADSR","WAVE ATTACK","WAVE DECAY","WAVE SUSTAIN","WAVE RELEASE","BRIGHT","RES","FLT MOD","FLT SRC","PHASE DEPTH","PHASE RATE","DETUNE","CHR DEPTH","CHR RATE","NOTE DELAY","ECHO LEVEL","ECHO COUNT","ECHO PAN","ZOMBIE ADSR","CTRL RATE","DSP CUTOFF","DSP RES","AUDIO DELAY","DELAY MIX","FEEDBACK","SLEW"};

const char * const voices[]={"PULSE1","PULSE2","WAVE1","NOISE"};
const char * const pages[]={"LIVE","TONE","MOD","BANK","CC","TABLE","FX","MONOSYNTH","SEQUENCER","MASTURBATE","SEQ SETTINGS","P1","P2","WAVE1","WAVE2","NOISE","SETTINGS","DRUMSYNTH","MIXER","LOAD PATTERN","SAVE PATTERN","COPY","PASTE","KITS","LOAD SONG","SAVE SONG","CLEAR PATTERN","SYNC"};
const uint8_t channelmenu[5]={11,12,13,15,14};
const uint8_t menuchannel[5]={0,1,2,4,3};
const char * const mononames[]={"OCTAVE","LEVEL","ATTACK","DECAY","PW","WAVEFORM","PAN"};
const char * const sourcenames[]={"ATTACK","DECAY","SUSTAIN","RELEASE","LFO WAVE","LFO RATE","BEND","LFO MODE","","ARP RATE","VELOCITY"};
const char * const lfonames[]={"TRIANGLE","SAW","SQUARE","S/H","SINE"};
const char * const arpnames[]={"OFF","MAJOR","MINOR","FIFTH","OCTAVE"};
const char * const dutynames[]={"OFF","CYCLE","ALTERNATE","ACCENT"};
const char * const modnames[]={"SPEED","ARPEGGIO","DUTY SEQ","VIBRATO","SLIDE","GATE","TABLE MODE","TABLE LEN"};
const char * const paramnames[]={"DUTY","VOLUME","ENV DIR","ENV RATE","SWP TIME","SWP DIR","SWP SHIFT","LENGTH","LENGTH ON","MUTE","MASTER R","VIN R","MASTER L","VIN L","WAVE SHAPE","WAVE LEVEL","WAVE LENGTH","WAVE DAC OFF","CLOCK","WIDTH","NOISE DIV","PAN","DAC OFF","SUSTAIN","STOP","BEND"};
const uint8_t toneids[3][20]={
 {0,1,2,3,4,5,6,7,8,9,21,22,25,10,12,11,13},
 {0,1,2,3,7,8,9,21,22,25,10,12,11,13},
 {14,15,16,17,8,9,21,25,10,12,11,13}};
const uint8_t tonecount[]={17,14,12};
const uint8_t modmax[]={15,4,3,7,16,63};
const char * const tablenames[]={"OFF","LOOP","ONCE","NOTE"};
/* Yield between UI strings so audio macros and incoming MIDI never wait for a page. */


void textat(uint8_t x,uint8_t y,const char *t,uint8_t inverse){uint8_t c,*dst=canvas+(uint16_t)y*20+x;if(!monomode)service();while(*t&&x<20){if(!monomode&&!(x&3))mixfill();c=*t++;if(c>='a'&&c<='z')c-=32;if(c<32||c>127)c='?';*dst++=c-32+(inverse?96:0);x++;}}
const uint16_t decimalplaces[]={1,10,100,1000,10000};
void number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits,uint8_t inverse){uint8_t v,*dst=canvas+(uint16_t)y*20+x;uint16_t place;if(!monomode)service();x=16+(inverse?96:0);while(digits>1){place=decimalplaces[--digits];v=0;while(n>=place){n-=place;v++;}*dst++=x+v;}*dst=x+n;}
void band(uint8_t y){memset(canvas+y*20,96,20);}
void line(uint8_t y){memset(canvas+y*20,201,20);}
void bar(uint8_t x,uint8_t y,uint8_t value,uint8_t max,uint8_t width){uint8_t i,n;mixfill();n=max?(uint16_t)value*width/max:0;for(i=0;i<width;i++)canvas[y*20+x+i]=i<n?200:193;}
uint8_t valueof(uint8_t id){if(id==10)return master&7;if(id==12)return(master>>4)&7;if(id==11)return !!(vin&8);if(id==13)return !!(vin&128);if(id==21)return ((route>>selected)&1)|(((route>>(selected+4))&1)<<1);if(id==23)return sustain[selected];return param[selected][id];}
void modvalue(uint8_t x,uint8_t y,uint8_t i,uint8_t inv){uint8_t v;if(i==6){textat(x,y,tablenames[tablemode[selected]],inv);return;}if(i==7){number(x,y,tablelen[selected],1,inv);return;}v=mods[selected][i];if(i==1)textat(x,y,arpnames[v%5],inv);else if(i==2)textat(x,y,dutynames[v&3],inv);else if(!v)textat(x,y,i==0?"1 FR":"OFF",inv);else if(i==4){if(v==8)textat(x,y,"HOLD",inv);else{ textat(x,y,v<8?"-":"+",inv);number(x+1,y,v<8?8-v:v-8,2,inv);}}else {number(x,y,v,2,inv);if(i==0||i==5)textat(x+3,y,"FR",inv);}}
const char *ccname(uint8_t n){if(n>=41&&n<=66)return paramnames[n-41];if(n>=70&&n<=101)return "WAVE SAMPLE";if(n>=112&&n<=119)return modnames[n-112];switch(n){case 67:return "FREQ LO7";case 68:return "FREQ HI4";case 69:return "RETRIGGER";case 102:return "PRESET";case 103:return "PANIC";case 104:return "MASTER R";case 105:return "MASTER L";case 106:return "VIN BOTH";case 107:return "APU POWER";case 108:return "PULSE1 PAN";case 109:return "PULSE2 PAN";case 110:return "WAVE PAN";case 111:return "NOISE PAN";case 122:return "WAVE ENGINE";case 124:return "FAST RATE";case 125:return "MIX SHAPE A";case 126:return "MIX SHAPE B";case 120:return "SOUND OFF";case 123:return "NOTES OFF";}return "RESERVED";}
uint8_t mapcc(uint8_t i){return i<79?41+i:i==79?120:i==80?123:i==81?122:i==82?124:i==83?125:126;}
uint8_t previewtile(uint8_t i){return i<32?64+i:i<64?128+i:140+i;}
void wavepoint(uint8_t x,uint8_t y){uint16_t off=(uint16_t)(y>>3)*320+((uint16_t)(x>>3)<<4)+((y&7)<<1);wavepixels[off]|=0x80>>(x&7);}
uint8_t previewsample(uint8_t shape,uint8_t width,uint8_t i){uint8_t a;if(shape==3)return i<width?15:0;a=monowaves[shape][i>>1];return i&1?a&15:a>>4;}
void eval_preview_mono(void) BANKED {}
uint8_t ui_menu_allowed(uint8_t item) BANKED;
void ui_menu_step(int8_t delta) BANKED;
void finder_first(void) BANKED;
void finder_step(int8_t delta) BANKED;
void ui_menu(void) BANKED;
extern __at (0xA4EC) uint8_t theorytrack;
void ui_channel(uint8_t c){uint8_t i;auditionstop();if(monomode||polymode){panic();monomode=polymode=0;TAC_REG=waveengine?4:0;route=0;for(i=0;i<4;i++)if(!param[i][9]){if(param[i][21]&1)route|=1<<i;if(param[i][21]&2)route|=0x10<<i;}globals();}
 eval_row=eval_col=eval_tab=0;seqtrack=c==4?5:c;selected=c;choice=c<4?program[c]:0;cursor[1]=cursor[2]=cursor[4]=cursor[5]=cursor[6]=0;tablefield=0;
}
/* The pixel roll borrows preview, meter and grey-font tile slots. */
void ui_restore_seq_tiles(void){extern uint8_t seqtilesready;uint8_t tile,y,c,v,buf[16];uint16_t bit,packed;
 if(page==SONG_PAGE)*(uint8_t *)0xBEA0=0;
 /* Publish from the local buffer: wavepixels is shared with pattern/file
    preparation, which mixfill may run before a deferred upload. */
 ui_transition_begin();
 for(tile=220;tile<243;tile++){mixfill();c=graychars[tile-220]-32;for(y=0;y<8;y++){v=0;if(c<64&&y<7){bit=((uint16_t)c*7+y)*5;packed=ui_glyphs[bit>>3]|((uint16_t)ui_glyphs[(bit>>3)+1]<<8);v=((packed>>(bit&7))&31)<<2;}buf[y*2]=v;buf[y*2+1]=0;}ui_upload_tile(tile,buf,0);}
 for(tile=0;tile<12;tile++){mixfill();for(y=0;y<8;y++){v=tile<9?(y+tile>=8?126:0):tile==9?(y==3?255:0):y==1||y==6?126:y>1&&y<6?(tile==11?126:66):0;buf[y*2]=v;buf[y*2+1]=tile==9?0:v;}ui_upload_tile(192+tile,buf,0);}ui_font_upload_pending=0;mixerfontdirty=0;seqfontdirty=0;seqtilesready=0;previewshape=255;
}

void ui_render(void) BANKED {uint8_t i,n,start,inv;if(page>=18)seqflushpending=1;
 if(navopen||(page!=1&&page!=2&&page!=17)||tonepresetopen)*(uint8_t *)0xA475=0;
 if(!navopen)*(uint8_t *)0xA4D0=0;
 if(navopen){if(page==SONG_PAGE)*(uint8_t *)0xBEA0=0;HIDE_SPRITES;seqflushpending=1;ui_menu();return;}
 /* Song owns its borrowed tiles until exit, just like the pixel roll. */
 {if(page!=18&&mixerfontdirty){if(page!=8&&page!=SONG_PAGE)ui_restore_seq_tiles();mixerfontdirty=0;}}
 if(page!=8)HIDE_SPRITES;if(page!=8&&page!=SONG_PAGE&&seqfontdirty)ui_restore_seq_tiles();
 if(tonepresetopen){tone_preset_render();return;}
 if(page==SONG_PAGE){song_render();return;}if(page==26){clear_render();return;}if(page==23){kits_render();return;}if(page==28){mixer_settings_render();return;}if(page==27){sync_render();return;}
 if(page>=18){seqflushpending=1;mixer_render();return;}if(page==17||page==1||page==2){eval_render();return;}if(page==16){global_render();return;}if(page==10){seq_settings_render();return;}if(page==8){seq_render();return;}
 if(page==3){memset(canvas,0,360);band(0);textat(0,0,"PRESETS",1);start=program[selected]>2?program[selected]-2:0;if(start>93)start=93;for(i=0;i<7;i++){n=start+i;inv=n==program[selected];number(0,4+i,n+1,3,inv);textat(4,4+i,patch(n)->name,inv);}textat(0,17,"A/B+ARROWS LOAD",0);return;}
 native_render();
}
void ui_flush(void) BANKED {
 uint8_t tries,r,x,left,right,writes=0;
 if(page==18)mixer_tick();
 if(page==8||page>=18){if(!seqflushpending)return;seqflushpending=0;}
 if(page==8)roll_commit();
 if(ui_font_upload_pending){uint8_t tile;ui_transition_begin();
  for(tile=0;tile<23;tile++){ui_upload_tile(220+tile,wavepixels+(uint16_t)tile*16,0);mixfill();}
  for(tile=0;tile<12;tile++){ui_upload_tile(192+tile,wavepixels+368+(uint16_t)tile*16,0);mixfill();}
  ui_font_upload_pending=0;
 }
 if(page>=7||page==1||page==2||navopen||selected==4||ui_transition_hidden){
  ui_flush_spans();
  if(ui_transition_hidden){ui_transition_hidden=0;SHOW_BKG;}
  if(page==8&&!navopen)seq_playhead();
  return;
 }
 for(tries=0;tries<18&&writes<3;tries++){
  mixfill();r=flushrow;if(++flushrow==18)flushrow=0;left=20;right=0;
  for(x=0;x<20;x++){if(!(x&3))mixfill();if(canvas[r*20+x]!=visible[r*20+x]){if(left==20)left=x;right=x;}}
  if(left<20){ui_upload_map(0x9800U+(uint16_t)r*32+left,canvas+r*20+left,right-left+1);memcpy(visible+r*20+left,canvas+r*20+left,right-left+1);writes++;}
 }
}
void ui_loading_prepare(void) BANKED {if(seqfontdirty)ui_restore_seq_tiles();}
void auditionstop(void){if(auditionvoice<4)stop(auditionvoice);auditionvoice=255;}
void auditionstart(void){auditionstop();play(selected,60,127);auditionvoice=selected;}
void browse(int8_t d){int16_t n=(int16_t)program[selected]+d;if(n<0)n+=100;if(n>=100)n-=100;choice=n;if(polymode)polyload(n);else load(selected,n);edited[selected]=0;if(lastpad&J_B)auditionstart();}
void ui_action(uint8_t p,uint8_t edge) BANKED {if(page==SONG_PAGE&&(song_playing||((p&(J_START|J_SELECT))==(J_START|J_SELECT)))){song_input(p,edge);return;}if((p&(J_SELECT|J_START))==(J_SELECT|J_START)&&(edge&(J_SELECT|J_START))){navopen=0;navblocked=seqselectused=1;if(seqplaying)panic();else{panic();smooth_playback_start();}overflow=0;dirty=1;return;}
 if(((lastpad&J_A)&&!(p&J_A))||(edge&J_START)){seq_audition_stop();if(auditionvoice!=255)auditionstop();}
 if((lastpad&J_B)&&!(p&J_B)){seq_live_release();auditionstop();}
 if(!(p&J_START))navblocked=0;
 if(page==26){clear_input(edge);return;}
 if(navopen){
  if(edge&J_SELECT){navblocked=1;navopen=0;seqselectused=1;seqdrawvalid=0;dirty=1;return;}
  if(edge&J_LEFT){navcategory=navcategory?navcategory-1:4;finder_first();dirty=1;}
  if(edge&J_RIGHT){navcategory=(navcategory+1)%5;finder_first();dirty=1;}
  if(edge&J_UP){finder_step(-1);dirty=1;}if(edge&J_DOWN){finder_step(1);dirty=1;}
  if((edge&(J_A|J_B))||(sticky_start&&(edge&J_START))||(!sticky_start&&((lastpad&J_START)&&!(p&J_START)))){
   if(navchoice==255)return;
   navopen=0;seqdrawvalid=0;if(page==SONG_PAGE)ui_restore_seq_tiles();
   if(navchoice>=48&&navchoice<=50){drum_file_open(navchoice-48);dirty=1;return;}
   if(navchoice==54){page=SONG_PAGE;song_open();dirty=1;return;}
   if(navchoice==47){seqtrack=theorytrack;page=8;seqhead=seqfocus=0;gen_open();dirty=1;return;}
   if(navchoice==45){page=28;mixer_settings_open();dirty=1;return;}
   if(navchoice==21||navchoice==22||navchoice==26||navchoice>=35){if(!finder_edit_action(navchoice))navopen=1;dirty=1;return;}
   if(page==9&&navchoice!=9)noise_close();
   if(navchoice==8||navchoice>=28){uint8_t track=navchoice==8?lastseqtrack:navchoice-28;seqmode=track==4;seqtrack=track;if(track<4)ui_channel(track);page=8;seq_open();}
   else {if(navchoice>=11&&navchoice<=15){ui_channel(menuchannel[navchoice-11]);page=1;}else page=navchoice;
    eval_row=eval_col=0;if(page==1||page==17)eval_tab=0;else if(page==2)eval_tab=1;else if(page==6)eval_tab=2;
    if((page>=18&&page<=20)||page==24||page==25)mixer_open();if(page==7)monoenable();if(page==8||page==10){seq_open();if(page==10)seqfocus=1;}}
   dirty=1;
  }return;
 }
 if(tonepresetopen){tone_preset_input(edge);return;}
 if((edge&J_START)&&page==16&&pageconfig==2){global_input(p,edge);return;}
 if((edge&J_START)&&((page==8&&seqpopup)||((page==8||page==10)&&genopen&&genrow>=8))){seq_input(p,edge);return;}
 if((edge&J_START)&&!navblocked){theorytrack=page==8?seqtrack:255;if(page==8)lastseqtrack=seqtrack;gen_cancel();seqpopup=0;clear_capture();drum_file_capture_context();if(page==18){mixer_view_capture();mixer_prepare_cancel();}tonepresetopen=0;monoedit=0;pageconfig=0;navopen=1;navcategory=0;finder_first();dirty=1;return;}

 if(page==SONG_PAGE){song_input(p,edge);return;}if(page==28){mixer_settings_input(p,edge);return;}if(page==27){sync_ui_input(p,edge);return;}if(page==23){kits_input(p,edge);return;}if(page>=18){mixer_input(p,edge);return;}if(page==17){eval_input(p,edge);return;}if(page==16){global_input(p,edge);return;}if(page==8||page==10){seq_input(p,edge);return;}
 if(page==2||selected<4&&(page==1||page==6)){eval_input(p,edge);return;}if((!experimental_mode||(selected<2&&page==1))&&(page==0||page==1||page==4)){native_input(p,edge);return;}if(edge&J_SELECT){if(auditionvoice!=255)auditionstop();selected=polymode?(selected+1)%3:(selected+1)%3;choice=selected<4?program[selected]:0;cursor[1]=0;dirty=1;}
 if(selected==4)return;
 if(page==0||page==3){if(p&(J_A|J_B)){if(edge&J_UP)browse(1);if(edge&J_DOWN)browse(-1);if(edge&J_LEFT)browse(-10);if(edge&J_RIGHT)browse(10);}if((edge&(J_A|J_B))&&!(p&(J_UP|J_DOWN|J_LEFT|J_RIGHT))){page=page==0?3:0;dirty=1;}}
 else if(page==4){if(edge&J_UP)cursor[4]=cursor[4]?cursor[4]-1:78;if(edge&J_DOWN)cursor[4]=(cursor[4]+1)%79;if(edge&J_LEFT)cursor[4]=cursor[4]>=7?cursor[4]-7:0;if(edge&J_RIGHT)cursor[4]=cursor[4]<72?cursor[4]+7:78;dirty=1;}

 if((lastpad&J_B)&&!(p&(J_A|J_B)))auditionstop();
}

extern uint8_t seqrecordtrack;
void seq_record_finish(void) BANKED;

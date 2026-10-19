#include "tones.h"
/* Tile UI: 20x18, original 5x7 type, inverted chrome, differential VRAM writes. */
#include "ui_tiles.h"
void seq_audition_stop(void) BANKED;
void mixer_prepare_cancel(void) BANKED;
uint8_t canvas[360],visible[360],flushrow,page,cursor[8],edited[4],lastcc,lastvalue,midiage;
__at (0xACF8) uint8_t ui_transition_hidden;
__at (0xACF9) uint8_t ui_font_upload_pending;
__at (0xACFE) uint8_t ui_loading_active;
__at (0xACFF) uint8_t ui_loading_step;
/* Never switch off the LCD or mask interrupts: only hide its background while
   a different page reuses the same tile graphics. Reveal after map publication. */
void ui_transition_begin(void) BANKED {if(!ui_transition_hidden){HIDE_BKG;HIDE_SPRITES;ui_transition_hidden=1;}}
uint8_t auditionvoice=255,navopen,navchoice,navblocked,repeataxis,repeatsteps,monoedit;
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
const uint8_t sourcehi[]={255,255,64,255,4,32,24,1,1,32,1};
const char graychars[]="0123456789ACDEIKLNRSTUY";
const char * const expnames[]={"ENGINE","WAVE ADSR","WAVE ATTACK","WAVE DECAY","WAVE SUSTAIN","WAVE RELEASE","BRIGHTNESS","RESONANCE","FILTER MOD","FILTER SOURCE","PHASE DEPTH","PHASE RATE","DETUNE CENTS","CHORUS DEPTH","CHORUS RATE","NOTE DELAY","ECHO LEVEL","ECHO REPEATS","ECHO PAN","ZOMBIE ADSR","CONTROL RATE","DSP CUTOFF","DSP RESONANCE","AUDIO DELAY","DELAY MIX","FEEDBACK","SLEW"};
const uint8_t exphi[]={1,1,255,255,64,255,15,3,15,2,31,32,64,32,32,120,15,8,1,1,2,7,7,64,15,12,7};
const char * const voices[]={"PULSE1","PULSE2","WAVE1","NOISE"};
const char * const pages[]={"LIVE","TONE","MODULATION","BANK","CC","TABLE","FX","MONOSYNTH","SEQUENCER","MASTURBATE","SEQ SETTINGS","P1","P2","WAVE1","WAVE2","NOISE","GLOBAL SETTINGS","DRUMSYNTH","MIXER","LOAD PATTERN","SAVE PATTERN","COPY","PASTE","KITS","LOAD SONG","SAVE SONG","CLEAR PATTERN","SYNC"};
const uint8_t channelmenu[5]={11,12,13,15,14};
const uint8_t menuchannel[5]={0,1,2,4,3};
const char * const mononames[]={"OCTAVE","LEVEL","ATTACK","DECAY","PW","WAVEFORM","PAN"};
const char * const sourcenames[]={"ATTACK","DECAY","SUSTAIN","RELEASE","LFO WAVE","LFO RATE","BEND RANGE","LFO MODE","","ARP RATE","VELOCITY"};
const char * const lfonames[]={"TRIANGLE","SAW","SQUARE","S/H","SINE"};
const char * const arpnames[]={"OFF","MAJOR","MINOR","FIFTH","OCTAVE"};
const char * const dutynames[]={"OFF","CYCLE","ALTERNATE","ACCENT"};
const char * const modnames[]={"SPEED","ARPEGGIO","DUTY SEQ","VIBRATO","SLIDE","GATE","TABLE MODE","TABLE LEN"};
const char * const paramnames[]={"DUTY","VOLUME","ENV DIR","ENV RATE","SWEEP TIME","SWEEP DIR","SWEEP SHIFT","LENGTH","LENGTH ON","MUTE","MASTER R","VIN R","MASTER L","VIN L","WAVE SHAPE","WAVE LEVEL","WAVE LENGTH","WAVE DAC OFF","NOISE SHIFT","NOISE WIDTH","NOISE DIV","PAN","DAC OFF","SUSTAIN","STOP","BEND RANGE"};
const uint8_t toneids[4][20]={
 {0,1,2,3,4,5,6,7,8,9,21,22,25,10,12,11,13},
 {0,1,2,3,7,8,9,21,22,25,10,12,11,13},
 {14,15,16,17,8,9,21,25,10,12,11,13},
 {1,2,3,18,19,20,7,8,9,21,22,10,12,11,13}};
const uint8_t tonecount[]={17,14,12,15};
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
void mono_preview(void){uint8_t shape,width=16,i,j,x,y,previous,a;uint16_t off;const uint8_t duties[4]={4,8,16,24};
 if(monoosc<2){shape=3;width=duties[monovalue(monoosc,4)];}else if(monoosc==2||monoosc==4){shape=monovalue(2,5);width=monovalue(2,4);}else shape=monosource[4]==4?0:monosource[4]==0?1:monosource[4]==1?2:monosource[4]==2?3:31;
 if(shape!=3)width=16;for(i=0;i<80;i++)canvas[i]=previewtile(i);
 if(shape==previewshape&&width==previewwidth)return;previewshape=shape;previewwidth=width;memset(wavepixels,0,sizeof(wavepixels));a=previewsample(shape,width,31);previous=29-((a*7)>>2);x=0;
 for(i=0;i<32;i++){a=previewsample(shape,width,i);y=29-((a*7)>>2);for(j=0;j<5;j++,x++){while(previous<y){wavepoint(x,previous);previous++;}while(previous>y){wavepoint(x,previous);previous--;}wavepoint(x,y);}}
 for(off=0;off<1280;off+=2)wavepixels[off+1]=wavepixels[off];
 set_bkg_data(64,32,wavepixels);service();set_bkg_data(160,32,wavepixels+512);service();set_bkg_data(204,16,wavepixels+1024);
}
uint8_t mono_id(uint8_t id){if(id==(monoosc==2?5:6))return 7;if(monoosc==2&&id>=2)return id+2;return id==5?6:id;}
uint8_t ui_menu_allowed(uint8_t item) BANKED;
void ui_menu_step(int8_t delta) BANKED;
void ui_menu(void){uint8_t i,row,inv,start,rank=0,count=0,n=0;
 for(i=1;i<PAGE_COUNT;i++)if(ui_menu_allowed(i)){if(i<navchoice)rank++;count++;}
 start=rank>5?rank-5:0;if(count<=11)start=0;else if(start>count-11)start=count-11;
 for(i=3;i<16;i++)memset(canvas+i*20,0,20);band(3);textat(1,3,page<7?pages[channelmenu[selected]]:"CHOOSE PAGE",1);
 for(i=1;i<PAGE_COUNT;i++)if(ui_menu_allowed(i)){if(n>=start&&n<start+11){row=5+n-start;inv=navchoice==i;if(inv)band(row);textat(2,row,pages[i],inv);}n++;}
}
void ui_channel(uint8_t c){uint8_t i;auditionstop();if(monomode||polymode){panic();monomode=polymode=0;TAC_REG=waveengine?4:0;route=0;for(i=0;i<4;i++)if(!param[i][9]){if(param[i][21]&1)route|=1<<i;if(param[i][21]&2)route|=0x10<<i;}globals();}
 seqtrack=c==4?5:c;selected=c;choice=c<4?program[c]:0;cursor[1]=cursor[2]=cursor[4]=cursor[5]=cursor[6]=0;tablefield=0;
}
/* The pixel roll borrows preview, meter and grey-font tile slots. */
void ui_restore_seq_tiles(void){uint8_t tile,y,c,v,buf[16],defer=page>=18;uint16_t bit,packed;
 if(!defer)ui_transition_begin();
 for(tile=220;tile<243;tile++){mixfill();c=graychars[tile-220]-32;for(y=0;y<8;y++){v=0;if(c<64&&y<7){bit=((uint16_t)c*7+y)*5;packed=ui_glyphs[bit>>3]|((uint16_t)ui_glyphs[(bit>>3)+1]<<8);v=((packed>>(bit&7))&31)<<2;}buf[y*2]=v;buf[y*2+1]=0;}if(defer)memcpy(wavepixels+(uint16_t)(tile-220)*16,buf,16);else ui_upload_tile(tile,buf,0);}
 for(tile=0;tile<12;tile++){mixfill();for(y=0;y<8;y++){v=tile<9?(y+tile>=8?126:0):tile==9?(y==3?255:0):y==1||y==6?126:y>1&&y<6?(tile==11?126:66):0;buf[y*2]=v;buf[y*2+1]=tile==9?0:v;}if(defer)memcpy(wavepixels+368+(uint16_t)tile*16,buf,16);else ui_upload_tile(192+tile,buf,0);}ui_font_upload_pending=defer;seqfontdirty=0;previewshape=255;
}
void mono_render(void){uint8_t i,id,row,inv,n,start;memset(canvas,0,sizeof(canvas));mono_preview();
band(4);textat(0,4,monoosc==4?(expconfig[0]?"EXP DSP":"EXP NATIVE"):monoosc==3?"MOD":voices[monoosc],1);textat(monoosc==4?15:9,4,monoosc>=3?"VALUE":"VAL MOD PHS",1);
if(monoosc==4){start=cursor[7]>6?cursor[7]-6:0;if(start>EXP_COUNT-13)start=EXP_COUNT-13;for(i=0;i<13;i++){id=start+i;row=5+i;inv=cursor[7]==id;textat(0,row,expnames[id],0);number(17,row,expconfig[id],3,inv);if(inv)textat(16,row,monoedit||(lastpad&J_B)?"*":">",0);service();}}else if(monoosc==3){textat(0,5,monosource[8]?"[X] ADSR":"[ ] ADSR",cursor[7]==8);
 for(i=0;i<11;i++){if(i==8)continue;service();row=i>=9?i+5:6+i;inv=cursor[7]==i;n=monosource[i];textat(0,row,sourcenames[i],0);if(i==4)textat(10,row,lfonames[n],inv);else if(i==7)textat(13,row,n?"FREE":"KEY",inv);else number(13,row,n,3,inv);if(inv)textat(i==4?9:12,row,monoedit||(lastpad&J_B)?"*":">",0);}
 if(!monosource[8])for(i=120;i<200;i++){id=graytiles[canvas[i]%96];if(id)canvas[i]=id;}
}else for(i=0;i<(monoosc==2?6:7);i++){service();row=5+i;id=mono_id(i);inv=cursor[7]==i;textat(0,row,id==7?"RELEASE":mononames[id],0);n=id==7?0:monoset[monoosc][id];if(id==7){number(9,row,exprelease[monoosc],3,inv);if(inv)textat(8,row,monoedit||(lastpad&J_B)?"*":">",0);continue;}if(id==6)textat(10,row,n==0?"L":n==1?"C":"R",inv&&monocol==0);else number(9,row,n,3,inv&&monocol==0);number(13,row,monodepth[monoosc][id],2,inv&&monocol==1);number(17,row,monophase[monoosc][id],3,inv&&monocol==2);if(inv)textat(monocol==0?8:monocol==1?12:16,row,monoedit||(lastpad&J_B)?"*":">",0);}
 if(monoosc==2)textat(0,12,monowavenames[monovalue(2,5)],0);

 if(navopen)ui_menu();
}
void ui_render(void) BANKED {uint8_t i,j,start,id,row,inv,n,h;/* Keep the covered page frozen while navigating. */if(navopen){HIDE_SPRITES;seqflushpending=1;ui_menu();return;}if(page==26){if(seqfontdirty)ui_restore_seq_tiles();clear_render();return;}if(tonepresetopen&&page==1){tone_preset_render();if(navopen)ui_menu();return;}if(page==23){seqflushpending=1;HIDE_SPRITES;if(seqfontdirty)ui_restore_seq_tiles();kits_render();if(navopen)ui_menu();return;}if(page==27){seqflushpending=1;HIDE_SPRITES;if(seqfontdirty)ui_restore_seq_tiles();sync_render();if(navopen)ui_menu();return;}if(page>=18){seqflushpending=1;HIDE_SPRITES;if(seqfontdirty)ui_restore_seq_tiles();mixer_render();if(navopen)ui_menu();return;}if(page==17){HIDE_SPRITES;drum_synth_render();if(navopen)ui_menu();return;}if(page==16){HIDE_SPRITES;global_render();if(navopen)ui_menu();return;}if(page!=8){HIDE_SPRITES;}if(page!=8&&seqfontdirty)ui_restore_seq_tiles();if((!experimental_mode||(selected<2&&page==1))&&(page==0||page==1||page==4)){native_render();if(navopen)ui_menu();return;}if(selected==4&&page<7){w2_render();if(navopen)ui_menu();return;}if(page==7){mono_render();return;}if(page==9){noise_render();if(navopen)ui_menu();return;}if(page==10){seq_settings_render();if(navopen)ui_menu();return;}if(page==8){seq_render();if(navopen)ui_menu();return;}for(i=0;i<18;i++){memset(canvas+i*20,0,20);mixfill();}
 band(0);textat(0,0,page==0&&!polymode?pages[channelmenu[selected]]:pages[page],1);textat(13,0,overflow?"RX FULL":midiage?"MIDI IN":"READY",1);

 textat(0,2,polymode?(monomode?"MONO 3":waveengine==2?"POLY 4":waveengine==1?"FASTARP":"POLY 3"):voices[selected],0);textat(8,2,"CH",0);number(10,2,polymode?5:selected+1,1,0);
 for(i=0;i<4;i++){textat(13+i,2,active[i]?"*":".",i==selected);}
 number(0,3,program[selected]+1,3,0);textat(4,3,patch(program[selected])->name,0);if(edited[selected])textat(19,3,"*",0);line(4);
 if(page==0){
 textat(0,5,"VOICE  VEL      NOTE",0);
 for(i=0;i<4;i++){row=6+i;textat(0,row,voices[i],i==selected);bar(7,row,active[i]?velocity[i]:0,127,7);if(active[i]){number(16,row,livepitch[i],3,0);}else textat(16,row,"---",0);}
 textat(0,10,"TIMBRE / DUTY",0);number(16,10,selected<2?liveduty[selected]:selected==2?param[2][14]:param[3][18],2,0);
 for(i=0;i<20;i++){if(!(i&3))mixfill();if(selected<2)h=(i%8)<(liveduty[selected]==0?1:liveduty[selected]==2?4:liveduty[selected]==3?6:2)?8:1;else if(selected==2){n=(i*32/20);j=REG(0xff30+n/2);h=((n&1)?j&15:j>>4)/2+1;}else h=((i*13+phase[3]*7)^(i*3))%8+1;canvas[11*20+i]=192+h;}
 textat(0,12,"ARP",0);modvalue(4,12,1,0);textat(12,12,"VIB",0);number(17,12,mods[selected][3],2,0);
 textat(0,13,"SLIDE",0);modvalue(6,13,4,0);textat(12,13,"GATE",0);modvalue(17,13,5,0);
 }else if(page==1){start=cursor[1]<tonecount[selected]?cursor[1]/7*7:0;for(i=0;i<7&&start+i<tonecount[selected];i++){id=toneids[selected][start+i];row=5+i;inv=cursor[1]==start+i;if(inv)band(row);textat(0,row,inv?">":" ",inv);textat(1,row,!experimental_mode&&id==2?"ENVELOPE RISE":!experimental_mode&&id==3?"ENVELOPE PACE":paramnames[id],inv);number(15,row,valueof(id),3,inv);}id=toneids[selected][cursor[1]<tonecount[selected]?cursor[1]:0];textat(0,12,"CC",0);number(3,12,41+id,3,0);bar(8,12,valueof(id),limits[id],12);textat(0,13,(id>=1&&id<=3)||id==14?"LATCH NEXT NOTE":"L/R EDIT  A RESET",0);
 }else if(page==2){for(i=0;i<8;i++){row=5+i;inv=cursor[2]==i;if(inv)band(row);textat(0,row,inv?">":" ",inv);textat(1,row,modnames[i],inv);modvalue(11,row,i,inv);}textat(0,13,"CC",0);number(3,13,112+cursor[2],3,0);textat(8,13,"L/R EDIT",0);
 }else if(page==3){start=program[selected];start=start>2?start-2:0;if(start>93)start=93;for(i=0;i<7;i++){n=start+i;row=5+i;inv=n==program[selected];if(inv)band(row);number(0,row,n+1,3,inv);textat(4,row,patch(n)->name,inv);}textat(0,12,"SUGGEST",0);textat(8,12,voices[patch(program[selected])->voice],0);textat(0,13,"U/D LOAD L/R BANK",0);
 }else if(page==4){start=cursor[4]/7*7;for(i=0;i<7&&start+i<85;i++){n=mapcc(start+i);row=5+i;inv=start+i==cursor[4];if(inv)band(row);number(0,row,n,3,inv);textat(4,row,ccname(n),inv);if(n>=70&&n<=101)number(17,row,n-70,2,inv);}n=mapcc(cursor[4]);textat(0,12,"IN",0);number(3,12,lastcc,3,0);textat(7,12,">",0);number(9,12,lastvalue,3,0);textat(0,13,n==102?"PRESET: RAW 0-99":n>=112&&n<=117?"MOD: SCALED 0-127":"CC INPUT: 0-127",0);}else if(page==5){textat(0,5,"ST  TSP  SHAPE  PAN",0);for(i=0;i<8;i++){row=6+i;inv=cursor[5]==i;if(inv)band(row);textat(0,row,active[selected]&&tablerow[selected]==i?">":" ",inv);number(1,row,i+1,1,inv);n=tables[selected][i][0];textat(4,row,(int8_t)n<0?"-":"+",inv);number(5,row,(int8_t)n<0?-(int8_t)n:n,2,inv);number(10,row,tables[selected][i][1],2,inv);textat(16,row,tables[selected][i][2]==0?"--":tables[selected][i][2]==1?"R-":tables[selected][i][2]==2?"-L":"RL",inv);if(inv)textat(tablefield==0?3:tablefield==1?9:15,row,">",1);}}else if(page==6){fx_render();
 textat(0,10,"A/B",0);number(5,10,softnote[0],3,0);number(11,10,softnote[1],3,0);textat(0,11,"DROP",0);number(6,11,mixunderruns,5,0);textat(0,12,"BLOCK",0);number(6,12,engineblocks,5,0);textat(0,13,"EXPERIMENTAL WAVE",0);}

 line(14);textat(0,15,"SEQ",0);for(i=0;i<4;i++)canvas[15*20+4+i*2]=active[selected]&&((phase[selected]-1)&3)==i?203:202;
 if(active[selected]){textat(13,15,"AGE",0);number(17,15,age[selected],3,0);}else textat(13,15,"IDLE",0);
 if(page==1)textat(1,17,"LOAD PRESET",cursor[1]==tonecount[selected]);
 if(navopen)ui_menu();
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
 if(page>=7||selected==4||ui_transition_hidden){
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
void auditionstop(void){uint8_t c;if(auditionvoice==5){monocount=0;monorelease();}else if(auditionvoice==4){for(c=0;c<3;c++)stop(c);}else if(auditionvoice<4)stop(auditionvoice);auditionvoice=255;}
void auditionstart(void){auditionstop();if(monomode){monokeys[0]=60;monocount=1;monostart(60,110);auditionvoice=5;}else if(polymode){polynote(60,110);polynote(64,110);polynote(67,110);if(waveengine==2)polynote(72,110);auditionvoice=4;}else{play(selected,60,110);auditionvoice=selected;}}
void browse(int8_t d){int16_t n=(int16_t)program[selected]+d;if(n<0)n+=100;if(n>=100)n-=100;choice=n;if(polymode)polyload(n);else load(selected,n);edited[selected]=0;if(lastpad&J_B)auditionstart();}
void editvalue(int8_t delta,uint8_t reset){uint8_t id,v,max,encoded;if(page==2&&cursor[2]>=6){id=cursor[2];if(id==6)tablemode[selected]=reset?(patch(program[selected])->tconfig&3):(tablemode[selected]+(delta<0?3:1))&3;else {v=tablelen[selected];tablelen[selected]=reset?((patch(program[selected])->tconfig>>2)+1):delta<0?(v>1?v-1:8):(v<8?v+1:1);}}else if(page==2){id=cursor[2];v=mods[selected][id];max=modmax[id];v=reset?patch(program[selected])->mod[id]:delta<0?(v?v-1:max):(v>=max?0:v+1);mods[selected][id]=v;}else{id=toneids[selected][cursor[1]];v=valueof(id);max=limits[id];v=reset?patch(program[selected])->v[id]:delta<0?(v?v-1:max):(v>=max?0:v+1);encoded=((uint16_t)v*128+max)/(max+1);if(encoded>127)encoded=127;cc(selected,41+id,encoded);if(id==16)param[selected][id]=v;}edited[selected]=1;dirty=1;}
void mono_edit(int8_t delta){uint8_t c,id=mono_id(cursor[7]),*cell,lo=0,hi;int16_t value;
 if(monoosc==4){value=(int16_t)expconfig[cursor[7]]+delta;expconfig[cursor[7]]=value<0?0:value>exphi[cursor[7]]?exphi[cursor[7]]:value;exp_changed();return;}
 if(monoosc<3&&id==7){if(monocol)return;value=(int16_t)exprelease[monoosc]+delta;exprelease[monoosc]=value<0?0:value>255?255:value;if(monoosc==2)expconfig[5]=exprelease[2];exp_changed();return;}
 if(monoosc<3&&monocol==2){value=monophase[monoosc][id]+delta;if(value<0)value+=360;if(value>=360)value-=360;monophase[monoosc][id]=value;dirty=1;return;}
 if(monoosc==3){if(cursor[7]<4&&!monosource[8])return;cell=&monosource[cursor[7]];hi=sourcehi[cursor[7]];}
 else{cell=monocol?&monodepth[monoosc][id]:&monoset[monoosc][id];hi=monomax(monoosc,id)-(monocol?0:1);if(!monocol&&monoosc==2&&id==4){lo=1;hi=32;}}
 value=(int16_t)*cell+delta;*cell=value<lo?lo:value>hi?hi:value;
 if(monoosc==3&&cursor[7]==9)monorefresh();
 if(monoosc==3&&cursor[7]==6)for(c=0;c<3;c++){param[c][25]=*cell;bendupdate(c);}
 if(monoosc<3&&monodown){monoeffective[monoosc][id]=monovalue(monoosc,id);monorefresh();if(id==6)monoroute();else if(id!=0)monoapply(monoosc);}dirty=1;
}
void mono_input(uint8_t p,uint8_t edge){uint8_t cols=monoosc>=3||mono_id(cursor[7])==7?1:3;
 if(!(p&J_B)){
 if(edge&J_A){if(monoosc==3&&cursor[7]==8)monosource[8]^=1;else monoedit^=1;dirty=1;return;}
 if(p&J_SELECT){if(edge&J_LEFT)mono_page(-1,0);if(edge&J_RIGHT)mono_page(1,0);return;}
 if(edge&J_LEFT){if(monocol)monocol--;else if(monoedit){monocol=cols-1;cursor[7]=mono_row(-1);}else mono_page(-1,1);dirty=1;}
 if(edge&J_RIGHT){if(monocol+1<cols)monocol++;else if(monoedit){monocol=0;cursor[7]=mono_row(1);}else mono_page(1,1);dirty=1;}
 }
 if(monoosc>=3||mono_id(cursor[7])==7)monocol=0;
 if(p&J_B){if(edge&J_LEFT)mono_edit(-10);if(edge&J_RIGHT)mono_edit(10);}
 if(monoedit||(p&J_B)){if(edge&J_UP)mono_edit(1);if(edge&J_DOWN)mono_edit(-1);}
 else{if(edge&J_UP){cursor[7]=mono_row(-1);dirty=1;}if(edge&J_DOWN){cursor[7]=mono_row(1);dirty=1;}}
 if(monoosc>=3||mono_id(cursor[7])==7)monocol=0;
}
void ui_action(uint8_t p,uint8_t edge) BANKED {uint8_t max;if(experimental_mode&&page<8&&selected<4&&(p&J_SELECT)&&(edge&J_A)){panic();if(monomode){monomode=0;page=0;polyload(program[selected]);}else if(polymode)polymode=0;else{polyload(program[selected]);if(selected>2)selected=0;}dirty=1;return;}if((p&J_SELECT)&&(edge&J_START)){panic();overflow=0;navopen=0;navblocked=1;dirty=1;return;}
 if(((lastpad&J_A)&&!(p&J_A))||(edge&J_START))seq_audition_stop();
 if((lastpad&J_B)&&!(p&J_B))auditionstop();
 if(!(p&J_START))navblocked=0;
 if(page==26){clear_input(edge);return;}
 if((edge&J_START)&&!navblocked){gen_cancel();clear_capture();if(page==18)mixer_prepare_cancel();tonepresetopen=0;monoedit=0;navopen=1;navchoice=page==0&&!polymode?channelmenu[selected]:page;dirty=1;}
 if(navopen){if(edge&J_UP){ui_menu_step(-1);dirty=1;}if(edge&J_DOWN){ui_menu_step(1);dirty=1;}if(!(p&J_START)){if(navchoice==26){navopen=0;clear_open();return;}if(navchoice==21||navchoice==22){navopen=0;if(navchoice==21)seq_copy();else seq_paste();dirty=1;return;}if(page==9&&navchoice!=9)noise_close();if(navchoice>=11&&navchoice<=15){ui_channel(menuchannel[navchoice-11]);page=1;}else page=navchoice;navopen=0;if((page>=18&&page<=20)||page==24||page==25)mixer_open();if(page==7&&!monomode)monoenable();if(page==8||page==10){seq_open();if(page==10)seqfocus=1;}if(page==9&&!noisesaved)noise_open();dirty=1;}return;}
 if(page==1&&tonepresetopen){tone_preset_input(edge);return;}
 if(page==27){sync_input(edge);return;}if(page==23){kits_input(p,edge);return;}if(page>=18){mixer_input(p,edge);return;}if(page==17){drum_synth_input(p,edge);return;}if(page==16){global_input(p,edge);return;}if(page==7){mono_input(p,edge);return;}if(page==8||page==10){seq_input(p,edge);return;}if(page==9){noise_input(p,edge);return;}
 if((!experimental_mode||(selected<2&&page==1))&&(page==0||page==1||page==4)){native_input(p,edge);return;}if(edge&J_SELECT){if(auditionvoice!=255)auditionstop();selected=polymode?(selected+1)%3:(selected+1)%(experimental_mode?5:4);choice=selected<4?program[selected]:0;cursor[1]=0;dirty=1;}
 if(selected==4){w2_input(p,edge);return;}
 if(page==0||page==3){if(edge&J_UP)browse(-1);if(edge&J_DOWN)browse(1);if(edge&J_LEFT)browse(-10);if(edge&J_RIGHT)browse(10);if(edge&J_A){page=page==0?3:0;dirty=1;}}
 else{max=page==1?tonecount[selected]+1:page==2?8:page==5?8:page==6?5:85;if(edge&J_UP){cursor[page]=cursor[page]?cursor[page]-1:max-1;dirty=1;}if(edge&J_DOWN){cursor[page]=(cursor[page]+1)%max;dirty=1;}if(page==4){if(edge&J_LEFT){cursor[4]=cursor[4]>=7?cursor[4]-7:0;dirty=1;}if(edge&J_RIGHT){cursor[4]=cursor[4]<78?cursor[4]+7:84;dirty=1;}}else if(page==6){if(edge&J_LEFT)fx_edit(p&J_B?-10:-1);if(edge&J_RIGHT)fx_edit(p&J_B?10:1);if((edge&J_A)&&!cursor[6]&&selected<3){finepitch[selected]=0;updatepitch(selected);dirty=1;}}else if(page==5){int8_t *cell=&tables[selected][cursor[5]][tablefield],v=*cell;int16_t hi=tablefield==0?24:tablefield==1?(selected<2?3:15):3;if(edge&J_A)tablefield=(tablefield+1)%3;if(edge&J_LEFT){*cell=v>(tablefield==0?-24:0)?v-1:hi;edited[selected]=1;}if(edge&J_RIGHT){*cell=v<hi?v+1:(tablefield==0?-24:0);edited[selected]=1;}if(edge&(J_A|J_LEFT|J_RIGHT))dirty=1;}else if(page==1&&cursor[1]==tonecount[selected]){if(edge&J_A)tone_preset_open();}else{if(edge&J_LEFT)editvalue(-1,0);if(edge&J_RIGHT)editvalue(1,0);if(edge&J_A)editvalue(0,1);}}
 if((edge&J_B)&&page!=6)auditionstart();if((lastpad&J_B)&&!(p&J_B))auditionstop();
}

extern uint8_t seqrecordtrack;
void seq_record_finish(void) BANKED;

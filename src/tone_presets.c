#pragma bank 40
#include "api.h"
#include "tones.h"
#include "mixer_shared.h"
uint8_t tonepresetopen,w2program;
static uint8_t presetchoice;
extern uint8_t w2row,w2tablemode,w2tablelen,w2tablespeed;
extern int8_t w2tables[8][3];
static const char * const banks[10]={"TETRIS","MARIO LAND","ZELDA LA","POKEMON RB","KIRBY DL","METROID II","MEGA MAN","CASTLEVANIA","WARIO LAND","DK LAND"};
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20){uint8_t c=*s++;if(c>='a'&&c<='z')c-=32;*d++=c-32+(inv?96:0);}}
void tone_preset_open(void) BANKED {presetchoice=selected==4?w2program:program[selected];if(presetchoice>99)presetchoice=0;tonepresetopen=1;dirty=1;}
void tone_preset_render(void) BANKED {uint8_t i,n,start=presetchoice>3?presetchoice-3:0;char digits[4];if(start>93)start=93;memset(canvas,0,360);memset(canvas,96,20);text(0,0,"LOAD PRESET",1);text(1,2,banks[presetchoice/10],0);
 for(i=0;i<7;i++){n=start+i;digits[0]='0'+(n+1)/100;digits[1]='0'+((n+1)/10)%10;digits[2]='0'+(n+1)%10;digits[3]=0;text(0,4+i,digits,n==presetchoice);text(4,4+i,patch(n)->name,n==presetchoice);mixfill();}
 text(0,12,"U/D SOUND L/R BANK",0);text(0,14,"A LOAD  B CANCEL",0);
}
static void w2_preset(uint8_t n){Preset *p=patch(n);uint8_t i,c;
 w2program=n;w2settings[0]=24;w2settings[1]=p->v[1];w2settings[2]=p->v[3]?8+p->v[3]*8:120;w2settings[3]=(n%10==7||n%10==8)?24:0;w2settings[4]=p->v[14]&3;
 w2tablemode=!!(p->tconfig&3);w2tablelen=(p->tconfig>>2)+1;w2tablespeed=p->mod[0]?p->mod[0]:1;
 /* Copy the library's pitch/shape motion into W2's independent table. */
 for(i=0;i<8;i++){w2tables[i][0]=0;w2tables[i][1]=w2settings[4];w2tables[i][2]=15;}
 /* Use a temporary hardware table, then restore that channel unchanged. */
 {int8_t saved[8][3];memcpy(saved,tables[2],24);stocktable(2,p->table);for(i=0;i<8;i++)for(c=0;c<2;c++)w2tables[i][c]=c?(tables[2][i][1]&3):tables[2][i][0];memcpy(tables[2],saved,24);}
}
void tone_preset_input(uint8_t edge) BANKED {
 if(edge&(J_B|J_SELECT|J_START)){tonepresetopen=0;dirty=1;return;}
 if(edge&J_UP)presetchoice=presetchoice?presetchoice-1:99;
 if(edge&J_DOWN)presetchoice=(presetchoice+1)%100;
 if(edge&J_LEFT)presetchoice=(presetchoice+90)%100;
 if(edge&J_RIGHT)presetchoice=(presetchoice+10)%100;
 if(edge&J_A){if(selected<4){load(selected,presetchoice);finepitch[selected]=0;choice=presetchoice;}else{w2_preset(presetchoice);finepitch[4]=0;}if(!syncmode)seq_irq_refresh(selected);tonepresetopen=0;}
 dirty=1;
}

uint8_t mono_rows(void) BANKED {return monoosc==4?EXP_COUNT:monoosc==3?11:monoosc==2?6:7;}
uint8_t mono_row(int8_t delta) BANKED {uint8_t r=cursor[7],max=mono_rows();if(monoosc==3){if(r==8)r=0;else if(r<8)r++;}r=delta<0?(r?r-1:max-1):(r+1)%max;if(monoosc==3){if(!r)return 8;if(r<9)r--;}return r;}
void mono_page(int8_t delta,uint8_t crossing) BANKED {monoedit=0;monoosc=(monoosc+(delta<0?4:1))%5;if(cursor[7]>=mono_rows())cursor[7]=mono_rows()-1;if(monoosc>=3)monocol=0;else if(crossing)monocol=delta<0?2:0;dirty=1;}

extern uint8_t ui_menu_allowed(uint8_t item) BANKED;
void ui_menu_step(int8_t delta) BANKED {do{navchoice=delta<0?(navchoice<=1?PAGE_COUNT-1:navchoice-1):(navchoice>=PAGE_COUNT-1?1:navchoice+1);}while(!ui_menu_allowed(navchoice));}

/* Finder lives beside presets to leave room in the main UI ROM bank. */
extern uint8_t navcategory;
static const char * const finderpages[]={"LIVE","TONE","MODULATION","BANK","CC","TABLE","FX","MONOSYNTH","SEQUENCER","MASTURBATE","SEQ SETTINGS","P1","P2","WAVE1","WAVE2","NOISE","GLOBAL SETTINGS","DRUMSYNTH","MIXER","LOAD PATTERN","SAVE PATTERN","COPY","PASTE","KITS","LOAD SONG","SAVE SONG","CLEAR PATTERN","SYNC"};
static void finder_text(uint8_t x,uint8_t y,const char *t,uint8_t inverse){uint8_t c;while(*t&&x<20){c=*t++;canvas[(uint16_t)y*20+x++]=c-32+(inverse?96:0);if(!(x&3))mixfill();}}
/* Finder categories keep existing page/action IDs; 28..34 jump to tracks. */
const uint8_t finderitems[5][14]={
 {18,8,16,27,4,44,255},
 {38,21,43,22,42,36,37,35,26,40,41,39,255},
 {28,29,30,31,32,33,34,10,255},
 {11,12,13,14,15,17,7,9,23,1,2,3,5,6},
 {19,20,24,25,255}};
const uint8_t findercount[5]={6,12,8,14,4};
const char *findertracks[]={"P1","P2","WAVE1","NOISE","MONOSYNTH","WAVE2","DRUMSYNTH"};
uint8_t pageconfig;
static uint8_t pageslot;
uint8_t finder_allowed(uint8_t item){if(item==255)return 0;if(pageconfig==2)return item!=18&&item!=8&&item!=16&&item!=27;if(item==21||item==22||item==26||item>=35)return finder_edit_allowed(item);if(item>=28)return experimental_mode||!(item==32||item==33);return ui_menu_allowed(item);}
static void page_defaults(void);
static uint8_t finder_count(void){return navcategory==0&&pageconfig!=2?12:findercount[navcategory];}
static uint8_t finder_item(uint8_t i){if(navcategory||pageconfig==2)return finderitems[navcategory][i];page_defaults();return i==0?18:i==1?8:i==10?16:i==11?27:pool_root[100+i-2];}
void finder_first(void) BANKED {uint8_t i,item;mx.error=0;navchoice=255;for(i=0;i<finder_count();i++){item=finder_item(i);if(finder_allowed(item)){navchoice=item;break;}}}
void finder_step(int8_t delta) BANKED {uint8_t i,n=finder_count(),tries,item;mx.error=0;for(i=0;i<n;i++)if(finder_item(i)==navchoice)break;for(tries=0;tries<n;tries++){i=delta<0?(i?i-1:n-1):(i+1)%n;item=finder_item(i);if(finder_allowed(item)){navchoice=item;break;}}}
static const char * const finderedit[]={"CLEAR TRACK","COPY TRACK","PASTE TRACK","SELECT ALL","CLEAR SONG","COPY PATTERN","PASTE PATTERN","DELETE NOTES","CUT"};
static const char *finder_label(uint8_t item){if(item==44||item==255)return "EMPTY SLOT";if(item>=35)return finderedit[item-35];if(item>=28)return findertracks[item-28];return finderpages[item];}
static const char *shortcut_label(uint8_t item);
void ui_menu(void) BANKED {uint8_t i,row=4,inv,rank=0,n=0,start;const char *labels[]={"PAGE","EDT","SEQ","INS","FIL"};const uint8_t x[]={0,5,9,13,17};
 memset(canvas,0,sizeof(canvas));
 for(i=0;i<5;i++)finder_text(x[i],0,labels[i],navcategory==i);
 memset(canvas+20,201,20);finder_text(0,2,navcategory==0?"PAGE":navcategory==1?"EDIT":navcategory==2?"SEQUENCER":navcategory==3?"INSTRUMENTS":"FILE",0);
 for(i=0;i<finder_count();i++){if(finder_item(i)==navchoice)break;if(finder_allowed(finder_item(i)))rank++;}start=rank>11?rank-11:0;
 for(i=0;i<finder_count();i++){uint8_t item=finder_item(i);if(!finder_allowed(item))continue;if(n++<start||row>=16)continue;inv=navchoice==item;if(inv)memset(canvas+row*20,96,20);finder_text(1,row,navcategory==0?shortcut_label(item):finder_label(item),inv);row++;}
 if(navchoice==255)finder_text(1,5,"NO ACTIONS HERE",0);
 if(mx.error==2)finder_text(0,16,"CANNOT DO THAT HERE",0);
 finder_text(0,17,pageconfig==2?"A ASSIGN   SEL BACK":"START/A OK  SEL BACK",0);
}

/* Settings use reserved root bytes, outside pattern/song payloads and audio RAM.
   They remain global when another song is loaded; legacy sessions use RAM only. */
#define PAGE_SLOTS 8
#define PAGE_ITEMS (pool_root+100)
static void page_defaults(void){uint8_t i,j;const uint8_t old_defaults[8]={18,8,38,21,22,35,16,255};
 if(pool_root[108]=='P'&&pool_root[109]==1){for(i=0;i<8;i++)if(PAGE_ITEMS[i]!=255&&(PAGE_ITEMS[i]<1||PAGE_ITEMS[i]>43))break;if(i==8)return;}
 if(pool_root[108]!='Q'||pool_root[109]!=1||!memcmp(PAGE_ITEMS,old_defaults,8))memset(PAGE_ITEMS,255,8);
 else for(i=0;i<8;i++){if(PAGE_ITEMS[i]<1||PAGE_ITEMS[i]>43||PAGE_ITEMS[i]==18||PAGE_ITEMS[i]==8||PAGE_ITEMS[i]==16||PAGE_ITEMS[i]==27)PAGE_ITEMS[i]=255;for(j=0;j<i;j++)if(PAGE_ITEMS[i]==PAGE_ITEMS[j])PAGE_ITEMS[i]=255;}
 pool_root[108]='P';pool_root[109]=1;
}
static const char *shortcut_label(uint8_t item){static const char * const tracks[]={"SEQ P1","SEQ P2","SEQ WAVE1","SEQ NOISE","SEQ MONOSYNTH","SEQ WAVE2","SEQ DRUMSYNTH"};return item>=28&&item<=34?tracks[item-28]:finder_label(item);}
void page_menu_settings_render(void) BANKED {uint8_t i;page_defaults();if(pageconfig==2){ui_menu();return;}
 memset(canvas,0,sizeof(canvas));memset(canvas,96,20);finder_text(0,0,"PAGE MENU SETTINGS",1);
 for(i=0;i<PAGE_SLOTS;i++){finder_text(0,3+i,i==pageslot?">":" ",0);finder_text(2,3+i,shortcut_label(PAGE_ITEMS[i]),i==pageslot);}
 if(mx.error==2)finder_text(0,12,"SETTINGS NOT SAVED",0);
 finder_text(0,14,"A: ASSIGN ITEM",0);finder_text(0,15,"B: REMOVE ITEM",0);finder_text(0,16,"L/R: REORDER",0);finder_text(0,17,"SELECT: BACK",0);
}
static void page_save(void){if(sparse_enabled==1&&!pool_commit())mx.error=2;}
void page_menu_settings_input(uint8_t edge) BANKED {uint8_t other,item;page_defaults();
 if(edge&J_SELECT){pageconfig--;dirty=1;return;}
 if(pageconfig==2){
  if(edge&J_LEFT){navcategory=navcategory?navcategory-1:4;finder_first();}
  if(edge&J_RIGHT){navcategory=(navcategory+1)%5;finder_first();}
  if(edge&J_UP)finder_step(-1);if(edge&J_DOWN)finder_step(1);
  if(edge&J_A){PAGE_ITEMS[pageslot]=navchoice==44?255:navchoice;page_save();pageconfig=1;}
 }else{
  if(edge&J_B){PAGE_ITEMS[pageslot]=255;mx.error=0;page_save();dirty=1;return;}
  if(edge&J_UP)pageslot=(pageslot+7)&7;if(edge&J_DOWN)pageslot=(pageslot+1)&7;
  if(edge&(J_LEFT|J_RIGHT)){other=(pageslot+(edge&J_LEFT?7:1))&7;item=PAGE_ITEMS[pageslot];PAGE_ITEMS[pageslot]=PAGE_ITEMS[other];PAGE_ITEMS[other]=item;pageslot=other;page_save();}
  if(edge&J_A){pageconfig=2;navcategory=0;finder_first();}
 }
 dirty=1;
}

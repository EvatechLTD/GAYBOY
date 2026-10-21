#pragma bank 40
#include "api.h"
#include "tones.h"
#include "user_presets.h"
#include "mixer_shared.h"
#include "link_control.h"
uint8_t tonepresetopen,w2program;
static uint8_t presetchoice;
extern uint8_t seqbused;
extern uint8_t w2row,w2tablemode,w2tablelen,w2tablespeed;
extern int8_t w2tables[8][3];
static const char * const banks[10]={"TETRIS","MARIO LAND","ZELDA LA","POKEMON RB","KIRBY DL","METROID II","MEGA MAN","CASTLEVANIA","WARIO LAND","DK LAND"};
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20){uint8_t c=*s++;if(c>='a'&&c<='z')c-=32;*d++=c-32+(inv?96:0);}}
/* Browser state fits three bytes; rename text uses modal-only preview scratch. */
static uint8_t usermode,usertarget,userrow;
#define PRESET_NAME ((uint8_t *)0xB000)
static const char preset_chars[]=" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/.";
static void preset_close(void){tonepresetopen=0;previewshape=255;dirty=1;}
void tone_user_open(uint8_t mode) BANKED {mixer_prepare_cancel();sparse_finish_install();usertarget=eval_instrument();if(usertarget>7)return;usermode=mode;userrow=0;presetchoice=mode||usertarget>=4?100:program[usertarget];if(presetchoice>131)presetchoice=100;tonepresetopen=1;dirty=1;}
void tone_preset_open(void) BANKED {tone_user_open(0);}
static uint8_t user_bank(void){return (presetchoice-100)>>3;}
static void preset_result(uint8_t ok){if(ok)preset_close();else{usermode|=128;dirty=1;}}
static void preset_save(void){if(user_preset_reference(presetchoice-100)!=POOL_NONE){usermode=9;userrow=1;}else preset_result(user_preset_save(presetchoice-100,usertarget));}
static void preset_load(void){if(presetchoice<100){load(usertarget,presetchoice);finepitch[usertarget]=0;choice=presetchoice;seq_irq_refresh(usertarget);preset_close();}else preset_result(user_preset_load(presetchoice-100,usertarget));}
void tone_preset_render(void) BANKED {uint8_t mode=usermode&127,i,n,start;uint8_t name[9];char digits[4];memset(canvas,0,360);memset(canvas,96,20);text(0,0,mode==0?"LOAD PRESET":mode==1?"SAVE PRESET":mode==3||mode==4?"RENAME":"PRESET BANKS",1);
 if(mode<=1){if(presetchoice<100)text(1,2,banks[presetchoice/10],0);else{user_bank_name(user_bank(),name);text(1,2,(char *)name,0);}start=presetchoice<100?(presetchoice/10)*10:100+user_bank()*8;
  for(i=0;i<(presetchoice<100?10:8);i++){n=start+i;digits[0]='0'+(n<100?n+1:n-99)/100;digits[1]='0'+((n<100?n+1:n-99)/10)%10;digits[2]='0'+(n<100?n+1:n-99)%10;digits[3]=0;text(0,4+i,digits,n==presetchoice);if(n<100)text(4,4+i,patch(n)->name,n==presetchoice);else{user_preset_name(n-100,name);text(4,4+i,(char *)name,n==presetchoice);}mixfill();}
  text(0,15,"U/D TONE  L/R BANK",0);text(0,17,mode?"A/B SAVE  SEL BACK":"A/B LOAD  SEL BACK",0);
 }else if(mode==2){for(i=0;i<USER_BANKS;i++){user_bank_name(i,name);text(2,4+i*2,(char *)name,userrow==i);}text(0,16,"USER BANKS ARE GLOBAL",0);text(0,17,"A/B OPEN  SEL BACK",0);
 }else if(mode==7){user_bank_name(user_bank(),name);text(1,2,(char *)name,0);for(i=0;i<8;i++){user_preset_name(user_bank()*8+i,name);text(1,3+i,(char *)name,userrow==i);}text(1,12,"RENAME BANK",userrow==8);text(1,13,"CLEAR BANK",userrow==9);text(0,17,"A/B OPEN  SEL BACK",0);
 }else if(mode==8){user_preset_name(presetchoice-100,name);text(1,2,(char *)name,0);text(2,5,"LOAD",userrow==0);text(2,7,"SAVE CURRENT TONE",userrow==1);text(2,9,"RENAME",userrow==2);text(2,11,"DELETE",userrow==3);text(0,17,"A/B SELECT  SEL BACK",0);
 }else if(mode==3||mode==4){text(1,4,"NAME",0);for(i=0;i<8;i++)canvas[6*20+4+i]=PRESET_NAME[i]-32+(userrow==i?96:0);text(2,9,"APPLY NAME",userrow==8);text(0,15,"A/B+ARROWS: EDIT",0);text(0,16,"L/R CURSOR DOWN APPLY",0);text(0,17,"SELECT CANCELS",0);
 }else{text(0,5,mode==9?"REPLACE THIS PRESET?":mode==5?"DELETE THIS PRESET?":"CLEAR ALL 8 PRESETS?",0);text(3,9,"CONTINUE",userrow==0);text(3,11,"CANCEL",userrow==1);text(0,17,"A/B OK  SELECT BACK",0);}
 if(usermode&128)text(0,16,"EMPTY / WRONG / FULL",0);
}
void tone_preset_input(uint8_t edge) BANKED {extern uint8_t seqselectused;uint8_t mode=usermode&127,p=lastpad,bank,n,ok;int16_t value;uint8_t name[9];if(edge&J_SELECT){seqselectused=1;if(mode<=2)preset_close();else{usermode=mode==7?2:mode==8||mode==3||mode==6?7:8;userrow=0;}dirty=1;return;}if(!edge)return;usermode=mode;
 if(mode==3||mode==4){if((edge&J_START)&&userrow==8)edge|=J_A;if(userrow<8&&(p&(J_A|J_B))&&(edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN))){for(n=0;n<sizeof(preset_chars)-1&&preset_chars[n]!=PRESET_NAME[userrow];n++);value=n+(edge&J_UP?1:edge&J_DOWN?-1:edge&J_RIGHT?10:-10);if(value<0)value+=sizeof(preset_chars)-1;if(value>=sizeof(preset_chars)-1)value-=sizeof(preset_chars)-1;PRESET_NAME[userrow]=preset_chars[value];}else if(!(p&(J_A|J_B))&&!(edge&J_START)){if(edge&J_LEFT)userrow=userrow?userrow-1:7;if(edge&J_RIGHT)userrow=userrow<7?userrow+1:0;if(edge&J_DOWN)userrow=8;if(edge&J_UP)userrow=0;}else if(userrow==8&&(edge&(J_A|J_B|J_START))){ok=mode==3?user_bank_rename(user_bank(),PRESET_NAME):user_preset_rename(presetchoice-100,PRESET_NAME);usermode=ok?7:mode|128;userrow=0;}dirty=1;return;}
 if(mode<=1){n=mode||usertarget>=4?100:0;if(edge&J_UP)presetchoice=presetchoice==n?131:presetchoice-1;if(edge&J_DOWN)presetchoice=presetchoice==131?n:presetchoice+1;
  if(edge&(J_LEFT|J_RIGHT)){bank=presetchoice<100?presetchoice/10:10+user_bank();value=bank+(edge&J_RIGHT?1:-1);if(value<(n?10:0))value=13;if(value>13)value=n?10:0;presetchoice=value<10?value*10:100+(value-10)*8;}
  if(edge&(J_A|J_B|J_START)){if(mode)preset_save();else preset_load();}
 }else if(mode==2){if(edge&J_UP)userrow=(userrow+3)%4;if(edge&J_DOWN)userrow=(userrow+1)%4;if(edge&(J_A|J_B|J_START)){presetchoice=100+userrow*8;usermode=7;userrow=0;}
 }else if(mode==7){if(edge&J_UP)userrow=userrow?userrow-1:9;if(edge&J_DOWN)userrow=(userrow+1)%10;if(edge&(J_A|J_B|J_START)){if(userrow<8){presetchoice=100+user_bank()*8+userrow;usermode=8;userrow=0;}else if(userrow==8){user_bank_name(user_bank(),name);memcpy(PRESET_NAME,name,9);usermode=3;userrow=0;}else{usermode=6;userrow=1;}}
 }else if(mode==8){if(edge&J_UP)userrow=(userrow+3)%4;if(edge&J_DOWN)userrow=(userrow+1)%4;if(edge&(J_A|J_B|J_START)){if(!userrow)preset_load();else if(userrow==1)preset_save();else if(userrow==2){user_preset_name(presetchoice-100,name);memcpy(PRESET_NAME,name,9);usermode=4;userrow=0;}else{usermode=5;userrow=1;}}
 }else{if(edge&(J_LEFT|J_RIGHT|J_UP|J_DOWN))userrow^=1;if(edge&(J_A|J_B|J_START)){if(userrow){usermode=7;userrow=0;}else if(mode==9)preset_result(user_preset_save(presetchoice-100,usertarget));else{ok=mode==5?user_preset_remove(presetchoice-100):user_bank_clear(user_bank());usermode=ok?7:mode|128;userrow=0;}}}
 dirty=1;
}


uint8_t mono_rows(void) BANKED {return 0;}
uint8_t mono_row(int8_t delta) BANKED {uint8_t r=cursor[7],max=mono_rows();r=delta<0?(r?r-1:max-1):(r+1)%max;return r;}
void mono_page(int8_t d,uint8_t c) BANKED {(void)d;(void)c;}

extern uint8_t ui_menu_allowed(uint8_t item) BANKED;
void ui_menu_step(int8_t delta) BANKED {do{navchoice=delta<0?(navchoice<=1?PAGE_COUNT-1:navchoice-1):(navchoice>=PAGE_COUNT-1?1:navchoice+1);}while(!ui_menu_allowed(navchoice));}

/* Finder lives beside presets to leave room in the main UI ROM bank. */
extern uint8_t navcategory,mixer_device;
static const char * const finderpages[]={"LIVE","TONE","MOD","BANK","CC","TABLE","FX","MONOSYNTH","SEQUENCER","MASTURBATE","SEQ SETTINGS","P1","P2","WAVE","WAVE2","NOISE","GLOBAL SETTINGS","DRUMSYNTH","MIXER","LOAD PATTERN","SAVE PATTERN","COPY","PASTE","KITS","LOAD SONG","SAVE SONG","CLEAR PATTERN","SYNC"};
static void finder_text(uint8_t x,uint8_t y,const char *t,uint8_t inverse){uint8_t c;while(*t&&x<20){c=*t++;canvas[(uint16_t)y*20+x++]=c-32+(inverse?96:0);if(!(x&3))mixfill();}}
/* Finder categories keep existing page/action IDs; 28..34 jump to tracks. */
const uint8_t finderitems[5][14]={
 {18,8,45,16,27,4,44,255},
 {38,21,43,22,42,36,37,35,26,40,41,39,255},
 {28,29,30,31,32,33,34,10,255},
 {11,12,13,14,15,17,7,9,23,1,2,3,5,6},
 {19,20,24,25,255}};
const uint8_t findercount[5]={7,12,8,14,4};
const char * const findertracks[]={"P1","P2","WAVE","NOISE","MONOSYNTH","WAVE2","DRUMSYNTH"};
uint8_t pageconfig;
static uint8_t pageslot;
uint8_t finder_allowed(uint8_t item){if(item==255||item==7||item==9||item==14||item==32||item==33||item==5||item==6)return 0;if(item>=28&&item<=34&&!eval_visible(item-28))return 0;if(page==18&&MIXER_LINK_VIEW&&(item==19||item==20))return 0;if(item==45)return pageconfig!=2;if(pageconfig==2)return item!=18&&item!=8&&item!=16&&item!=27;if(item==21||item==22||item==26||item>=35)return finder_edit_allowed(item);if(item>=28)return experimental_mode||!(item==32||item==33);return ui_menu_allowed(item);}
static void page_defaults(void);
static uint8_t finder_count(void){return navcategory==0&&pageconfig!=2?13:findercount[navcategory];}
static uint8_t finder_item(uint8_t i){if(navcategory||pageconfig==2)return finderitems[navcategory][i];page_defaults();return i==0?18:i==1?8:i==2?45:i==11?16:i==12?27:pool_root[100+i-3];}
void finder_first(void) BANKED {uint8_t i,item;mx.error=0;navchoice=255;for(i=0;i<finder_count();i++){item=finder_item(i);if(finder_allowed(item)){navchoice=item;break;}}}
void finder_step(int8_t delta) BANKED {uint8_t i,n=finder_count(),tries,item;mx.error=0;for(i=0;i<n;i++)if(finder_item(i)==navchoice)break;for(tries=0;tries<n;tries++){i=delta<0?(i?i-1:n-1):(i+1)%n;item=finder_item(i);if(finder_allowed(item)){navchoice=item;break;}}}
static const char * const finderedit[]={"CLEAR TRACK","COPY TRACK","PASTE TRACK","SELECT ALL","CLEAR SONG","COPY PATTERN","PASTE PATTERN","DELETE NOTES","CUT"};
static const char *finder_label(uint8_t item){if(item==45)return "MIXER SETTINGS";if(item==44||item==255)return "EMPTY SLOT";if(item>=35)return finderedit[item-35];if(item>=28)return findertracks[item-28];return finderpages[item];}
static const char *shortcut_label(uint8_t item);
void ui_menu(void) BANKED {uint8_t i,row=4,inv,rank=0,n=0,start;const char *labels[]={"PAGE","EDT","SEQ","INS","FIL"};const uint8_t x[]={0,5,9,13,17};
 memset(canvas,0,sizeof(canvas));
 for(i=0;i<5;i++)finder_text(x[i],0,labels[i],navcategory==i);
 memset(canvas+20,13,20);finder_text(0,2,navcategory==0?"PAGE":navcategory==1?"EDIT":navcategory==2?"SEQUENCER":navcategory==3?"INSTRUMENTS":"FILE",0);
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
static const char *shortcut_label(uint8_t item){static const char * const tracks[]={"SEQ P1","SEQ P2","SEQ WAVE","SEQ NOISE","SEQ MONOSYNTH","SEQ WAVE2","SEQ DRUMSYNTH"};return item>=28&&item<=34?tracks[item-28]:finder_label(item);}
void page_menu_settings_render(void) BANKED {uint8_t i;page_defaults();if(pageconfig==2){ui_menu();return;}
 memset(canvas,0,sizeof(canvas));memset(canvas,96,20);finder_text(0,0,"PAGE MENU SETTINGS",1);
 for(i=0;i<PAGE_SLOTS;i++){finder_text(0,3+i,i==pageslot?">":" ",0);finder_text(2,3+i,shortcut_label(PAGE_ITEMS[i]),i==pageslot);}
 if(mx.error==2)finder_text(0,12,"SETTINGS NOT SAVED",0);
 finder_text(0,14,"A/B: ASSIGN ITEM",0);finder_text(0,15,"EMPTY ITEM TO REMOVE",0);finder_text(0,16,"A/B+ARROWS: REORDER",0);finder_text(0,17,"SELECT: BACK",0);
}
static void page_save(void){if(sparse_enabled==1&&!pool_commit())mx.error=2;}
void page_menu_settings_input(uint8_t p,uint8_t edge) BANKED {uint8_t other,item;page_defaults();
 if(edge&J_SELECT){pageconfig--;dirty=1;return;}
 if(pageconfig==2){
  if(edge&J_LEFT){navcategory=navcategory?navcategory-1:4;finder_first();}
  if(edge&J_RIGHT){navcategory=(navcategory+1)%5;finder_first();}
  if(edge&J_UP)finder_step(-1);if(edge&J_DOWN)finder_step(1);
  if(edge&(J_A|J_B|J_START)){PAGE_ITEMS[pageslot]=navchoice==44?255:navchoice;page_save();pageconfig=1;}
 }else{
  if(edge&(J_A|J_B))seqbused=2;
  if(p&(J_A|J_B)){int8_t direction=edge&J_UP?-1:edge&J_DOWN?1:edge&J_LEFT?-10:edge&J_RIGHT?10:0;if(direction){int16_t target=(int16_t)pageslot+direction;if(target<0)target=0;if(target>7)target=7;seqbused=3;while(pageslot!=target){other=pageslot+(pageslot<target?1:-1);item=PAGE_ITEMS[pageslot];PAGE_ITEMS[pageslot]=PAGE_ITEMS[other];PAGE_ITEMS[other]=item;pageslot=other;}page_save();}}
  else{if(edge&J_UP)pageslot=(pageslot+7)&7;if(edge&J_DOWN)pageslot=(pageslot+1)&7;if(seqbused==2){pageconfig=2;navcategory=0;finder_first();}seqbused=0;}

 }
 dirty=1;
}

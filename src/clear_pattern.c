#pragma bank 45
#include "api.h"
#include "mixer_shared.h"
#include "link_control.h"
#include "clear_pattern.h"
#include "ui_startup_font.h"
static uint8_t origin,slot,track,clear_choice,operation;
extern uint8_t mixer_device;
uint8_t mixer_file_pad(void) BANKED;
uint8_t mixer_file_load(void) BANKED;
uint8_t mixer_file_save(void) BANKED;
extern uint8_t seqselectused;
extern uint8_t seqauditionnote,seqauditiontrack;
void seq_audition_stop(void) BANKED {uint8_t n=seqauditionnote,c=seqauditiontrack;seqauditionnote=0;if(n)event(0x80|c,n-1,0);}
uint8_t seq_group_contains(uint8_t step,uint8_t pitch) BANKED {return seqgrouptrack==seqtrack&&step>=seqgroupx0&&step<=seqgroupx1&&pitch>=seqgroupy0&&pitch<=seqgroupy1;}
uint8_t mixer_clear_saved(uint8_t slot) BANKED;
static void clear_text(uint8_t x,uint8_t y,const char *text,uint8_t inverse){uint8_t c;while(*text&&x<20){c=*text++;if(c>='a'&&c<='z')c-=32;canvas[(uint16_t)y*20+x++]=c-32+(inverse?96:0);}mixfill();}
static void clear_number(uint8_t x,uint8_t y,uint8_t value,uint8_t digits,uint8_t inverse){uint8_t place=digits==3?100:1,n;while(digits--){n=0;while(value>=place){value-=place;n++;}canvas[(uint16_t)y*20+x++]=16+n+(inverse?96:0);place/=10;}}
/* Commit progress to VRAM immediately: boot and song loading do not return
   to the foreground renderer between their storage operations. */
extern __at (0xACF8) uint8_t ui_transition_hidden;
void ui_loading(uint8_t done,uint8_t total) BANKED {uint8_t i,filled,percent;
 if(!total)total=1;if(done>total)done=total;
 /* Nested allocator walks report their own progress during a larger load.
    Keep the visible percentage moving forward until an explicit zero reset. */
 if(done&&((uint16_t)done*12)/total<ui_loading_step){done=ui_loading_step;total=12;}
 percent=((uint16_t)done*100)/total;filled=((uint16_t)done*18)/total;
 ui_loading_active=done<total;ui_loading_step=((uint16_t)done*12)/total;
 HIDE_SPRITES;ui_loading_prepare();
 if(ui_font_upload_pending){
  for(i=0;i<23;i++){ui_upload_tile(220+i,wavepixels+(uint16_t)i*16,0);mixfill();}
  for(i=0;i<12;i++){ui_upload_tile(192+i,wavepixels+368+(uint16_t)i*16,0);mixfill();}
  ui_font_upload_pending=0;
 }
 memset(canvas,0,sizeof(canvas));
 clear_text(6,6,"LOADING",0);clear_number(8,8,percent,3,0);clear_text(11,8,"%",0);
 for(i=0;i<18;i++)canvas[10*20+1+i]=i<filled?96:13;
 SCX_REG=SCY_REG=0;BGP_REG=0xe4;ui_flush_spans();
 seqflushpending=1;ui_transition_hidden=0;SHOW_BKG;DISPLAY_ON;
}
void ui_loading_begin(void) BANKED {uint8_t tile;
 HIDE_SPRITES;memset(shadow_OAM,0,160);ui_transition_hidden=ui_font_upload_pending=seqfontdirty=0;
 memset(visible,255,sizeof(visible));*(volatile uint8_t *)0xACF7=0;*(volatile uint8_t *)0xACFA=0;
 *(volatile uint8_t *)0xACC2=0;*(volatile uint8_t *)0xACC3=255;seqviewtrack=255;BGP_REG=0xe4;
 for(tile=0;tile<23;tile++)graytiles[startup_graychars[tile]-32]=220+tile;
 /* The LCD is still off after the intro. Native ROM tiles avoid unpacking
    the same glyph bits hundreds of times before the first loading frame. */
 set_bkg_data(0,192,startup_font_base);set_bkg_data(220,23,startup_font_gray);
 set_bkg_data(192,12,startup_font_widgets);ui_loading(0,12);
}
void ui_init(void) BANKED {ui_loading_active=0;memset(visible,255,sizeof(visible));page=8;seqtrack=6;seq_open();ui_render();roll_commit();set_bkg_tiles(0,0,20,18,canvas);memcpy(visible,canvas,sizeof(visible));ui_transition_hidden=0;SHOW_BKG;}
uint8_t clear_available(void) BANKED {return page==8||page==18;}
void clear_capture(void) BANKED {origin=page;track=page==8?seqtrack:255;slot=page==18&&mx.focus>=30&&mx.focus<38?mx.focus-30:mx.slot;operation=0;}
uint8_t mixer_menu_pad(void) BANKED {return origin==18?slot:(origin==19||origin==20)?mixer_file_pad():mx.slot;}
void mixer_file_confirm(uint8_t target,uint8_t saving) BANKED {origin=page;slot=target;track=255;operation=saving?5:4;clear_choice=1;page=26;dirty=1;}
void clear_open(void) BANKED {if(origin!=8&&origin!=18)return;clear_choice=1;page=26;dirty=1;}
void clear_song_open(uint8_t song) BANKED {origin=24;slot=song;track=255;operation=1;clear_choice=1;page=26;dirty=1;}
void clear_render(void) BANKED {uint8_t row;seqflushpending=1;HIDE_SPRITES;
 for(row=0;row<18;row++)memset(canvas+row*20,0,20);
 memset(canvas,96,20);clear_text(0,0,operation==1?"DELETE SAVED SONG":operation==2?"CLEAR SONG":operation==5?"SAVE PATTERN":operation==4?"LOAD PATTERN":operation==3?"PASTE PATTERN":track<7?"CLEAR TRACK":"CLEAR PATTERN",1);
 if(operation==1){clear_text(0,4,"DELETE SAVED SONG",0);clear_number(0,6,slot+1,3,0);}
 else if(operation==2){clear_text(0,4,"EMPTY ALL 8 PADS?",0);clear_text(0,6,"SAVED SONGS AND",0);clear_text(0,7,"LIBRARY ARE KEPT",0);}
 else if(operation==5){clear_text(0,4,"REPLACE SAVED ITEM",0);clear_number(0,6,mx.browser+1,3,0);}
 else if(operation>=3){clear_text(0,4,"REPLACE PATTERN",0);clear_number(17,4,slot+1,1,0);clear_text(0,6,"ALL NOTES, SETTINGS",0);clear_text(0,7,"AND PATCHES REPLACED",0);}
 else {clear_text(0,3,"SELECTED PATTERN",0);clear_number(17,3,slot+1,3,0);
  clear_text(0,5,track==255?"ALL SEQUENCES WILL":"ONLY THIS TRACK WILL",0);clear_text(0,6,"BE CLEARED",0);if(track<7){clear_text(0,8,"TRACK",0);clear_number(6,8,track+1,1,0);}clear_text(0,10,"PATCHES ARE KEPT",0);
 }
 clear_text(3,12,"Do it",clear_choice==0);clear_text(3,14,"Cancel",clear_choice==1);clear_text(0,17,"START/A OK  SEL BACK",0);
}
static void close(void){page=origin;if(page==8){seqdrawvalid=0;seqviewtrack=255;}mx.padcache=0;dirty=1;}
void clear_input(uint8_t edge) BANKED {uint8_t ok=1;
 if(edge&(J_UP|J_DOWN|J_LEFT|J_RIGHT)){clear_choice^=1;dirty=1;}
 if(edge&J_SELECT){seqselectused=1;close();return;}if(!(edge&(J_A|J_START)))return;if(clear_choice){close();return;}
 if(operation==1)ok=sparse_delete_song(slot);
 else if(operation==2)ok=sparse_clear_working_song();
 else if(operation==3)ok=sparse_paste_pad(slot);
 else if(operation==4)ok=mixer_file_load();
 else if(operation==5)ok=mixer_file_save();
 else if(slot==mx.slot)seq_clear_notes(track);
 else if(sparse_enabled)ok=sparse_clear_slot(slot);
 else ok=mixer_clear_saved(slot);
 close();if(ok&&operation>=4){page=18;mx.focus=30+slot;mx.naming=0;}if(!ok)mx.error=2;
}

extern uint8_t seqrecordtrack;
extern uint16_t seqrecordlength,seqdeadline;
void mixer_pattern_changed(void) BANKED;
void seq_clear_release(uint8_t track) BANKED;
void seq_clear_notes(uint8_t track) BANKED {uint8_t c,busy=seqservicing;seqservicing=1;
 sparse_journal_edit_barrier();
 if(seqeventcache==2)sparse_finish_install();if(track==255){seqrecordtrack=255;seqrecordlength=0;for(c=0;c<7;c++)seq_clear_release(c);seq_storage_clear();}
 else if(track<7){if(seqrecordtrack==track){seqrecordtrack=255;seqrecordlength=0;}seq_clear_release(track);seq_track_clear(track);}
 else {seqservicing=busy;return;}
 seqgrouptrack=255;seqapending=seqamoved=0;seqdrawvalid=0;seqviewtrack=255;seqdeadline=1;mixer_pattern_changed();seqservicing=busy;dirty=1;
}

/* Edit context follows the displayed grid or the focused mixer pad. */
static uint8_t edit_pad(void){return origin==18?slot:(origin==19||origin==20)?mixer_file_pad():mx.slot;}
static uint8_t edit_grid(void){return page==8;}
uint8_t finder_edit_allowed(uint8_t item) BANKED {
 if(page==18&&MIXER_LINK_VIEW)return 0;
 if(item==26)return page==18;
 if(item==39)return page==18&&sparse_enabled==1;
 if(item==40)return page==18&&sparse_enabled==1&&(edit_pad()==mx.slot||sparse_slots[edit_pad()]!=POOL_NONE);
 if(item==41)return page==18&&sparse_enabled==1&&pool_reference(POOL_PATTERN_CLIP)!=POOL_NONE;
 if(!edit_grid())return 0;
 if(item==21||item==42||item==43)return seqgrouptrack==seqtrack;
 if(item==22)return seq_clip_kind()==2;
 if(item==37)return seq_clip_kind()==1;
 return item==35||item==36||item==38;
}
uint8_t finder_edit_action(uint8_t item) BANKED {uint8_t ok=1;
 if(!finder_edit_allowed(item))return 0;
 if(item==26||item==35){clear_open();return 1;}
 if(item==39){operation=2;origin=18;clear_choice=1;page=26;dirty=1;return 1;}
 if(item==40)ok=sparse_copy_pad(edit_pad());
 if(item==41){slot=edit_pad();origin=18;operation=3;
  if(sparse_slots[slot]!=POOL_NONE||(slot==mx.slot&&seq_event_total()!=0)){clear_choice=1;page=26;dirty=1;return 1;}
  ok=sparse_paste_pad(slot);
 }
 if(item==36)seq_copy_track();
 if(item==37)seq_paste();
 if(item==38)seq_select_visible();
 if(item==21||item==43){sparse_finish_install();ok=seq_region_copy(item==43);if(ok&&item==43)mixer_pattern_changed();}
 if(item==22){sparse_journal_edit_barrier();sparse_finish_install();ok=seq_region_paste(seqcursor[seqtrack],seqtrack==6?drumrow:seqpitch[seqtrack]);if(ok)mixer_pattern_changed();}
 if(item==42)seq_delete_selection();
 if(!ok)mx.error=2;seqdrawvalid=0;mx.padcache=0;dirty=1;return ok;
}

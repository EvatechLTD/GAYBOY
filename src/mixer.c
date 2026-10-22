#pragma bank 18
#pragma opt_code_speed
#include "api.h"
#include "ui_fields.h"
void roll_clear_transition(void) BANKED;
void eval_chord_dirty(uint8_t c) BANKED;
#include "mixer.h"
#include "tones.h"
#include "sparse_store.h"
extern uint8_t toneready,syncrole;
extern volatile uint8_t padsampled,padread,padwrite;
void mixer_pattern_changed(void) BANKED;
void mixer_pattern_clean(void) BANKED;
void mixer_prepare_focus(uint8_t slot) BANKED;
void mixer_journal_recover(void) BANKED;
void mixer_prepare_barrier(void) BANKED;
uint8_t mixer_prepare_status(uint8_t slot) BANKED;
extern uint16_t pattern_generation;
extern uint8_t seqgate[7],seqbeats,seqdenom,seqcachedgate[7];
extern uint16_t seqcachedbpm,seqstepunits,seqgateunits[7],seqdeadline,seqclock;
extern void seq_pattern_release(void) BANKED;
extern void seq_pattern_start(void) BANKED;
extern void seq_pattern_handoff(void) BANKED;
extern uint8_t seqeventcache,seqrecordtrack;
extern uint16_t seqrecordlength;
#define PREP_UNITS ((uint16_t *)0xACD0)
#define PREP_STEP (*(uint16_t *)0xACDE)
/* Bank zero stays selected whenever audio or sequencing can run. */

#include "mixer_shared.h"
#include "mixer_drum_names.h"
#include "mixer_pads.h"
#include "link_control.h"
__at (0xAC80) Mixer mx;
static const char * const tracks[7]={"P1","P2","WV","N","MON","W2","DR"};
static const char * const pans[4]={"OFF","R","L","LR"};
static uint8_t mixscroll;
/* Durable session state; renderer SRAM is reused by other screens. */
static uint8_t mixer_view_focus;
uint8_t mixer_pad_pages[2];
void mixer_view_capture(void) BANKED {mixer_view_focus=mx.focus;}
/* Session layout is presentation-only; logical track/pad IDs never move. */
uint8_t mixer_hidden[8],layout_cursor,mixer_device,mixer_layout_dirty;
void mixer_layout_load(void) BANKED;
void mixer_layout_render(void) BANKED;
void mixer_link_render(void) BANKED;
void mixer_link_input(uint8_t p,uint8_t edge) BANKED;
uint8_t link_pending(void) BANKED;
static uint8_t layout_hidden(uint8_t id){if(id==4||id==5||id>=25)return 1;if(id>=20)return 0;return mixer_hidden[(MIXER_LINK_VIEW?4:0)+(id>>3)]&(1U<<(id&7));}
static uint8_t strip_visible(uint8_t c){return !layout_hidden(c)&&(experimental_mode||(c!=4&&c!=5));}
static const uint8_t striporder[20]={0,1,2,3,4,5,6,17,18,19,7,8,9,10,11,12,13,14,15,16};
static uint8_t stripposition(uint8_t c){uint8_t i;for(i=0;i<20;i++)if(striporder[i]==c)return i;return 0;}
static uint8_t firststrip(void){uint8_t c;for(c=0;c<20;c++)if(strip_visible(striporder[c]))return striporder[c];return 255;}
static uint8_t firstpad(void){uint8_t c;for(c=0;c<8;c++)if(!layout_hidden(20+c))return 30+c;return 0;}
static uint8_t stripcolumn(uint8_t c){uint8_t i,n=0;for(i=0;i<20&&striporder[i]!=c;i++)if(strip_visible(striporder[i]))n++;return n;}
/* Page-local graphics caches share only renderer scratch, never audio state.
   Opening Mixer invalidates them after any roll has reused those addresses. */
__at (0xA433) uint8_t mixerfontdirty;
__at (0xA434) static uint16_t fader_ready_frame;
__at (0xA436) static uint8_t fader_pattern;
__at (0xA437) static uint8_t fader_requested[6];
__at (0xA43D) static uint8_t fader_pending;
__at (0xA43E) static uint16_t fader_last_frame;
__at (0xACC4) uint8_t pad_image_playing;
__at (0xACC5) uint8_t pad_image_queued;
__at (0xACC6) uint8_t pad_names_valid;
__at (0xACB5) uint8_t fader_image_knob[6];
extern __at (0xAE40) uint8_t pad_names[8][5];
typedef struct {uint8_t valid,focus,quant,playing,edit,mode,muted,solo;uint16_t drummute,drumsolo,tempo;uint8_t strips[14];} MixerImage;
__at (0xAE68) MixerImage mixer_image;
static void ram(uint8_t b){ENABLE_RAM;SWITCH_RAM(b);}
static uint8_t bank(uint8_t s){return 1+s/3;}
static uint8_t *record(uint8_t s){return (uint8_t *)(0xA000U+(uint16_t)(s%3)*RECORD);}
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
static void num(uint8_t x,uint8_t y,uint16_t n,uint8_t inv){uint8_t h=0,t=0,base=16+(inv?96:0),*dst=canvas+(uint16_t)y*20+x;while(n>=100){n-=100;h++;}while(n>=10){n-=10;t++;}dst[0]=base+h;dst[1]=base+t;dst[2]=base+n;}
/* Exact additive checksum; the common sixteen-byte block avoids C stack spills. */
static uint16_t checksum_chunk(const uint8_t *buf,uint8_t n) __naked { __asm
 ld l,e
 ld h,d
 ld e,a
 ld bc,#0
 cp #16
 jr nz,checksum_loop$
 .rept 16
 ld a,(hl+)
 add a,c
 ld c,a
 ld a,b
 adc a,#0
 ld b,a
 .endm
 ret
checksum_loop$:
 ld a,(hl+)
 add a,c
 ld c,a
 ld a,b
 adc a,#0
 ld b,a
 dec e
 jr nz,checksum_loop$
 ret
 __endasm; }




static uint16_t getword(const uint8_t *p){return p[0]|((uint16_t)p[1]<<8);}
static void setword(uint8_t *p,uint16_t n){p[0]=n;p[1]=n>>8;}
static void offsets(void){uint8_t c;uint16_t n=0;for(c=0;c<7;c++){seqeventoffsets[c]=n;n+=seqeventcounts[c];}}






/* Legacy records remain untouched. Stage each source track independently so
   converting its three old arrays cannot overwrite the next unread track. */





void mixer_init(void) BANKED {uint8_t magic[4],i;ram(0);if(mx.magic==0xD3)return;memset(&mx,0,sizeof(mx));mx.magic=0xD3;mx.pending=255;mx.quant=4;mixer_pattern_changed();for(i=0;i<7;i++){mx.level[i]=127;mx.pan[i]=3;}if(sparse_enabled){if(sparse_enabled==1){sparse_restore(pool_root[7]<8?pool_root[7]:0);mx.quant=pool_root[8]<=7?pool_root[8]:4;sparse_finish_install();}else {defaults();mx.error=3;}return;}defaults();}

void mixer_boot(void) BANKED {ram(0);mx.magic=0;mixer_prepare_cancel();sparse_boot();mixer_init();mixer_layout_load();}
/* File-menu scratch overlays the drum-grid renderer only while that grid is
   covered. Audio state and the live pattern name remain independent. */
__at (0xAE98) static char file_name[17];
__at (0xAEA9) static uint8_t file_target;
uint8_t mixer_menu_pad(void) BANKED;
void mixer_file_confirm(uint8_t target,uint8_t saving) BANKED;
uint8_t sparse_save_pad_pattern(uint8_t pad,uint8_t index,const char *name) BANKED;
uint8_t sparse_load_pad_pattern(uint8_t index,uint8_t pad) BANKED;
void mixer_open(void) BANKED {if(page==19||page==20){file_target=mixer_menu_pad();getname(file_target,file_name);if(file_target==mx.slot)memcpy(file_name,mx.name,17);}mixer_prepare_cancel();mixer_init();if(page==18)mx.openempty=0;mixer_image.valid=0;pad_names_valid=0;fader_pending=0;fader_pattern=mx.slot;fader_ready_frame=sys_time+2;memset(fader_image_knob,255,6);mx.focus=page==18?mixer_view_focus:0;mx.edit=mx.naming=mx.letter=0;mx.browser=(page==24||page==25)?(sparse_song<POOL_SONGS?sparse_song:0):sparse_enabled&&page==20?mx.slot:sparse_enabled&&page==19?0:mx.slot;previewshape=255;mx.cachevalid=0;if(page==19||page==20){mx.pending=255;mx.presaved=mx.openempty=0;}mx.padcache=0;dirty=1;}
uint8_t mixer_velocity(uint8_t c,uint8_t v) BANKED {if(mx.magic!=0xD3||mx.level[c]==127)return v;if(!mx.level[c])return 0;{uint16_t n=(uint16_t)v*mx.level[c]+63;uint8_t q=n>>7;/* n<=16192: n=127*q+(q+(n&127)), with the remainder sum below254. */return q+((uint8_t)((n&127)+q)>=127);}}
uint8_t mixer_pan(uint8_t c) BANKED {return mx.magic==0xD3?mx.pan[c]:3;}
/* Source cache is16-byte aligned; destination WRAM need not be. Timer IRQs
   stay enabled and produce PCM independently while the complete pool installs. */
extern uint8_t seqnativeearly,seqnativelaunchfired,lastpad;
void seq_native_launch_installed(uint8_t slot) BANKED;
uint8_t seq_native_launch_boundary(void) BANKED;uint8_t seq_native_live_commit(void) BANKED;
static uint8_t retrigger(uint8_t quantized){uint8_t busy=seqservicing;seqservicing=1;
 mx.pending=255;mx.presaved=mx.openempty=0;if((!syncmode||!syncslave)&&!MIXER_KEEP_SYNC_GRID)mx.boundary=0;
 /* Same-pad repeats keep the pad image; queued/playing changes are diffed. */
 if(seqplaying){if(seqnativelaunchfired==mx.slot+1){seqnativeearly=1;seqnativelaunchfired=0;seq_native_launch_installed(mx.slot);}else seq_native_live_commit();seqrecordtrack=255;seqrecordlength=0;if(!quantized&&(!syncmode||!syncslave)){__critical {seqclock=seqticks=seqfraction=0;}}seq_pattern_handoff();}
 else {memset(seqposition,0,7);seqclock=seqticks=seqfraction=0;seqdeadline=1;}
 seqservicing=busy;if(page!=18||!mx.padcache||pad_image_playing!=mx.slot||pad_image_queued!=255)dirty=1;return 1;
}
static uint8_t switchslot(uint8_t s){return sparse_activate(s);}

void mixer_clock_reset(void) BANKED {if(mx.magic==0xD3)mx.boundary=0;}
/* Called before positions advance: the outgoing longest populated track
   must be on its last step. Muting does not shorten an arrangement. Scan
   only when LONG has an armed, prepared request; steady playback is unchanged. */
static uint8_t longest_boundary(void){uint8_t c,track=255;uint16_t longest=0;
 for(c=0;c<7;c++)if((!experimental_mode?(c<4||c==6):seqmode?c==4:c!=4)&&seqeventcounts[c]&&seqlength[c]>longest){longest=seqlength[c];track=c;}
 if(track==255){for(c=0;c<7;c++)if((!experimental_mode?(c<4||c==6):seqmode?c==4:c!=4)&&seqlength[c]>longest){longest=seqlength[c];track=c;}}
 return track<7&&(uint16_t)seqposition[track]+1>=longest;
}
static void held_rearm(void){
 /* Re-arm the live pad before testing this boundary. Holding A repeats at
    every eligible interval, including one-step LONG patterns. Retriggers use
    live data directly; switches and paired launches retain preparation.
    This only queues a request; an input action must not suppress its boundary. */
 if((padsampled&~(J_UP|J_DOWN|J_LEFT|J_RIGHT))==J_A&&(lastpad&J_A)&&page==18&&!navopen&&!MIXER_LINK_VIEW&&mx.quant&&mx.pending==255&&mx.focus==30+mx.slot&&!(linkpair&&MIXER_LINK_AVAILABLE)){mx.pending=mx.slot;mx.openempty=0;}
 }
static uint8_t launch_pending(void){if(link_pair_phase==2){link_pair_phase=5;sync_pattern();}return mx.pending==mx.slot?retrigger(1):switchslot(mx.pending);}
uint8_t mixer_half_boundary(void) BANKED {if(mx.magic!=0xD3||mx.quant!=7)return 0;held_rearm();if(mx.pending==255||mixer_prepare_busy()||link_pair_hold)return 0;return launch_pending();}
uint8_t mixer_boundary(void) BANKED {uint8_t interval;if(mx.magic!=0xD3)return 0;held_rearm();
 mx.boundary=(mx.boundary+1)&15;if(seq_native_launch_boundary())return 0;if(mx.pending==255||mixer_prepare_busy())return 0;if(link_pair_hold)return 0;interval=mx.quant&&mx.quant<5?1U<<mx.quant:1;if(mx.quant==5?longest_boundary():!(mx.boundary&(interval-1))){
 /* Both sides are prepared. Publish this boundary before installing the
    master's patch, so the slave installs alongside it rather than after it. */
 return launch_pending();}return 0;}
void mixer_name(void) BANKED {uint8_t i,ended=mx.magic!=0xD3;for(i=0;i<3;i++){if(!mx.name[i])ended=1;canvas[9+i]=(ended?' ':mx.name[i])-32+96;}}
/* Two pixel tiles per strip, outside both pad buffers and the restored font.
   The six-pixel knob travels ten pixels along a two-pixel-wide rail. */
static uint8_t scale127(uint16_t value){uint8_t q=value>>7;return q+((uint8_t)((value&127)+q)>=127);}
static uint8_t fader_tile(uint8_t slot,uint8_t part){uint8_t index=slot*7+part;return index<12?192+index:220+index-12;}
static void fader(uint8_t x,uint8_t slot,uint8_t value,uint8_t selected){uint8_t tile,knob=1+50-scale127((uint16_t)value*50+63),display=scale127((uint16_t)value*99+63),base=16+(selected?96:0);
 canvas[5*20+x+1]=base+display/10;canvas[5*20+x+2]=base+display%10;
 for(tile=0;tile<7;tile++)canvas[(uint16_t)(6+tile)*20+x+1]=fader_image_knob[slot]==255?0:fader_tile(slot,tile);
 fader_requested[slot]=knob;if(fader_image_knob[slot]!=knob)fader_pending|=1<<slot;else fader_pending&=~(1<<slot);
}
/* Sound, queued input, pad feedback and the launch settle interval all precede
   graphics. Unchanged rail tiles never need another upload. */
void mixer_fader_service(void) BANKED {uint8_t slot,tile,y,row,bits,id,old,knob,x,buf[16];uint16_t at;
 if(page!=18||navopen||MIXER_LINK_VIEW||!fader_pending||mx.pending!=255||seqservicing||padread!=padwrite||fader_last_frame==sys_time||(int16_t)(sys_time-fader_ready_frame)<0)return;
 if(seqplaying&&seqclock<seqthreshold&&seqthreshold-seqclock<(uint16_t)seqbpm*8)return;
 mixfill();if(mixrunning&&(!mixready[0]||!mixready[1]))return;
 for(slot=0;slot<6;slot++)if(fader_pending&(1<<slot))break;
 if(slot==6)return;old=fader_image_knob[slot];knob=fader_requested[slot];x=3+slot*3;
 for(tile=0;tile<7;tile++){
  if(old!=255&&tile!=old/8&&tile!=(old+2)/8&&tile!=knob/8&&tile!=(knob+2)/8)continue;
  for(y=0;y<8;y++){row=tile*8+y;bits=row>=1&&row<=53?0x18:0;if(row>=knob&&row<knob+3)bits=row==knob+1?0x42:0x7E;buf[y*2]=buf[y*2+1]=bits;}
  ui_upload_tile(fader_tile(slot,tile),buf,0);mixfill();
 }
 fader_image_knob[slot]=knob;fader_pending&=~(1<<slot);fader_last_frame=sys_time;
 if(old==255)for(tile=0;tile<7;tile++){id=fader_tile(slot,tile);at=(uint16_t)(6+tile)*20+x;canvas[at]=visible[at]=id;ui_upload_map(0x9800U+(uint16_t)(6+tile)*32+x,&id,1);mixfill();}
}
static const char namekeys[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
static const char * const nameactions[4]={"SPC","DEL","CLR","SAVE"};
static char *namebuffer(void){return page==25?sparse_song_name:page==20&&sparse_enabled?file_name:mx.name;}
uint8_t mixer_file_pad(void) BANKED {return file_target;}
uint8_t mixer_file_load(void) BANKED {uint8_t ok=sparse_load_pad_pattern(mx.browser,file_target);if(ok){page=18;mx.focus=mixer_view_focus;pad_names_valid=0;mx.padcache=0;}return ok;}
uint8_t mixer_file_save(void) BANKED {pad_names_valid=0;mx.error=0;if(page==25){if(!sparse_save_song(mx.browser)){mx.error=2;return 0;}}else if(sparse_enabled){if(!sparse_save_pad_pattern(file_target,mx.browser,file_name)){mx.error=2;return 0;}}else {snapshot(mx.browser);if(mx.error)return 0;if(mx.browser!=mx.slot)snapshot(mx.slot);if(mx.error)return 0;}mx.naming=0;mx.focus=mixer_view_focus;page=18;return 1;}
static void namesave(void){if(page==20&&sparse_enabled==1&&mx.browser<sparse_patterns){mixer_file_confirm(file_target,1);return;}mixer_file_save();}
static void nameopen(void){char *name=namebuffer();mx.naming=1;mx.focus=0;mx.letter=0;while(mx.letter<16&&name[mx.letter])mx.letter++;}
static void nameinput(uint8_t edge){uint8_t col=mx.focus<36?mx.focus%6:mx.focus-36,row=mx.focus<36?mx.focus/6:6;
 char *name=namebuffer();
 if(edge&J_SELECT){mx.naming=0;mx.focus=0;return;}
 if(edge&J_LEFT)col=col?col-1:(row==6?3:5);
 if(edge&J_RIGHT)col=(col+1)%(row==6?4:6);
 if(edge&J_UP){if(!row){row=6;if(col>3)col=3;}else row--;}
 if(edge&J_DOWN){if(row==6)row=0;else {row++;if(row==6&&col>3)col=3;}}
 mx.focus=row==6?36+col:row*6+col;
 if((edge&J_B)||((edge&J_A)&&mx.focus==37)){if(mx.letter)name[--mx.letter]=0;}
 else if(edge&J_A){if(mx.focus==39){namesave();return;}if(mx.focus==38){memset(name,0,17);mx.letter=0;}else if(mx.letter<16){name[mx.letter++]=mx.focus==36?' ':namekeys[mx.focus];name[mx.letter]=0;}}
 pad_names_valid=0;mx.padcache=0;
}
static void storage_footer(void);
static void namekeyboard(void){uint8_t i;char key[2];key[1]=0;
 text(0,1,page==25?"SONG":"SLOT",0);num(5,1,mx.browser+1,0);text(10,1,"NAME",0);
 for(i=0;i<16;i++)canvas[2*20+2+i]=(i<mx.letter?namebuffer()[i]:'_')-32;
 canvas[3*20+2+(mx.letter<16?mx.letter:15)]='^'-32;
 for(i=0;i<36;i++){key[0]=namekeys[i];text(2+(i%6)*3,5+i/6,key,mx.focus==i);if(!(i%6))mixfill();}
 for(i=0;i<4;i++)text(i*5,12,nameactions[i],mx.focus==36+i);
 text(0,14,"A TYPE  B DELETE",0);text(0,15,"D-PAD MOVE",0);text(0,16,"SELECT BACK",0);
 if(mx.error)text(0,16,pool_error==2?"SAVE DATA DAMAGED":"NOT ENOUGH SPACE",0);
 storage_footer();
}
static void space_number(uint8_t x,uint8_t y,uint16_t n,uint8_t digits){uint16_t place=digits==5?10000:digits==3?100:10;uint8_t d;
 while(digits--){d=0;while(n>=place){n-=place;d++;}canvas[(uint16_t)y*20+x++]=16+d;place/=10;}
}
static void storage_footer(void){uint16_t free;if(sparse_enabled!=1)return;free=pool_free();text(0,17,"FREE",0);space_number(5,17,free,5);text(10,17,"B",0);space_number(13,17,((uint32_t)free*100)/(300U*62U),3);text(16,17,"%",0);}
static void song_render(void){uint8_t i,start=mx.browser>3?mx.browser-3:0;char name[17];uint16_t needed;
 if(sparse_enabled!=1){text(0,4,"LEGACY SAVE FORMAT",0);text(0,6,"IMPORT ON COMPUTER",0);return;}
 if(mx.naming){namekeyboard();return;}if(start>POOL_SONGS-8)start=POOL_SONGS-8;
 for(i=start;i<start+8;i++){sparse_get_song_name(i,name);num(0,2+i-start,i+1,mx.browser==i);text(4,2+i-start,name[0]?name:"EMPTY",mx.browser==i);mixfill();}
 if(page==25){text(0,11,"NAME",0);text(0,12,sparse_song_name,0);text(0,14,"A NAME  B SAVE",0);text(0,15,"FROM PAD",0);num(10,15,file_target+1,0);needed=sparse_song_size();text(0,15,"NEED",0);space_number(5,15,needed,5);text(10,15,"B",0);}
 else {text(0,12,"A LOAD WHOLE SONG",0);text(0,14,"B DELETE SONG",0);}
 if(mx.error)text(0,16,pool_error==2?"SAVE DATA DAMAGED":"NOT ENOUGH SPACE",0);storage_footer();
}
static void pattern_library_render(void){uint8_t i,start=mx.browser>3?mx.browser-3:0,count=sparse_patterns;char name[17];
 if(mx.naming){namekeyboard();return;}if(count>8&&start>count-8)start=count-8;
 for(i=start;i<count&&i<start+8;i++){sparse_library_name(i,name);num(0,2+i-start,i+1,mx.browser==i);text(4,2+i-start,i==sparse_patterns?"NEW PATTERN":name[0]?name:"UNTITLED",mx.browser==i);mixfill();}
 if(!count)text(0,3,"NO SAVED PATTERNS",0);
 if(page==20){text(0,11,"NAME",0);text(0,12,file_name,0);text(0,14,"A NAME  B SAVE",0);text(0,15,"FROM PAD",0);num(10,15,file_target+1,0);}else {text(0,12,"A LOAD INTO LIVE PAD",0);text(0,14,"SHARED BY ALL SONGS",0);}
 if(mx.error)text(0,16,"NOT ENOUGH SPACE",0);storage_footer();
}
static char *pad_hint(void){uint8_t state;if(mx.error)return sparse_enabled?(pool_error==2?"SAVE DATA DAMAGED":"NOT ENOUGH SPACE"):"PATTERN >256 EVENTS";if(link_pair_phase)return "PAIR PREPARING...";if(linkpair&&linkstate!=2)return "PAIR NEEDS LINK";if(mx.focus==64)return "A+ARROWS B OFF";if(mx.focus>=65)return "A/B+ARROWS VOLUME";if(mx.focus>=38)return "A/B TOGGLE";if(mx.focus<30)return "A PICK B EDIT";state=mixer_prepare_status(mx.focus-30);return state==1?"READY A/B":state==2?"PREPARING...":state==3?"QUEUED":"A PICK B EDIT";}
void mixer_render(void) BANKED {uint8_t c,i,rendering_slot;char name[17];mixer_init();rendering_slot=mx.slot;
 if(page==18&&MIXER_LINK_VIEW){mixer_image.valid=0;mixer_link_render();return;}
 /* Pad navigation changes only the two pattern rows and their footer. Reuse
    the published strip image when every value that affects it is unchanged. */
 if(page==18&&!navopen&&mixer_image.valid&&canvas[0]=='M'-32+96&&canvas[1]=='I'-32+96&&mx.focus>=30&&mx.focus<38&&mixer_image.focus>=30&&mixer_image.focus<38&&mixer_image.tempo==seqglobalbpm&&mixer_image.quant==mx.quant&&mixer_image.playing==seqplaying&&mixer_image.edit==mx.edit&&mixer_image.mode==experimental_mode&&mixer_image.muted==seqmuted&&mixer_image.solo==seqsolo&&mixer_image.drummute==drummutemask&&mixer_image.drumsolo==drumsolomask&&!memcmp(mixer_image.strips,mx.level,14))goto pattern_controls;
 mixer_image.valid=0;memset(canvas,0,360);mixfill();memset(canvas,96,20);text(0,0,page==18?"MIXER":page==19?"LOAD PATTERN":page==24?"LOAD SONG":page==25?"SAVE SONG":"SAVE PATTERN",1);mixfill();
 if(sparse_enabled==2&&page!=18){text(0,4,"SAVE NOT RECOGNIZED",0);text(0,6,"LOAD A VALID SAVE",0);return;}
 if(page==24||page==25){song_render();return;}
 if(sparse_enabled&&(page==19||page==20)){pattern_library_render();return;}
 if(page==20&&mx.naming){namekeyboard();return;}
 if(page!=18){for(i=0;i<8;i++){getname(i,name);num(0,2+i,i+1,mx.browser==i);text(4,2+i,name[0]?name:"EMPTY",mx.browser==i);mixfill();}if(page==20){text(0,11,"NAME",0);text(0,12,mx.name,0);text(0,14,"A NAME WITH KEYBOARD",0);text(0,15,"B SAVE",0);}else {text(0,12,"A LOAD INTO PAD",0);num(16,12,file_target+1,0);}if(mx.error)text(0,16,sparse_enabled?"NOT ENOUGH SPACE":"TOO MANY NOTES (>512)",0);storage_footer();return;}
 if(fader_pattern!=mx.slot){fader_pattern=mx.slot;fader_ready_frame=sys_time+2;}
 if(ui_font_upload_pending){ui_transition_begin();ui_font_upload_pending=0;}mixerfontdirty=1;
 /* A new strip viewport replaces pending graphics requests from the old one. */
 fader_pending=0;
 text(15,0,"LOCAL",1);text(8,0,seqplaying?"STOP":"PLAY",mx.focus!=0);text(0,1,"BPM",0);if(seqglobalbpm)num(4,1,seqglobalbpm,mx.focus==64);else text(4,1,"OFF",mx.focus==64);
 {const char *quant=mx.quant==0?"NOW":mx.quant==7?"1/32":mx.quant==6?"1/16":mx.quant==1?"1/8":mx.quant==2?"1/4":mx.quant==3?"1/2":mx.quant==5?"LONG":"1/1";uint8_t x=20-7-strlen(quant);text(x,1,"LAUNCH",0);text(x+7,1,quant,mx.focus==1);}mixfill();
 /* Six vertical strips fit beside the shared control labels. */
 {uint8_t col=mx.focus>=65?17+mx.focus-65:mx.focus==64?0:mx.focus>=38?7+(mx.focus-38)/2:mx.focus>=2&&mx.focus<30?(mx.focus-2)/4:0;
  col=stripcolumn(col);
  if(mx.focus>=2&&mx.focus<68&&mx.focus!=64&&(mx.focus<30||mx.focus>=38)){if(col<mixscroll)mixscroll=col;if(col>=mixscroll+6)mixscroll=col-5;}
 }
 text(0,3,"M",0);text(0,4,"S",0);text(0,5,"V",0);text(0,13,"P",0);
 {uint8_t col=0,order;for(order=0;order<20;order++){uint8_t f,x;c=striporder[order];if(!strip_visible(c))continue;if(col<mixscroll||col>=mixscroll+6){col++;continue;}x=2+(col-mixscroll)*3;
  if(c<7){f=2+c*4;field_center(x,2,3,tracks[c],0);text(x+1,3,(seqmuted&(1<<c))?"M":"-",mx.focus==f);text(x+1,4,(seqsolo&(1<<c))?"S":"-",mx.focus==f+1);fader(x,col-mixscroll,mx.level[c],mx.focus==f+2);text(x,13,pans[mx.pan[c]],mx.focus==f+3);}
  else {uint8_t voice=c-7;uint16_t bit=1U<<voice;f=38+voice*2;text(x,2,mixer_drum_name(drumkit,voice),0);text(x+1,3,drummutemask&bit?"M":"-",mx.focus==f);text(x+1,4,drumsolomask&bit?"S":"-",mx.focus==f+1);if(voice>=10)fader(x,col-mixscroll,evalpatch[4][voice-10],mx.focus==65+voice-10);}
  mixfill();col++;
 }}
 pattern_controls:
 mixer_pads_render();
 memset(canvas+17*20,0,20);text(0,17,pad_hint(),0);mixfill();
 mixer_image.valid=!navopen&&rendering_slot==mx.slot;mixer_image.focus=mx.focus;mixer_image.quant=mx.quant;mixer_image.tempo=seqglobalbpm;mixer_image.playing=seqplaying;mixer_image.edit=mx.edit;mixer_image.mode=experimental_mode;mixer_image.muted=seqmuted;mixer_image.solo=seqsolo;mixer_image.drummute=drummutemask;mixer_image.drumsolo=drumsolomask;memcpy(mixer_image.strips,mx.level,14);
}
extern void seq_mixer_mute(uint8_t c,uint8_t solo) BANKED;
extern void seq_mixer_refresh(void) BANKED;
static void mutechange(uint8_t c,uint8_t solo){if(!syncmode){seqirqready=0;seqirqdirty=1;}mixer_pattern_changed();seq_mixer_mute(c,solo);}
/* Focus IDs stay stable for pattern storage and external tools. */
static uint8_t stripfocus(uint8_t c,uint8_t field){return c<7?2+c*4+field:c>=17&&field==2?65+c-17:38+(c-7)*2+(field>1?1:field);}
static void stripnav(uint8_t edge){uint8_t c=mx.focus>=65?17+mx.focus-65:mx.focus>=38?7+(mx.focus-38)/2:(mx.focus-2)/4,field=mx.focus>=65?2:mx.focus>=38?(mx.focus-38)%2:(mx.focus-2)%4;
 if(edge&J_LEFT){uint8_t n=stripposition(c);while(n){n--;if(strip_visible(striporder[n])){c=striporder[n];break;}}}
 if(edge&J_RIGHT){uint8_t n=stripposition(c);while(n<19){n++;if(strip_visible(striporder[n])){c=striporder[n];break;}}}
 if(edge&J_UP){if(field)field--;else {mx.focus=0;return;}}
 if(edge&J_DOWN){if(field<(c<7?3:c>=17?2:1))field++;else {mx.focus=firstpad();return;}}
 if(c>=7&&c<17&&field>1)field=1;mx.focus=stripfocus(c,field);
}
extern uint8_t drumnoiseowned;
static void livepan(uint8_t c){uint8_t pan=mx.pan[c],mask,bit;if(c==4)return;if(c==5)c=2;if(c==6){mask=(waveengine==3?0x44:0)|(drumnoiseowned?0x88:0)|(pulsekickleft?0x11:0);route&=~mask;if(pan&1)route|=mask&15;if(pan&2)route|=mask&240;NR51_REG=route;return;}if(c==0&&pulsekickleft){param[0][21]=pan;return;}if(c==2&&waveengine==3)return;bit=1<<c;mask=bit|(bit<<4);route&=~mask;if(pan&1)route|=bit;if(pan&2)route|=bit<<4;param[c][21]=pan;NR51_REG=route;}
static void change(uint8_t c,uint8_t field,int8_t delta){int16_t n=(int16_t)(field==2?mx.level[c]:mx.pan[c])+delta;mixer_pattern_changed();if(field==2){mx.level[c]=n<0?0:n>127?127:n;if(c==6&&waveengine==3){uint8_t v=mx.level[6];pcmoutlevel=!v?0:v<=42?3:v<=84?2:1;NR32_REG=pcmoutlevel<<5;}}else {mx.pan[c]=n<0?0:n>3?3:n;livepan(c);}if(!syncmode&&field==2)seq_irq_refresh(c);}
void mixer_remote_apply(uint8_t c,uint8_t field,uint8_t value) BANKED {
 if(field==5){if(value>=1&&value<=7)mx.quant=value;dirty=1;return;}
 if(c<7){if(field<2){uint8_t mask=field?seqsolo:seqmuted;if(!!(mask&(1<<c))!=value)mutechange(c,field);}
  else if(field==2&&value<=127)change(c,field,(int16_t)value-mx.level[c]);
  else if(field==3&&value<=3)change(c,field,(int8_t)value-mx.pan[c]);
 }else if(c<20&&field<2){uint16_t bit=1U<<(c-7);mixer_pattern_changed();if(field){if(value)drumsolomask|=bit;else drumsolomask&=~bit;}else {if(value)drummutemask|=bit;else drummutemask&=~bit;}seq_mixer_refresh();}
 dirty=1;
}

void mixer_tempo_edit(int16_t delta) BANKED {int16_t bpm;if(syncmode&&syncslave&&(syncmode!=1||syncrole||seqplaying))return;if(!syncmode){seqirqready=0;seqirqdirty=1;}if(seqplaying)seq_frame();bpm=(int16_t)seqbpm+delta;seqbpm=bpm<30?30:bpm>300?300:bpm;if(seqglobalbpm)seqglobalbpm=seqbpm;seqcachedbpm=0;seqdeadline=1;dirty=1;}
static void warmfocus(void){mixer_prepare_focus(mx.focus>=30&&mx.focus<38?mx.focus-30:255);}
void mixer_input(uint8_t p,uint8_t edge) BANKED {uint8_t c,f;
 /* Remote/paired launches re-arm only after the preceding request drains.
    This is foreground input, never a clock/serial interrupt or frame timer.
    NOW remains one-shot: an unquantized hold must not hammer the transport. */
 if(!edge&&page==18&&(p&~(J_UP|J_DOWN|J_LEFT|J_RIGHT))==J_A&&seqplaying&&mx.focus>=30&&mx.focus<38){
  if(MIXER_LINK_VIEW){if(linkmirror.quant&&linkmirror.quant<=7&&linkmirror.pending==255&&!link_pending())edge=J_A;}
  else if(linkpair&&MIXER_LINK_AVAILABLE&&mx.quant&&mx.pending==255&&!mx.error&&!mixer_prepare_busy()&&!link_pair_phase)edge=J_A;
 }
 if(!edge)return;mixer_init();if(page==18&&padflash_off&&(edge&(J_A|J_B)))mixer_pad_restore();
 /* Move first, then dispatch a launch to the destination device. Keep A held
    through preparation and subsequent musical retrigger boundaries. */
 if((edge&(J_LEFT|J_RIGHT))&&page==18&&(p&J_A)&&!(p&J_B)&&mx.focus>=30&&mx.focus<38){mixer_pads_move(edge&J_LEFT?-1:1);edge=J_A;}
 if(page==18&&MIXER_LINK_VIEW){mixer_link_input(p,edge);return;}
 if(page==18&&(p&J_A)&&mx.focus>=30&&mx.focus<38&&(edge&(J_UP|J_DOWN))){mx.quant=(edge&J_UP)?MIXER_QUANT_DOWN(mx.quant):MIXER_QUANT_UP(mx.quant);if(syncmode&&syncslave&&!mx.quant)mx.quant=7;seqdeadline=1;mixer_image.valid=0;dirty=1;return;}
 if((page==20||page==25)&&mx.naming){nameinput(edge);dirty=1;return;}
 if(page==24||page==25){if(sparse_enabled!=1)return;if(edge&J_UP)mx.browser=mx.browser?mx.browser-1:POOL_SONGS-1;if(edge&J_DOWN)mx.browser=(mx.browser+1)%POOL_SONGS;
  if(edge&J_A){if(page==25)nameopen();else if(sparse_load_song(mx.browser)){page=18;mx.focus=mixer_view_focus;pad_names_valid=0;}else mx.error=1;}
  if(edge&J_B){if(page==25)namesave();else clear_song_open(mx.browser);}dirty=1;return;
 }
 if(sparse_enabled&&(page==19||page==20)){uint8_t count=sparse_patterns;
  if(count){if(edge&J_UP)mx.browser=mx.browser?mx.browser-1:count-1;if(edge&J_DOWN)mx.browser=(mx.browser+1)%count;}
  if(edge&J_A){if(page==20)nameopen();else if(sparse_slots[file_target]!=POOL_NONE||(file_target==mx.slot&&seq_event_total()))mixer_file_confirm(file_target,0);else if(!mixer_file_load())mx.error=2;}
  if(page==20&&(edge&J_B))namesave();dirty=1;return;
 }
 if(page!=18){mixer_prepare_barrier();
 {if(edge&J_UP)mx.browser=mx.browser?mx.browser-1:7;if(edge&J_DOWN)mx.browser=(mx.browser+1)&7;if(edge&J_A){if(page==20){nameopen();}else if(valid(mx.browser)){uint8_t run=seqplaying;if(run)seq_transport();if(!restore(mx.browser,0)){if(run)seq_transport();dirty=1;return;}snapshot(mx.slot);seqdrawvalid=0;if(run)seq_transport();page=18;mx.focus=mixer_view_focus;mx.padcache=0;}}}
 if(page==20&&(edge&J_B)){namesave();}dirty=1;return;}
 /* Tempo is a separate header control; keep existing strip IDs stable. */
 if(mx.focus==64){
  if(syncmode&&syncslave&&(syncmode!=1||syncrole||seqplaying)&&((p&J_A)||(edge&J_B)))return;
  if(p&(J_A|J_B)){if(!seqglobalbpm){seqglobalbpm=seqbpm;}else {int16_t bpm=seqglobalbpm;if(edge&J_UP)bpm++;if(edge&J_DOWN)bpm--;if(edge&J_LEFT)bpm-=10;if(edge&J_RIGHT)bpm+=10;if(seqplaying)seq_frame();seqglobalbpm=seqbpm=bpm<30?30:bpm>300?300:bpm;seqcachedbpm=0;seqdeadline=1;}}
  
  else if(edge&J_UP)mx.focus=1;
  else if(edge&J_DOWN){c=firststrip();mx.focus=c<20?stripfocus(c,0):firstpad();}
  else if(edge&(J_LEFT|J_RIGHT))mx.focus=0;
  mixer_image.valid=0;warmfocus();dirty=1;return;
 }
 if(mx.focus>=65&&mx.focus<=67){mx.edit=0;if(p&(J_A|J_B)){int16_t value=evalpatch[4][mx.focus-65];if(edge&J_UP)value++;if(edge&J_DOWN)value--;if(edge&J_RIGHT)value+=10;if(edge&J_LEFT)value-=10;evalpatch[4][mx.focus-65]=value<0?0:value>127?127:value;mixer_pattern_changed();}else stripnav(edge);mixer_image.valid=0;warmfocus();dirty=1;return;}
 if(mx.focus>=38){uint16_t bit=1U<<((mx.focus-38)/2);mx.edit=0;
  if(edge&(J_A|J_B)){mixer_pattern_changed();if(mx.focus&1)drumsolomask^=bit;else drummutemask^=bit;seq_mixer_refresh();}
  stripnav(edge);warmfocus();
  dirty=1;return;
 }
 if(mx.focus>=30){if(edge&(J_LEFT|J_RIGHT))mixer_pads_move(edge&J_LEFT?-1:1);if(edge&J_UP){c=firststrip();mx.focus=c<20?stripfocus(c,3):0;}else {if(edge&J_A){uint8_t start=!seqplaying,target=mx.focus-30;mx.error=0;mixer_launch_request(target,0);if(start&&mx.slot==target&&!mx.error&&!mixer_prepare_busy()){mx.openempty=0;page=18;seq_transport();}}if(edge&J_B)mixer_launch_request(mx.focus-30,1);}warmfocus();dirty=1;return;}
 if(mx.focus>=2){c=(mx.focus-2)/4;f=(mx.focus-2)%4;if(f>=2){mx.edit=0;if(p&(J_A|J_B)){int8_t delta=0;if(edge&J_UP)delta++;if(edge&J_DOWN)delta--;if(edge&J_LEFT)delta-=10;if(edge&J_RIGHT)delta+=10;if(delta)change(c,f,delta);dirty=1;return;}}else if(edge&(J_A|J_B)){mutechange(c,f);dirty=1;return;}}
 if(mx.focus>=2){if(!mx.edit&&!(p&(J_A|J_B)))stripnav(edge);}
 else if(!(p&(J_A|J_B))) {if(edge&J_LEFT)mx.focus=mx.focus?0:1;if(edge&J_RIGHT)mx.focus=mx.focus?0:1;if(edge&J_UP)mx.focus=firstpad();if(edge&J_DOWN)mx.focus=64;}
 if(mx.focus>=2&&mx.focus<30&&(mx.focus-2)%4<2)mx.edit=0;
 if(mx.focus==0){if(edge&(J_A|J_B)){seq_transport();mx.boundary=0;}}
 else if(mx.focus==1){if((p&(J_A|J_B))&&(edge&(J_UP|J_DOWN|J_LEFT|J_RIGHT)))mx.quant=(edge&(J_UP|J_RIGHT))?MIXER_QUANT_DOWN(mx.quant):MIXER_QUANT_UP(mx.quant);if(syncmode&&syncslave&&!mx.quant)mx.quant=7;}
 warmfocus();dirty=1;
}

/* The eighth pattern ends at bank 3 B3FF. The remaining B400..BFFF is
   reserved for a track clipboard, separate from renderer and sample RAM. */
#define CLIP ((uint8_t *)0xB400)
static void clip_part(uint16_t offset,uint8_t *data,uint16_t count,uint8_t writing){
 uint8_t buf[16],n;while(count){n=count>16?16:count;
  if(writing)memcpy(buf,data,n);
  __critical {ram(3);if(writing)memcpy(CLIP+offset,buf,n);else memcpy(buf,CLIP+offset,n);ram(0);}
  if(!writing)memcpy(data,buf,n);data+=n;offset+=n;count-=n;mixfill();
 }
}
void seq_copy(void) BANKED {uint8_t c=seqtrack,meta[16]={0},e[4];uint16_t i,n=seq_event_count(c);if(seqgrouptrack==c){seq_region_copy(0);return;}meta[1]=c;setword(meta+2,n);setword(meta+4,seqlength[c]);setword(meta+6,seqdefaultdur[c]);meta[8]=127;meta[9]=100;meta[10]=seqpitch[c];meta[11]=0x73;clip_part(0,meta,16,1);for(i=0;i<n;i++){seq_event_get(c,i,e);clip_part(16+i*4,e,4,1);}meta[0]=0xC8;clip_part(0,meta,1,1);}
void seq_paste(void) BANKED {uint8_t c=seqtrack,meta[16],e[4];uint16_t i,n;clip_part(0,meta,16,0);if(meta[0]==0xC9){seq_region_paste(seqcursor[c],c==6?drumrow:seqpitch[c]);return;}n=getword(meta+2);if(meta[0]!=0xC8||meta[11]!=0x73||n>256||seq_event_total()-seq_event_count(c)+n>256)return;seq_track_clear(c);for(i=0;i<n;i++){clip_part(16+i*4,e,4,0);if(c==6){if(e[1]>13)e[1]=13;}else if(meta[1]==6)e[1]=seqpitch[c]+1;seq_event_put(c,65535U,e);}seqlength[c]=getword(meta+4);seqdefaultdur[c]=getword(meta+6);if(c<3)evalpatch[c][EV_CHORD_HISTORY]=1;mixer_pattern_changed();seqdrawvalid=0;dirty=1;}
void mixer_activate(uint8_t slot,uint8_t edit) BANKED {if(slot==mx.slot){retrigger(0);return;}if(sparse_enabled){if(sparse_activate(slot)&&edit){page=8;seq_open();}return;}if(switchslot(slot)&&edit){page=8;seq_open();}}


#pragma bank 18
#pragma opt_code_speed
#include "api.h"
#include "mixer.h"
#include "tones.h"
#include "sparse_store.h"
extern uint8_t toneready,syncrole;
extern volatile uint8_t padsampled;
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
static const char * const tracks[7]={"P1","P2","W1","N1","M1","W2","D1"};
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
static uint8_t layout_hidden(uint8_t id){return mixer_hidden[(MIXER_LINK_VIEW?4:0)+(id>>3)]&(1U<<(id&7));}
static uint8_t strip_visible(uint8_t c){return !layout_hidden(c)&&(experimental_mode||(c!=4&&c!=5));}
static uint8_t firststrip(void){uint8_t c;for(c=0;c<20;c++)if(strip_visible(c))return c;return 255;}
static uint8_t firstpad(void){uint8_t c;for(c=0;c<8;c++)if(!layout_hidden(20+c))return 30+c;return 0;}
static uint8_t stripcolumn(uint8_t c){uint8_t i,n=0;for(i=0;i<c;i++)if(strip_visible(i))n++;return n;}
/* Page-local graphics caches share only renderer scratch, never audio state.
   Opening Mixer invalidates them after any roll has reused those addresses. */
__at (0xACC4) uint8_t pad_image_playing;
__at (0xACC5) uint8_t pad_image_queued;
__at (0xACC6) uint8_t pad_names_valid;
__at (0xACC7) uint8_t fader_image_knob[5];
extern __at (0xAE40) uint8_t pad_names[8][5];
typedef struct {uint8_t valid,focus,quant,playing,edit,mode,muted,solo;uint16_t drummute,drumsolo,tempo;uint8_t strips[14];} MixerImage;
__at (0xAE68) MixerImage mixer_image;
static void ram(uint8_t b){ENABLE_RAM;SWITCH_RAM(b);}
static uint8_t bank(uint8_t s){return 1+s/3;}
static uint8_t *record(uint8_t s){return (uint8_t *)(0xA000U+(uint16_t)(s%3)*RECORD);}
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
static void num(uint8_t x,uint8_t y,uint8_t n,uint8_t inv){uint8_t h=0,t=0,base=16+(inv?96:0),*dst=canvas+(uint16_t)y*20+x;if(n>=100){n-=100;h=1;}while(n>=10){n-=10;t++;}dst[0]=base+h;dst[1]=base+t;dst[2]=base+n;}
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
static uint8_t *liveevent(uint16_t n){return n<256?seqevents_lo[n]:seqevents_hi[n-256];}
static void offsets(void){uint8_t c;uint16_t n=0;for(c=0;c<7;c++){seqeventoffsets[c]=n;n+=seqeventcounts[c];}}






/* Legacy records remain untouched. Stage each source track independently so
   converting its three old arrays cannot overwrite the next unread track. */





void mixer_init(void) BANKED {uint8_t magic[4],i;ram(0);if(mx.magic==0xD3)return;memset(&mx,0,sizeof(mx));mx.magic=0xD3;mx.pending=255;mx.quant=4;mixer_pattern_changed();for(i=0;i<7;i++){mx.level[i]=127;mx.pan[i]=3;}if(sparse_enabled){if(sparse_enabled==1){sparse_restore(pool_root[7]<8?pool_root[7]:0);mx.quant=pool_root[8]<=5?pool_root[8]:4;sparse_finish_install();}else {defaults();mx.error=3;}return;}readpart(0,2500,magic,4);if(memcmp(magic,"GBM2",4)){for(i=0;i<8;i++){uint8_t z=0;writepart(i,0,&z,1);}memcpy(magic,"GBM2",4);writepart(0,2500,magic,4);}else if(valid(0))restore(0,0);}
void mixer_boot(void) BANKED {ram(0);mx.magic=0;mixer_prepare_cancel();if(!sparse_boot())mixer_journal_recover();mixer_init();mixer_layout_load();}
/* File-menu scratch overlays the drum-grid renderer only while that grid is
   covered. Audio state and the live pattern name remain independent. */
__at (0xAE98) static char file_name[17];
__at (0xAEA9) static uint8_t file_target;
uint8_t mixer_menu_pad(void) BANKED;
void mixer_file_confirm(uint8_t target,uint8_t saving) BANKED;
uint8_t sparse_save_pad_pattern(uint8_t pad,uint8_t index,const char *name) BANKED;
uint8_t sparse_load_pad_pattern(uint8_t index,uint8_t pad) BANKED;
void mixer_open(void) BANKED {if(page==19||page==20){file_target=mixer_menu_pad();getname(file_target,file_name);if(file_target==mx.slot)memcpy(file_name,mx.name,17);}mixer_prepare_cancel();mixer_init();mixer_image.valid=0;pad_names_valid=0;memset(fader_image_knob,255,5);mx.focus=page==18?mixer_view_focus:0;mx.edit=mx.naming=mx.letter=0;mx.browser=(page==24||page==25)?(sparse_song<POOL_SONGS?sparse_song:0):sparse_enabled&&page==20?sparse_patterns:sparse_enabled&&page==19?0:mx.slot;previewshape=255;mx.cachevalid=0;if(page==19||page==20){mx.pending=255;mx.presaved=mx.openempty=0;}mx.padcache=0;dirty=1;}
uint8_t mixer_velocity(uint8_t c,uint8_t v) BANKED {if(mx.magic!=0xD3||mx.level[c]==127)return v;if(!mx.level[c])return 0;{uint16_t n=(uint16_t)v*mx.level[c]+63;uint8_t q=n>>7;/* n<=16192: n=127*q+(q+(n&127)), with the remainder sum below254. */return q+((uint8_t)((n&127)+q)>=127);}}
uint8_t mixer_pan(uint8_t c) BANKED {return mx.magic==0xD3?mx.pan[c]:3;}
/* Source cache is16-byte aligned; destination WRAM need not be. Timer IRQs
   stay enabled and produce PCM independently while the complete pool installs. */
static void install_events(void) __naked { __asm
 ld de,#0xb020
 ld hl,#_seqevents_lo
 ld c,#64
install_low$:
 .rept 16
 ld a,(de)
 inc e
 ld (hl+),a
 .endm
 ld a,e
 or a,a
 jr nz,install_low_page$
 inc d
install_low_page$:
 dec c
 jr nz,install_low$
 ld hl,#0xa800
 ld c,#64
install_high$:
 .rept 16
 ld a,(de)
 inc e
 ld (hl+),a
 .endm
 ld a,e
 or a,a
 jr nz,install_high_page$
 inc d
install_high_page$:
 dec c
 jr nz,install_high$
 ret
 __endasm; }
static void prime(void){applymeta(CACHE+META);if(toneready)tones_apply();seqstepunits=PREP_STEP;memcpy(seqgateunits,PREP_UNITS,14);memcpy(seqcachedgate,CACHE+META+49,7);seqcachedbpm=seqglobalbpm?0:seqbpm;memcpy(mx.name,CACHE+1,17);mx.name[16]=0;seqeventcache=1;}
/* Keep sounding voices and their gates during a live retrigger. New beat-one
   onsets replace their own voices; rests retain the previous release tails.
   Relaunch the live pattern directly: restoring its saved slot would discard
   edits made since the last snapshot and add SRAM work at the boundary. */
static uint8_t retrigger(uint8_t quantized){uint8_t busy=seqservicing;seqservicing=1;
 mx.pending=255;mx.presaved=mx.openempty=0;if((!syncmode||!syncslave)&&!MIXER_KEEP_SYNC_GRID)mx.boundary=0;mx.padcache=0;
 if(seqplaying){seqrecordtrack=255;seqrecordlength=0;if(!quantized&&(!syncmode||!syncslave)){__critical {seqclock=seqticks=seqfraction=0;}}seq_pattern_handoff();}
 else {memset(seqposition,0,7);seqclock=seqticks=seqfraction=0;seqdeadline=1;}
 seqservicing=busy;dirty=1;return 1;
}
static uint8_t switchslot(uint8_t s){uint8_t run=seqplaying,busy=seqservicing,primed,handoff;uint16_t oldbpm,residual,generation;
 if(sparse_enabled)return sparse_activate(s);
 if(!mx.cachevalid||mx.cacheslot!=s||(page!=18&&!link_ui_hold))prefetch(s);if(mx.cachevalid==3){mx.pending=255;mx.presaved=0;mx.error=1;dirty=1;return 0;}
 /* Save while the outgoing pattern still plays, including quantize OFF.
    Compute eligibility after prefetch so immediate launches use the cache. */
 mx.pending=255;if(!mx.presaved||(page!=18&&!link_ui_hold))autosnapshot(mx.slot);mx.presaved=0;
 primed=run&&mx.cachevalid==1;handoff=(run&&syncmode&&syncslave)||(primed&&seqmode==(experimental_mode?CACHE[META+74]:0));oldbpm=seqbpm;residual=seqclock;
 generation=pattern_generation;if(handoff){seqservicing=1;}else if(run)seq_transport();mx.slot=s;if(primed)prime();else restore(s,1);if((!syncmode||!syncslave)&&!MIXER_KEEP_SYNC_GRID)mx.boundary=0;seqdeadline=1;memset(seqcursor,0,7);seqdrawvalid=0;mx.padcache=0;
 if(handoff){seq_pattern_release();if(oldbpm!=seqbpm)seqclock=((uint32_t)residual*seqbpm)/oldbpm;seq_pattern_handoff();}else {memset(seqposition,0,7);if(run)seq_transport();}
 if(primed){seqservicing=1;install_events();seqeventcache=0;mx.cachevalid=0;seqservicing=busy;if(generation==pattern_generation)mixer_pattern_clean();}
 if(mx.openempty){mx.openempty=0;if(!link_ui_hold){page=8;seq_open();}}dirty=1;return 1;}
void mixer_clock_reset(void) BANKED {if(mx.magic==0xD3)mx.boundary=0;}
/* Called before positions advance: the outgoing longest populated track
   must be on its last step. Muting does not shorten an arrangement. Scan
   only when LONG has an armed, prepared request; steady playback is unchanged. */
static uint8_t longest_boundary(void){uint8_t c,track=255;uint16_t longest=0;
 for(c=0;c<7;c++)if((!experimental_mode?(c<4||c==6):seqmode?c==4:c!=4)&&seqeventcounts[c]&&seqlength[c]>longest){longest=seqlength[c];track=c;}
 if(track==255){for(c=0;c<7;c++)if((!experimental_mode?(c<4||c==6):seqmode?c==4:c!=4)&&seqlength[c]>longest){longest=seqlength[c];track=c;}}
 return track<7&&(uint16_t)seqposition[track]+1>=longest;
}
uint8_t mixer_boundary(void) BANKED {uint8_t interval;if(mx.magic!=0xD3)return 0;
 /* Sample the held pad at the musical boundary, not after a slow redraw.
    Retrigger live data only; switches and paired launches still prepare via
    their normal request/ready path. No storage or cable work is added here. */
 if(padsampled==J_A&&page==18&&!navopen&&!MIXER_LINK_VIEW&&mx.quant&&mx.pending==255&&mx.focus==30+mx.slot&&!(linkpair&&MIXER_LINK_AVAILABLE))mx.pending=mx.slot;
 mx.boundary=(mx.boundary+1)&15;if(mx.pending==255||mixer_prepare_busy())return 0;if(link_pair_hold)return 0;interval=mx.quant&&mx.quant<5?1U<<mx.quant:1;if(mx.quant==5?longest_boundary():!(mx.boundary&(interval-1))){
 /* Both sides are prepared. Publish this boundary before installing the
    master's patch, so the slave installs alongside it rather than after it. */
 if(link_pair_phase==2){link_pair_phase=5;sync_pattern();}
 return mx.pending==mx.slot?retrigger(1):switchslot(mx.pending);}return 0;}
void mixer_name(void) BANKED {uint8_t i,ended=mx.magic!=0xD3;for(i=0;i<3;i++){if(!mx.name[i])ended=1;canvas[9+i]=(ended?' ':mx.name[i])-32+96;}}
/* Two pixel tiles per strip, outside both pad buffers and the restored font.
   The six-pixel knob travels ten pixels along a two-pixel-wide rail. */
static uint8_t scale127(uint16_t value){uint8_t q=value>>7;return q+((uint8_t)((value&127)+q)>=127);}
static void fader(uint8_t x,uint8_t slot,uint8_t value,uint8_t selected){
 uint8_t tile,y,row,bits,buf[16],knob=1+10-scale127((uint16_t)value*10+63),display=scale127((uint16_t)value*99+63),base=16+(selected?96:0);
 canvas[7*20+x]=base+display/10;canvas[7*20+x+1]=base+display%10;
 for(tile=0;tile<2;tile++){
  canvas[(uint16_t)(8+tile)*20+x+1]=243+slot*2+tile;
  if(fader_image_knob[slot]==knob)continue;
  for(y=0;y<8;y++){row=tile*8+y;bits=row>=1&&row<=13?0x18:0;if(row>=knob&&row<knob+3)bits=row==knob+1?0x42:0x7E;buf[y*2]=buf[y*2+1]=bits;}
  ui_upload_tile(243+slot*2+tile,buf,0);mixfill();
 }fader_image_knob[slot]=knob;
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
static void pattern_library_render(void){uint8_t i,start=mx.browser>3?mx.browser-3:0,count=sparse_patterns+(page==20);char name[17];
 if(mx.naming){namekeyboard();return;}if(count>8&&start>count-8)start=count-8;
 for(i=start;i<count&&i<start+8;i++){sparse_library_name(i,name);num(0,2+i-start,i+1,mx.browser==i);text(4,2+i-start,i==sparse_patterns?"NEW PATTERN":name[0]?name:"UNTITLED",mx.browser==i);mixfill();}
 if(!count)text(0,3,"NO SAVED PATTERNS",0);
 if(page==20){text(0,11,"NAME",0);text(0,12,file_name,0);text(0,14,"A NAME  B SAVE",0);text(0,15,"FROM PAD",0);num(10,15,file_target+1,0);}else {text(0,12,"A LOAD INTO LIVE PAD",0);text(0,14,"SHARED BY ALL SONGS",0);}
 if(mx.error)text(0,16,"NOT ENOUGH SPACE",0);storage_footer();
}
static char *pad_hint(void){uint8_t state;if(mx.error)return sparse_enabled?(pool_error==2?"SAVE DATA DAMAGED":"NOT ENOUGH SPACE"):"PATTERN >512 EVENTS";if(link_pair_phase)return "PAIR PREPARING...";if(linkpair&&linkstate!=2)return "PAIR NEEDS LINK";if(mx.focus==64)return "A+ARROWS B OFF";if(mx.focus>=38)return "A/B TOGGLE";if(mx.focus<30)return "A PICK B EDIT";state=mixer_prepare_status(mx.focus-30);return state==1?"READY A/B":state==2?"PREPARING...":state==3?"QUEUED":"A PICK B EDIT";}
void mixer_render(void) BANKED {uint8_t c,i,rendering_slot;char name[17];mixer_init();rendering_slot=mx.slot;
 if(page==18&&MIXER_LINK_VIEW){mixer_image.valid=0;mixer_link_render();return;}
 /* Pad navigation changes only the two pattern rows and their footer. Reuse
    the published strip image when every value that affects it is unchanged. */
 if(page==18&&!navopen&&mixer_image.valid&&mx.focus>=30&&mx.focus<38&&mixer_image.focus>=30&&mixer_image.focus<38&&mixer_image.tempo==seqglobalbpm&&mixer_image.quant==mx.quant&&mixer_image.playing==seqplaying&&mixer_image.edit==mx.edit&&mixer_image.mode==experimental_mode&&mixer_image.muted==seqmuted&&mixer_image.solo==seqsolo&&mixer_image.drummute==drummutemask&&mixer_image.drumsolo==drumsolomask&&!memcmp(mixer_image.strips,mx.level,14))goto pattern_controls;
 mixer_image.valid=0;memset(canvas,0,360);mixfill();memset(canvas,96,20);text(0,0,page==18?"MIXER":page==19?"LOAD PATTERN":page==24?"LOAD SONG":page==25?"SAVE SONG":"SAVE PATTERN",1);mixfill();
 if(sparse_enabled==2&&page!=18){text(0,4,"SAVE NOT RECOGNIZED",0);text(0,6,"LOAD A VALID SAVE",0);return;}
 if(page==24||page==25){song_render();return;}
 if(sparse_enabled&&(page==19||page==20)){pattern_library_render();return;}
 if(page==20&&mx.naming){namekeyboard();return;}
 if(page!=18){for(i=0;i<8;i++){getname(i,name);num(0,2+i,i+1,mx.browser==i);text(4,2+i,name[0]?name:"EMPTY",mx.browser==i);mixfill();}if(page==20){text(0,11,"NAME",0);text(0,12,mx.name,0);text(0,14,"A NAME WITH KEYBOARD",0);text(0,15,"B SAVE",0);}else {text(0,12,"A LOAD INTO PAD",0);num(16,12,file_target+1,0);}if(mx.error)text(0,16,sparse_enabled?"NOT ENOUGH SPACE":"TOO MANY NOTES (>512)",0);storage_footer();return;}
 text(15,0,"LOCAL",1);if(mx.edit)text(17,0,"ED",1);text(0,2,seqplaying?"STOP":"PLAY",mx.focus==0);text(7,2,"LAUNCH",0);text(14,2,mx.quant==0?"NOW":mx.quant==1?"1/8":mx.quant==2?"1/4":mx.quant==3?"1/2":mx.quant==5?"LONG":"1/1",mx.focus==1);text(0,3,"TEMPO",0);if(seqglobalbpm)num(7,3,seqglobalbpm,mx.focus==64);else text(7,3,"OFF",mx.focus==64);mixfill();
 /* Five vertical strips fit beside the shared control labels. */
 {uint8_t col=mx.focus==64?0:mx.focus>=38?7+(mx.focus-38)/2:mx.focus>=2&&mx.focus<30?(mx.focus-2)/4:0;
  col=stripcolumn(col);
  if(mx.focus>=2&&mx.focus<64&&(mx.focus<30||mx.focus>=38)){if(col<mixscroll)mixscroll=col;if(col>=mixscroll+5)mixscroll=col-4;}
 }
 text(0,5,"M",0);text(0,6,"S",0);text(0,7,"VOL",0);text(0,12,"PAN",0);
 {uint8_t col=0;for(c=0;c<20;c++){uint8_t f,x;if(!strip_visible(c))continue;if(col<mixscroll||col>=mixscroll+5){col++;continue;}x=4+(col-mixscroll)*3;
  if(c<7){f=2+c*4;text(x,4,tracks[c],0);text(x+1,5,(seqmuted&(1<<c))?"M":"-",mx.focus==f);text(x+1,6,(seqsolo&(1<<c))?"S":"-",mx.focus==f+1);fader(x,col-mixscroll,mx.level[c],mx.focus==f+2);text(x,12,pans[mx.pan[c]],mx.focus==f+3);}
  else {uint8_t voice=c-7;uint16_t bit=1U<<voice;f=38+voice*2;text(x,4,mixer_drum_name(drumkit,voice),0);text(x+1,5,drummutemask&bit?"M":"-",mx.focus==f);text(x+1,6,drumsolomask&bit?"S":"-",mx.focus==f+1);}
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
static uint8_t stripfocus(uint8_t c,uint8_t field){return c<7?2+c*4+field:38+(c-7)*2+(field>1?1:field);}
static void stripnav(uint8_t edge){uint8_t c=mx.focus>=38?7+(mx.focus-38)/2:(mx.focus-2)/4,field=mx.focus>=38?(mx.focus-38)%2:(mx.focus-2)%4;
 if(edge&J_LEFT){uint8_t n=c;while(n){n--;if(strip_visible(n)){c=n;break;}}}
 if(edge&J_RIGHT){uint8_t n=c;while(n<19){n++;if(strip_visible(n)){c=n;break;}}}
 if(edge&J_UP){if(field)field--;else {mx.focus=0;return;}}
 if(edge&J_DOWN){if(field<(c<7?3:1))field++;else {mx.focus=firstpad();return;}}
 mx.focus=stripfocus(c,field);
}
extern uint8_t drumnoiseowned;
static void livepan(uint8_t c){uint8_t pan=mx.pan[c],mask,bit;if(c==4)return;if(c==5)c=2;if(c==6){mask=(waveengine==3?0x44:0)|(drumnoiseowned?0x88:0)|(pulsekickleft?0x11:0);route&=~mask;if(pan&1)route|=mask&15;if(pan&2)route|=mask&240;NR51_REG=route;return;}if(c==0&&pulsekickleft){param[0][21]=pan;return;}if(c==2&&waveengine==3)return;bit=1<<c;mask=bit|(bit<<4);route&=~mask;if(pan&1)route|=bit;if(pan&2)route|=bit<<4;param[c][21]=pan;NR51_REG=route;}
static void change(uint8_t c,uint8_t field,int8_t delta){int16_t n=(int16_t)(field==2?mx.level[c]:mx.pan[c])+delta;mixer_pattern_changed();if(field==2){mx.level[c]=n<0?0:n>127?127:n;if(c==6&&waveengine==3){uint8_t v=mx.level[6];pcmoutlevel=!v?0:v<=42?3:v<=84?2:1;NR32_REG=pcmoutlevel<<5;}}else {mx.pan[c]=n<0?0:n>3?3:n;livepan(c);}if(!syncmode&&field==2)seq_irq_refresh(c);}
void mixer_remote_apply(uint8_t c,uint8_t field,uint8_t value) BANKED {
 if(field==5){if(value>=1&&value<=5)mx.quant=value;dirty=1;return;}
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
 if(!edge&&page==18&&p==J_A&&seqplaying&&mx.focus>=30&&mx.focus<38){
  if(MIXER_LINK_VIEW){if(linkmirror.quant&&linkmirror.quant<=5&&linkmirror.pending==255&&!link_pending())edge=J_A;}
  else if(linkpair&&MIXER_LINK_AVAILABLE&&mx.quant&&mx.pending==255&&!mx.error&&!mixer_prepare_busy()&&!link_pair_phase)edge=J_A;
 }
 if(!edge)return;mixer_init();if(page==18&&padflash_off&&(edge&(J_A|J_B)))mixer_pad_restore();
 if(page==18&&MIXER_LINK_VIEW){mixer_link_input(p,edge);return;}
 if((page==20||page==25)&&mx.naming){nameinput(edge);dirty=1;return;}
 if(page==24||page==25){if(sparse_enabled!=1)return;if(edge&J_UP)mx.browser=mx.browser?mx.browser-1:POOL_SONGS-1;if(edge&J_DOWN)mx.browser=(mx.browser+1)%POOL_SONGS;
  if(edge&J_A){if(page==25)nameopen();else if(sparse_load_song(mx.browser)){page=18;mx.focus=mixer_view_focus;pad_names_valid=0;}else mx.error=1;}
  if(edge&J_B){if(page==25)namesave();else clear_song_open(mx.browser);}dirty=1;return;
 }
 if(sparse_enabled&&(page==19||page==20)){uint8_t count=sparse_patterns+(page==20);
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
  if(p&J_A){if(!seqglobalbpm){seqglobalbpm=seqbpm;}else {int16_t bpm=seqglobalbpm;if(edge&J_UP)bpm++;if(edge&J_DOWN)bpm--;if(edge&J_LEFT)bpm-=10;if(edge&J_RIGHT)bpm+=10;if(seqplaying)seq_frame();seqglobalbpm=seqbpm=bpm<30?30:bpm>300?300:bpm;seqcachedbpm=0;seqdeadline=1;}}
  else if((edge&J_B)&&!syncmode)seqglobalbpm=0;
  else if(edge&J_UP)mx.focus=1;
  else if(edge&J_DOWN){c=firststrip();mx.focus=c<20?stripfocus(c,0):firstpad();}
  else if(edge&(J_LEFT|J_RIGHT))mx.focus=0;
  mixer_image.valid=0;warmfocus();dirty=1;return;
 }
 if(mx.focus>=38){uint16_t bit=1U<<((mx.focus-38)/2);mx.edit=0;
  if(edge&(J_A|J_B)){mixer_pattern_changed();if(mx.focus&1)drumsolomask^=bit;else drummutemask^=bit;seq_mixer_refresh();}
  stripnav(edge);warmfocus();
  dirty=1;return;
 }
 if(mx.focus>=30){if(edge&(J_LEFT|J_RIGHT))mixer_pads_move(edge&J_LEFT?-1:1);if(edge&J_UP){c=firststrip();mx.focus=c<20?stripfocus(c,3):0;}else {if(edge&J_A){uint8_t start=!seqplaying,target=mx.focus-30;mx.error=0;mixer_launch_request(target,0);if(start&&mx.slot==target&&!mx.error&&!mixer_prepare_busy()){mx.openempty=0;page=18;seq_transport();}}if(edge&J_B)mixer_launch_request(mx.focus-30,1);}warmfocus();dirty=1;return;}
 if(mx.focus>=2){c=(mx.focus-2)/4;f=(mx.focus-2)%4;if(f>=2){mx.edit=0;if(p&(J_A|J_B)){int8_t delta=0;if(edge&J_UP)delta++;if(edge&J_DOWN)delta--;if(edge&J_LEFT)delta-=10;if(edge&J_RIGHT)delta+=10;if(delta)change(c,f,delta);dirty=1;return;}}else if(edge&(J_A|J_B)){mutechange(c,f);dirty=1;return;}}
 if(mx.focus>=2){if(!mx.edit&&!(p&J_B))stripnav(edge);}
 else {if(edge&J_LEFT)mx.focus=mx.focus?0:1;if(edge&J_RIGHT)mx.focus=mx.focus?0:1;if(edge&J_UP)mx.focus=firstpad();if(edge&J_DOWN)mx.focus=64;}
 if(mx.focus>=2&&mx.focus<30&&(mx.focus-2)%4<2)mx.edit=0;
 if(mx.focus==0){if(edge&(J_A|J_B)){seq_transport();mx.boundary=0;}}
 else if(mx.focus==1){if(edge&(J_A|J_B))mx.quant=(mx.quant+1)%6;if(syncmode&&syncslave&&!mx.quant)mx.quant=1;}
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
void seq_copy(void) BANKED {
 uint8_t c=seqtrack,meta[16];uint16_t at,count,off=16,n;
 mx.pending=255;sparse_finish_install();if(seqgrouptrack==c){seq_region_copy(0);return;}at=seqeventoffsets[c];count=seqeventcounts[c];
 memset(meta,0,16);clip_part(0,meta,1,1);meta[1]=c;setword(meta+2,count);setword(meta+4,seqlength[c]);setword(meta+6,seqdefaultdur[c]);meta[8]=seqdefaultvel[c];meta[9]=seqgate[c];meta[10]=seqpitch[c];meta[11]=0x73;clip_part(1,meta+1,15,1);
 while(count){n=count;if(n>4)n=4;if(at<256&&at+n>256)n=256-at;clip_part(off,liveevent(at),n*4,1);at+=n;count-=n;off+=n*4;}
 meta[0]=0xC8;clip_part(0,meta,1,1);
}
extern uint16_t drum_clip_plot(uint8_t step,uint8_t row,uint16_t dur,uint8_t vel) BANKED;
void seq_paste(void) BANKED {
 uint8_t c=seqtrack,meta[16],ev[4],seen[32],busy,base=seqpitch[c],note;uint16_t count,total,old,at,i,tail,n;
 mx.pending=255;sparse_journal_edit_barrier();sparse_finish_install();
 clip_part(0,meta,16,0);if(meta[0]==0xC9){if(seq_region_paste(seqcursor[c],c==6?drumrow:seqpitch[c]))mixer_pattern_changed();return;}count=getword(meta+2);if(meta[0]!=0xC8||meta[11]!=0x73||meta[1]>6||count>512||!getword(meta+4)||getword(meta+4)>256||(getword(meta+6)>256||(meta[1]<6&&!getword(meta+6)))||!meta[8]||meta[8]>127||meta[9]>100)return;
 total=seqeventoffsets[6]+seqeventcounts[6];old=seqeventcounts[c];
 /* The clipboard cache is independent of live events and PCM state. Validate
    the complete source before changing the destination or its transport. */
 clip_part(16,CACHE,count*4,0);for(i=0;i<count;i++){uint8_t *e=CACHE+i*4;if(!e[1]||e[1]>(meta[1]==6?13:128)||e[2]>127)return;mixfill();}
 if(c!=6&&meta[1]==6){n=0;memset(seen,0,32);for(i=0;i<count;i++){uint8_t *e=CACHE+i*4;if(!(seen[e[0]>>3]&(1<<(e[0]&7)))){seen[e[0]>>3]|=1<<(e[0]&7);memcpy(CACHE+n*4,e,4);n++;}}count=n;}
 if(total-old+count>512){seqeventfull=1;return;}
 mixer_pattern_changed();seqgrouptrack=255;busy=seqservicing;seqservicing=1;if(c==6)drum_stop();else {note=seqowned[c];seqowned[c]=0;seqgateleft[c]=0;if(note)event(0x80|c,note-1,0);}
 at=seqeventoffsets[c];tail=at+old;
 /* Remove the old segment in one forward pass, then reserve the new one. */
 for(i=tail;i<total;i++){memcpy(ev,liveevent(i),4);memcpy(liveevent(i-old),ev,4);if(!(i&3))mixfill();}
 total-=old;seqeventcounts[c]=0;offsets();
 seqlength[c]=getword(meta+4);seqdefaultdur[c]=getword(meta+6);seqdefaultvel[c]=meta[8];seqgate[c]=meta[9];seqcachedbpm=0;seqdeadline=1;
 if(c==6&&meta[1]!=6){
  for(i=0;i<count;i++){memcpy(ev,CACHE+i*4,4);drum_clip_plot(ev[0],(ev[1]-1)%13,ev[3]?ev[3]:256,ev[2]?ev[2]:meta[8]);mixfill();}
 }else{
  for(i=total;i>at;i--){memcpy(ev,liveevent(i-1),4);memcpy(liveevent(i-1+count),ev,4);if(!(i&3))mixfill();}
  for(i=0;i<count;i++){memcpy(ev,CACHE+i*4,4);if(c!=6&&meta[1]==6){n=(uint16_t)base+ev[1];ev[1]=n>128?128:n;}memcpy(liveevent(at+i),ev,4);if(!(i&3))mixfill();}
  seqeventcounts[c]=count;offsets();
 }
 seqeventfull=0;if(seqposition[c]>=seqlength[c])seqposition[c]=0;if(seqcursor[c]>=seqlength[c])seqcursor[c]=seqlength[c]-1;seqservicing=busy;seqdrawvalid=0;seqviewtrack=255;dirty=1;
}


void mixer_activate(uint8_t slot,uint8_t edit) BANKED {if(slot==mx.slot){retrigger(0);return;}if(sparse_enabled){sparse_activate(slot);return;}if(switchslot(slot)&&edit){page=8;seq_open();}}

#pragma bank 18
#pragma opt_code_speed
#include "api.h"
#include "mixer.h"
#include "tones.h"
#include "sparse_store.h"
extern uint8_t toneready;
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
extern uint8_t seqeventcache,seqrecordtrack;
extern uint16_t seqrecordlength;
#define PREP_UNITS ((uint16_t *)0xACD0)
#define PREP_STEP (*(uint16_t *)0xACDE)
/* Bank zero stays selected whenever audio or sequencing can run. */

#include "mixer_shared.h"
__at (0xAC80) Mixer mx;
static const char * const tracks[7]={"P1","P2","WV1","NS","M5","WV2","DRM"};
static const char * const pans[4]={"OFF","R","L","LR"};
static uint8_t mixscroll;
/* Page-local graphics caches share only renderer scratch, never audio state.
   Opening Mixer invalidates them after any roll has reused those addresses. */
__at (0xACC4) uint8_t pad_image_playing;
__at (0xACC5) uint8_t pad_image_queued;
__at (0xACC6) uint8_t pad_names_valid;
__at (0xACC7) uint8_t fader_image_knob[5];
__at (0xAE40) uint8_t pad_names[8][3];
typedef struct {uint8_t valid,focus,quant,playing,edit,mode,muted,solo;uint16_t drummute,drumsolo,tempo;uint8_t strips[14];} MixerImage;
__at (0xAE58) MixerImage mixer_image;
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





void mixer_init(void) BANKED {uint8_t magic[4],i;ram(0);if(mx.magic==0xD3)return;memset(&mx,0,sizeof(mx));mx.magic=0xD3;mx.pending=255;mixer_pattern_changed();for(i=0;i<7;i++){mx.level[i]=127;mx.pan[i]=3;}if(sparse_enabled){if(sparse_enabled==1){sparse_restore(pool_root[7]<8?pool_root[7]:0);mx.quant=pool_root[8]<5?pool_root[8]:0;sparse_finish_install();}else {defaults();mx.error=3;}return;}readpart(0,2500,magic,4);if(memcmp(magic,"GBM2",4)){for(i=0;i<8;i++){uint8_t z=0;writepart(i,0,&z,1);}memcpy(magic,"GBM2",4);writepart(0,2500,magic,4);}else if(valid(0))restore(0,0);}
void mixer_boot(void) BANKED {ram(0);mx.magic=0;mixer_prepare_cancel();if(!sparse_boot())mixer_journal_recover();mixer_init();}
void mixer_open(void) BANKED {mixer_prepare_cancel();mixer_init();mixer_image.valid=0;pad_names_valid=0;memset(fader_image_knob,255,5);mixscroll=0;mx.focus=mx.edit=mx.naming=mx.letter=0;mx.browser=(page==24||page==25)?(sparse_song<POOL_SONGS?sparse_song:0):sparse_enabled&&page==20?sparse_patterns:sparse_enabled&&page==19?0:mx.slot;previewshape=255;mx.cachevalid=0;if(page==19||page==20){mx.pending=255;mx.presaved=mx.openempty=0;}mx.padcache=0;dirty=1;}
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
 mx.pending=255;mx.presaved=mx.openempty=0;mx.boundary=0;mx.padcache=0;
 if(seqplaying){seqrecordtrack=255;seqrecordlength=0;if(!quantized){__critical {seqclock=seqticks=seqfraction=0;}}seq_pattern_start();}
 else {memset(seqposition,0,7);seqclock=seqticks=seqfraction=0;seqdeadline=1;}
 seqservicing=busy;dirty=1;return 1;
}
static uint8_t switchslot(uint8_t s){uint8_t run=seqplaying,busy=seqservicing,primed,handoff;uint16_t oldbpm,residual,generation;
 if(sparse_enabled)return sparse_activate(s);
 if(!mx.cachevalid||mx.cacheslot!=s||page!=18)prefetch(s);if(mx.cachevalid==3){mx.pending=255;mx.presaved=0;mx.error=1;dirty=1;return 0;}
 /* Save while the outgoing pattern still plays, including quantize OFF.
    Compute eligibility after prefetch so immediate launches use the cache. */
 mx.pending=255;if(!mx.presaved||page!=18)autosnapshot(mx.slot);mx.presaved=0;
 primed=run&&mx.cachevalid==1;handoff=primed&&seqmode==(experimental_mode?CACHE[META+74]:0);oldbpm=seqbpm;residual=seqclock;
 generation=pattern_generation;if(handoff){seqservicing=1;}else if(run)seq_transport();mx.slot=s;if(primed)prime();else restore(s,1);mx.boundary=0;seqdeadline=1;memset(seqcursor,0,7);seqdrawvalid=0;mx.padcache=0;
 if(handoff){seq_pattern_release();if(oldbpm!=seqbpm)seqclock=((uint32_t)residual*seqbpm)/oldbpm;seq_pattern_start();}else {memset(seqposition,0,7);if(run)seq_transport();}
 if(primed){seqservicing=1;install_events();seqeventcache=0;mx.cachevalid=0;seqservicing=busy;if(generation==pattern_generation)mixer_pattern_clean();}
 if(mx.openempty){mx.openempty=0;page=8;seq_open();}dirty=1;return 1;}
void mixer_clock_reset(void) BANKED {if(mx.magic==0xD3)mx.boundary=0;}
uint8_t mixer_boundary(void) BANKED {uint8_t interval;if(mx.magic!=0xD3)return 0;mx.boundary=(mx.boundary+1)&15;if(mx.pending==255||mixer_prepare_busy())return 0;interval=mx.quant?1U<<mx.quant:1;if(!(mx.boundary&(interval-1))){return mx.pending==mx.slot?retrigger(1):switchslot(mx.pending);}return 0;}
void mixer_name(void) BANKED {uint8_t i,ended=mx.magic!=0xD3;for(i=0;i<3;i++){if(!mx.name[i])ended=1;canvas[9+i]=(ended?' ':mx.name[i])-32+96;}}
/* Pad bitmaps use forty tiles, keeping all ordinary font tiles intact. */
#include "mixer_font.h"
static uint8_t glyph(char c,uint8_t y){if(c<32||c>90)return 0;return mixerfont[c-32][y];}
/* Two disjoint sets of forty preview tiles. Publish the new map only after
   every bitmap is ready; leave the currently displayed pad graphics intact. */
__at (0xACFA) uint8_t padbank;
__at (0xACC0) uint16_t padflash_started;
__at (0xACC2) uint8_t padflash_off;
__at (0xACC3) uint8_t padflash_slot;
static uint8_t padtile(uint8_t tile,uint8_t bank){return bank?(tile<24?168+tile:180+tile):(tile<32?64+tile:128+tile);}
/* Flash by changing just six map cells between already-uploaded bitmaps.
   The inactive bank holds the queued pad's normal state, the active bank its
   inverted state. Never rebuild graphics or run this from the audio timer. */
static void padmap(uint8_t slot,uint8_t bank){uint8_t row,x,col=slot*2+slot/2,ids[3];uint16_t at;
 for(row=0;row<2;row++){at=(uint16_t)(14+row)*20+col;for(x=0;x<3;x++){ids[x]=padtile(row*20+col+x,bank);visible[at+x]=canvas[at+x]=ids[x];}ui_upload_map(0x9800U+(uint16_t)(14+row)*32+col,ids,3);mixfill();}
}
static void padrestore(void){if(padflash_off){padflash_off=0;padmap(padflash_slot,padbank);}}
void mixer_tick(void) BANKED {uint8_t off;
 if(navopen){padflash_off=0;return;}
 if(page!=18||mx.pending==255||!mx.padcache||mx.pending!=padflash_slot){padrestore();return;}
 off=((uint16_t)(sys_time-padflash_started)>>4)&1;
 if(off!=padflash_off){padflash_off=off;padmap(mx.pending,padbank^off);}
}
/* Invert exactly one 20-pixel pad without touching its half-width neighbor. */
static void pad_toggle(uint8_t slot) __naked { __asm
 cp #8
 ret nc
 push bc
 ld e,a
 add a,a
 ld l,a
 ld a,e
 srl a
 add a,l
 ld l,a
 ld h,#0xad
 ld b,#255
 ld c,#240
 bit 0,e
 jr z,pad_toggle_begin$
 ld b,#15
 ld c,#255
pad_toggle_begin$:
 ld d,#16
pad_toggle_row$:
 ld a,(hl)
 xor a,b
 ld (hl+),a
 ld a,(hl)
 cpl
 ld (hl+),a
 ld a,(hl)
 xor a,c
 ld (hl),a
 ld a,l
 add a,#18
 ld l,a
 jr nc,pad_toggle_next$
 inc h
pad_toggle_next$:
 dec d
 jr nz,pad_toggle_row$
 pop bc
 ret
 __endasm; }
static void pad_dirty(uint8_t slot,uint8_t *columns){uint8_t b;if(slot>=8)return;b=slot*2+slot/2;columns[b]=columns[b+1]=columns[b+2]=1;}
static void pad_upload_columns(uint8_t bank,uint8_t *columns){uint8_t k,tx,y,buf[16],*src,*dst,*rows=(uint8_t *)0xAD00;
 for(k=0;k<2;k++)for(tx=0;tx<20;tx++)if(columns[tx]){src=rows+(k?160:0)+tx;dst=buf;for(y=0;y<8;y++){*dst++=*src;*dst++=*src;src+=20;}ui_upload_tile(padtile(k*20+tx,bank),buf,0);mixfill();}
}
static void pads(void){uint8_t *rows=(uint8_t *)0xAD00,columns[20],s,y,b,a0,a1,a2,g0,g1,g2,playing=mx.slot,queued=mx.pending;char name[17];
 padrestore();
 /* The name may be assigned by the outgoing autosnapshot while preparation
    is active; detect that without re-reading all eight cartridge records. */
 if(pad_names_valid&&mx.name[0]&&memcmp(pad_names[playing],mx.name,3))pad_names_valid=0;
 memset(columns,0,20);
 if(!pad_names_valid){
  memset(rows,0,320);
  for(s=0;s<8;s++){getname(s,name);if(s==playing&&mx.name[0])memcpy(name,mx.name,17);if(!name[0]){name[0]='1'+s;name[1]=name[2]=0;}memcpy(pad_names[s],name,3);b=s*2+s/2;
   for(y=0;y<16;y++){a0=128;a1=0;a2=16;if(!y||y==15){a0=a1=255;a2=240;}else if(y>=4&&y<11){g0=glyph(name[0],y-4);g1=glyph(name[1],y-4);g2=glyph(name[2],y-4);a0|=g0<<1;a1=(g1<<3)|(g2>>3);a2|=g2<<5;}if(s&1){rows[y*20+b]|=a0>>4;rows[y*20+b+1]=(a0<<4)|(a1>>4);rows[y*20+b+2]=(a1<<4)|(a2>>4);}else{rows[y*20+b]=a0;rows[y*20+b+1]=a1;rows[y*20+b+2]=a2;}}
   mixfill();
  }
  pad_names_valid=1;memset(columns,1,20);
 }else{pad_dirty(pad_image_playing,columns);pad_dirty(pad_image_queued,columns);pad_dirty(playing,columns);pad_dirty(queued,columns);}
 /* Keep the published bank fixed. Only columns containing changed highlights
    need new pixels; ordinary focus/fader changes leave all pad graphics alone. */
 pad_toggle(playing);if(queued!=playing)pad_toggle(queued);
 if(ui_font_upload_pending)ui_transition_begin();
 pad_upload_columns(padbank,columns);
 if(queued<8){
  pad_toggle(queued);memset(columns,0,20);pad_dirty(queued,columns);pad_upload_columns(padbank^1,columns);pad_toggle(queued);
 }
 if(queued!=playing)pad_toggle(queued);pad_toggle(playing);
 pad_image_playing=playing;pad_image_queued=queued;padflash_slot=queued;padflash_started=sys_time;
 mx.padcache=mx.slot==playing&&mx.pending==queued;if(!mx.padcache)dirty=1;
}
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
static char *namebuffer(void){return page==25?sparse_song_name:mx.name;}
static void namesave(void){pad_names_valid=0;mx.error=0;if(page==25){if(!sparse_save_song(mx.browser)){mx.error=2;return;}}else if(sparse_enabled){if(!sparse_save_pattern(mx.browser)){mx.error=2;return;}}else {snapshot(mx.browser);if(mx.error)return;if(mx.browser!=mx.slot)snapshot(mx.slot);if(mx.error)return;}mx.naming=0;mx.focus=0;page=18;}
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
 if(page==25){text(0,11,"NAME",0);text(0,12,sparse_song_name,0);text(0,14,"A NAME  B SAVE",0);needed=sparse_song_size();text(0,15,"NEED",0);space_number(5,15,needed,5);text(10,15,"B",0);}
 else {text(0,12,"A LOAD WHOLE SONG",0);text(0,14,"B DELETE SONG",0);}
 if(mx.error)text(0,16,pool_error==2?"SAVE DATA DAMAGED":"NOT ENOUGH SPACE",0);storage_footer();
}
static void pattern_library_render(void){uint8_t i,start=mx.browser>3?mx.browser-3:0,count=sparse_patterns+(page==20);char name[17];
 if(mx.naming){namekeyboard();return;}if(count>8&&start>count-8)start=count-8;
 for(i=start;i<count&&i<start+8;i++){sparse_library_name(i,name);num(0,2+i-start,i+1,mx.browser==i);text(4,2+i-start,i==sparse_patterns?"NEW PATTERN":name[0]?name:"UNTITLED",mx.browser==i);mixfill();}
 if(!count)text(0,3,"NO SAVED PATTERNS",0);
 if(page==20){text(0,11,"NAME",0);text(0,12,mx.name,0);text(0,14,"A NAME  B SAVE",0);}else {text(0,12,"A LOAD INTO LIVE PAD",0);text(0,14,"SHARED BY ALL SONGS",0);}
 if(mx.error)text(0,16,"NOT ENOUGH SPACE",0);storage_footer();
}
static char *pad_hint(void){uint8_t state;if(mx.error)return sparse_enabled?(pool_error==2?"SAVE DATA DAMAGED":"NOT ENOUGH SPACE"):"PATTERN >512 EVENTS";if(mx.focus==64)return "A+ARROWS B OFF";if(mx.focus>=38)return "A/B TOGGLE";if(mx.focus<30)return "A PICK B EDIT";state=mixer_prepare_status(mx.focus-30);return state==1?"READY A/B":state==2?"PREPARING...":state==3?"QUEUED":"A PICK B EDIT";}
void mixer_render(void) BANKED {uint8_t c,i,rendering_slot;char name[17];mixer_init();rendering_slot=mx.slot;
 /* Pad navigation changes only the two pattern rows and their footer. Reuse
    the published strip image when every value that affects it is unchanged. */
 if(page==18&&!navopen&&mixer_image.valid&&mx.focus>=30&&mx.focus<38&&mixer_image.focus>=30&&mixer_image.focus<38&&mixer_image.tempo==seqglobalbpm&&mixer_image.quant==mx.quant&&mixer_image.playing==seqplaying&&mixer_image.edit==mx.edit&&mixer_image.mode==experimental_mode&&mixer_image.muted==seqmuted&&mixer_image.solo==seqsolo&&mixer_image.drummute==drummutemask&&mixer_image.drumsolo==drumsolomask&&!memcmp(mixer_image.strips,mx.level,14))goto pattern_controls;
 mixer_image.valid=0;memset(canvas,0,360);mixfill();memset(canvas,96,20);text(0,0,page==18?"MIXER":page==19?"LOAD PATTERN":page==24?"LOAD SONG":page==25?"SAVE SONG":"SAVE PATTERN",1);mixfill();
 if(sparse_enabled==2&&page!=18){text(0,4,"SAVE NOT RECOGNIZED",0);text(0,6,"LOAD A VALID SAVE",0);return;}
 if(page==24||page==25){song_render();return;}
 if(sparse_enabled&&(page==19||page==20)){pattern_library_render();return;}
 if(page==20&&mx.naming){namekeyboard();return;}
 if(page!=18){for(i=0;i<8;i++){getname(i,name);num(0,2+i,i+1,mx.browser==i);text(4,2+i,name[0]?name:"EMPTY",mx.browser==i);mixfill();}if(page==20){text(0,11,"NAME",0);text(0,12,mx.name,0);text(0,14,"A NAME WITH KEYBOARD",0);text(0,15,"B SAVE",0);}else text(0,12,"A LOAD INTO LIVE PAD",0);if(mx.error)text(0,16,sparse_enabled?"NOT ENOUGH SPACE":"TOO MANY NOTES (>512)",0);storage_footer();return;}
 if(mx.edit)text(15,0,"EDIT",1);text(0,2,seqplaying?"STOP":"PLAY",mx.focus==0);text(7,2,"LAUNCH",0);text(14,2,mx.quant==0?"NOW":mx.quant==1?"1/8":mx.quant==2?"1/4":mx.quant==3?"1/2":"1/1",mx.focus==1);text(0,3,"TEMPO",0);if(seqglobalbpm)num(7,3,seqglobalbpm,mx.focus==64);else text(7,3,"OFF",mx.focus==64);mixfill();
 /* Five vertical strips fit beside the shared control labels. */
 {uint8_t col=mx.focus==64?0:mx.focus>=38?7+(mx.focus-38)/2:mx.focus>=2&&mx.focus<30?(mx.focus-2)/4:0;
  if(!experimental_mode&&col>=6)col-=2;
  if(mx.focus<2||mx.focus==64)mixscroll=0;
  else if(mx.focus<30||mx.focus>=38){if(col<mixscroll)mixscroll=col;if(col>=mixscroll+5)mixscroll=col-4;}
 }
 text(0,5,"M",0);text(0,6,"S",0);text(0,7,"VOL",0);text(0,11,"PAN",0);
 for(c=0;c<20;c++){uint8_t col=c,f,x;if(!experimental_mode&&(c==4||c==5))continue;if(!experimental_mode&&c>=6)col-=2;if(col<mixscroll||col>=mixscroll+5)continue;x=4+(col-mixscroll)*3;
  if(c<7){f=2+c*4;text(x,4,tracks[c],0);text(x+1,5,(seqmuted&(1<<c))?"M":"-",mx.focus==f);text(x+1,6,(seqsolo&(1<<c))?"S":"-",mx.focus==f+1);fader(x,col-mixscroll,mx.level[c],mx.focus==f+2);text(x,11,pans[mx.pan[c]],mx.focus==f+3);}
  else {uint8_t voice=c-7;uint16_t bit=1U<<voice;f=38+voice*2;if(voice<10){text(x,4,"S",0);canvas[4*20+x+1]=16+(voice+1)/10;canvas[4*20+x+2]=16+(voice+1)%10;}else text(x,4,voice==10?"NHH":voice==11?"NSN":"PK",0);text(x+1,5,drummutemask&bit?"M":"-",mx.focus==f);text(x+1,6,drumsolomask&bit?"S":"-",mx.focus==f+1);}
  mixfill();
 }
 pattern_controls:
 text(0,12,"PATTERNS",0);for(i=0;i<8;i++){char digit[2];digit[0]='1'+i;digit[1]=0;text((i*20+8)/8,13,digit,mx.focus==30+i);mixfill();}if(!mx.padcache)pads();for(i=0;i<40;i++)canvas[14*20+i]=padtile(i,padbank);if(padflash_off&&padflash_slot<8){uint8_t col=padflash_slot*2+padflash_slot/2;for(i=0;i<2;i++)for(c=0;c<3;c++)canvas[(uint16_t)(14+i)*20+col+c]=padtile(i*20+col+c,padbank^1);}memset(canvas+17*20,0,20);num(0,17,(mx.focus>=30&&mx.focus<38?mx.focus-29:mx.slot+1),mx.focus>=30&&mx.focus<38);text(4,17,pad_hint(),0);mixfill();
 mixer_image.valid=!navopen&&rendering_slot==mx.slot;mixer_image.focus=mx.focus;mixer_image.quant=mx.quant;mixer_image.tempo=seqglobalbpm;mixer_image.playing=seqplaying;mixer_image.edit=mx.edit;mixer_image.mode=experimental_mode;mixer_image.muted=seqmuted;mixer_image.solo=seqsolo;mixer_image.drummute=drummutemask;mixer_image.drumsolo=drumsolomask;memcpy(mixer_image.strips,mx.level,14);
}
extern void seq_mixer_mute(uint8_t c,uint8_t solo) BANKED;
extern void seq_mixer_refresh(void) BANKED;
static void mutechange(uint8_t c,uint8_t solo){if(!syncmode){seqirqready=0;seqirqdirty=1;}mixer_pattern_changed();seq_mixer_mute(c,solo);}
/* Focus IDs stay stable for pattern storage and external tools. */
static uint8_t stripfocus(uint8_t c,uint8_t field){return c<7?2+c*4+field:38+(c-7)*2+(field>1?1:field);}
static void stripnav(uint8_t edge){uint8_t c=mx.focus>=38?7+(mx.focus-38)/2:(mx.focus-2)/4,field=mx.focus>=38?(mx.focus-38)%2:(mx.focus-2)%4;
 if(edge&J_LEFT){if(c)c--;if(!experimental_mode&&c==5)c=3;}
 if(edge&J_RIGHT){if(c<19)c++;if(!experimental_mode&&c==4)c=6;}
 if(edge&J_UP){if(field)field--;else {mx.focus=0;return;}}
 if(edge&J_DOWN){if(field<(c<7?3:1))field++;else {mx.focus=30;return;}}
 mx.focus=stripfocus(c,field);
}
extern uint8_t drumnoiseowned;
static void livepan(uint8_t c){uint8_t pan=mx.pan[c],mask,bit;if(c==4)return;if(c==5)c=2;if(c==6){mask=(waveengine==3?0x44:0)|(drumnoiseowned?0x88:0)|(pulsekickleft?0x11:0);route&=~mask;if(pan&1)route|=mask&15;if(pan&2)route|=mask&240;NR51_REG=route;return;}if(c==0&&pulsekickleft){param[0][21]=pan;return;}if(c==2&&waveengine==3)return;bit=1<<c;mask=bit|(bit<<4);route&=~mask;if(pan&1)route|=bit;if(pan&2)route|=bit<<4;param[c][21]=pan;NR51_REG=route;}
static void change(uint8_t c,uint8_t field,int8_t delta){int16_t n=(int16_t)(field==2?mx.level[c]:mx.pan[c])+delta;mixer_pattern_changed();if(field==2){mx.level[c]=n<0?0:n>127?127:n;if(c==6&&waveengine==3){uint8_t v=mx.level[6];pcmoutlevel=!v?0:v<=42?3:v<=84?2:1;NR32_REG=pcmoutlevel<<5;}}else {mx.pan[c]=n<0?0:n>3?3:n;livepan(c);}if(!syncmode&&field==2)seq_irq_refresh(c);}

void mixer_tempo_edit(int16_t delta) BANKED {int16_t bpm;if(syncmode&&syncslave)return;if(!syncmode){seqirqready=0;seqirqdirty=1;}if(seqplaying)seq_frame();bpm=(int16_t)seqbpm+delta;seqbpm=bpm<30?30:bpm>300?300:bpm;if(seqglobalbpm)seqglobalbpm=seqbpm;seqcachedbpm=0;seqdeadline=1;dirty=1;}
static void warmfocus(void){mixer_prepare_focus(mx.focus>=30&&mx.focus<38?mx.focus-30:255);}
void mixer_input(uint8_t p,uint8_t edge) BANKED {uint8_t c,f;if(!edge)return;mixer_init();if(page==18&&padflash_off&&(edge&(J_A|J_B)))padrestore();
 if((page==20||page==25)&&mx.naming){if(page==20)mixer_pattern_changed();nameinput(edge);dirty=1;return;}
 if(page==24||page==25){if(sparse_enabled!=1)return;if(edge&J_UP)mx.browser=mx.browser?mx.browser-1:POOL_SONGS-1;if(edge&J_DOWN)mx.browser=(mx.browser+1)%POOL_SONGS;
  if(edge&J_A){if(page==25)nameopen();else if(sparse_load_song(mx.browser)){page=18;mx.focus=0;pad_names_valid=0;}else mx.error=1;}
  if(edge&J_B){if(page==25)namesave();else clear_song_open(mx.browser);}dirty=1;return;
 }
 if(sparse_enabled&&(page==19||page==20)){uint8_t count=sparse_patterns+(page==20);
  if(count){if(edge&J_UP)mx.browser=mx.browser?mx.browser-1:count-1;if(edge&J_DOWN)mx.browser=(mx.browser+1)%count;}
  if(edge&J_A){if(page==20)nameopen();else if(sparse_load_pattern(mx.browser)){page=18;mx.focus=0;pad_names_valid=0;}else mx.error=2;}
  if(page==20&&(edge&J_B))namesave();dirty=1;return;
 }
 if(page!=18){mixer_prepare_barrier();
 {if(edge&J_UP)mx.browser=mx.browser?mx.browser-1:7;if(edge&J_DOWN)mx.browser=(mx.browser+1)&7;if(edge&J_A){if(page==20){nameopen();}else if(valid(mx.browser)){uint8_t run=seqplaying;if(run)seq_transport();if(!restore(mx.browser,0)){if(run)seq_transport();dirty=1;return;}snapshot(mx.slot);seqdrawvalid=0;if(run)seq_transport();page=18;mx.focus=0;mx.padcache=0;}}}
 if(page==20&&(edge&J_B)){namesave();}dirty=1;return;}
 /* Tempo is a separate header control; keep existing strip IDs stable. */
 if(mx.focus==64){
  if(syncmode&&syncslave&&((p&J_A)||(edge&J_B)))return;
  if(p&J_A){if(!seqglobalbpm){seqglobalbpm=seqbpm;}else {int16_t bpm=seqglobalbpm;if(edge&J_UP)bpm++;if(edge&J_DOWN)bpm--;if(edge&J_LEFT)bpm-=10;if(edge&J_RIGHT)bpm+=10;if(seqplaying)seq_frame();seqglobalbpm=seqbpm=bpm<30?30:bpm>300?300:bpm;seqcachedbpm=0;seqdeadline=1;}}
  else if((edge&J_B)&&!syncmode)seqglobalbpm=0;
  else if(edge&J_UP)mx.focus=1;
  else if(edge&J_DOWN)mx.focus=2;
  else if(edge&(J_LEFT|J_RIGHT))mx.focus=0;
  mixer_image.valid=0;warmfocus();dirty=1;return;
 }
 if(mx.focus>=38){uint16_t bit=1U<<((mx.focus-38)/2);mx.edit=0;
  if(edge&(J_A|J_B)){mixer_pattern_changed();if(mx.focus&1)drumsolomask^=bit;else drummutemask^=bit;seq_mixer_refresh();}
  stripnav(edge);warmfocus();
  dirty=1;return;
 }
 if(mx.focus>=30){if(edge&J_LEFT)mx.focus=mx.focus==30?37:mx.focus-1;if(edge&J_RIGHT)mx.focus=mx.focus==37?30:mx.focus+1;if(edge&J_UP)mx.focus=stripfocus(experimental_mode?mixscroll:mixscroll>=4?mixscroll+2:mixscroll,3);if(edge&J_A)mixer_launch_request(mx.focus-30,0);if(edge&J_B)mixer_launch_request(mx.focus-30,1);warmfocus();dirty=1;return;}
 if(mx.focus>=2){c=(mx.focus-2)/4;f=(mx.focus-2)%4;if(f>=2){mx.edit=0;if(p&(J_A|J_B)){int8_t delta=0;if(edge&J_UP)delta++;if(edge&J_DOWN)delta--;if(edge&J_LEFT)delta-=10;if(edge&J_RIGHT)delta+=10;if(delta)change(c,f,delta);dirty=1;return;}}else if(edge&(J_A|J_B)){mutechange(c,f);dirty=1;return;}}
 if(mx.focus>=2){if(!mx.edit&&!(p&J_B))stripnav(edge);}
 else {if(edge&(J_LEFT|J_RIGHT))mx.focus^=1;if(edge&J_UP)mx.focus=30;if(edge&J_DOWN)mx.focus=64;}
 if(mx.focus>=2&&mx.focus<30&&(mx.focus-2)%4<2)mx.edit=0;
 if(mx.focus==0){if(edge&(J_A|J_B)){seq_transport();mx.boundary=0;}}
 else if(mx.focus==1){if(edge&(J_A|J_B))mx.quant=(mx.quant+1)%5;}
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

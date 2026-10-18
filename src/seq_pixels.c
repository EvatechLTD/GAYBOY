#pragma bank 13
#pragma opt_code_speed
#include "api.h"
/* Foreground-only VRAM copy. Keep the STAT check and byte write together:
   the PCM ISR can otherwise return after the safe LCD window has ended.
   Interrupts run between bytes, never across a complete tile/map upload. */
void ui_vram_copy(uint8_t *dst,const uint8_t *src,uint8_t count) __naked {
 __asm
 ldhl sp,#2
 ld a,(hl)
 ld h,b
 ld l,c
 push bc
 ld b,a
vram_byte$:
 di
vram_wait$:
 ldh a,(0x41)
 and #2
 jr nz,vram_wait$
 ld a,(hl+)
 ld (de),a
 ei
 inc de
 dec b
 jr nz,vram_byte$
 pop bc
 pop hl
 inc sp
 jp (hl)
 __endasm;
}
void ui_upload_tile(uint8_t tile,const uint8_t *data,uint8_t sprite) BANKED {
 uint16_t address;if(sprite||(LCDC_REG&0x10))address=0x8000U+(uint16_t)tile*16;
 else address=tile<128?0x9000U+(uint16_t)tile*16:0x8800U+(uint16_t)(tile-128)*16;
 ui_vram_copy((uint8_t *)address,data,16);
}
void ui_upload_map(uint16_t address,const uint8_t *data,uint8_t count) BANKED {ui_vram_copy((uint8_t *)address,data,count);}
extern uint8_t seqbeats,seqdenom;
void roll_begin(void) BANKED;
void roll_retain(void) BANKED;
void roll_clear_transition(void) BANKED;
/* Scratch cache occupies the unused upper half of cartridge RAM; audio delay
   remains at A000-AFFF. No saves or SD writes are involved. */
__at (0xB000) uint8_t rolltiles[128][16];
__at (0xB800) uint8_t rollheads[256];
__at (0xB900) uint8_t rollnext[128];
__at (0xB980) uint8_t rollnotey[40];
__at (0xBFE8) uint8_t rolldirty[20];
__at (0xBA00) uint8_t rollrow[320];
__at (0xBB40) uint8_t rollbackground[320];
__at (0xBC80) uint8_t rollx[41];
__at (0xBCC0) uint8_t rollnotes[40];
__at (0xBD00) uint8_t rollkind[40];
__at (0xBD40) uint8_t rollbasepixels[2][320];
__at (0xBFC0) uint8_t rollbaseids[2][20];
/* The piano and DRUM views share scratch RAM, never their retained caches.
   Pin both the displayed map and next map while an edit is being rebuilt. */
__at (0xAD00) uint8_t rollpins[128];
/* Shared with DRUM scratch only while its view is inactive. */
__at (0xAF00) uint8_t rollonsets[40][4];
__at (0xAD80) uint8_t rollcache[10];
__at (0xAD90) uint8_t rolloldkind[40];
__at (0xADB8) uint8_t rolloldvel[40];
__at (0xADE0) uint8_t rollrowsdirty[17];
uint8_t rollpinslazy;
uint8_t seqgridheight=112;
uint8_t seqviewtop,seqviewbase,seqviewcols;
__at (0xACE0) uint8_t rollpending[15];
__at (0xACEF) uint8_t rollreplace;
__at (0xACF7) uint8_t rollbuilding;
__at (0xACFB) uint8_t seqfontdirty;
__at (0xACFC) uint8_t seqviewtrack;
__at (0xACFD) uint8_t rolltop;
uint8_t rollcursorx=255,rollcursory=255,rollcursorw,rollcursorh;
uint8_t rollplayx=255,rollplayheight,rollplayvalid;
uint8_t rollplaypos=255,rollplaybase,rollplaycols,rollplaytrack=255;
uint8_t rollcursorcell=255,rollcursorcols,rollcursortrack=255,rollcursorhead=255,rollcursorvisible;
const uint8_t rollmasks[9]={255,127,63,31,15,7,3,1,0};
const uint8_t rolldigits[11][7]={{14,17,19,21,25,17,14},{4,12,4,4,4,4,14},{14,17,1,2,4,8,31},{30,1,1,14,1,1,30},{2,6,10,18,31,2,2},{31,16,16,30,1,1,30},{14,16,16,30,17,17,14},{31,1,2,4,8,8,8},{14,17,17,14,17,17,14},{14,17,17,15,1,1,14},{0,0,0,14,0,0,0}};
const uint8_t rollqx[20]={0,8,16,24,32,0,8,16,24,32,0,8,16,24,32,0,8,16,24,32};
const uint8_t rollqy[20]={0,0,0,0,0,8,8,8,8,8,16,16,16,16,16,24,24,24,24,24};
void roll_audio(void){mixfill();if(monomode&&expconfig[0])exp_fill();}
void seq_dimensions(void) BANKED {
 seqcols=(seqzoom+1)*8;
 seqheight=seqzoom==0?16:8;
 seqgridheight=seqzoom==1&&!seqvelocityhidden?112:136;
 seqrows=seqzoom==0?9:seqgridheight/8;
 if(seqtrack==6){seqheight=8;seqgridheight=seqcols==16&&!seqvelocityhidden?112:136;seqrows=13;}
 seqbase=(seqcursor[seqtrack]/seqcols)*seqcols;
 if(seqlength[seqtrack]>seqcols&&seqbase+seqcols>seqlength[seqtrack])seqbase=seqlength[seqtrack]-seqcols;
}
/* The font uses 0..63 and 96..159; M/S retain 244..251. */
uint8_t roll_id(uint8_t n){return n<32?64+n:n<116?128+n:136+n;}
/* SDCC register arguments: row DE, scanline A; remaining bytes on stack.
   The shared renderer scratch is never used by the audio interrupt. */
void roll_span(uint8_t *row,uint8_t y,uint8_t left,uint8_t right,uint8_t color) __naked {
 __asm
 push bc
 add a,a
 ld (0xafd0),a
 ld a,e
 ld (0xafd3),a
 ld a,d
 ld (0xafd4),a
 ldhl sp,#4
 ld b,(hl)
 inc hl
 ld c,(hl)
 inc hl
 ld d,(hl)
roll_span_loop$:
 ld a,b
 cp a,c
 jp nc,roll_span_done$
 and #0xf8
 add a,#8
 cp a,c
 jr c,roll_span_end$
 ld a,c
roll_span_end$:
 ld (0xafd2),a
 dec a
 and #7
 inc a
 add a,#<_rollmasks
 ld l,a
 ld a,#>_rollmasks
 adc a,#0
 ld h,a
 ld a,(hl)
 ld (0xafd1),a
 ld a,b
 and #7
 add a,#<_rollmasks
 ld l,a
 ld a,#>_rollmasks
 adc a,#0
 ld h,a
 ld a,(hl)
 ld hl,#0xafd1
 xor a,(hl)
 ld e,a
 ld a,b
 and #0xf8
 add a,a
 ld l,a
 ld a,#0
 adc a,#0
 ld h,a
 ld a,(0xafd0)
 add a,l
 ld l,a
 ld a,(0xafd3)
 add a,l
 ld l,a
 ld a,(0xafd4)
 adc a,h
 ld h,a
 ld a,e
 cpl
 and a,(hl)
 bit 0,d
 jr z,roll_span_low$
 or a,e
roll_span_low$:
 ld (hl+),a
 ld a,e
 cpl
 and a,(hl)
 bit 1,d
 jr z,roll_span_high$
 or a,e
roll_span_high$:
 ld (hl),a
 ld a,(0xafd2)
 ld b,a
 jp roll_span_loop$
roll_span_done$:
 pop bc
 pop hl
 inc sp
 inc sp
 inc sp
 jp (hl)
 __endasm;
}
/* Carry-fed addition avoids the cancellation of repeated grid scanlines that
   made the previous rotating-XOR hash build long chains of unrelated tiles. */
uint8_t roll_hash(uint8_t *data) __naked {
 __asm
 ld h,d
 ld l,e
 ld b,#16
 ld a,#167
00001$:
 rlca
 adc a,(hl)
 inc hl
 dec b
 jr nz,00001$
 ret
 __endasm;
}
uint8_t roll_equal(uint8_t *src,uint8_t *dst) __naked {
 __asm
 ld h,b
 ld l,c
 ld b,#16
00002$:
 ld a,(de)
 cp a,(hl)
 jr nz,00003$
 inc de
 inc hl
 dec b
 jr nz,00002$
 ld a,#1
 ret
00003$:
 xor a,a
 ret
 __endasm;
}
uint8_t roll_index(uint8_t id){return id>=64&&id<96?id-64:id>=160&&id<244?id-128:id>=252?id-136:255;}
/* The three maps must stay pinned until publication, but doing a C function
   call for each of their 1080 cells dominated even a one-row scroll. */
void roll_pinmap(uint8_t *map,uint16_t count) __naked { __asm
 push bc
 ld a,b
 or a,c
 jr z,pin_done$
pin_cell$:
 ld a,(de)
 cp #64
 jr c,pin_next$
 cp #96
 jr c,pin_low$
 cp #160
 jr c,pin_next$
 cp #244
 jr c,pin_mid$
 cp #252
 jr c,pin_next$
 sub #136
 jr pin_store$
pin_low$:
 sub #64
 jr pin_store$
pin_mid$:
 sub #128
pin_store$:
 ld l,a
 ld h,#0xad
 ld (hl),#1
pin_next$:
 inc de
 dec bc
 ld a,c
 and #15
 jr nz,pin_more$
 push bc
 push de
 call _roll_audio
 pop de
 pop bc
pin_more$:
 ld a,b
 or a,c
 jr nz,pin_cell$
pin_done$:
 pop bc
 ret
 __endasm; }
static void roll_pin_bases(void){uint8_t x,style;if(seqtrack!=6)for(style=0;style<(seqheight==16?2:1);style++)for(x=0;x<20;x++){uint8_t n=roll_index(rollbaseids[style][x]);if(n!=255)rollpins[n]=1;}}
void roll_pinmaps(void){rollpinslazy=0;memset(rollpins,0,128);roll_audio();roll_pinmap(visible,360);roll_audio();if(memcmp(canvas,visible,360))roll_pinmap(canvas,360);roll_audio();if(memcmp(seqscreen,visible,360)&&memcmp(seqscreen,canvas,360))roll_pinmap(seqscreen,360);roll_pin_bases();}
uint8_t roll_intern(uint8_t *bytes){uint8_t h=roll_hash(bytes),n,id,*link;
 for(n=rollheads[h];n!=255;n=rollnext[n])if(roll_equal(rolltiles[n],bytes)){rollpins[n]=1;return roll_id(n);}
 if(seqtilecount<120)n=seqtilecount++;
 else{
  if(rollpinslazy)roll_pinmaps();
  for(n=0;n<120;n++)if(!rollpins[n])break;
  if(n==120){seqtileoverflow=1;return roll_id(0);}
  /* Remove the unused immutable tile from its old hash chain before reuse. */
  link=&rollheads[roll_hash(rolltiles[n])];while(*link!=n&&*link!=255)link=&rollnext[*link];if(*link==n)*link=rollnext[n];
 }
 memcpy(rolltiles[n],bytes,16);rollnext[n]=rollheads[h];rollheads[h]=n;rollpins[n]=1;id=roll_id(n);
 /* Stage in the existing RAM cache. The outgoing screen's VRAM stays intact
    throughout construction, including complete cache replacements. */
 rollpending[n>>3]|=1<<(n&7);return id;
}
void roll_markrow(uint8_t y){uint8_t row;if(y==255)return;row=y>>3;if(row<17&&!rollrowsdirty[row])rollrowsdirty[row]=1;if(seqheight==16&&row+1<17&&!rollrowsdirty[row+1])rollrowsdirty[row+1]=1;}
void roll_keyboard(uint8_t tiley){
 uint8_t y,gy,pitch=255,within,digitrow,oct=0,n=0,lo0,hi0,lo1,hi1,newpitch,black=0,shift=seqzoom==0?4:3;uint16_t bits;
 for(y=0;y<8;y++){if(!(y&3))roll_audio();gy=tiley*8+y;newpitch=rolltop-(gy>>shift);within=gy&(seqheight-1);
  if(newpitch!=pitch){pitch=newpitch;n=pitch%12;black=!!(0x54A&(1U<<n));oct=pitch>=12?pitch/12-1:10;}
  lo0=hi0=lo1=hi1=0;
  if(black){lo0=hi0=255;lo1=hi1=0xC0;}
  else if(within==seqheight-1){lo0=lo1=255;}
  if(n==0){digitrow=within>=(seqheight-7)/2?within-(seqheight-7)/2:7;if(digitrow<7){bits=(uint16_t)rolldigits[oct][digitrow]<<6;lo0|=bits>>8;hi0|=bits>>8;lo1|=bits;hi1|=bits;}}
  rollrow[y*2]=lo0;rollrow[y*2+1]=hi0;rollrow[16+y*2]=lo1;rollrow[17+y*2]=hi1;
 }
}
/* Ordinary navigation leaves event data unchanged. Reuse its resolved cells
   as well as its tiles; edits use the general comparison path below. */
void roll_scroll_cells(void){uint8_t i;int16_t y;for(i=0;i<seqcols;i++){rollkind[i]=rolloldkind[i]&3;if(!rollnotes[i]){rollnotey[i]=255;continue;}y=((int16_t)rolltop-(rollnotes[i]-1))*seqheight;rollnotey[i]=y>=0&&y<seqgridheight?y:255;}}
/* Invert both bitplanes inside the selected cells, including empty cells. */
void roll_invert_selection(uint8_t row) BANKED {
 uint16_t a,b,x,end,off;int16_t top,bottom,y;uint8_t mask;
 if(seqgrouptrack!=seqtrack)return;
 a=seqgroupx0;b=(uint16_t)seqgroupx1+1;
 if(a<seqbase)a=seqbase;if(b>(uint16_t)seqbase+seqcols)b=(uint16_t)seqbase+seqcols;if(a>=b)return;
 a=rollx[a-seqbase];b=rollx[b-seqbase];
 if(seqtrack==6){top=(uint16_t)seqgroupy0*8;bottom=((uint16_t)seqgroupy1+1)*8;}
 else{top=((int16_t)rolltop-seqgroupy1)*seqheight;bottom=((int16_t)rolltop-seqgroupy0+1)*seqheight;}
 if(top<(int16_t)row*8)top=(uint16_t)row*8;if(bottom>(int16_t)(row+1)*8)bottom=(uint16_t)(row+1)*8;
 for(y=top;y<bottom;y++){roll_audio();for(x=a;x<b;x=end){end=(x|7)+1;if(end>b)end=b;mask=(uint8_t)(255>>(x&7))& (uint8_t)(255<<(8-((end-1)&7)-1));off=(x>>3)*16+((y&7)<<1);rollrow[off]^=mask;rollrow[off+1]^=mask;}}
}
void roll_selection_dirty(uint8_t low,uint8_t high){int16_t top=((int16_t)rolltop-high)*seqheight,bottom=((int16_t)rolltop-low+1)*seqheight;uint8_t t;for(t=0;t<seqgridheight/8;t++)if(top<(int16_t)(t+1)*8&&bottom>(int16_t)t*8&&!rollrowsdirty[t])rollrowsdirty[t]=1;}
/* Selection gestures do not change notes. XOR only the rectangle's changed
   edge tiles against the immutable displayed image, without scanning events
   or rebuilding the piano, drum grid and velocity strip. */
static void roll_box_pixels(uint8_t *box,uint8_t track,uint8_t x0,uint8_t x1,uint8_t y0,uint8_t y1){
 uint16_t a=x0,b=(uint16_t)x1+1;int16_t top,bottom;
 memset(box,0,4);if(track!=seqtrack)return;
 if(a<seqbase)a=seqbase;if(b>(uint16_t)seqbase+seqcols)b=(uint16_t)seqbase+seqcols;if(a>=b)return;
 if(seqtrack==6){top=(uint16_t)y0*8;bottom=((uint16_t)y1+1)*8;}
 else{top=((int16_t)seqtop[seqtrack]-y1)*seqheight;bottom=((int16_t)seqtop[seqtrack]-y0+1)*seqheight;}
 if(top<0)top=0;if(bottom>seqgridheight)bottom=seqgridheight;if(top>=bottom)return;
 box[0]=rollx[a-seqbase];box[1]=rollx[b-seqbase];box[2]=top;box[3]=bottom;
}
static uint8_t roll_box_mask(uint8_t left,uint8_t right,uint8_t x){
 uint8_t end=x+8;if(left>=end||right<=x)return 0;
 return (uint8_t)(255>>(left>x?left-x:0))&(uint8_t)(255<<(right<end?end-right:0));
}
static void roll_xor_tile(uint8_t *pixels,uint8_t mask) __naked { __asm
 ld h,d
 ld l,e
 ld c,a
 ld b,#16
selection_xor$:
 ld a,(hl)
 xor a,c
 ld (hl+),a
 dec b
 jr nz,selection_xor$
 ret
 __endasm; }
/* AF00..AFEF is the onset/drum event staging area. Selection-only gestures
   do not read that staging data; retain current-map reference counts there
   until the next ordinary renderer replaces it and restores marker 167. */
static void roll_selection_count(uint8_t *map,uint16_t count) __naked { __asm
 push bc
selection_count_cell$:
 ld a,(de)
 cp #64
 jr c,selection_count_next$
 cp #96
 jr c,selection_count_low$
 cp #160
 jr c,selection_count_next$
 cp #244
 jr c,selection_count_mid$
 cp #252
 jr c,selection_count_next$
 sub #136
 jr selection_count_store$
selection_count_low$:
 sub #64
 jr selection_count_store$
selection_count_mid$:
 sub #128
selection_count_store$:
 add a,a
 ld l,a
 ld h,#0xaf
 inc (hl)
 jr nz,selection_count_next$
 inc l
 inc (hl)
selection_count_next$:
 inc de
 dec bc
 ld a,c
 and #63
 jr nz,selection_count_more$
 push bc
 push de
 call _roll_audio
 pop de
 pop bc
selection_count_more$:
 ld a,b
 or a,c
 jr nz,selection_count_cell$
 pop bc
 ret
 __endasm; }
static void roll_selection_pins(void) __naked { __asm
 ld de,#0xaf00
 ld hl,#0xad00
 ld b,#120
selection_pin_cell$:
 ld a,(de)
 inc de
 ld c,a
 ld a,(de)
 inc de
 or a,c
 jr z,selection_pin_zero$
 ld a,#1
selection_pin_zero$:
 ld (hl+),a
 dec b
 jr nz,selection_pin_cell$
 ret
 __endasm; }
uint8_t roll_selection_update(void) BANKED {
 uint8_t old[4],next[4],row,x,oldon,newon,mask,n,id,first,last,offset,pixels[16];uint16_t at,*refs=(uint16_t *)rollonsets;
 if(!seqfontdirty||(rollcache[0]!=167&&rollcache[0]!=168)||seqviewtrack!=seqtrack||seqviewbase!=seqbase||seqviewcols!=seqcols||rollcache[4]!=seqgridheight||(seqtrack!=6&&seqviewtop!=seqtop[seqtrack]))return 0;
 roll_box_pixels(old,rollcache[5],rollcache[6],rollcache[7],rollcache[8],rollcache[9]);
 roll_box_pixels(next,seqgrouptrack,seqgroupx0,seqgroupx1,seqgroupy0,seqgroupy1);
 ENABLE_RAM_MBC5;SWITCH_RAM_MBC5(0);memcpy(canvas,seqscreen,360);
 if(rollcache[0]!=168){memset(refs,0,240);roll_selection_count(seqscreen,360);}
 rollpinslazy=0;roll_selection_pins();roll_pin_bases();
 seqtileoverflow=0;rollbuilding=1;rollreplace=0;memset(rollpending,0,15);HIDE_SPRITES;
 /* Horizontal masks are shared by every selected scanline. The row staging
    buffer is otherwise unused by this path; no extra persistent RAM. */
 for(x=0;x<20;x++){rollrow[x]=roll_box_mask(old[0],old[1],x*8);rollrow[20+x]=roll_box_mask(next[0],next[1],x*8);rollrow[40+x]=rollrow[x]^rollrow[20+x];}
 for(row=0;row<seqgridheight/8;row++){
  oldon=row*8>=old[2]&&row*8<old[3];newon=row*8>=next[2]&&row*8<next[3];
  if(!oldon&&!newon)continue;
  if(oldon&&newon&&old[0]==next[0]&&old[1]==next[1])continue;
  if(oldon&&newon){offset=40;first=old[0]<next[0]?old[0]:next[0];last=old[1]>next[1]?old[1]:next[1];}
  else if(oldon){offset=0;first=old[0];last=old[1];}else{offset=20;first=next[0];last=next[1];}
  first>>=3;last=(last+7)>>3;
  for(x=first;x<last;x++){
   mask=rollrow[offset+x];if(!mask)continue;
   at=(uint16_t)(row+1)*20+x;n=roll_index(seqscreen[at]);if(n==255)goto selection_full;
   memcpy(pixels,rolltiles[n],16);roll_xor_tile(pixels,mask);
   id=roll_intern(pixels);refs[n]--;refs[roll_index(id)]++;canvas[at]=id;roll_audio();
  }
  service();
 }
 if(seqtileoverflow||seqdrawvalid!=2)goto selection_full;
 rollcache[0]=168;rollcache[5]=seqgrouptrack;rollcache[6]=seqgroupx0;rollcache[7]=seqgroupx1;rollcache[8]=seqgroupy0;rollcache[9]=seqgroupy1;
 return 1;
 selection_full:
 /* Staged cache pixels have not reached VRAM. Discard them together so a
    full retry cannot reuse an unuploaded tile with a cleared pending bit. */
 roll_clear_transition();seqfontdirty=0;return 0;
}
void seq_pixels(uint8_t navigation) BANKED {
 uint8_t c=seqtrack,i,x,t,y,gy,within,left,right,color,style,firstcol,lastcol,built=0,retained,velocitydirty=0,selectiondirty=0,oldy,oldnote,kind,event[4],lastnote=0,beatsteps=16/seqdenom,retried=0;
 int16_t note_y,scroll;uint16_t at,s,last=256,lastdur=0,e,count;
 redraw:
 built=0;velocitydirty=selectiondirty=0;scroll=0;last=256;lastdur=0;lastnote=0;
 ENABLE_RAM_MBC5;SWITCH_RAM_MBC5(0);seqtileoverflow=0;rollbuilding=1;rollreplace=rollpinslazy=0;memset(rollpending,0,15);HIDE_SPRITES;
 retained=(rollcache[0]==167||rollcache[0]==168)&&seqfontdirty&&seqviewtrack==c&&seqviewbase==seqbase&&seqviewcols==seqcols&&rollcache[1]==(uint8_t)seqlength[c]&&rollcache[2]==seqbeats&&rollcache[3]==seqdenom&&rollcache[4]==seqgridheight;
 if(retained){scroll=((int16_t)seqtop[c]-seqviewtop)*(seqheight>>3);if(scroll>=seqgridheight/8||scroll<=-(int16_t)(seqgridheight/8)){retained=0;scroll=0;}}
 if(retained){if(scroll&&navigation){rollpinslazy=1;memset(rollpins,0,128);}else roll_pinmaps();memcpy(canvas,seqscreen,360);memset(rollrowsdirty,0,17);built=3;
  /* Pitch scrolling moves immutable tile references, not their pixels.
     Dirty value 2 marks newly exposed rows that also need a piano label. */
  if(scroll)for(t=0;t<seqgridheight/8;t++){note_y=(int16_t)t-scroll;if(note_y>=0&&note_y<seqgridheight/8)memcpy(canvas+(uint16_t)(t+1)*20,seqscreen+(uint16_t)(note_y+1)*20,20);else rollrowsdirty[t]=2;}
 }
 else{if(seqfontdirty)roll_retain();else roll_begin();memset(rollrowsdirty,1,17);velocitydirty=1;roll_audio();memset(rollbackground,0,320);roll_audio();
  /* Coordinates and the underlying grid do not change during note edits. */
  for(i=0;i<=seqcols;i++){rollx[i]=16+((uint16_t)i*144)/seqcols;roll_audio();}
 }
 rolltop=seqtop[c];
 if(retained&&(rollcache[5]!=seqgrouptrack||rollcache[6]!=seqgroupx0||rollcache[7]!=seqgroupx1||rollcache[8]!=seqgroupy0||rollcache[9]!=seqgroupy1)){
  selectiondirty=1;if(rollcache[5]==c)roll_selection_dirty(rollcache[8],rollcache[9]);if(seqgrouptrack==c)roll_selection_dirty(seqgroupy0,seqgroupy1);
 }

 if(scroll&&navigation){roll_scroll_cells();goto paint_rows;}
 /* Cache each visible onset once; insertion order need not match step order.
    The nearest prior onset supplies any sustained body crossing the left edge. */
 memset(rollonsets,0,sizeof(rollonsets));count=seq_event_count(c);
 for(e=0;e<count;e++){seq_event_get(c,e,event);
  if(event[1]){s=event[0];if(s<seqbase){if(last==256||s>last){last=s;lastnote=event[1];lastdur=event[3]?event[3]:256;}}
   else if(s<(uint16_t)seqbase+seqcols)memcpy(rollonsets[s-seqbase],event,4);
  }if(!(e&3))roll_audio();
 }
 for(i=0;i<seqcols;i++){s=(uint16_t)seqbase+i;
  if(s<256&&rollonsets[i][1]){last=s;lastnote=rollonsets[i][1];lastdur=rollonsets[i][3]?rollonsets[i][3]:256;}
  oldy=rollnotey[i];if(scroll&&oldy!=255){note_y=(int16_t)oldy+scroll*8;oldy=note_y>=0&&note_y<seqgridheight?note_y:255;}oldnote=rollnotes[i];rollnotes[i]=rollkind[i]=0;
  if(last!=256&&s<256&&s-last<lastdur){rollnotes[i]=lastnote;rollkind[i]=last==s?1:2;}
  note_y=((int16_t)rolltop-(rollnotes[i]-1))*seqheight;rollnotey[i]=rollnotes[i]&&note_y>=0&&note_y<seqgridheight?note_y:255;
  kind=rollkind[i];if(rollnotes[i]&&seq_group_contains(last,rollnotes[i]-1))kind|=4;if(retained&&(oldnote!=rollnotes[i]||oldy!=rollnotey[i]||rolloldkind[i]!=kind)){roll_markrow(oldy);roll_markrow(rollnotey[i]);if(i){roll_markrow(rollnotey[i-1]);}if(i+1<seqcols)roll_markrow(rollnotey[i+1]);}rolloldkind[i]=kind;
  if(!retained){color=s>=seqlength[c]?1:s%beatsteps?1:s%((uint16_t)beatsteps*seqbeats)?2:3;
   if(s>=seqlength[c])roll_span(rollbackground,0,rollx[i],rollx[i+1],1);
   else roll_span(rollbackground,0,rollx[i],rollx[i]+1,color);
  }
  roll_audio();
 }
 if(!retained)for(x=0;x<20;x++){at=(uint16_t)x*16;for(y=1;y<8;y++){rollbackground[at+y*2]=rollbackground[at];rollbackground[at+y*2+1]=rollbackground[at+1];}roll_audio();}
 paint_rows:
 for(t=0;t<seqgridheight/8;t++){
  if(!rollrowsdirty[t])continue;service();
  style=seqheight>8?(((t+1)*8)&(seqheight-1))==0:0;
  if(!(built&(1<<style))){
   built|=1<<style;
   roll_audio();memcpy(rollrow,rollbackground,320);roll_audio();
   for(y=0;y<8;y++){gy=t*8+y;within=gy&(seqheight-1);
    if(within==seqheight-1)for(x=0;x<20;x++){at=(uint16_t)x*16+y*2;rollrow[at]|=(uint8_t)~rollrow[at+1];}
   }
   memcpy(rollbasepixels[style],rollrow,320);
   for(x=0;x<20;x++){roll_audio();rollbaseids[style][x]=roll_intern(rollrow+x*16);}
  }
  memset(rolldirty,0,20);if(selectiondirty||seqgrouptrack==c)memset(rolldirty+2,1,18);if(!retained||rollrowsdirty[t]==2)rolldirty[0]=rolldirty[1]=1;
  for(i=0;i<seqcols;i++)if(rollnotey[i]!=255&&rollnotey[i]<t*8+8&&rollnotey[i]+seqheight>t*8){
   firstcol=rollx[i]>>3;lastcol=(rollx[i+1]-1)>>3;for(x=firstcol;x<=lastcol;x++)rolldirty[x]=1;
  }

  for(x=0;x<20;x++)if(rolldirty[x]){roll_audio();memcpy(rollrow+x*16,rollbasepixels[style]+x*16,16);}
  /* A retained edit cannot change the piano; keep its immutable tile IDs. */
  if(!retained||rollrowsdirty[t]==2)roll_keyboard(t);roll_audio();
  for(i=0;i<seqcols;i++)if(rollnotey[i]!=255&&rollnotey[i]<t*8+8&&rollnotey[i]+seqheight>t*8){
   note_y=rollnotey[i];left=rollx[i]+(rollkind[i]==1);right=rollx[i+1];color=seqbase+i>=seqlength[c]?2:3;
   if(i+1==seqcols||rollnotes[i+1]!=rollnotes[i]||rollkind[i+1]==1)right--;
   for(y=0;y<8;y++){gy=t*8+y;if((int16_t)gy>=note_y+1&&(int16_t)gy<note_y+seqheight-1)roll_span(rollrow,y,left,right,color);}
   roll_audio();
  }

  if(seqgrouptrack==c)roll_invert_selection(t);
  for(x=retained&&rollrowsdirty[t]!=2?2:0;x<20;x++){roll_audio();canvas[(uint16_t)(t+1)*20+x]=rolldirty[x]?roll_intern(rollrow+x*16):rollbaseids[style][x];}
 }
 if(seqcols==16&&!seqvelocityhidden&&!(scroll&&navigation)){
  for(i=0;i<16;i++){s=(uint16_t)seqbase+i;rollkind[i]=0;if(s<256&&rollonsets[i][1]){rollkind[i]=1+((uint16_t)rollonsets[i][2]*20)/127;}if(rolloldvel[i]!=rollkind[i])velocitydirty=1;rolloldvel[i]=rollkind[i];roll_audio();}
  if(velocitydirty)for(t=0;t<3;t++){roll_audio();memset(rollrow,0,320);
   for(y=0;y<8;y++){gy=t*8+y;if(!gy)roll_span(rollrow,y,0,160,2);
    for(i=0;i<16;i++){s=seqbase+i;left=rollx[i];right=rollx[i+1];
     if(rollkind[i]){
      if(gy>=24-rollkind[i])roll_span(rollrow,y,left+2,right-2,s>=seqlength[c]?2:3);
      if(gy==23)roll_span(rollrow,y,left,right,2);
     }
     roll_audio();
    }
   }
   for(x=0;x<20;x++){roll_audio();canvas[(uint16_t)(15+t)*20+x]=roll_intern(rollrow+x*16);}
  }
 }
 if(seqtileoverflow&&!retried){retried=1;roll_clear_transition();seqfontdirty=0;goto redraw;}
 rollcache[0]=167;rollcache[1]=(uint8_t)seqlength[c];rollcache[2]=seqbeats;rollcache[3]=seqdenom;rollcache[4]=seqgridheight;rollcache[5]=seqgrouptrack;rollcache[6]=seqgroupx0;rollcache[7]=seqgroupx1;rollcache[8]=seqgroupy0;rollcache[9]=seqgroupy1;
 previewshape=255;seqfontdirty=1;seqviewtop=seqtop[c];seqviewbase=seqbase;seqviewcols=seqcols;seqviewtrack=c;
}
/* Playhead and cursor sprites move without touching the background cache. */
void seq_playhead(void) BANKED {
 uint8_t ch,limit,i,x,c=seqtrack,on=0,left,right,width,top,q,y,gy,gx,bits,edge,buf[16];int16_t cursor_y;
 OAM_item_t *sprite;
 if(rollbuilding){HIDE_SPRITES;return;}
 const uint8_t line[16]={0,128,0,128,0,128,0,128,0,128,0,128,0,128,0,128};
 if(navopen||seqpopup){HIDE_SPRITES;return;}
 SPRITES_8x8;OBP0_REG=0xE4;
 if(seqplaying&&seqposition[c]>=seqbase&&seqposition[c]<seqbase+seqcols&&(seqmode?c==4:c!=4)){
  if(rollplaypos!=seqposition[c]||rollplaybase!=seqbase||rollplaycols!=seqcols||rollplaytrack!=c||rollplayx==255){
   x=(c==6?24:16)+((uint16_t)(seqposition[c]-seqbase)*(c==6?136:144))/seqcols;
   if(!rollplayvalid||rollplayheight!=seqgridheight){
    if(!rollplayvalid){ui_upload_tile(0,line,1);rollplayvalid=1;}
    sprite=shadow_OAM;for(i=0;i<17;i++,sprite++){sprite->tile=0;sprite->prop=0;sprite->y=24+i*8;sprite->x=i<seqgridheight/8?x+8:0;}
    rollplayheight=seqgridheight;
   }else if(rollplayx!=x){sprite=shadow_OAM;for(i=0;i<seqgridheight/8;i++,sprite++)sprite->x=x+8;}
   rollplayx=x;rollplaypos=seqposition[c];rollplaybase=seqbase;rollplaycols=seqcols;rollplaytrack=c;
  }on=1;
 }else if(rollplayx!=255){sprite=shadow_OAM;for(i=0;i<17;i++,sprite++)sprite->x=0;rollplayx=255;}
 if(c==6){seqheight=8;seqgridheight=seqcols==16&&!seqvelocityhidden?112:136;cursor_y=drumrow*8;}else cursor_y=((int16_t)seqtop[c]-seqpitch[c])*seqheight;
 ch=seqhead==5?24:seqheight;limit=seqhead==5?136:seqgridheight;if(seqhead==5)cursor_y=112;
 if((!seqhead||seqhead==5||seqhead==6)&&!seqfocus&&cursor_y>=0&&cursor_y<limit){
  i=seqcursor[c]-seqbase;top=cursor_y+8;
  if(!rollcursorvisible||rollcursorcell!=i||rollcursory!=top||rollcursorcols!=seqcols||rollcursortrack!=c||rollcursorhead!=seqhead||rollcursorh!=ch){
  if(seqhead==6){left=0;right=16;}else{left=(c==6?24:16)+((uint16_t)i*(c==6?136:144))/seqcols;right=(c==6?24:16)+((uint16_t)(i+1)*(c==6?136:144))/seqcols;}width=right-left;top=cursor_y+8;
  if(rollcursorw!=width||rollcursorh!=ch){
   for(q=0;q<20;q++){gx=rollqx[q];if(gx>=width||rollqy[q]>=ch)continue;
    for(y=0;y<8;y++){gy=rollqy[q]+y;bits=0;
     if(gy<ch&&gx<width){
      if(!gy||gy==ch-1)bits=width-gx>=8?255:(uint8_t)(255<<(8-(width-gx)));
      else{if(!gx)bits|=128;edge=width-1;if(edge>=gx&&edge<gx+8)bits|=128>>(edge-gx);}
     }buf[y*2]=0;buf[y*2+1]=bits;
    }ui_upload_tile(2+q,buf,1);roll_audio();
   }
   sprite=shadow_OAM+17;for(q=0;q<20;q++,sprite++){sprite->tile=2+q;sprite->prop=0;sprite->x=0;}
   rollcursorw=width;rollcursorh=ch;
  }
  /* The usual cursor has two visible tiles. Hidden spare tiles need no writes
     when a same-sized rectangle moves to another cell. */
  for(gy=0;gy<ch;gy+=8)for(gx=0;gx<width;gx+=8){
   q=(gy>>3)*5+(gx>>3);sprite=shadow_OAM+17+q;
   if(top+gy<limit+8){sprite->x=left+8+gx;sprite->y=top+16+gy;}else sprite->x=0;
  }
  rollcursorx=left;rollcursory=top;rollcursorcell=i;rollcursorcols=seqcols;rollcursortrack=c;rollcursorhead=seqhead;rollcursorvisible=1;
  }on=1;
 }else if(rollcursorvisible){for(gy=0;gy<rollcursorh;gy+=8)for(gx=0;gx<rollcursorw;gx+=8){q=(gy>>3)*5+(gx>>3);shadow_OAM[17+q].x=0;}rollcursorvisible=0;}

 if(on){SHOW_SPRITES;}else{HIDE_SPRITES;}
}

void roll_begin(void) BANKED {ENABLE_RAM_MBC5;SWITCH_RAM_MBC5(0);rollcache[0]=0;seqtilecount=seqtileoverflow=0;rollbuilding=rollreplace=1;rollpinslazy=0;memset(rollpending,0,15);memset(rollheads,255,256);memset(rollpins,0,128);}
/* Cache pressure retries from an empty RAM cache. The old VRAM remains visible
   until roll_commit briefly hides the background for the replacement upload. */
void roll_clear_transition(void) BANKED {uint8_t row;HIDE_SPRITES;
 for(row=1;row<18;row++){memset(canvas+(uint16_t)row*20,0,20);memset(seqscreen+(uint16_t)row*20,0,20);roll_audio();}
 roll_begin();
}
void roll_retain(void) BANKED {ENABLE_RAM_MBC5;SWITCH_RAM_MBC5(0);rollcache[0]=0;seqtileoverflow=0;rollbuilding=1;rollreplace=rollpinslazy=0;memset(rollpending,0,15);if(seqtrack==6){memset(rollpins,0,128);roll_audio();roll_pinmap(visible,360);}else roll_pinmaps();}
void roll_upload_dirty(uint8_t row) BANKED {uint8_t x,old,id,n;uint16_t at,*refs=(uint16_t *)rollonsets;
 /* A bare row-focus change also stages new velocity tiles. It has no grid
    renderer to open the transaction, unlike a rectangle selection update. */
 if(!rollbuilding){rollbuilding=1;rollreplace=0;memset(rollpending,0,15);if(rollcache[0]==168){rollpinslazy=0;roll_selection_pins();roll_pin_bases();}else{rollpinslazy=1;memset(rollpins,0,128);}}
 for(x=0;x<20;x++)if(rolldirty[x]){mixfill();at=(uint16_t)(row+1)*20+x;old=canvas[at];id=roll_intern(rollrow+x*16);
 /* Row-only DRUM velocity refreshes share the selection cache. Account for
    their tile replacements before the next selection gesture pins its map. */
 if(rollcache[0]==168&&old!=id){n=roll_index(old);if(n!=255)refs[n]--;n=roll_index(id);if(n!=255)refs[n]++;}canvas[at]=id;}}
void roll_upload(uint8_t row) BANKED {memset(rolldirty,1,20);roll_upload_dirty(row);}
void roll_commit(void) BANKED {uint8_t n;if(!rollbuilding)return;
 if(rollreplace)ui_transition_begin();
 for(n=0;n<seqtilecount;n++)if(rollpending[n>>3]&(1<<(n&7))){ui_upload_tile(roll_id(n),rolltiles[n],0);roll_audio();}
 memset(rollpending,0,15);rollreplace=rollbuilding=0;
}

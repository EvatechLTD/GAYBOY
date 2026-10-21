#pragma bank 46
#pragma opt_code_speed
#include "api.h"
#include "drum_rows.h"
extern __at (0xBA00) uint8_t rollrow[320];
extern __at (0xBB40) uint8_t rollbackground[320];
extern __at (0xBC80) uint8_t rollx[41];
extern __at (0xAD80) uint8_t drumleft[192];
extern __at (0xAE40) uint8_t drumright[192];
extern __at (0xAF00) uint8_t drumnext[192];
extern __at (0xAFC0) uint8_t drumheads[13];
extern __at (0xA500) uint32_t fastrowbits[13];
extern __at (0xA534) uint16_t fastoverlap;
extern __at (0xA536) uint16_t fastghostrows;
extern __at (0xA800) uint16_t fastcells[13][32];
extern __at (0xA540) uint8_t fastcoverorigin[13][32];
const uint8_t drum_masks[9]={255,127,63,31,15,7,3,1,0};
static uint16_t grid_duration(const uint8_t *e){return e[3]?e[3]:256U;}
static uint8_t grid_selected(const uint8_t *e){return seqgrouptrack==6&&e[1]&&e[0]>=seqgroupx0&&e[0]<=seqgroupx1&&DRUM_VIEW_ROW(e[1]-1)>=seqgroupy0&&DRUM_VIEW_ROW(e[1]-1)<=seqgroupy1;}
/* Span compositing is a live-performance path. Keep all temporaries in the
   reserved renderer scratch, below neither the tile pins nor the audio state. */
void drum_span(uint8_t y,uint8_t left,uint8_t right,uint8_t color) __naked { __asm
 push bc
 add a,a
 ld (0xafd0),a
 ld b,e
 ldhl sp,#4
 ld c,(hl)
 inc hl
 ld d,(hl)
drum_span_loop$:
 ld a,b
 cp a,c
 jp nc,drum_span_done$
 and #0xf8
 add a,#8
 cp a,c
 jr c,drum_span_end$
 ld a,c
drum_span_end$:
 ld (0xafd2),a
 dec a
 and #7
 inc a
 add a,#<_drum_masks
 ld l,a
 ld a,#>_drum_masks
 adc a,#0
 ld h,a
 ld a,(hl)
 ld (0xafd1),a
 ld a,b
 and #7
 add a,#<_drum_masks
 ld l,a
 ld a,#>_drum_masks
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
 ld a,#0xba
 adc a,#0
 ld h,a
 ld a,(0xafd0)
 add a,l
 ld l,a
 ld a,e
 cpl
 and a,(hl)
 bit 0,d
 jr z,drum_span_low$
 or a,e
drum_span_low$:
 ld (hl+),a
 ld a,e
 cpl
 and a,(hl)
 bit 1,d
 jr z,drum_span_high$
 or a,e
drum_span_high$:
 ld (hl),a
 ld a,(0xafd2)
 ld b,a
 jp drum_span_loop$
drum_span_done$:
 pop bc
 pop hl
 inc sp
 inc sp
 jp (hl)
 __endasm; }
void drum_replicate(uint8_t first,uint8_t last) __naked { __asm
 push bc
 ld d,a
 ld a,e
 sub a,d
 ld (0xafd4),a
 ld a,d
 add a,a
 add a,#0x30
 ld l,a
 ld h,#0xba
 ld b,#17
drum_copy_tile$:
 ld a,(hl+)
 ld c,a
 ld a,(hl-)
 ld d,a
 ld a,(0xafd4)
 ld e,a
 or a
 jr z,drum_copy_next$
 push hl
drum_copy_line$:
 inc hl
 inc hl
 ld (hl),c
 inc hl
 ld (hl),d
 dec hl
 dec e
 jr nz,drum_copy_line$
 pop hl
drum_copy_next$:
 ld a,l
 add a,#16
 ld l,a
 jr nc,drum_copy_low$
 inc h
drum_copy_low$:
 dec b
 jr z,drum_copy_done$
 ld a,b
 and #7
 jr nz,drum_copy_tile$
 push bc
 push de
 push hl
 call _mixfill
 pop hl
 pop de
 pop bc
 jr drum_copy_tile$
drum_copy_done$:
 pop bc
 ret
 __endasm; }
void roll_retain(void) BANKED;
extern __at (0xBD00) uint8_t rollkind[40];
extern __at (0xAD80) uint8_t rollcache[10];
extern __at (0xADB8) uint8_t rolloldvel[40];
extern __at (0xBFE8) uint8_t rolldirty[20];
void roll_upload_dirty(uint8_t row) BANKED;
void drum_velocity_render(void) BANKED {uint8_t t,scan,i,vel,e[4],saved[5],changed=0,full=rollcache[0]!=167&&rollcache[0]!=168,left,right,x,row;uint16_t scaled,n,step,a,b,span,bit,count=seq_event_count(6),end=(uint16_t)seqbase+16,*covered=(uint16_t *)rollrow;
 /* The full drum grid has already consumed its background scanline. Reuse
    that scratch for all thirteen rows' onset velocities, until a note edit
    or viewport change rebuilds the grid. Row focus then costs sixteen bytes,
    rather than sixteen scans of every event on every selection edge. */
 if(full||rollcache[2]!=225||rollcache[1]!=(uint8_t)count||rollcache[3]!=(uint8_t)(count>>8)){
  /* The extra unused bytes are safe. SDCC's PUSH-AF constant optimization
     miscompiles a 208-byte memset count as 144 on this GBZ80 toolchain. */
  memset(rollbackground,0,256);memset(covered,0,26);
  for(n=0;n<count;n++){if(!(n&7))mixfill();if(!seq_event_get(6,n,e)||!e[1]||e[1]>13)continue;row=DRUM_VIEW_ROW(e[1]-1);a=e[0];b=a+grid_duration(e);if(b<=seqbase||a>=end)continue;
   left=a<seqbase?0:a-seqbase;right=b>end?16:b-seqbase;span=(65535U<<left)&(65535U>>(16-right));
   if(a>=seqbase){i=a-seqbase;bit=1U<<i;if(!(covered[row]&bit))rollbackground[(uint16_t)row*16+i]=e[2];}covered[row]|=span;
  }
  rollcache[1]=count;rollcache[2]=225;rollcache[3]=count>>8;
 }
 memcpy(rollkind,rollbackground+(uint16_t)drumrow*16,16);
 memset(rolldirty,full?1:0,20);
 for(i=0;i<16;i++){vel=rollkind[i];scaled=(uint16_t)vel*20;rollkind[i]=vel?1+((scaled+1+(scaled>>7))>>7):0;
  if(full||rollkind[i]!=rolloldvel[i]){changed=1;left=(rollx[i]+2)>>3;right=(rollx[i+1]-3)>>3;for(x=left;x<=right;x++)rolldirty[x]=1;}rolloldvel[i]=rollkind[i];
 }
 if(changed)for(t=14;t<17;t++){if(rollcache[0]==168)memcpy(saved,(const void *)0xAFD0,5);memset(rollrow,0,320);scan=(t-14)*8;if(!scan)drum_span(0,0,160,2);for(i=0;i<16;i++){if(rollkind[i]){step=(uint16_t)seqbase+i;scan=(t-14)*8;if(scan<24-rollkind[i])scan=24-rollkind[i];for(;scan<(t-13)*8;scan++)drum_span(scan&7,rollx[i]+2,rollx[i+1]-2,step>=seqlength[6]?2:3);}mixfill();}if(rollcache[0]==168)memcpy((void *)0xAFD0,saved,5);roll_upload_dirty(t);service();}seqviewtop=drumrow;
}
extern uint8_t seqbeats,seqdenom;
void roll_clear_transition(void) BANKED;
__at (0xAFD8) uint8_t drumselectcache[24];
static uint8_t drumdim[24];
uint8_t roll_navigation_abort(void) BANKED;
void roll_render_begin(void) BANKED;
void drum_render(void) BANKED {
 uint8_t t,row,i,left,boundary,color,scan,last,target,retried=0,e[4];
 uint16_t a,b,event,visible=0,k,s,count,viewend;uint32_t cellbits;
 roll_render_begin();if(roll_navigation_abort())return;
 redraw:
 visible=0;memset(fastcells,0,sizeof(fastcells));memset(fastrowbits,0,sizeof(fastrowbits));fastoverlap=fastghostrows=0;viewend=(uint16_t)seqbase+seqcols;count=seq_event_count(6);memset(drumselectcache,0,24);memset(drumdim,0,24);HIDE_SPRITES;drum_init();if(seqfontdirty)roll_retain();else roll_begin();mixfill();if(roll_navigation_abort())return;memset(rollbackground,0,320);mixfill();if(roll_navigation_abort())return;memset(rollrow,0,320);mixfill();if(roll_navigation_abort())return;
 for(i=0;i<=seqcols;i++){rollx[i]=24+((uint16_t)i*136)/seqcols;mixfill();if(roll_navigation_abort())return;}
 boundary=seqlength[6]<=seqbase?24:seqlength[6]>=viewend?160:rollx[seqlength[6]-seqbase];if(boundary<160)drum_span(0,boundary,160,1);
 for(i=0;i<seqcols;i++){s=seqbase+i;left=rollx[i];color=s>=seqlength[6]?2:(s%(16/seqdenom))?1:((s/(16/seqdenom))%seqbeats)?2:3;drum_span(0,left,left+1,color);mixfill();if(roll_navigation_abort())return;}
 drum_replicate(0,7);mixfill();if(roll_navigation_abort())return;
 memcpy(rollbackground,rollrow,320);memcpy((void *)0xBD40,rollrow,320);memset(drumheads,255,13);mixfill();if(roll_navigation_abort())return;
 for(event=0;event<count;event++){if(!(event&7))mixfill();if(roll_navigation_abort())return;if(!seq_event_get(6,event,e)||!e[1]||e[1]>13)continue;row=DRUM_VIEW_ROW(e[1]-1);a=e[0];b=a+grid_duration(e);
  if(b<=seqbase||a>=viewend)continue;left=a>seqbase?a-seqbase:0;last=b<viewend?b-seqbase:seqcols;cellbits=(0xffffffffUL<<left)&(0xffffffffUL>>(32-last));if(fastrowbits[row]&cellbits)fastoverlap|=1U<<row;for(i=left;i<last;i++)if(!(fastrowbits[row]&(1UL<<i)))fastcoverorigin[row][i]=a;fastrowbits[row]|=cellbits;if(a>=seqbase&&!fastcells[row][a-seqbase])fastcells[row][a-seqbase]=event+1;if(visible>=192)continue;
  if(grid_selected(e))drumselectcache[visible>>3]|=1<<(visible&7);
  drumleft[visible]=rollx[a>seqbase?a-seqbase:0]+1;if(!eval_drum_allowed(event)){drumdim[visible>>3]|=1<<(visible&7);fastghostrows|=1U<<row;}drumright[visible]=rollx[b<viewend?b-seqbase:seqcols];drumnext[visible]=drumheads[row];drumheads[row]=visible;visible++;mixfill();if(roll_navigation_abort())return;
 }
 for(t=0;t<seqgridheight/8;t++){
  target=DRUM_SCREEN_INDEX(t);if(target==255){memset(rollrow,0,320);roll_upload(t);continue;}
  memcpy(rollrow,rollbackground,320);drum_label(DRUM_VOICE_ROW(target),rollrow);
  /* Every note in a drum row has the same six-pixel body. Composite one
     scanline, then copy that finished grid scanline; never redraw each pixel. */
  scan=1;last=6;
  k=target<13?drumheads[target]:255;while(k!=255){
   if(drumleft[k]<boundary)drum_span(scan,drumleft[k],drumright[k]<boundary?drumright[k]:boundary,drumdim[k>>3]&(1<<(k&7))?2:3);
   if(drumright[k]>boundary)drum_span(scan,drumleft[k]>boundary?drumleft[k]:boundary,drumright[k],2);
   mixfill();if(roll_navigation_abort())return;k=drumnext[k];
  }
  drum_replicate(scan,last);if(target<13)drum_span(7,24,160,1);mixfill();if(roll_navigation_abort())return;
  if(seqgrouptrack==6)roll_invert_selection(t);
  roll_upload(t);service();
 }
 if(seqcols==16&&!seqvelocityhidden)drum_velocity_render();
 if(seqtileoverflow&&!retried){retried=1;roll_clear_transition();seqfontdirty=0;goto redraw;}
 seqfontdirty=1;seqviewbase=seqbase;seqviewcols=seqcols;seqviewtrack=6;seqviewtop=drumrow;rollcache[0]=167;rollcache[4]=seqgridheight;rollcache[5]=seqgrouptrack;rollcache[6]=seqgroupx0;rollcache[7]=seqgroupx1;rollcache[8]=seqgroupy0;rollcache[9]=seqgroupy1;
}

void drum_feedback_span(uint8_t left,uint8_t right) BANKED {drum_span(1,left,right,3);}

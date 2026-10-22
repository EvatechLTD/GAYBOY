#pragma bank 44
#pragma opt_code_speed
#include "api.h"
#include "resident.h"
void mixer_pattern_changed(void) BANKED;
void storage_sorted_dirty(void) BANKED;
#include "sparse_store.h"
#include "mixer_shared.h"
#include "tones.h"
extern volatile uint8_t padread,padwrite;
extern uint8_t noisepatch[2][5],pulsekickpatch[8],drumkit;
extern uint8_t globalmod[10];
uint8_t coarse_matches(const uint8_t *raw) BANKED;
uint8_t tones_match_buffer(const uint8_t *raw) BANKED {uint8_t c;
 if(raw[164]!='S'||raw[165]!=1||raw[176]!='S'||raw[177]!=1)return 0;
 for(c=0;c<4;c++)if(memcmp(param[c],raw+c*32,26)||program[c]!=raw[c*32+26])return 0;
 if(custom!=raw[128]||memcmp(customwave,raw+129,16)||memcmp(finepitch,raw+145,6)||memcmp(noisepatch,raw+151,10)||drumkit!=raw[161]||master!=raw[162]||power!=raw[163]||memcmp(pulsekickpatch,raw+168,8))return 0;
 if(memcmp(evalpatch,raw+178,128)||memcmp(globalmod,raw+306,10)||!coarse_matches(raw))return 0;
 return DRUM_MAPPED&&raw[320]=='D'&&raw[321]==1&&!memcmp(drumsourcekit,raw+322,10)&&!memcmp(drumsourceslot,raw+332,10);
}

void seq_pattern_release(void) BANKED;void seq_pattern_handoff(void) BANKED;
uint8_t sparse_enabled,sparse_install_slot=255,sparse_song=0,sparse_patterns=5;
uint16_t sparse_slots[8],sparse_tones[8];char sparse_song_name[17]="STRIPPED";
uint8_t pool_root[128],pool_error,pool_used[38],sparse_journal_slot=255;
extern uint8_t pattern_dirty,seqgate[7],seqbeats,seqdenom,seqcachedgate[7];
extern uint16_t pattern_generation,seqcachedbpm,seqstepunits,seqgateunits[7],seqclock,seqdeadline;
static uint16_t saved_generation,last_edit;static uint8_t io_busy;
/* Private WRAM staging survives renderer scratch reuse and navigation. */
static uint8_t launchdata[449],launchslot=255,launchequal,launchready,firstready;
static uint8_t launchnotes[6][4];
static uint16_t launchscan;
static uint16_t launchbytes,launchgeneration;
uint16_t resident_tone_generation;
uint8_t resident_same_tones;
void sparse_prepare_invalidate(void) BANKED;

static void bank_copy(uint8_t *source,uint8_t *target,uint8_t bank,uint8_t n) __naked {__asm
 ldhl sp,#2
 ld a,(hl+)
 ld (0x4000),a
 ld a,(hl)
 ld h,b
 ld l,c
 ld b,a
 cp #16
 jr nz,resident_bank_loop$
 .rept 16
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 jr resident_bank_done$
resident_bank_loop$:
 ld a,(de)
 inc de
 ld (hl+),a
 dec b
 jr nz,resident_bank_loop$
resident_bank_done$:
 xor a,a
 ld (0x4000),a
 pop hl
 inc sp
 inc sp
 jp (hl)
 __endasm;}
static void io(uint8_t bank,uint16_t address,uint8_t *data,uint16_t count,uint8_t writing){uint8_t n,buf[16];while(count){n=count>16?16:count;if(writing)memcpy(buf,data,n);__critical{if(writing)bank_copy(buf,(uint8_t *)address,bank,n);else bank_copy((uint8_t *)address,buf,bank,n);}if(!writing)memcpy(data,buf,n);address+=n;data+=n;count-=n;}}

void resident_read(uint8_t slot,uint16_t offset,uint8_t *data,uint16_t count) BANKED {if(slot>=5){memset(data,0,count);return;}io(1+(slot>>2),0xA000U+(uint16_t)(slot&3)*2048U+offset,data,count,0);}
void resident_write(uint8_t slot,uint16_t offset,const uint8_t *data,uint16_t count) BANKED {if(slot==launchslot){launchbytes=0;launchready=0;launchequal=0;}if(slot<5)io(1+(slot>>2),0xA000U+(uint16_t)(slot&3)*2048U+offset,(uint8_t *)data,count,1);}
uint16_t resident_move_left;uint8_t resident_move_bank,resident_move_ie;
static void move_forward(uint8_t *target,uint8_t *source,uint16_t bytes,uint8_t bank) __naked {__asm
 ldhl sp,#2
 ld a,(hl+)
 ld (_resident_move_left),a
 ld a,(hl+)
 ld (_resident_move_left+1),a
 ld a,(hl)
 ld (_resident_move_bank),a
 ld h,b
 ld l,c
move_forward_block$:
 ldh a,(0xff)
 ld (_resident_move_ie),a
 xor a,a
 ldh (0xff),a
 ld a,(_resident_move_bank)
 ld (0x4000),a
 ld a,(_resident_move_left+1)
 or a,a
 jr nz,move_forward_full$
 ld a,(_resident_move_left)
 cp #16
 jr nc,move_forward_full$
 ld c,a
move_forward_tail$:
 ld a,(hl+)
 ld (de),a
 inc de
 dec c
 jr nz,move_forward_tail$
 xor a,a
 ld (0x4000),a
 ld (_resident_move_left),a
 ld a,(_resident_move_ie)
 ldh (0xff),a
 jr move_forward_done$
move_forward_full$:
 .rept 16
 ld a,(hl+)
 ld (de),a
 inc de
 .endm
 xor a,a
 ld (0x4000),a
 ld a,(_resident_move_ie)
 ldh (0xff),a
 ld a,(_resident_move_left)
 sub #16
 ld (_resident_move_left),a
 ld c,a
 ld a,(_resident_move_left+1)
 sbc a,#0
 ld (_resident_move_left+1),a
 or a,c
 jr nz,move_forward_block$
move_forward_done$:
 pop hl
 add sp,#3
 jp (hl)
 __endasm;}
static void move_backward(uint8_t *target,uint8_t *source,uint16_t bytes,uint8_t bank) __naked {__asm
 ldhl sp,#2
 ld a,(hl+)
 ld (_resident_move_left),a
 ld a,(hl+)
 ld (_resident_move_left+1),a
 ld a,(hl)
 ld (_resident_move_bank),a
 ld h,b
 ld l,c
move_backward_block$:
 ldh a,(0xff)
 ld (_resident_move_ie),a
 xor a,a
 ldh (0xff),a
 ld a,(_resident_move_bank)
 ld (0x4000),a
 ld a,(_resident_move_left+1)
 or a,a
 jr nz,move_backward_full$
 ld a,(_resident_move_left)
 cp #16
 jr nc,move_backward_full$
 ld c,a
move_backward_tail$:
 ld a,(hl-)
 ld (de),a
 dec de
 dec c
 jr nz,move_backward_tail$
 xor a,a
 ld (0x4000),a
 ld (_resident_move_left),a
 ld a,(_resident_move_ie)
 ldh (0xff),a
 jr move_backward_done$
move_backward_full$:
 .rept 16
 ld a,(hl-)
 ld (de),a
 dec de
 .endm
 xor a,a
 ld (0x4000),a
 ld a,(_resident_move_ie)
 ldh (0xff),a
 ld a,(_resident_move_left)
 sub #16
 ld (_resident_move_left),a
 ld c,a
 ld a,(_resident_move_left+1)
 sbc a,#0
 ld (_resident_move_left+1),a
 or a,c
 jr nz,move_backward_block$
move_backward_done$:
 pop hl
 add sp,#3
 jp (hl)
 __endasm;}
void resident_move(uint16_t to,uint16_t from,uint16_t bytes) BANKED {uint8_t bank=1+(mx.slot>>2);uint16_t base=0xA000U+(uint16_t)(mx.slot&3)*2048U+RESIDENT_EVENTS;uint8_t *dst=(uint8_t *)(base+to),*src=(uint8_t *)(base+from);if(!bytes||to==from)return;if(to>from)move_backward(dst+bytes-1,src+bytes-1,bytes,bank);else move_forward(dst,src,bytes,bank);}
void resident_events_changed(void) BANKED {last_edit=sys_time;mixer_pattern_changed();seqirqdirty=1;}
static void metadata(uint8_t slot,uint8_t writing){uint8_t b[81];if(writing){memcpy(b,seqeventcounts,14);memcpy(b+14,seqlength,14);memcpy(b+28,seqdefaultdur,14);memcpy(b+42,seqdefaultvel,7);memcpy(b+49,seqgate,7);memcpy(b+56,mx.level,7);memcpy(b+63,mx.pan,7);b[70]=seqmuted;b[71]=seqsolo;b[72]=seqbeats;b[73]=seqdenom;b[74]=0;memcpy(b+75,&seqbpm,2);memcpy(b+77,&drummutemask,2);memcpy(b+79,&drumsolomask,2);resident_write(slot,32,b,81);resident_write(slot,16,(uint8_t *)mx.name,16);}else{resident_read(slot,32,b,81);applymeta(b);resident_read(slot,16,(uint8_t *)mx.name,16);mx.name[16]=0;}}
uint8_t sparse_snapshot(uint8_t slot) BANKED {if(slot>=5||slot!=mx.slot||io_busy)return 0;io_busy=1;metadata(slot,1);tones_capture();resident_write(slot,128,TONE_RAW,POOL_TONE_BYTES);saved_generation=pattern_generation;pattern_dirty=0;io_busy=0;return 1;}
uint8_t sparse_restore(uint8_t slot) BANKED {if(slot>=5||sparse_enabled!=1)return 0;resident_same_tones=0;mx.slot=slot;storage_sorted_dirty();
 if(slot==launchslot&&launchready){
  applymeta(launchdata+16);memcpy(mx.name,launchdata,16);mx.name[16]=0;
  if(launchequal&&launchgeneration==resident_tone_generation)resident_same_tones=1;
  else tones_apply_buffer(launchdata+97);
 }else {metadata(slot,0);resident_read(slot,128,TONE_RAW,POOL_TONE_BYTES);tones_apply();}
 firstready=slot==launchslot&&launchready;sparse_prepare_invalidate();seqeventcache=0;saved_generation=pattern_generation;pattern_dirty=0;return 1;}
uint8_t sparse_activate(uint8_t slot) BANKED {uint8_t busy=seqservicing;if(slot>=5)return 0;seqservicing=1;if(!sparse_restore(slot)){seqservicing=busy;return 0;}mx.pending=255;mx.padcache=0;seqdrawvalid=0;if(seqplaying)seq_pattern_handoff();seqservicing=busy;dirty=1;return 1;}
void sparse_request(uint8_t slot,uint8_t edit) BANKED {if(slot>=5)return;firstready=0;if(edit&&slot==mx.slot){page=8;seq_open();dirty=1;return;}if(pattern_dirty)sparse_snapshot(mx.slot);sparse_prepare_invalidate();launchslot=slot;mx.pending=slot;mx.openempty=edit;mx.cachevalid=0;if(!seqplaying||!mx.quant){mx.pending=255;mixer_activate(slot,edit);}dirty=1;}
void sparse_service(void) BANKED {sparse_prepare_service();if(!io_busy&&pattern_dirty&&!seqservicing&&!seqplaying&&padread==padwrite&&(uint16_t)(sys_time-last_edit)>30)sparse_snapshot(mx.slot);}
uint8_t sparse_boot(void) BANKED {uint8_t i,magic[4];io(3,0xBF80,magic,4,0);sparse_enabled=1;if(memcmp(magic,"GSR1",4)){if(magic[0]!=0&&magic[0]!=255){sparse_enabled=2;return 1;}{uint8_t z=0;uint16_t at;for(at=0;at<2080;at+=64)io(3,0xA000U+at,&z,1,1);}memset(pool_root,0,128);memcpy(pool_root,"GSR1",4);pool_root[8]=4;io(3,0xBF80,pool_root,128,1);mx.slot=0;defaults();eval_defaults();for(i=0;i<5;i++){mx.slot=i;mx.name[0]='P';mx.name[1]='1'+i;mx.name[2]=0;sparse_snapshot(i);}mx.slot=0;}else io(3,0xBF80,pool_root,128,0);for(i=0;i<8;i++)sparse_slots[i]=sparse_tones[i]=i<5?i:65535U;return 1;}
void sparse_finish_install(void) BANKED {}
uint8_t resident_first_note(uint8_t c,uint8_t *e) BANKED {if(!firstready||c>=6)return 2;if(!launchnotes[c][1])return 0;memcpy(e,launchnotes[c],4);return 1;}
void resident_first_clear(void) BANKED {firstready=0;}
void sparse_prepare_service(void) BANKED {uint16_t source,left,end;uint8_t n,c,e[4];
 if(io_busy||seqservicing||!seqplaying||mx.pending==255||mx.pending==mx.slot||launchslot!=mx.pending||launchready)return;
 if(seqticks>=seqdeadline||seqdeadline-seqticks<8)return;
 if(launchbytes<sizeof(launchdata)){
  if(launchbytes<16){source=16+launchbytes;left=16-launchbytes;}
  else if(launchbytes<97){source=32+launchbytes-16;left=97-launchbytes;}
  else {source=128+launchbytes-97;left=sizeof(launchdata)-launchbytes;}
  n=left>16?16:left;resident_read(launchslot,source,launchdata+launchbytes,n);launchbytes+=n;
  if(launchbytes==sizeof(launchdata)){launchscan=0;memset(launchnotes,0,sizeof(launchnotes));}
  return;
 }
 /* Resolve beat-one notes before launch, including sparse/unsorted tracks. */
 end=0;for(c=0;c<6;c++){end+=launchdata[16+c*2]|((uint16_t)launchdata[17+c*2]<<8);if(launchscan<end)break;}
 if(c<6){resident_read(launchslot,RESIDENT_EVENTS+launchscan*4,e,4);launchscan++;if(!e[0]&&e[1]&&(!launchnotes[c][1]||e[1]<launchnotes[c][1]))memcpy(launchnotes[c],e,4);return;}
 launchequal=tones_match_buffer(launchdata+97);launchgeneration=resident_tone_generation;launchready=1;
}
uint8_t sparse_prepare_busy(void) BANKED {return mx.pending<5&&mx.pending!=mx.slot&&(launchslot!=mx.pending||!launchready);}
void sparse_prepare_invalidate(void) BANKED {launchslot=255;launchbytes=0;launchready=0;launchequal=0;}
void sparse_name(uint8_t slot,char *name) BANKED {resident_read(slot,16,(uint8_t *)name,16);name[16]=0;}
void sparse_library_name(uint8_t slot,char *name) BANKED {sparse_name(slot,name);} void sparse_get_song_name(uint8_t song,char *name) BANKED {(void)song;memcpy(name,"STRIPPED",9);}
uint8_t sparse_save_song(uint8_t song) BANKED {(void)song;return sparse_snapshot(mx.slot);}uint8_t sparse_load_song(uint8_t song) BANKED {(void)song;return 1;}uint8_t sparse_delete_song(uint8_t song) BANKED {(void)song;return 0;}uint16_t sparse_song_size(void) BANKED {return 5;}
uint8_t sparse_clear_slot(uint8_t slot) BANKED {uint8_t b[14]={0};if(slot>=5)return 0;resident_write(slot,32,b,14);if(slot==mx.slot){memset(seqeventcounts,0,14);memset(seqeventoffsets,0,14);}return 1;}
uint8_t sparse_load_pattern(uint8_t slot) BANKED {return sparse_restore(slot);}uint8_t sparse_save_pattern(uint8_t slot) BANKED {return sparse_snapshot(slot);}uint8_t sparse_save_pad_pattern(uint8_t pad,uint8_t index,const char *name) BANKED {(void)index;resident_write(pad,16,(uint8_t *)name,16);return pad==mx.slot?sparse_snapshot(pad):1;}
uint8_t sparse_copy_pad(uint8_t slot) BANKED {uint8_t b[16];uint16_t at;if(slot>=5)return 0;if(slot==mx.slot)sparse_snapshot(slot);for(at=0;at<2048;at+=16){resident_read(slot,at,b,16);io(3,0xAA00U+at,b,16,1);}pool_root[9]=1;pool_commit();return 1;}
uint8_t sparse_paste_pad(uint8_t slot) BANKED {uint8_t b[16];uint16_t at;if(slot>=5||!pool_root[9])return 0;for(at=0;at<2048;at+=16){io(3,0xAA00U+at,b,16,0);resident_write(slot,at,b,16);}if(slot==mx.slot)sparse_restore(slot);return 1;}
uint16_t pool_reference(uint8_t offset) BANKED {return offset==POOL_PATTERN_CLIP&&pool_root[9]?0:65535U;}uint8_t sparse_clear_working_song(void) BANKED {uint8_t i;for(i=0;i<5;i++)sparse_clear_slot(i);return 1;}
uint8_t sparse_prepared_prefix(uint8_t s,uint8_t *d) BANKED {(void)s;(void)d;return 0;}uint8_t sparse_prepared_apply(uint8_t s) BANKED {(void)s;return 0;}uint8_t sparse_prepared_tones(uint8_t s) BANKED {(void)s;return 0;}void sparse_prepared_chords(uint8_t s) BANKED {(void)s;}
uint8_t sparse_prepared_stream(uint8_t s,PoolStream *p) BANKED {(void)s;(void)p;return 0;}uint8_t sparse_prepared_map(uint16_t s,uint8_t *d) BANKED {(void)s;(void)d;return 0;}uint8_t sparse_first_note(uint8_t c,uint8_t *e) BANKED {(void)c;(void)e;return 0;}uint8_t sparse_first_kick(void) BANKED {return 0;}uint8_t sparse_first_drum(uint16_t *c,uint8_t *e) BANKED {(void)c;(void)e;return 2;}
uint8_t sparse_event(uint16_t i,uint8_t *e) BANKED {resident_read(mx.slot,RESIDENT_EVENTS+i*4,e,4);return 1;}uint8_t sparse_scan(uint8_t c,uint8_t s,uint16_t *i,uint8_t *e) BANKED {return seq_event_next_step(c,s,i,e);}
uint8_t sparse_journal_busy(void) BANKED {return 0;}uint8_t sparse_journal_retaining(void) BANKED {return 0;}uint8_t sparse_journal_flush(void) BANKED {return 1;}void sparse_journal_service(void) BANKED {}void sparse_journal_edit_barrier(void) BANKED {}uint8_t sparse_journal_recover(void) BANKED {return 1;}
uint16_t pool_word(const uint8_t *p) BANKED {return p[0]|((uint16_t)p[1]<<8);}void pool_setword(uint8_t *p,uint16_t n) BANKED {p[0]=n;p[1]=n>>8;}uint8_t pool_commit(void) BANKED {io(3,0xBF80,pool_root,128,1);return 1;}uint16_t pool_free(void) BANKED {return 0;}uint8_t pool_reclaim(void) BANKED {return 1;}
uint16_t pool_object_size(uint16_t o) BANKED {return o<5?POOL_TONE_BYTES:0;}uint8_t pool_object_read(uint16_t o,uint16_t at,uint8_t *d,uint16_t n) BANKED {if(o>=5||at+n>POOL_TONE_BYTES)return 0;resident_read(o,128+at,d,n);return 1;}

void resident_user_read(uint16_t offset,uint8_t *d,uint16_t n) BANKED {io(3,0xA000U+offset,d,n,0);}
void resident_user_write(uint16_t offset,const uint8_t *d,uint16_t n) BANKED {io(3,0xA000U+offset,(uint8_t *)d,n,1);}

volatile uint8_t seqnativepending;uint8_t seqnativeearly,seqnativeconfiguration,seqnativeautoarm,seqnativelaunchfired,seqnativefallback;uint16_t seqnativehits,seqnativemisses;
__at (0xFF98) volatile uint8_t seqirqready;__at (0xFF99) volatile uint8_t seqirqfired;__at (0xFFAA) uint8_t seqirqsuppress;__at (0xFFAE) uint8_t seqirqdirty;__at (0xFF9C) uint8_t seqirqstep[2];__at (0xFF9E) uint8_t seqirqnote[2];
void seq_native_hardware(void) NONBANKED {}
uint8_t seq_native_launch_copy(uint8_t slot) BANKED {(void)slot;return 0;}
void seq_native_prepare(void) BANKED {}
void seq_native_cached_compat(uint8_t value) BANKED {(void)value;}
uint8_t seq_native_fx_idle(void) BANKED {return 0;}
uint8_t seq_native_supported(void) BANKED {return 0;}
void seq_native_reset(void) BANKED {}
void seq_native_launch(void) BANKED {}
void seq_irq_launch(void) BANKED;
extern volatile uint8_t editirq_running;
void seq_native_launch_clear(void) BANKED {if(editirq_running)seq_irq_launch();}
void seq_native_launch_request_clear(void) BANKED {}
void seq_native_touch(void) NONBANKED {resident_tone_generation++;}
void seq_native_prime(void) BANKED {}
uint8_t seq_native_fire(uint8_t expired) BANKED {(void)expired;return 0;}

void seq_native_cancel_voice(uint8_t c) BANKED {(void)c;}
void seq_native_launch_clear_voices(void) BANKED {}
void seq_native_launch_irq(void) BANKED {}
void seq_native_schedule_tick(uint8_t elapsed) BANKED {(void)elapsed;}
uint8_t seq_native_restore_pulse1(void) BANKED {return 0;}
uint8_t seq_native_committed(uint8_t c) BANKED {(void)c;return 0;}
void seq_native_launch_begin(uint8_t slot,uint8_t count,uint8_t overflow) BANKED {(void)slot;(void)count;(void)overflow;}
uint8_t seq_native_launch_service(void) BANKED {return 0;}
void seq_native_launch_installed(uint8_t slot) BANKED {(void)slot;}
uint8_t seq_native_launch_early(uint8_t slot) BANKED {(void)slot;return 0;}
uint8_t seq_native_live_ready(void) BANKED {return 0;}
void seq_native_launch_future_store(uint8_t step) BANKED {(void)step;}
void seq_native_live_service(void) BANKED {}
uint8_t seq_native_live_commit(void) BANKED {return 0;}
void seq_native_launch_future_begin(uint8_t slot,uint8_t step) BANKED {(void)slot;(void)step;}
void seq_native_launch_ring_ready(void) BANKED {}
uint8_t seq_native_launch_locked(void) BANKED {return 0;}
void seq_native_launch_request_begin(void) BANKED {}
void seq_native_launch_arm(void) BANKED {}
uint8_t seq_native_launch_boundary(void) BANKED {return 0;}
void seq_native_launch_clock(void) BANKED {}





uint8_t sparse_load_pad_pattern(uint8_t index,uint8_t pad) BANKED {uint8_t b[16];uint16_t at;if(index>=5||pad>=5)return 0;if(index==pad)return 1;for(at=0;at<2048;at+=16){resident_read(index,at,b,16);resident_write(pad,at,b,16);}if(pad==mx.slot)sparse_restore(pad);return 1;}

/* User kits occupy free bank 2 A800..ACFF, outside the five resident pools. */
void resident_kit_read(uint8_t slot,uint8_t *data) BANKED {if(slot<DRUM_KIT_SLOTS)io(2,0xA800U+(uint16_t)slot*DRUM_KIT_BYTES,data,DRUM_KIT_BYTES,0);}
void resident_kit_write(uint8_t slot,const uint8_t *data) BANKED {uint8_t zero=0;if(slot>=DRUM_KIT_SLOTS)return;io(2,0xA800U+(uint16_t)slot*DRUM_KIT_BYTES,&zero,1,1);io(2,0xA801U+(uint16_t)slot*DRUM_KIT_BYTES,(uint8_t *)data+1,DRUM_KIT_BYTES-1,1);io(2,0xA800U+(uint16_t)slot*DRUM_KIT_BYTES,(uint8_t *)data,1,1);}

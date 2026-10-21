#pragma bank 41
#pragma opt_code_speed
#include "api.h"
#include "link_control.h"
#include "tones.h"
#include "mixer_shared.h"
extern uint8_t link_ui_hold;
#include "sparse_store.h"
extern uint16_t seqcachedbpm,seqstepunits,seqgateunits[7],seqdeadline;
extern uint8_t seqgate[7],seqbeats,seqdenom;
#define PREP_UNITS ((uint16_t *)0xACD0)
#define PREP_STEP (*(uint16_t *)0xACDE)
#define PREP_ONSETS (*(uint8_t *)0xACCF)
void mixer_prepare_barrier(void) BANKED;
uint8_t toneready;
typedef struct {uint8_t phase;} PrepareJob;
__at (0xACB4) PrepareJob prep;
__at (0xACCC) uint8_t pattern_dirty;
__at (0xACCD) uint16_t pattern_generation;
void storage_sorted_dirty(void) BANKED;
void seq_native_launch_clear(void) BANKED;
void mixer_pattern_changed(void) BANKED {pattern_dirty=1;pattern_generation++;seqirqdirty=1;}
void mixer_pattern_clean(void) BANKED {pattern_dirty=0;}
static uint16_t getword(const uint8_t *p){return p[0]|((uint16_t)p[1]<<8);}static void offsets(void){uint8_t c;uint16_t n=0;for(c=0;c<7;c++){seqeventoffsets[c]=n;n+=seqeventcounts[c];}}
void defaults(void) BANKED {uint8_t c;mixer_pattern_changed();seqgrouptrack=255;seq_storage_clear();for(c=0;c<7;c++){seqlength[c]=16;seqdefaultvel[c]=127;seqdefaultdur[c]=c==6?0:c==5?4:1;seqgate[c]=100;mx.level[c]=127;mx.pan[c]=3;}drummutemask=drumsolomask=0;seqmuted=seqsolo=seqmode=0;seqbpm=seqglobalbpm?seqglobalbpm:120;seqbeats=seqdenom=4;memset(mx.name,0,17);}
void applymeta(const uint8_t *meta) BANKED {seqgrouptrack=255;memcpy(seqeventcounts,meta,14);offsets();memcpy(seqlength,meta+14,14);memcpy(seqdefaultdur,meta+28,14);memcpy(seqdefaultvel,meta+42,7);memset(seqgate,100,7);memcpy(mx.level,meta+56,7);memcpy(mx.pan,meta+63,7);seqmuted=meta[70];seqsolo=meta[71];seqbeats=meta[72];seqdenom=meta[73];seqmode=experimental_mode?meta[74]:0;seqbpm=seqglobalbpm?seqglobalbpm:getword(meta+75);drummutemask=getword(meta+77);drumsolomask=getword(meta+79);seqdeadline=1;seqeventfull=0;}
void tailcopy(uint8_t *dst,const uint8_t *src,uint16_t size) BANKED {uint8_t n;while(size){n=size>16?16:size;memcpy(dst,src,n);dst+=n;src+=n;size-=n;mixfill();}}

uint8_t tag(uint8_t s) BANKED {return sparse_enabled==1&&s<8&&sparse_slots[s]!=POOL_NONE?VALID:0;}
uint8_t valid(uint8_t s) BANKED {return tag(s)!=0;}
void getname(uint8_t s,char *name) BANKED {sparse_name(s,name);}
void snapshot(uint8_t s) BANKED {if(!sparse_snapshot(s))mx.error=2;}
void autosnapshot(uint8_t s) BANKED {if(pattern_dirty&&!(mx.protectedslots&(1<<s)))snapshot(s);}
uint8_t restore(uint8_t s,uint8_t cached) BANKED {(void)cached;return sparse_restore(s);}
void prefetch(uint8_t s) BANKED {(void)s;}
void mixer_journal_recover(void) BANKED {}
uint8_t mixer_clear_saved(uint8_t s) BANKED {return sparse_clear_slot(s);}
void sparse_prepare_invalidate(void) BANKED;
void mixer_prepare_cancel(void) BANKED {if(seqeventcache==3)sparse_finish_install();sparse_prepare_invalidate();prep.phase=0;mx.pending=255;mx.cachevalid=0;}
void mixer_prepare_barrier(void) BANKED {mixer_prepare_cancel();}
uint8_t mixer_prepare_busy(void) BANKED {return sparse_prepare_busy();}
uint8_t mixer_prepare_status(uint8_t s) BANKED {if(mx.pending==s)return mixer_prepare_busy()?2:3;if(mx.slot==s||mx.cachevalid&&mx.cacheslot==s)return 1;return 0;}
void mixer_prepare_focus(uint8_t s) BANKED {(void)s;}
void mixer_launch_request(uint8_t s,uint8_t edit) BANKED {if(link_pair_request(s,edit))return;if(syncmode&&syncslave&&!mx.quant)mx.quant=4;sparse_request(s,edit);}
void mixer_prepare_service(void) BANKED {sparse_prepare_service();}
void readpart(uint8_t s,uint16_t o,uint8_t *d,uint16_t n) BANKED {(void)s;(void)o;memset(d,0,n);}
void writepart(uint8_t s,uint16_t o,const uint8_t *d,uint16_t n) BANKED {(void)s;(void)o;(void)d;(void)n;}

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
__at (0xACCC) uint8_t pattern_dirty;
__at (0xACCD) uint16_t pattern_generation;
void mixer_pattern_changed(void) BANKED {if(!syncmode)seqirqdirty=1;pattern_dirty=1;pattern_generation++;if(mx.magic==0xD3){mx.presaved=0;
 /* Editing the playing generation cancels its queued launch. This keeps
    subsequent edits on the visible pattern and never revives an old stage. */
 if(sparse_enabled==1&&sparse_journal_slot==mx.slot&&sparse_journal_busy()){mx.pending=255;mx.padcache=0;dirty=1;}}}
void mixer_pattern_clean(void) BANKED {pattern_dirty=0;}
static void ram(uint8_t b){ENABLE_RAM;SWITCH_RAM(b);}
static uint8_t bank(uint8_t s){return s<3?1:s<6?2:3;}
static uint8_t *record(uint8_t s){if(s>=6)s-=6;else if(s>=3)s-=3;return (uint8_t *)(s? s==1?0xAA00U:0xB400U:0xA000U);}
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
/* The fixed block does its bank switch, copy and additive checksum in one
   register pass. Callers keep the short banked-RAM window interrupt-atomic. */
static uint16_t ram_read16(uint8_t *source,uint8_t *buffer,uint8_t slotbank) __naked { __asm
 ldhl sp,#2
 ld a,(hl)
 ld h,b
 ld l,c
 ld (0x4000),a
 ld a,#0x0a
 ld (0x0000),a
 ld bc,#0
 .rept 16
 ld a,(de)
 inc de
 ld (hl+),a
 add a,c
 ld c,a
 ld a,b
 adc a,#0
 ld b,a
 .endm
 xor a,a
 ld (0x4000),a
 pop hl
 inc sp
 jp (hl)
 __endasm; }
static uint16_t ram_write16(uint8_t *buffer,uint8_t *target,uint8_t slotbank) __naked { __asm
 ldhl sp,#2
 ld a,(hl)
 ld h,b
 ld l,c
 ld (0x4000),a
 ld a,#0x0a
 ld (0x0000),a
 ld bc,#0
 .rept 16
 ld a,(de)
 inc de
 ld (hl+),a
 add a,c
 ld c,a
 ld a,b
 adc a,#0
 ld b,a
 .endm
 xor a,a
 ld (0x4000),a
 pop hl
 inc sp
 jp (hl)
 __endasm; }
void readpart(uint8_t s,uint16_t off,uint8_t *dst,uint16_t n) BANKED {uint8_t chunk,buf[16],b=bank(s);uint16_t partial;uint8_t *addr=record(s)+off;
 while(n){chunk=n>16?16:n;
  if(chunk==16){__critical {partial=ram_read16(addr,buf,b);}}
  else {__critical {ram(b);memcpy(buf,addr,chunk);ram(0);}partial=mx.checking?checksum_chunk(buf,chunk):0;}
  memcpy(dst,buf,chunk);if(mx.checking)mx.checksum+=partial;addr+=chunk;dst+=chunk;n-=chunk;mixfill();
 }
}
void writepart(uint8_t s,uint16_t off,const uint8_t *src,uint16_t n) BANKED {uint8_t chunk,buf[16],b=bank(s);uint16_t partial;uint8_t *addr=record(s)+off;
 while(n){chunk=n>16?16:n;memcpy(buf,src,chunk);
  if(chunk==16){__critical {partial=ram_write16(buf,addr,b);}}
  else {partial=mx.checking?checksum_chunk(buf,chunk):0;__critical {ram(b);memcpy(addr,buf,chunk);ram(0);}}
  if(mx.checking)mx.checksum+=partial;addr+=chunk;src+=chunk;n-=chunk;mixfill();
 }
}
uint8_t tag(uint8_t s) BANKED {uint8_t v;if(sparse_enabled)return sparse_enabled==1&&s<8&&sparse_slots[s]!=POOL_NONE?VALID:0;readpart(s,0,&v,1);return v;}
uint8_t valid(uint8_t s) BANKED {uint8_t v=tag(s);return v==VALID||v==NOTE_VALID||v==SPARSE_VALID||v==OLD_VALID;}
void getname(uint8_t s,char *name) BANKED {uint8_t i,ended=0;if(sparse_enabled){sparse_name(s,name);return;}if(valid(s))readpart(s,1,(uint8_t *)name,17);else name[0]=0;name[16]=0;for(i=0;i<17;i++){if(!name[i])ended=1;if(ended)name[i]=0;}}
void defaults(void) BANKED {uint8_t c;mixer_pattern_changed();seqgrouptrack=255;seq_storage_clear();for(c=0;c<7;c++){seqlength[c]=16;seqdefaultvel[c]=100;seqdefaultdur[c]=c==6?0:c==5?4:1;seqgate[c]=(c<2||c>=5)?100:80;mx.level[c]=127;mx.pan[c]=3;}drummutemask=drumsolomask=0;seqmuted=seqsolo=seqmode=0;seqbpm=seqglobalbpm?seqglobalbpm:120;seqbeats=seqdenom=4;memset(mx.name,0,17);}
void snapshot(uint8_t s) BANKED {uint16_t generation;uint8_t meta[METASIZE],i=0;if(sparse_enabled){if(!sparse_snapshot(s))mx.error=2;return;}mixer_prepare_barrier();generation=pattern_generation;if(!mx.name[0]){mx.name[0]='0';mx.name[1]='0';mx.name[2]='1'+mx.slot;mx.name[3]=0;}mx.checking=0;writepart(s,0,&i,1);mx.checksum=0;mx.checking=1;writepart(s,1,(uint8_t *)mx.name,17);writepart(s,DATA,(uint8_t *)seqevents_lo,1024);writepart(s,DATA+1024,(uint8_t *)seqevents_hi,1024);
 memcpy(meta,seqeventcounts,14);memcpy(meta+14,seqlength,14);memcpy(meta+28,seqdefaultdur,14);memcpy(meta+42,seqdefaultvel,7);memcpy(meta+49,seqgate,7);memcpy(meta+56,mx.level,7);memcpy(meta+63,mx.pan,7);meta[70]=seqmuted;meta[71]=seqsolo;meta[72]=seqbeats;meta[73]=seqdenom;meta[74]=seqmode;setword(meta+75,seqbpm);setword(meta+77,drummutemask);setword(meta+79,drumsolomask);writepart(s,META,meta,METASIZE);tones_pack();writepart(s,TONE_OFFSET,TONE_PACK,TONE_SIZE);mx.checking=0;writepart(s,18,(uint8_t *)&mx.checksum,2);i=VALID;writepart(s,0,&i,1);mx.protectedslots&=~(1<<s);mx.padcache=0;link_names_dirty|=1<<s;if(s==mx.slot&&generation==pattern_generation)mixer_pattern_clean();
}
void autosnapshot(uint8_t s) BANKED {if(pattern_dirty&&!(mx.protectedslots&(1<<s)))snapshot(s);}
uint8_t oldmetaok(const uint8_t *m) BANKED {uint8_t i;uint16_t bpm=getword(m+47);if(bpm<30||bpm>300||m[44]<1||m[44]>12||(m[45]!=2&&m[45]!=4&&m[45]!=8&&m[45]!=16)||m[46]>1)return 0;for(i=0;i<7;i++)if(!m[i]||m[i]>64||!m[7+i]||m[7+i]>127||m[14+i]>64||m[21+i]>100||m[28+i]>127||m[35+i]>3)return 0;return 1;}
uint8_t metaok(const uint8_t *m) BANKED {uint8_t c;uint16_t n,total=0,bpm=getword(m+75),i;const uint8_t *event=CACHE+DATA;PREP_ONSETS=0;if((getword(m+77)|getword(m+79))&0xE000)return 0;if(bpm<30||bpm>300||m[72]<1||m[72]>12||(m[73]!=2&&m[73]!=4&&m[73]!=8&&m[73]!=16)||m[74]>1)return 0;
 for(c=0;c<7;c++){n=getword(m+c*2);if(n>512||total+n>512||!getword(m+14+c*2)||getword(m+14+c*2)>256||(getword(m+28+c*2)>256||(c<6&&!getword(m+28+c*2)))||!m[42+c]||m[42+c]>127||m[49+c]>100||m[56+c]>127||m[63+c]>3)return 0;total+=n;for(i=0;i<n;i++,event+=4){if(!event[1]||event[1]>(c==6?13:128)||event[2]>127)return 0;if(c<6&&!event[0])PREP_ONSETS|=1<<c;if(!(i&7))mixfill();}}
 return 1;
}
uint8_t migrate(uint8_t s) BANKED {uint8_t old[49],*scratch=(uint8_t *)0xBC00,*meta=CACHE+META,c,n,best,event[4];uint16_t total=0,count,i,at,age,min;
 memcpy(old,CACHE+OLD_META,49);if(!oldmetaok(old))return 0;
 for(i=0;i<384;i++)if(CACHE[DATA+i])total++;
 for(i=0;i<128;i++){if(CACHE[OLD_DRUM+i])total++;if(CACHE[OLD_DRUM+640+i])total++;}
 if(total>512){mx.error=1;mx.protectedslots|=1<<s;mx.cachevalid=3;return 0;}total=0;memset(meta,0,METASIZE);
 for(c=0;c<6;c++){readpart(s,DATA+(uint16_t)c*64,scratch,64);readpart(s,DATA+384+(uint16_t)c*64,scratch+64,64);readpart(s,DATA+768+(uint16_t)c*64,scratch+128,64);count=0;
  for(i=0;i<64;i++)if(scratch[i]){event[0]=i;event[1]=scratch[i];event[2]=scratch[64+i]?scratch[64+i]:old[7+c];event[3]=scratch[128+i]?scratch[128+i]:old[14+c]?old[14+c]:1;memcpy(CACHE+DATA+total*4,event,4);total++;count++;}setword(meta+c*2,count);mixfill();}
 readpart(s,OLD_DRUM,scratch,1024);count=0;
 /* Stable age ordering preserves the legacy oldest-hit replacement rule. */
 while(1){best=255;min=65535;for(i=0;i<128;i++)if(scratch[i]){age=getword(scratch+384+i*2);if(best==255||age<min){best=i;min=age;}}if(best==255)break;n=scratch[best];if(n>10)return 0;event[0]=best/2;event[1]=n;event[2]=scratch[128+best]?scratch[128+best]:old[13];event[3]=scratch[256+best]?scratch[256+best]:1;memcpy(CACHE+DATA+total*4,event,4);scratch[best]=0;total++;count++;mixfill();}
 for(i=0;i<128;i++)if(scratch[640+i]){event[0]=i/2;event[1]=11+(i&1);event[2]=scratch[768+i]?scratch[768+i]:old[13];event[3]=scratch[896+i]?scratch[896+i]:1;memcpy(CACHE+DATA+total*4,event,4);total++;count++;mixfill();}setword(meta+12,count);
 for(c=0;c<7;c++){setword(meta+14+c*2,old[c]);setword(meta+28+c*2,old[14+c]?old[14+c]:c==6?0:1);meta[42+c]=old[7+c];meta[49+c]=old[21+c];meta[56+c]=old[28+c];meta[63+c]=old[35+c];}memcpy(meta+70,old+42,7);
 at=total*4;while(at<2048){count=2048-at>16?16:2048-at;memset(CACHE+DATA+at,0,count);at+=count;mixfill();}return metaok(meta);
}
void prefetch(uint8_t s) BANKED {uint8_t t=tag(s),i;uint16_t expected,bpm;toneready=0;mx.cachevalid=2;mx.cacheslot=s;mx.error=0;if(t!=VALID&&t!=NOTE_VALID&&t!=SPARSE_VALID&&t!=OLD_VALID)return;mx.checksum=0;mx.checking=1;readpart(s,1,CACHE+1,17);
 if(t==VALID||t==NOTE_VALID||t==SPARSE_VALID){readpart(s,DATA,CACHE+DATA,2048);readpart(s,META,CACHE+META,t!=SPARSE_VALID?METASIZE:77);if(t==SPARSE_VALID)memset(CACHE+META+77,0,4);if(t==VALID)readpart(s,TONE_OFFSET,CACHE+TONE_OFFSET,TONE_SIZE);}else {readpart(s,DATA,CACHE+DATA,1152);readpart(s,OLD_DRUM,CACHE+OLD_DRUM,1024);readpart(s,OLD_META,CACHE+OLD_META,49);}mx.checking=0;readpart(s,18,(uint8_t *)&expected,2);if(expected!=mx.checksum)return;
 if(t==OLD_VALID){if(!migrate(s))return;}else if(!metaok(CACHE+META))return;
 if(t==VALID){if(!tones_decode())return;toneready=1;}
 bpm=getword(CACHE+META+75);PREP_STEP=15360U/bpm;for(i=0;i<7;i++){PREP_UNITS[i]=(PREP_STEP*CACHE[META+49+i])/100;mixfill();}mx.cachevalid=1;
}
void applymeta(const uint8_t *meta) BANKED {seqgrouptrack=255;memcpy(seqeventcounts,meta,14);offsets();memcpy(seqlength,meta+14,14);memcpy(seqdefaultdur,meta+28,14);memcpy(seqdefaultvel,meta+42,7);memcpy(seqgate,meta+49,7);memcpy(mx.level,meta+56,7);memcpy(mx.pan,meta+63,7);seqmuted=meta[70];seqsolo=meta[71];seqbeats=meta[72];seqdenom=meta[73];seqmode=experimental_mode?meta[74]:0;seqbpm=seqglobalbpm?seqglobalbpm:getword(meta+75);drummutemask=getword(meta+77);drumsolomask=getword(meta+79);seqdeadline=1;seqeventfull=0;}
void tailcopy(uint8_t *dst,const uint8_t *src,uint16_t size) BANKED {uint8_t n;while(size){n=size>16?16:size;memcpy(dst,src,n);dst+=n;src+=n;size-=n;mixfill();}}
uint8_t restore(uint8_t s,uint8_t cached) BANKED {uint16_t generation;if(sparse_enabled)return sparse_restore(s);mixer_prepare_barrier();if(!cached||!mx.cachevalid||mx.cacheslot!=s)prefetch(s);if(mx.cachevalid==3){mx.error=1;return 0;}if(mx.cachevalid==2){mx.cachevalid=0;defaults();return 1;}generation=pattern_generation;applymeta(CACHE+META);if(toneready)tones_apply();memcpy(mx.name,CACHE+1,17);mx.name[16]=0;tailcopy((uint8_t *)seqevents_lo,CACHE+DATA,1024);tailcopy((uint8_t *)seqevents_hi,CACHE+DATA+1024,1024);mx.cachevalid=0;if(s==mx.slot){if(generation==pattern_generation)mixer_pattern_clean();}else mixer_pattern_changed();return 1;}

/* A journal fits in unused record holes and bank tails. It never touches
   any checksummed pattern bytes, the boot magic, or the maximum 2064-byte
   track/region clipboard at bank 3 B400..BC0F. */
#define JOURNAL_NAME 16U
#define JOURNAL_DATA 33U
#define JOURNAL_META 2081U
#define JOURNAL_TONE 2162U
#define JOURNAL_BYTES 2434U
typedef struct {uint8_t slot;uint16_t offset,size;} JournalSpan;
static const JournalSpan journalspans[]={
 {2,2560,512},{5,2560,512},{8,2560,512},
 {0,2449,51},{0,2504,56},
 {1,2449,111},{2,2449,111},{3,2449,111},{4,2449,111},
 {5,2449,111},{6,2449,111},{7,2449,111},
 {0,20,12},{1,20,12},{2,20,12},{3,20,12},
 {4,20,12},{5,20,12},{6,20,12},{7,20,12}
};
static void journal_part(uint16_t at,uint8_t *data,uint16_t size,uint8_t writing){uint8_t span=0;uint16_t n;
 while(at>=journalspans[span].size){at-=journalspans[span].size;span++;}
 while(size){n=journalspans[span].size-at;if(n>size)n=size;
  if(writing)writepart(journalspans[span].slot,journalspans[span].offset+at,data,n);
  else readpart(journalspans[span].slot,journalspans[span].offset+at,data,n);
  size-=n;data+=n;at=0;span++;
 }
}
static void journal_clear(void){uint8_t zero=0;mx.checking=0;journal_part(0,&zero,1,1);}
/* Every commit operation copies at most one 16-byte block. Once captured,
   no renderer scratch or mutable note data is needed to finish the save. */
static uint16_t journal_copy(uint8_t slot,uint16_t at){uint8_t buf[16],n;uint16_t dest;
 n=JOURNAL_BYTES-at>16?16:JOURNAL_BYTES-at;
 if(at<17){if(n>17-at)n=17-at;dest=1+at;}else dest=15+at;
 journal_part(JOURNAL_NAME+at,buf,n,0);writepart(slot,dest,buf,n);return at+n;
}
static uint8_t journal_header(uint8_t *header){uint8_t i,check=0;
 if(memcmp(header,"GBJ1",4)||header[4]>7||header[5]!=(uint8_t)(header[4]^255)||header[14]!=1)return 0;
 if(header[15]&&header[15]!=VALID&&header[15]!=NOTE_VALID)return 0;check=header[15];
 for(i=0;i<10;i++)check+=header[i];
 return header[10]==check&&header[11]==(uint8_t)(check^255)&&header[12]==0xA5&&header[13]==0x5A;
}
void mixer_journal_recover(void) BANKED {uint8_t header[16],buf[16],n,zero=0,validtag=VALID;uint16_t at,sum=0;mx.checking=0;
 journal_part(0,header,16,0);if(!journal_header(header))return;
 for(at=0;at<JOURNAL_BYTES;at+=n){n=JOURNAL_BYTES-at>16?16:JOURNAL_BYTES-at;journal_part(JOURNAL_NAME+at,buf,n,0);sum+=checksum_chunk(buf,n);}
 if(sum!=getword(header+6)){journal_clear();return;}
 writepart(header[4],0,&zero,1);
 for(at=0;at<JOURNAL_BYTES;)at=journal_copy(header[4],at);
 if(header[15])validtag=header[15];writepart(header[4],18,header+6,2);writepart(header[4],0,&validtag,1);journal_clear();
}
/* Legacy batteries retain their original format and recovery path. Clear an
   inactive slot through the durable journal; never load it into the playing
   voices or alter another track's patches/settings. */
uint8_t mixer_clear_saved(uint8_t slot) BANKED {uint8_t header[16],i,format;
 if(slot>=8)return 0;mixer_prepare_barrier();format=tag(slot);if(!format)return 1;prefetch(slot);if(mx.cachevalid!=1)return 0;
 memset(CACHE+META,0,14);mx.checking=0;journal_clear();mx.checksum=0;mx.checking=1;
 journal_part(JOURNAL_NAME,CACHE+1,17,1);journal_part(JOURNAL_DATA,CACHE+DATA,2048,1);journal_part(JOURNAL_META,CACHE+META,METASIZE,1);
 if(format!=VALID)memset(CACHE+TONE_OFFSET,0,TONE_SIZE);journal_part(JOURNAL_TONE,CACHE+TONE_OFFSET,TONE_SIZE,1);
 mx.checking=0;memset(header,0,16);memcpy(header,"GBJ1",4);header[4]=slot;header[5]=slot^255;setword(header+6,mx.checksum);header[12]=0xA5;header[13]=0x5A;header[14]=1;header[15]=format==VALID?VALID:NOTE_VALID;
 header[10]=header[15];for(i=0;i<10;i++)header[10]+=header[i];header[11]=header[10]^255;journal_part(1,header+1,15,1);journal_part(0,header,1,1);mixer_journal_recover();mx.cachevalid=0;mx.padcache=0;return 1;
}
/* Only foreground preparation owns this gap between Mixer state and pad flash.
   No live audio buffers, renderer scratch or fixed DSP lookup tables overlap. */
typedef struct {uint8_t phase,target,edit,source,format,pad;uint16_t position,expected,checksum;} PrepareJob;
__at (0xACB4) PrepareJob prep;
void tones_pack_begin(void) BANKED;
void tones_decode_begin(void) BANKED;
uint8_t tones_step(void) BANKED;
static void prepare_once(void);
void mixer_prepare_cancel(void) BANKED {
 if(sparse_enabled){if(seqeventcache==3)sparse_finish_install();prep.phase=0;mx.pending=255;mx.cachevalid=0;return;}
 /* Capturing only changes journal holes. A started commit finishes from
    those private bytes in the background even after renderer scratch changes. */
 if(mx.magic==0xD3&&prep.phase==18){prep.pad|=8;mx.checking=0;mx.pending=255;mx.cachevalid=0;mx.presaved=0;return;}
 if(mx.magic==0xD3&&prep.phase&&prep.phase<=6)journal_clear();
 prep.phase=0;prep.pad=0;mx.checking=0;mx.pending=255;mx.cachevalid=0;mx.presaved=0;
}
void mixer_prepare_barrier(void) BANKED {
 if(mx.magic!=0xD3||!prep.phase)return;
 mixer_prepare_cancel();while(prep.phase==18){prepare_once();mixfill();}
}
uint8_t mixer_prepare_busy(void) BANKED {
 if(sparse_enabled)return sparse_prepare_busy();
 if(!prep.phase&&pattern_dirty&&mx.pending!=255&&mx.pending!=mx.slot&&!(mx.protectedslots&(1<<mx.slot)))return 1;
 return mx.pending==mx.slot&&((prep.phase==18&&(prep.pad&8))||(prep.pad&1))?0:prep.phase;
}
/* Footer state: 0 idle, 1 prepared, 2 loading, 3 waiting for quantization. */
uint8_t mixer_prepare_status(uint8_t slot) BANKED {
 if(mx.pending==slot)return mixer_prepare_busy()?2:3;
 if(mx.slot==slot)return 1;
 if(mx.cachevalid&&mx.cacheslot==slot&&!prep.phase)return 1;
 return prep.phase&&prep.target==slot?2:0;
}
/* Quiet work never writes the outgoing slot. A highlighted pad can be
   validated and decoded before A, without changing the live arrangement. */
void mixer_prepare_focus(uint8_t slot) BANKED {
 if(sparse_enabled)return;
 if(navopen||mx.magic!=0xD3||mx.pending!=255||(prep.phase&&!(prep.pad&1)))return;
 if(slot==mx.slot)slot=seqplaying?(slot+1)&7:255;
 if(slot==255){if(prep.pad&1){prep.phase=0;prep.pad=0;mx.cachevalid=0;toneready=0;}return;}
 if((prep.pad&1)&&prep.target==slot&&(prep.phase||mx.cachevalid||prep.format==OLD_VALID))return;
 prep.phase=7;prep.pad=1;prep.target=slot;prep.edit=0;prep.source=mx.slot;prep.position=0;
 mx.cachevalid=0;mx.presaved=0;mx.openempty=0;mx.checking=0;toneready=0;
}
void mixer_launch_request(uint8_t slot,uint8_t edit) BANKED {
 if(link_pair_request(slot,edit))return;
 /* A slave cannot establish a new clock epoch with an immediate launch. */
 if(syncmode&&syncslave&&!mx.quant){mx.quant=4;dirty=1;}if(!syncmode){seqirqready=0;seqirqdirty=1;}
 if(sparse_enabled){sparse_request(slot,edit);return;}
 if(edit&&slot==mx.slot){mixer_prepare_cancel();page=8;seq_open();dirty=1;return;}
 if(slot==mx.pending)return;
 if(slot==mx.slot&&(prep.pad&1)){mx.pending=slot;mx.padcache=0;if(!seqplaying||!mx.quant){mx.pending=255;mixer_activate(slot,edit);}return;}
 if(prep.phase==18){
  if(slot==mx.slot){prep.pad|=8;mx.pending=slot;if(!mx.quant||!seqplaying){mx.pending=255;mixer_activate(slot,edit);}return;}
  prep.target=slot;prep.edit=edit;prep.pad&=~10;mx.pending=slot;mx.cachevalid=0;mx.padcache=0;dirty=1;return;
 }
 if(slot!=mx.slot&&(prep.pad&1)&&prep.target==slot){
  prep.pad=0;prep.edit=edit;mx.pending=slot;mx.padcache=0;dirty=1;
  if(prep.phase)return;
  if(mx.cachevalid){
   if(!pattern_dirty||(mx.protectedslots&(1<<mx.slot))){mx.presaved=1;mx.openempty=edit||mx.cachevalid==2;if(!mx.quant||!seqplaying){mx.pending=255;mixer_activate(slot,edit);}return;}
   prep.source=mx.slot;prep.phase=1;prep.pad=2;return;
  }
 }
 if(prep.phase&&prep.phase<=6&&slot!=mx.slot){prep.target=slot;prep.edit=edit;mx.pending=slot;mx.padcache=0;dirty=1;return;}
 mixer_prepare_cancel();mx.cachevalid=0;mx.presaved=0;mx.openempty=0;prep.pad=0;
 if(slot==mx.slot){mx.pending=slot;mx.padcache=0;if(!seqplaying||!mx.quant){mx.pending=255;mixer_activate(slot,edit);}return;}
 if(!seqplaying){mixer_activate(slot,edit);return;}
 prep.target=slot;prep.edit=edit;prep.source=mx.slot;prep.position=0;prep.phase=pattern_dirty?1:7;
 mx.pending=slot;mx.error=0;mx.padcache=0;toneready=0;dirty=1;
}
static void prepare_fail(void){prep.phase=0;mx.pending=255;mx.checking=0;mx.cachevalid=0;mx.presaved=0;mx.error=1;dirty=1;}
static uint8_t prepare_metadata(void){uint8_t c;uint16_t total=0,n,bpm=getword(CACHE+META+75);const uint8_t *m=CACHE+META;
 if((getword(m+77)|getword(m+79))&0xE000)return 0;
 if(bpm<30||bpm>300||m[72]<1||m[72]>12||(m[73]!=2&&m[73]!=4&&m[73]!=8&&m[73]!=16)||m[74]>1)return 0;
 for(c=0;c<7;c++){n=getword(m+c*2);if(n>512||total+n>512||!getword(m+14+c*2)||getword(m+14+c*2)>256||getword(m+28+c*2)>256||(c<6&&!getword(m+28+c*2))||!m[42+c]||m[42+c]>127||m[49+c]>100||m[56+c]>127||m[63+c]>3)return 0;total+=n;}
 prep.expected=total;return 1;
}
static void prepare_once(void){uint8_t v,c,result,header[16];uint16_t n,total;uint8_t *m=CACHE+META,*source_meta=CACHE+TONE_OFFSET;
 switch(prep.phase){
 case 1:
  if(!pattern_dirty||(mx.protectedslots&(1<<prep.source))){prep.phase=prep.pad&2?17:7;break;}
  prep.expected=pattern_generation;
  journal_clear();
  if(!mx.name[0]){mx.name[0]='0';mx.name[1]='0';mx.name[2]='1'+mx.slot;mx.name[3]=0;}
  mx.checksum=0;mx.checking=1;journal_part(JOURNAL_NAME,(uint8_t *)mx.name,17,1);
  memcpy(source_meta,seqeventcounts,14);memcpy(source_meta+14,seqlength,14);memcpy(source_meta+28,seqdefaultdur,14);memcpy(source_meta+42,seqdefaultvel,7);memcpy(source_meta+49,seqgate,7);memcpy(source_meta+56,mx.level,7);memcpy(source_meta+63,mx.pan,7);
  source_meta[70]=seqmuted;source_meta[71]=seqsolo;source_meta[72]=seqbeats;source_meta[73]=seqdenom;source_meta[74]=seqmode;setword(source_meta+75,seqbpm);setword(source_meta+77,drummutemask);setword(source_meta+79,drumsolomask);
  journal_part(JOURNAL_META,source_meta,METASIZE,1);prep.position=0;prep.phase=2;break;
 case 2:
  mx.checking=1;n=64;if(prep.position<1024)journal_part(JOURNAL_DATA+prep.position,(uint8_t *)seqevents_lo+prep.position,n,1);else journal_part(JOURNAL_DATA+prep.position,(uint8_t *)seqevents_hi+prep.position-1024,n,1);
  prep.position+=n;if(prep.position==2048)prep.phase=3;break;
 case 3:tones_pack_begin();prep.phase=4;break;
 case 4:result=tones_step();if(result){if(result==2){prepare_fail();break;}prep.position=0;prep.phase=5;}break;
 case 5:
  mx.checking=1;n=TONE_SIZE-prep.position;if(n>64)n=64;journal_part(JOURNAL_TONE+prep.position,TONE_PACK+prep.position,n,1);prep.position+=n;if(prep.position==TONE_SIZE)prep.phase=6;break;
 case 6:
  if(pattern_generation!=prep.expected){prep.phase=1;break;}
  prep.checksum=mx.checksum;mx.checking=0;memset(header,0,16);memcpy(header,"GBJ1",4);header[4]=prep.source;header[5]=prep.source^255;setword(header+6,prep.checksum);setword(header+8,prep.expected);
  for(c=0;c<10;c++)header[10]+=header[c];header[11]=header[10]^255;header[12]=0xA5;header[13]=0x5A;header[14]=1;
  journal_part(1,header+1,15,1);journal_part(0,header,1,1);prep.position=0;prep.format=0;prep.phase=18;break;
 case 18:
  mx.checking=0;if(!prep.format){v=0;writepart(prep.source,0,&v,1);prep.format=1;break;}
  if(prep.position<JOURNAL_BYTES){prep.position=journal_copy(prep.source,prep.position);break;}
  writepart(prep.source,18,(uint8_t *)&prep.checksum,2);v=VALID;writepart(prep.source,0,&v,1);journal_clear();mx.protectedslots&=~(1<<prep.source);
  if(mx.slot==prep.source&&pattern_generation==prep.expected)mixer_pattern_clean();
  if(prep.pad&8){prep.phase=0;break;}
  if(pattern_generation!=prep.expected){prep.phase=1;break;}
  prep.phase=prep.pad&2?17:7;break;
 case 7:
  prep.format=tag(prep.target);mx.cacheslot=prep.target;mx.cachevalid=2;prep.position=0;mx.checksum=0;
  if(prep.format!=VALID&&prep.format!=NOTE_VALID&&prep.format!=SPARSE_VALID&&prep.format!=OLD_VALID){mx.openempty=1;prep.phase=17;break;}
  if(prep.format==OLD_VALID){if(prep.pad&1){prep.phase=0;mx.cachevalid=0;dirty=1;break;}prefetch(prep.target);if(mx.cachevalid!=1){prepare_fail();break;}prep.phase=17;break;}
  mx.checking=1;readpart(prep.target,1,CACHE+1,17);prep.phase=8;break;
 case 8:
  mx.checking=1;readpart(prep.target,DATA+prep.position,CACHE+DATA+prep.position,64);prep.position+=64;if(prep.position==2048)prep.phase=9;break;
 case 9:
  mx.checking=1;readpart(prep.target,META,m,prep.format==SPARSE_VALID?77:METASIZE);if(prep.format==SPARSE_VALID)memset(m+77,0,4);prep.position=0;prep.phase=prep.format==VALID?10:11;break;
 case 10:
  mx.checking=1;n=TONE_SIZE-prep.position;if(n>64)n=64;readpart(prep.target,TONE_OFFSET+prep.position,CACHE+TONE_OFFSET+prep.position,n);prep.position+=n;if(prep.position==TONE_SIZE)prep.phase=11;break;
 case 11:
  mx.checking=0;readpart(prep.target,18,(uint8_t *)&prep.expected,2);if(prep.expected!=mx.checksum){prepare_fail();break;}if(!prepare_metadata()){prepare_fail();break;}PREP_ONSETS=0;prep.position=0;prep.phase=12;break;
 case 12:
  total=prep.position+16;if(total>prep.expected)total=prep.expected;
  for(;prep.position<total;prep.position++){uint16_t at=prep.position;uint8_t *e=CACHE+DATA+at*4;uint16_t offset=0;for(c=0;c<7;c++){offset+=getword(m+c*2);if(at<offset)break;}if(!e[1]||e[1]>(c==6?13:128)||e[2]>127){prepare_fail();return;}if(c<6&&!e[0])PREP_ONSETS|=1<<c;}
  if(prep.position==prep.expected)prep.phase=prep.format==VALID?13:15;break;
 case 13:tones_decode_begin();prep.phase=14;break;
 case 14:result=tones_step();if(result){if(result==2){prepare_fail();break;}toneready=1;prep.phase=15;}break;
 case 15:PREP_STEP=15360U/getword(m+75);prep.position=0;prep.phase=16;break;
 case 16:c=prep.position;PREP_UNITS[c]=(PREP_STEP*m[49+c])/100;if(++prep.position==7){mx.cachevalid=1;prep.phase=17;}break;
 case 17:
  if(prep.pad&1){prep.phase=0;mx.presaved=0;dirty=1;break;}
  if(pattern_dirty&&!(mx.protectedslots&(1<<mx.slot))&&!(prep.pad&2)){prep.source=mx.slot;prep.pad|=2;prep.phase=1;break;}
  mx.presaved=1;mx.openempty|=prep.edit;prep.phase=0;dirty=1;
  if(!mx.quant||!seqplaying){mx.pending=255;mixer_activate(prep.target,prep.edit);}break;
 default:prepare_fail();break;
 }
 mx.checking=0;
}
void mixer_prepare_service(void) BANKED {uint8_t i;if(!prep.phase){
 if(page!=18&&!link_ui_hold)return;
 if(mx.pending!=255){if(mx.pending==mx.slot||!pattern_dirty||(mx.protectedslots&(1<<mx.slot)))return;prep.target=mx.pending;prep.source=mx.slot;prep.pad=mx.cachevalid&&mx.cacheslot==mx.pending?2:0;prep.phase=1;}
 else mixer_prepare_focus(mx.focus>=30&&mx.focus<38?mx.focus-30:255);
 if(!prep.phase)return;
}if(page!=18&&!link_ui_hold&&prep.phase!=18){mixer_prepare_cancel();mx.pending=255;return;}for(i=0;i<1&&prep.phase;i++){prepare_once();mixfill();}}

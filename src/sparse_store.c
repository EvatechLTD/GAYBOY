#pragma bank 44
#pragma opt_code_speed
#include "api.h"
#include "link_control.h"
#include "tones.h"
#include "mixer_shared.h"
extern uint8_t mixer_hidden[8],mixer_device,mixer_layout_dirty;
#include "sparse_store.h"

uint8_t sparse_enabled,sparse_install_slot=255,sparse_song=255;
uint8_t sparse_patterns;
uint16_t sparse_slots[8],sparse_tones[8];
char sparse_song_name[17];
static uint16_t install_position;
static PoolStream install_stream;
extern uint8_t pattern_dirty,seqgate[7],seqbeats,seqdenom,seqcachedgate[7],seqrecordtrack;
extern uint16_t pattern_generation,seqcachedbpm,seqstepunits,seqgateunits[7],seqclock,seqdeadline,seqrecordlength;
void mixer_pattern_clean(void) BANKED;
void mixer_pattern_changed(void) BANKED;
void seq_pattern_release(void) BANKED;
void seq_pattern_start(void) BANKED;
void seq_pattern_handoff(void) BANKED;
void mixer_activate(uint8_t slot,uint8_t edit) BANKED;
uint8_t sparse_seed_install(void) BANKED;
/* A fixed-size prefix is prepared before publishing the object. It contains
   only slot settings and timing, never reserved capacity for absent notes. */
#define PREFIX ((uint8_t *)0xB900)
#define META_BUFFER ((uint8_t *)0xB820)
static uint16_t word(const uint8_t *p){return p[0]|((uint16_t)p[1]<<8);}
static void setword(uint8_t *p,uint16_t n){p[0]=n;p[1]=n>>8;}
static uint16_t reference(uint8_t slot){return word(pool_root+POOL_ACTIVE+slot*2);}
static uint8_t pattern_read(uint16_t object,uint16_t offset,uint8_t *data,uint16_t size){return object==SPARSE_JOURNAL_REF?sparse_journal_read(offset,data,size):pool_object_read(object,offset,data,size);}
static void refresh(void){uint8_t i,buf[2];for(i=0;i<8;i++){
 sparse_slots[i]=reference(i);sparse_tones[i]=POOL_NONE;
 if(sparse_slots[i]!=POOL_NONE&&pool_object_read(sparse_slots[i],POOL_PATCH_OFFSET,buf,2))sparse_tones[i]=word(buf);
 if(sparse_journal_busy()&&i==sparse_journal_slot){sparse_slots[i]=sparse_tones[i]=SPARSE_JOURNAL_REF;}
}sparse_patterns=word(pool_root+POOL_LIBRARY_ROOT)==POOL_NONE?0:(pool_object_size(word(pool_root+POOL_LIBRARY_ROOT))-2)/2;}
static uint16_t library_reference(uint8_t index){uint8_t data[2];uint16_t object=word(pool_root+POOL_LIBRARY_ROOT);
 if(index>=sparse_patterns||object==POOL_NONE||!pool_object_read(object,2+(uint16_t)index*2,data,2))return POOL_NONE;return word(data);
}
/* Append any new pattern identities in a single COW directory operation.
   Songs and the browser share these objects; deleting a song does not delete
   independently browsable patterns. Empty slots never create library rows. */
static uint8_t library_add(const uint16_t *extra,uint8_t count,uint8_t replace){uint16_t old=word(pool_root+POOL_LIBRARY_ROOT),object,ref;uint8_t include[8],i,j,n=0,data[2];
 memset(include,1,8);for(i=0;i<count;i++){if(extra[i]==POOL_NONE){include[i]=0;continue;}for(j=0;j<i;j++)if(extra[j]==extra[i])include[i]=0;}
 if(replace<sparse_patterns){memset(include,0,8);}
 else for(j=0;j<sparse_patterns;j++){ref=library_reference(j);for(i=0;i<count;i++)if(extra[i]==ref)include[i]=0;}
 for(i=0;i<count;i++)n+=include[i];if(!n&&replace>=sparse_patterns)return 1;
 object=pool_object_begin(POOL_LIBRARY,2+((uint16_t)sparse_patterns+n)*2);if(object==POOL_NONE)return 0;setword(data,sparse_patterns+n);pool_object_write(object,0,data,2);
 for(j=0;j<sparse_patterns;j++){ref=j==replace?extra[0]:library_reference(j);setword(data,ref);if(!pool_object_write(object,2+(uint16_t)j*2,data,2))return 0;}
 j=sparse_patterns;for(i=0;i<count;i++)if(include[i]){setword(data,extra[i]);if(!pool_object_write(object,2+(uint16_t)j++*2,data,2))return 0;}
 if(!pool_object_finish(object))return 0;pool_set_reference(POOL_LIBRARY_ROOT,object);(void)old;return 1;
}
void sparse_library_name(uint8_t index,char *name) BANKED {uint16_t object=library_reference(index);memset(name,0,17);if(object!=POOL_NONE)pool_object_read(object,0,(uint8_t *)name,16);}
/* Keep the clone buffer off the live snapshot/save call stack. */
static uint16_t named_pattern(uint16_t source,const char *name){uint16_t object,size,at;uint8_t buf[16],n;
 if(source==POOL_NONE||!pool_object_read(source,0,buf,16))return POOL_NONE;
 if(!memcmp(buf,name,16))return source;
 if(!pool_reclaim())return POOL_NONE;size=pool_object_size(source);object=pool_object_begin(POOL_PATTERN,size);if(object==POOL_NONE)return POOL_NONE;
 for(at=0;at<size;at+=n){n=size-at>16?16:size-at;if(!pool_object_read(source,at,buf,n))return POOL_NONE;if(!at)memcpy(buf,name,16);if(!pool_object_write(object,at,buf,n))return POOL_NONE;mixfill();}
 return pool_object_finish(object)?object:POOL_NONE;
}
/* Saving an unplayed pad reads its immutable snapshot, never the live engine. */
uint8_t sparse_save_pad_pattern(uint8_t pad,uint8_t index,const char *name) BANKED {uint16_t object,old;
 if(sparse_enabled!=1||pad>=8||index>sparse_patterns||!sparse_journal_flush())return 0;
 if(pad==mx.slot){memcpy(mx.name,name,16);mx.name[16]=0;mixer_pattern_changed();if(!sparse_snapshot(pad))return 0;object=sparse_slots[pad];}
 else object=named_pattern(sparse_slots[pad],name);
 if(object==POOL_NONE)return 0;
 old=word(pool_root+POOL_LIBRARY_ROOT);if(!library_add(&object,1,index)){pool_set_reference(POOL_LIBRARY_ROOT,old);return 0;}
 pool_set_reference(POOL_ACTIVE+pad*2,object);if(!pool_commit())return 0;refresh();link_names_dirty|=1<<pad;return 1;
}
uint8_t sparse_save_pattern(uint8_t index) BANKED {return sparse_save_pad_pattern(mx.slot,index,mx.name);}
static void compact_meta(uint8_t *to,const uint8_t *from){uint8_t c;memcpy(to,from,14);
 for(c=0;c<7;c++){to[14+c]=word(from+14+c*2);to[21+c]=word(from+28+c*2);}memcpy(to+28,from+42,39);
}
static void expand_meta(uint8_t *to,const uint8_t *from){uint8_t c;memcpy(to,from,14);
 for(c=0;c<7;c++){setword(to+14+c*2,from[14+c]?from[14+c]:256);setword(to+28+c*2,from[21+c]?from[21+c]:c==6?0:256);}memcpy(to+42,from+28,39);
}
static void capture_meta(uint8_t *meta){memcpy(meta,seqeventcounts,14);memcpy(meta+14,seqlength,14);memcpy(meta+28,seqdefaultdur,14);memcpy(meta+42,seqdefaultvel,7);memcpy(meta+49,seqgate,7);memcpy(meta+56,mx.level,7);memcpy(meta+63,mx.pan,7);meta[70]=seqmuted;meta[71]=seqsolo;meta[72]=seqbeats;meta[73]=seqdenom;meta[74]=seqmode;setword(meta+75,seqbpm);setword(meta+77,drummutemask);setword(meta+79,drumsolomask);}
static uint8_t *live(uint16_t byte){return byte<1024?(uint8_t *)seqevents_lo+byte:(uint8_t *)seqevents_hi+byte-1024;}
static uint16_t total(void){return seqeventoffsets[6]+seqeventcounts[6];}
static void prepare_prefix(uint8_t slot,uint16_t patch){uint8_t c,e[4];uint16_t size,cursor=0;
 capture_meta(META_BUFFER);memset(PREFIX,0,POOL_PATTERN_BYTES);memcpy(PREFIX,mx.name,16);if(!PREFIX[0]){PREFIX[0]='0';PREFIX[1]='0';PREFIX[2]='1'+slot;}
 compact_meta(PREFIX+16,META_BUFFER);size=15360U/seqbpm;setword(PREFIX+97,size);
 for(c=0;c<7;c++)setword(PREFIX+83+c*2,(size*seqgate[c])/100);
 PREFIX[99]=0;for(c=0;c<6;c++)if(seq_note_event(c,0,e))PREFIX[99]|=1<<c;
 /* Two spare preparation bits avoid a complete drum-tail scan at step 0.
    Multiple onsets and old objects with neither hint retain the full scan. */
 if(!seq_event_next_step(6,0,&cursor,e))PREFIX[99]|=64;
 else if(!seq_event_next_step(6,0,&cursor,e))PREFIX[99]|=128;
 setword(PREFIX+100,patch);
}
static uint8_t retain_outgoing(void){uint8_t busy=seqservicing;
 sparse_finish_install();if(!sparse_journal_flush())return 0;seqservicing=1;
 seqrecordtrack=255;seqrecordlength=0;
 tones_capture();prepare_prefix(mx.slot,sparse_tones[mx.slot]);
 if(!sparse_journal_begin(mx.slot,PREFIX,total()*4)){seqservicing=busy;return 0;}
 sparse_slots[mx.slot]=sparse_tones[mx.slot]=SPARSE_JOURNAL_REF;mixer_pattern_clean();seqservicing=busy;return 1;
}
static uint8_t patch_equal(uint16_t object){uint8_t buf[16],n;uint16_t at;PoolStream stream;
 if(!pool_stream_seek(&stream,object,0))return 0;
 for(at=0;at<TONE_RAW_BYTES;at+=n){n=TONE_RAW_BYTES-at>16?16:TONE_RAW_BYTES-at;if(!pool_stream_read(&stream,buf,n)||memcmp(buf,TONE_RAW+at,n))return 0;}
 return pool_stream_read(&stream,buf,8)&&!memcmp(buf,TONE_KICK_RAW,8);
}
static uint16_t find_patch(void){uint16_t page;uint8_t header[6];
 for(page=4;page<POOL_PAGES;page++)if(pool_used[page>>3]&(1<<(page&7))){
  pool_page_read(page,2,header,6);
  if(header[0]==POOL_PATCH&&header[1]==1&&word(header+2)==POOL_TONE_BYTES&&patch_equal(page)&&pool_object_check(page,POOL_PATCH))return page;
 }
 return POOL_NONE;
}
static uint16_t capture_patch(void){uint16_t object;tones_capture();object=find_patch();if(object!=POOL_NONE)return object;
 object=pool_object_begin(POOL_PATCH,POOL_TONE_BYTES);if(object==POOL_NONE)return object;
 if(!pool_object_write(object,0,TONE_RAW,TONE_RAW_BYTES)||!pool_object_write(object,TONE_RAW_BYTES,TONE_KICK_RAW,8)||!pool_object_finish(object))return POOL_NONE;return object;
}
static uint8_t metadata_ok(uint16_t object){uint8_t c,buf[4],prefix[83];uint16_t n,sum=0,bpm;PoolStream stream;
 if(!pool_object_read(object,0,prefix,83))return 0;expand_meta(META_BUFFER,prefix+16);bpm=word(META_BUFFER+75);
 if(bpm<30||bpm>300||META_BUFFER[72]<1||META_BUFFER[72]>12||(META_BUFFER[73]!=2&&META_BUFFER[73]!=4&&META_BUFFER[73]!=8&&META_BUFFER[73]!=16)||META_BUFFER[74]>1||((word(META_BUFFER+77)|word(META_BUFFER+79))&0xE000))return 0;
 if(!pool_stream_seek(&stream,object,POOL_EVENTS_OFFSET))return 0;
 for(c=0;c<7;c++){n=word(META_BUFFER+c*2);if(n>512||sum+n>512||!META_BUFFER[42+c]||META_BUFFER[42+c]>127||META_BUFFER[49+c]>100||META_BUFFER[56+c]>127||META_BUFFER[63+c]>3)return 0;
  while(n--){if(!pool_stream_read(&stream,buf,4)||!buf[1]||buf[1]>(c==6?13:128)||buf[2]>127)return 0;sum++;}
 }return pool_object_size(object)==POOL_PATTERN_BYTES+sum*4;
}
uint8_t sparse_boot(void) BANKED {uint8_t old[4],i;
 sparse_enabled=0;sparse_install_slot=sparse_song=255;memset(sparse_song_name,0,17);
 ui_loading(1,12);
 if(pool_mount()){ui_loading(3,12);sparse_enabled=1;if(!sparse_journal_recover()){sparse_enabled=2;pool_error=2;return 1;}refresh();for(i=0;i<8;i++){ui_loading(4+i,12);if(sparse_slots[i]!=POOL_NONE&&!metadata_ok(sparse_slots[i])){sparse_enabled=2;pool_error=2;}}ui_loading(12,12);return 1;}
 /* Existing fixed-record batteries retain their original reader/journal.
    Unknown or damaged media must never be formatted as an empty library. */
 readpart(0,2500,old,4);if(!memcmp(old,"GBM2",4)){pool_error=0;return 0;}
 if(!pool_is_blank()){sparse_enabled=2;pool_error=2;return 1;}ui_loading(2,12);pool_format();ui_loading(3,12);sparse_seed_install();ui_loading(9,12);if(!pool_mount()){sparse_enabled=2;return 1;}sparse_enabled=1;refresh();return 1;
}
uint8_t sparse_snapshot(uint8_t slot) BANKED {uint16_t patch,object,size,at,generation;uint8_t n;
 if(sparse_enabled!=1||slot>=8)return 0;mx.pending=255;sparse_finish_install();if(!sparse_journal_flush())return 0;generation=pattern_generation;
 /* Reclaim only outside a launch. Allocation never compacts or moves live
    event references, and full storage leaves every committed root intact. */
 if(!pool_reclaim())return 0;patch=capture_patch();if(patch==POOL_NONE)return 0;
 prepare_prefix(slot,patch);
 size=total()*4;object=pool_object_begin(POOL_PATTERN,POOL_PATTERN_BYTES+size);if(object==POOL_NONE){pool_reclaim();pool_error=1;return 0;}
 if(!pool_object_write(object,0,PREFIX,POOL_PATTERN_BYTES))return 0;
 for(at=0;at<size;at+=n){n=size-at>16?16:size-at;if(!pool_object_write(object,POOL_EVENTS_OFFSET+at,live(at),n))return 0;}
 if(!pool_object_finish(object))return 0;
 pool_set_reference(POOL_ACTIVE+slot*2,object);pool_root[7]=mx.slot;pool_root[8]=mx.quant;if(!pool_commit())return 0;refresh();mx.padcache=0;mx.error=0;
 link_names_dirty|=1<<slot;if(slot==mx.slot&&generation==pattern_generation)mixer_pattern_clean();return 1;
}
void sparse_name(uint8_t slot,char *name) BANKED {memset(name,0,17);if(slot<8&&sparse_slots[slot]!=POOL_NONE)pattern_read(sparse_slots[slot],0,(uint8_t *)name,16);name[16]=0;}
uint8_t sparse_restore(uint8_t slot) BANKED {uint8_t busy=seqservicing;
 if(sparse_enabled!=1||slot>=8)return 0;sparse_install_slot=255;seqservicing=1;
 if(sparse_slots[slot]==POOL_NONE){uint8_t c;
   /* Empty note descriptors need no live-array erase. A retained outgoing
      generation can keep those bytes until its journal capture finishes. */
   mixer_pattern_changed();seqgrouptrack=255;memset(seqeventcounts,0,14);memset(seqeventoffsets,0,14);
   for(c=0;c<7;c++){seqlength[c]=16;seqdefaultvel[c]=100;seqdefaultdur[c]=c==6?0:c==5?4:1;seqgate[c]=(c<2||c>=5)?100:80;seqcachedgate[c]=seqgate[c];seqgateunits[c]=(c<2||c>=5)?128:102;mx.level[c]=127;mx.pan[c]=3;}
   drummutemask=drumsolomask=0;seqmuted=seqsolo=seqmode=0;seqbpm=seqglobalbpm?seqglobalbpm:120;seqcachedbpm=0;seqstepunits=128;seqbeats=seqdenom=4;memset(mx.name,0,17);seqeventfull=0;seqeventcache=2;install_position=0;sparse_install_slot=slot;*(uint8_t *)0xACCF=64;
  mx.slot=slot;seqservicing=busy;return 1;}
 if(!sparse_prepared_apply(slot)){
 if(!pattern_read(sparse_slots[slot],0,PREFIX,POOL_PATTERN_BYTES)){seqservicing=busy;return 0;}
 expand_meta(META_BUFFER,PREFIX+16);applymeta(META_BUFFER);memcpy(mx.name,PREFIX,16);mx.name[16]=0;
 seqstepunits=word(PREFIX+97);memcpy(seqgateunits,PREFIX+83,14);memcpy(seqcachedgate,seqgate,7);seqcachedbpm=seqglobalbpm?0:seqbpm;*(uint8_t *)0xACCF=PREFIX[99];
 }
 if(sparse_tones[slot]==SPARSE_JOURNAL_REF){sparse_journal_tones(0,TONE_RAW,POOL_TONE_BYTES);memcpy(TONE_KICK_RAW,TONE_RAW+TONE_RAW_BYTES,8);tones_apply();}
 else if(!sparse_prepared_tones(slot)&&!tones_apply_object(sparse_tones[slot])){seqservicing=busy;return 0;}
 mx.slot=slot;seqeventcache=2;install_position=0;if(sparse_slots[slot]!=SPARSE_JOURNAL_REF&&!sparse_prepared_stream(slot,&install_stream))pool_stream_seek(&install_stream,sparse_slots[slot],POOL_EVENTS_OFFSET);sparse_install_slot=slot;seqservicing=busy;mixer_pattern_clean();return 1;
}
uint8_t sparse_activate(uint8_t slot) BANKED {uint8_t run=seqplaying,busy=seqservicing,mode=seqmode;uint16_t bpm=seqbpm,residual=seqclock;
 seqservicing=1;if(!sparse_restore(slot)){seqservicing=busy;return 0;}mx.pending=255;mx.presaved=0;if(!syncmode||!syncslave)mx.boundary=0;mx.padcache=0;seqdrawvalid=0;memset(seqcursor,0,7);
 if(run&&(mode==seqmode||(syncmode&&syncslave))){seq_pattern_release();if(bpm!=seqbpm)seqclock=((uint32_t)residual*seqbpm)/bpm;seq_pattern_handoff();}
 else {if(run){seqplaying=1;seq_transport();seq_transport();}else {memset(seqposition,0,7);seqclock=seqticks=seqfraction=0;seqdeadline=1;}}
 seqservicing=busy;if(mx.openempty)mx.openempty=2;dirty=1;return 1;
}
void sparse_prepare_now(uint8_t slot) BANKED;
void sparse_request(uint8_t slot,uint8_t edit) BANKED {
 if(slot>=8||sparse_enabled!=1)return;
 if(edit&&slot==mx.slot){mx.pending=255;mx.openempty=0;sparse_finish_install();page=8;seq_open();dirty=1;return;}
 if(slot==mx.pending)return;
 /* A superseded request must not launch from a pool I/O yield while the
    outgoing live notes and patch are being captured. */
 mx.pending=255;
 if(slot!=mx.slot&&pattern_dirty&&!retain_outgoing()){mx.error=1;dirty=1;return;}
 mx.openempty=edit||sparse_slots[slot]==POOL_NONE;mx.pending=slot;mx.padcache=0;dirty=1;
 if(!seqplaying||!mx.quant){mx.pending=255;if(seqplaying)sparse_prepare_now(slot);mixer_activate(slot,edit);}
}
uint8_t sparse_event(uint16_t index,uint8_t *event) BANKED {return pattern_read(sparse_slots[mx.slot],POOL_EVENTS_OFFSET+index*4,event,4);}
static uint8_t journal_scan(uint8_t track,uint8_t step,uint16_t *cursor,uint8_t *event){uint16_t index=*cursor,count=seqeventcounts[track];uint8_t data[16],n,i;
 while(index<count){n=count-index>4?4:count-index;if(!sparse_journal_read(POOL_EVENTS_OFFSET+(seqeventoffsets[track]+index)*4,data,n*4))return 0;
  for(i=0;i<n;i++,index++)if(data[i*4]==step&&data[i*4+1]){memcpy(event,data+i*4,4);*cursor=index+1;return 1;}}
 *cursor=count;return 0;
}
uint8_t sparse_scan(uint8_t track,uint8_t step,uint16_t *cursor,uint8_t *event) BANKED {
 uint16_t index=*cursor,count=seqeventcounts[track],installed;
 /* Installed prefixes already belong to this slot. Use them immediately,
    so high-tempo playback does not keep rescanning the cartridge chain
    while the remaining tracks install in the background. */
 if(sparse_install_slot==mx.slot&&seqeventoffsets[track]<install_position/4){
  installed=install_position/4-seqeventoffsets[track];if(installed>count)installed=count;
  while(index<installed){memcpy(event,live((seqeventoffsets[track]+index)*4),4);index++;if(event[0]==step&&event[1]){*cursor=index;return 1;}}
  *cursor=index;if(index>=count)return 0;
 }
 if(sparse_slots[mx.slot]==SPARSE_JOURNAL_REF)return journal_scan(track,step,cursor,event);
 return pool_object_scan(sparse_slots[mx.slot],POOL_EVENTS_OFFSET+seqeventoffsets[track]*4,count,step,cursor,event);
}
void sparse_service(void) BANKED {uint16_t size;uint8_t n,buf[16],busy,i;
 if(sparse_enabled!=1)return;
 if(!seqplaying||seqticks<seqdeadline)sparse_prepare_service();
 /* Editor setup is foreground UI work. The timed callback only requests it;
    wait until its actual-note installation is complete before opening. */
 if(!seqservicing&&mx.openempty==2&&sparse_install_slot==255){mx.openempty=0;page=8;seq_open();}
 for(i=0;i<4&&sparse_journal_busy();i++){sparse_journal_service();mixfill();}if(sparse_journal_retaining()||sparse_install_slot==255)return;
 if(sparse_install_slot!=mx.slot){sparse_install_slot=255;return;}size=total()*4;
 busy=seqservicing;seqservicing=1;
 if(install_position<size){n=size-install_position>16?16:size-install_position;
  if(sparse_slots[mx.slot]==SPARSE_JOURNAL_REF)sparse_journal_read(POOL_EVENTS_OFFSET+install_position,buf,n);
  else if(!pool_stream_read(&install_stream,buf,n)){seqservicing=busy;mx.error=3;return;}memcpy(live(install_position),buf,n);install_position+=n;
 }seqservicing=busy;
 if(install_position==size){busy=seqservicing;seqservicing=1;seqeventcache=0;sparse_install_slot=255;seqservicing=busy;}
}
void sparse_finish_install(void) BANKED {while(sparse_journal_retaining()||sparse_install_slot!=255){sparse_service();mixfill();}}
void sparse_journal_published(uint8_t slot,uint16_t pattern,uint16_t tone) BANKED {
 sparse_slots[slot]=pattern;sparse_tones[slot]=tone;
 if(sparse_install_slot==slot)pool_stream_seek(&install_stream,pattern,POOL_EVENTS_OFFSET+install_position);
 mx.padcache=0;
}
void sparse_get_song_name(uint8_t song,char *name) BANKED {uint16_t object;memset(name,0,17);if(song>=POOL_SONGS)return;object=word(pool_root+POOL_SONG_REFS+song*2);if(object!=POOL_NONE)pool_object_read(object,0,(uint8_t *)name,16);}
uint8_t sparse_save_song(uint8_t song) BANKED {uint8_t data[POOL_SONG_BYTES],i;uint16_t object,old_library;
 if(sparse_enabled!=1||song>=POOL_SONGS)return 0;if(!sparse_journal_flush())return 0;if((pattern_dirty||sparse_slots[mx.slot]==POOL_NONE)&&!sparse_snapshot(mx.slot))return 0;
 memset(data,0,sizeof(data));memcpy(data,sparse_song_name,16);if(!data[0]){data[0]='S';data[1]='0'+(song+1)/10;data[2]='0'+(song+1)%10;}
 data[35]=1;memcpy(data+36,mixer_hidden,8);data[44]=linkpair;data[45]=mixer_device;
 data[16]=0;data[17]=mx.quant;data[18]=mx.slot;for(i=0;i<8;i++)setword(data+19+i*2,sparse_slots[i]);
 old_library=word(pool_root+POOL_LIBRARY_ROOT);if(!library_add(sparse_slots,8,255)){pool_set_reference(POOL_LIBRARY_ROOT,old_library);return 0;}
 object=pool_object_begin(POOL_SONG,sizeof(data));if(object==POOL_NONE){pool_set_reference(POOL_LIBRARY_ROOT,old_library);return 0;}
 if(!pool_object_write(object,0,data,sizeof(data))||!pool_object_finish(object)){pool_set_reference(POOL_LIBRARY_ROOT,old_library);return 0;}pool_set_reference(POOL_SONG_REFS+song*2,object);if(!pool_commit())return 0;refresh();sparse_song=song;memcpy(sparse_song_name,data,17);return 1;
}
uint8_t sparse_load_song(uint8_t song) BANKED {uint16_t object,size;uint8_t data[POOL_SONG_BYTES],i,run=seqplaying;
 if(sparse_enabled!=1||song>=POOL_SONGS)return 0;object=word(pool_root+POOL_SONG_REFS+song*2);if(object==POOL_NONE)return 0;size=pool_object_size(object);if(size!=POOL_SONG_BYTES&&size!=POOL_SONG_LEGACY_BYTES)return 0;memset(data,0,sizeof(data));if(!pool_object_read(object,0,data,size)||data[17]>4||data[18]>7||(size==POOL_SONG_BYTES&&(data[35]!=1||data[44]>1||data[45]>1)))return 0;
 /* Publish feedback before validation or an outgoing save can block the
    normal renderer. A queued pad launch must not change the song mid-load. */
 mx.pending=255;ui_loading(0,12);
 if(!sparse_journal_flush()){ui_loading(12,12);return 0;}
 for(i=0;i<8;i++){if(word(data+19+i*2)!=POOL_NONE&&!metadata_ok(word(data+19+i*2))){ui_loading(12,12);return 0;}ui_loading(i+1,12);}
 if(pattern_dirty&&!sparse_snapshot(mx.slot)){ui_loading(12,12);return 0;}ui_loading(9,12);
 if(run)seq_transport();for(i=0;i<8;i++)pool_set_reference(POOL_ACTIVE+i*2,word(data+19+i*2));pool_root[7]=data[18];pool_root[8]=data[17];memcpy(pool_root+110,data+36,8);pool_root[118]='M';pool_root[119]=1;pool_root[120]=data[44];pool_root[121]=data[45];if(!pool_commit()){ui_loading(12,12);return 0;}
 memcpy(mixer_hidden,data+36,8);linkpair=data[44];mixer_device=data[45];mixer_layout_dirty=0;
 ui_loading(10,12);refresh();mx.quant=data[17];sparse_restore(data[18]);ui_loading(11,12);sparse_finish_install();sparse_song=song;memcpy(sparse_song_name,data,17);link_names_dirty=255;ui_loading(12,12);if(run)seq_transport();mx.padcache=0;seqdrawvalid=0;dirty=1;return 1;
}
uint8_t sparse_delete_song(uint8_t song) BANKED {if(sparse_enabled!=1||song>=POOL_SONGS||!sparse_journal_flush())return 0;pool_set_reference(POOL_SONG_REFS+song*2,POOL_NONE);if(!pool_commit())return 0;if(sparse_song==song){sparse_song=255;memset(sparse_song_name,0,17);}return 1;}
uint16_t sparse_song_size(void) BANKED {uint16_t needed=62U,ref;uint8_t i,j,added=0,snapshot=pattern_dirty||sparse_slots[mx.slot]==POOL_NONE,include;
 if(snapshot){needed+=((POOL_PATTERN_BYTES+total()*4+6+61)/62)*62;tones_capture();if(find_patch()==POOL_NONE)needed+=8*62;added=1;}
 for(i=0;i<8;i++){
  if((snapshot&&i==mx.slot)||sparse_slots[i]==POOL_NONE)continue;include=1;
  for(j=0;j<i;j++)if(!(snapshot&&j==mx.slot)&&sparse_slots[j]==sparse_slots[i])include=0;
  for(j=0;j<sparse_patterns&&include;j++){ref=library_reference(j);if(ref==sparse_slots[i])include=0;}
  added+=include;
 }
 /* Directory replacement is COW too: budget its entire new page chain,
    including existing rows, rather than only the appended references. */
 if(added)needed+=((2U+((uint16_t)sparse_patterns+added)*2U+6U+61U)/62U)*62U;
 return needed;
}
uint8_t sparse_clear_slot(uint8_t slot) BANKED {uint16_t source,object;
 if(slot>=8||sparse_enabled!=1)return 0;mx.pending=255;if(!sparse_journal_flush())return 0;if(slot==mx.slot){seq_clear_notes(255);return 1;}
 source=sparse_slots[slot];if(source==POOL_NONE)return 1;if(!pool_reclaim()||!pool_object_read(source,0,PREFIX,POOL_PATTERN_BYTES))return 0;
 memset(PREFIX+16,0,14);PREFIX[99]=64;object=pool_object_begin(POOL_PATTERN,POOL_PATTERN_BYTES);if(object==POOL_NONE)return 0;
 if(!pool_object_write(object,0,PREFIX,POOL_PATTERN_BYTES)||!pool_object_finish(object))return 0;pool_set_reference(POOL_ACTIVE+slot*2,object);if(!pool_commit())return 0;refresh();mx.padcache=0;return 1;
}
uint8_t sparse_load_pad_pattern(uint8_t index,uint8_t pad) BANKED {uint8_t active=mx.slot,run=seqplaying;uint16_t source,tone;
 if(sparse_enabled!=1||index>=sparse_patterns||pad>=8)return 0;mx.pending=255;mixer_prepare_cancel();if(!sparse_journal_flush())return 0;
 source=library_reference(index);if(!pool_object_read(source,POOL_PATCH_OFFSET,(uint8_t *)&tone,2))return 0;
 if(pad==active&&pattern_dirty&&!sparse_snapshot(active))return 0;
 if(pad==active&&run)seq_transport();pool_set_reference(POOL_ACTIVE+pad*2,source);if(!pool_commit())return 0;
 sparse_slots[pad]=source;sparse_tones[pad]=tone;
 if(pad==active){if(!sparse_restore(active))return 0;sparse_finish_install();if(run)seq_transport();}
 link_names_dirty|=1<<pad;mx.padcache=0;seqdrawvalid=0;dirty=1;return 1;
}
uint8_t sparse_load_pattern(uint8_t index) BANKED {return sparse_load_pad_pattern(index,mx.slot);}

/* Immutable clipboard root survives pad edits, saved-song loads and reclamation.
   Pasting shares a snapshot; the next edit creates an independent generation. */
uint8_t sparse_copy_pad(uint8_t slot) BANKED {uint16_t source;
 if(sparse_enabled!=1||slot>=8)return 0;mx.pending=255;mixer_prepare_cancel();sparse_finish_install();if(!sparse_journal_flush())return 0;
 if(slot==mx.slot&&(pattern_dirty||sparse_slots[slot]==POOL_NONE)&&!sparse_snapshot(slot))return 0;source=sparse_slots[slot];if(source==POOL_NONE)return 0;
 pool_set_reference(POOL_PATTERN_CLIP,source);return pool_commit();
}
uint8_t sparse_paste_pad(uint8_t slot) BANKED {uint16_t source;uint8_t run;
 if(sparse_enabled!=1||slot>=8)return 0;mx.pending=255;mixer_prepare_cancel();sparse_finish_install();if(!sparse_journal_flush())return 0;
 source=pool_reference(POOL_PATTERN_CLIP);if(source==POOL_NONE||!pool_object_check(source,POOL_PATTERN))return 0;
 pool_set_reference(POOL_ACTIVE+slot*2,source);if(!pool_commit())return 0;refresh();mx.cachevalid=0;mx.padcache=0;
 if(slot==mx.slot){run=seqplaying;if(run)seq_transport();if(!sparse_restore(slot))return 0;sparse_finish_install();if(run)seq_transport();}
 dirty=1;return 1;
}
uint8_t sparse_clear_working_song(void) BANKED {uint8_t i;
 if(sparse_enabled!=1)return 0;mx.pending=255;mixer_prepare_cancel();sparse_finish_install();if(!sparse_journal_flush())return 0;
 for(i=0;i<8;i++)pool_set_reference(POOL_ACTIVE+i*2,POOL_NONE);pool_root[7]=0;if(!pool_commit())return 0;
 if(seqplaying)seq_transport();refresh();mx.slot=0;mx.pending=255;mx.cachevalid=mx.presaved=mx.protectedslots=0;mx.focus=30;
 sparse_song=255;memset(sparse_song_name,0,17);seq_clear_notes(255);defaults();mixer_pattern_clean();mx.padcache=0;seqdrawvalid=0;dirty=1;return 1;
}

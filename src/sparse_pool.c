/* Portable persistent allocator. This exact implementation is tested with
   interrupted byte writes on the host as well as linked into the ROM. */
#ifndef POOL_HOST
#pragma bank 43
#include "api.h"
#endif
#include "sparse_pool.h"
#include <string.h>
#ifdef POOL_HOST
void pool_host_page_read(uint16_t page,uint8_t offset,uint8_t *data,uint8_t size);
void pool_host_page_write(uint16_t page,uint8_t offset,const uint8_t *data,uint8_t size);
#define pool_page_read_local pool_host_page_read
#define pool_page_write_local pool_host_page_write
#define pool_yield_local pool_yield
#endif


#ifndef POOL_HOST
/* Physical layout: 128 pages in bank 1, 96 in bank 2, 80 in bank 3.
   No operation can reach audio bank zero, the clipboard at 3:B400..BC0F,
   or recovery reserve 2:B800..BFFF + 3:BC10..BFFF. Sixteen-byte windows
   bound interrupt masking independently of object size. */
static uint8_t page_bank(uint16_t page){return page<128?1:page<224?2:3;}
static uint8_t *page_address(uint16_t page){if(page>=224)page-=224;else if(page>=128)page-=128;return (uint8_t *)(0xA000U+page*64);}
/* Near ABI: source DE, destination BC, bank/count on stack. A source span
   stays inside one 64-byte physical page, so INC E is sufficient. Callers
   mask interrupts only for this bounded copy and always restore bank zero. */
static void ram_read(uint8_t *source,uint8_t *destination,uint8_t bank,uint8_t count) __naked {__asm
 ldhl sp,#2
 ld a,(hl+)
 ld (0x4000),a
 ld a,#0x0a
 ld (0x0000),a
 ld a,(hl)
 ld h,b
 ld l,c
 ld b,a
 cp #16
 jr nz,pool_read_loop$
 .rept 16
 ld a,(de)
 inc e
 ld (hl+),a
 .endm
 jr pool_read_done$
pool_read_loop$:
 ld a,(de)
 inc e
 ld (hl+),a
 dec b
 jr nz,pool_read_loop$
pool_read_done$:
 xor a,a
 ld (0x4000),a
 pop hl
 inc sp
 inc sp
 jp (hl)
 __endasm;}
/* Both pointers are in the currently mapped bank-zero SRAM/WRAM. Keep the
   frequent full transfer window out of generic memcpy's per-byte loop;
   this copy needs no interrupt masking or cartridge-bank transition. */
static void copy16(const uint8_t *source,uint8_t *destination) __naked {__asm
 ld h,b
 ld l,c
 .rept 16
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 ret
 __endasm;}
/* Same two register pointers/two stack bytes as ram_read; the second
   pointer is unused and the last byte is the uniform erased value. */
static uint8_t ram_equal16(uint8_t *source,uint8_t *unused,uint8_t bank,uint8_t expected) __naked {__asm
 ldhl sp,#2
 ld a,(hl+)
 ld (0x4000),a
 ld a,#0x0a
 ld (0x0000),a
 ld b,(hl)
 .rept 16
 ld a,(de)
 inc de
 cp b
 jr nz,pool_equal_no$
 .endm
 ld b,#1
 jr pool_equal_done$
pool_equal_no$:
 ld b,#0
pool_equal_done$:
 xor a,a
 ld (0x4000),a
 ld a,b
 pop hl
 inc sp
 inc sp
 jp (hl)
 __endasm;}
/* Near ABI matches ram_read. Stack frame: 16-byte bounce buffer, source,
   destination, return address, bank, remaining count. Only the <=16 source
   reads run with interrupts masked; destination writes and audio service
   happen after restoring bank zero and enabling interrupts. */
static void page_to_sram(uint8_t *source,uint8_t *destination,uint8_t bank,uint8_t count) __naked {__asm
 push bc
 push de
 add sp,#-16
pool_sram_window$:
 ldhl sp,#23
 ld a,(hl)
 or a
 jp z,pool_sram_done$
 cp #16
 jr c,pool_sram_count$
 ld a,#16
pool_sram_count$:
 push af
 ld b,a
 ldhl sp,#18
 ld a,(hl+)
 ld e,a
 ld d,(hl)
 ldhl sp,#24
 ld a,(hl)
 di
 ld (0x4000),a
 ld a,#0x0a
 ld (0x0000),a
 ldhl sp,#2
 ld a,b
 cp #16
 jr nz,pool_sram_read_small$
 .rept 16
 ld a,(de)
 inc de
 ld (hl+),a
 .endm
 jr pool_sram_read_done$
pool_sram_read_small$:
 ld a,(de)
 inc de
 ld (hl+),a
 dec b
 jr nz,pool_sram_read_small$
pool_sram_read_done$:
 xor a,a
 ld (0x4000),a
 ei
 ldhl sp,#18
 ld (hl),e
 inc hl
 ld (hl),d
 pop af
 ld b,a
 ldhl sp,#23
 ld a,(hl)
 sub a,b
 ld (hl),a
 ldhl sp,#18
 ld a,(hl+)
 ld e,a
 ld d,(hl)
 ldhl sp,#0
 ld a,b
 cp #16
 jr nz,pool_sram_copy_small$
 .rept 16
 ld a,(hl+)
 ld (de),a
 inc de
 .endm
 jr pool_sram_copy_done$
pool_sram_copy_small$:
 ld a,(hl+)
 ld (de),a
 inc de
 dec b
 jr nz,pool_sram_copy_small$
pool_sram_copy_done$:
 ldhl sp,#18
 ld (hl),e
 inc hl
 ld (hl),d
 call _mixfill
 jp pool_sram_window$
pool_sram_done$:
 add sp,#20
 pop hl
 inc sp
 inc sp
 jp (hl)
 __endasm;}
static void pool_page_read_local(uint16_t page,uint8_t offset,uint8_t *data,uint8_t size) {uint8_t n,bank;uint8_t *source;
 if(page>=POOL_PAGES||offset+size>64){pool_error=2;return;}bank=page_bank(page);source=page_address(page)+offset;
 if((uint16_t)data<0xC000U){page_to_sram(source,data,bank,size);return;}
 while(size){n=size>16?16:size;__critical {ram_read(source,data,bank,n);}data+=n;source+=n;size-=n;mixfill();}
}
static void pool_page_write_local(uint16_t page,uint8_t offset,const uint8_t *data,uint8_t size) {uint8_t buf[16],n,bank;uint8_t *target;
 if(page>=POOL_PAGES||offset+size>64){pool_error=2;return;}bank=page_bank(page);target=page_address(page)+offset;
 while(size){n=size>16?16:size;if((uint16_t)data>=0xC000U){__critical {ENABLE_RAM;SWITCH_RAM(bank);memcpy(target,data,n);SWITCH_RAM(0);}}
  else {if(n==16)copy16(data,buf);else memcpy(buf,data,n);__critical {ENABLE_RAM;SWITCH_RAM(bank);memcpy(target,buf,n);SWITCH_RAM(0);}}data+=n;target+=n;size-=n;mixfill();}
}
static void pool_yield_local(void) {mixfill();}
#endif

uint8_t pool_root[POOL_ROOT_SIZE],pool_error;
uint8_t pool_used[(POOL_PAGES+7)/8];
static uint8_t pool_publishing;
/* Immutable validation cache: empty / pattern / patch / song. The current
   walk's used bits distinguish shared heads already visited this time.
   Mount and explicit collection discard cached validation completely. */
static uint8_t object_types[(POOL_PAGES+3)/4];
static uint8_t object_type(uint16_t page){return (object_types[page>>2]>>((page&3)*2))&3;}
static void set_type(uint16_t page,uint8_t type){object_types[page>>2]|=type<<((page&3)*2);}
static void clear_type(uint16_t page){if(page<POOL_PAGES)object_types[page>>2]&=~(3<<((page&3)*2));}
static uint16_t pool_word_local(const uint8_t *p) {return p[0]|((uint16_t)p[1]<<8);}
static void pool_setword_local(uint8_t *p,uint16_t n) {p[0]=n;p[1]=n>>8;}
static uint16_t pool_crc_local(uint16_t crc,const uint8_t *data,uint8_t size) {
 static const uint16_t nibble[16]={0,0x1021,0x2042,0x3063,0x4084,0x50A5,0x60C6,0x70E7,0x8108,0x9129,0xA14A,0xB16B,0xC18C,0xD1AD,0xE1CE,0xF1EF};
 uint8_t b;while(size--){b=*data++;crc=(crc<<4)^nibble[(crc>>12)^(b>>4)];crc=(crc<<4)^nibble[(crc>>12)^(b&15)];}return crc;
}
static uint8_t used(uint16_t page){return pool_used[page>>3]&(1<<(page&7));}
static void mark(uint16_t page){pool_used[page>>3]|=1<<(page&7);}
static uint16_t next(uint16_t page){
#ifdef POOL_HOST
 uint8_t data[2];pool_page_read_local(page,0,data,2);return pool_word_local(data);
#else
 uint16_t link;uint8_t bank=page_bank(page);uint8_t *source=page_address(page);
 /* Link reads always target a two-byte WRAM local. Avoid building another
    sixteen-byte bounce-buffer frame for every page crossed by a seek. */
 __critical {ram_read(source,(uint8_t *)&link,bank,2);}mixfill();return link;
#endif
}
static uint8_t pool_stream_seek_local(PoolStream *stream,uint16_t object,uint16_t offset) {
 uint16_t limit=POOL_PAGES;
 /* Bound before adding the object header: a hostile offset must not wrap
    back into the header or cause an unbounded linked-page walk. */
 if(offset>POOL_PAGES*POOL_PAYLOAD-6){pool_error=2;return 0;}
 offset+=6;stream->page=object;
 while(offset>=POOL_PAYLOAD){if(stream->page<4||stream->page>=POOL_PAGES||!limit--)return 0;stream->page=next(stream->page);offset-=POOL_PAYLOAD;}
 stream->within=offset;return stream->page>=4&&stream->page<POOL_PAGES;
}
static uint8_t pool_stream_read_local(PoolStream *stream,uint8_t *data,uint8_t size) {uint8_t n;
 while(size){if(stream->page<4||stream->page>=POOL_PAGES||stream->within>=POOL_PAYLOAD){pool_error=2;return 0;}
  n=POOL_PAYLOAD-stream->within;if(n>size)n=size;pool_page_read_local(stream->page,stream->within+2,data,n);
  size-=n;data+=n;stream->within+=n;if(stream->within==POOL_PAYLOAD){stream->page=next(stream->page);stream->within=0;}
 }return 1;
}
static uint8_t object_io(uint16_t object,uint16_t offset,uint8_t *data,uint16_t size,uint8_t writing){
 uint16_t page=object,limit=POOL_PAGES;uint8_t n,within;
 while(offset>=POOL_PAYLOAD){if(page<4||page>=POOL_PAGES||!limit--){pool_error=2;return 0;}page=next(page);offset-=POOL_PAYLOAD;}
 within=(uint8_t)offset;
 while(size){if(page<4||page>=POOL_PAGES||!limit--){pool_error=2;return 0;}n=POOL_PAYLOAD-within;if(n>size)n=size;
  if(writing)pool_page_write_local(page,2+within,data,n);else pool_page_read_local(page,2+within,data,n);
  data+=n;size-=n;within=0;if(size)page=next(page);pool_yield_local();
 }return 1;
}
static uint8_t object_range(uint16_t object,uint16_t offset,uint16_t size){uint8_t header[6];uint16_t length;
 if(!object_io(object,0,header,6,0))return 0;length=pool_word_local(header+2);
 if(offset>length||size>length-offset||length>POOL_PAGES*POOL_PAYLOAD-6){pool_error=2;return 0;}return 1;
}
static uint8_t pool_object_read_local(uint16_t object,uint16_t offset,uint8_t *data,uint16_t size) {return object_range(object,offset,size)&&object_io(object,offset+6,data,size,0);}
static uint8_t pool_object_write_local(uint16_t object,uint16_t offset,const uint8_t *data,uint16_t size) {clear_type(object);return object_range(object,offset,size)&&object_io(object,offset+6,(uint8_t *)data,size,1);}
static uint16_t pool_object_size_local(uint16_t object) {uint8_t header[6];if(!object_io(object,0,header,6,0))return POOL_NONE;return pool_word_local(header+2);}
static uint8_t check(uint16_t object,uint8_t type);
uint8_t pool_object_check(uint16_t object,uint8_t type) BANKED {return check(object,type);}
static uint16_t pool_free_local(void) {uint16_t page,n=0;for(page=4;page<POOL_PAGES;page++)if(!used(page))n++;return n*POOL_PAYLOAD;}
uint16_t pool_object_begin(uint8_t type,uint16_t size) BANKED {
 uint16_t count=(size+6+POOL_PAYLOAD-1)/POOL_PAYLOAD,page,head=POOL_NONE,last=POOL_NONE;
 uint8_t header[6],link[2];if(pool_publishing)return POOL_NONE;pool_error=0;
 if(size>POOL_PAGES*POOL_PAYLOAD-6||!count||pool_free_local()<count*POOL_PAYLOAD){pool_error=1;return POOL_NONE;}
 for(page=4;page<POOL_PAGES&&count;page++)if(!used(page)){
  clear_type(page);mark(page);pool_setword_local(link,POOL_NONE);pool_page_write_local(page,0,link,2);
  if(head==POOL_NONE)head=page;else {pool_setword_local(link,page);pool_page_write_local(last,0,link,2);}last=page;count--;pool_yield_local();
 }
 header[0]=type;header[1]=1;pool_setword_local(header+2,size);header[4]=header[5]=0;object_io(head,0,header,6,1);return head;
}
/* CRC is stored immediately after the four-byte typed length header. It is
   calculated over header[0..3] followed by the object's data, excluding the
   CRC field itself. The check uses the same order, not a zero-residue shortcut. */
uint8_t pool_object_finish(uint16_t object) BANKED {
 uint8_t header[6],buf[16],n;uint16_t size,at,crc;PoolStream stream;
 if(!object_io(object,0,header,6,0))return 0;size=pool_word_local(header+2);crc=pool_crc_local(0xFFFF,header,4);
 stream.page=object;stream.within=6;
 for(at=0;at<size;at+=n){n=size-at>16?16:size-at;if(!pool_stream_read_local(&stream,buf,n))return 0;crc=pool_crc_local(crc,buf,n);}
 pool_setword_local(header,crc);return object_io(object,4,header,2,1);
}
static uint8_t check(uint16_t object,uint8_t type){uint8_t header[6],buf[16],n;uint16_t at,size,crc;PoolStream stream;
 if(!object_io(object,0,header,6,0)||header[0]!=type||header[1]!=1)return 0;
 size=pool_word_local(header+2);if(size>POOL_PAGES*POOL_PAYLOAD-6)return 0;crc=pool_crc_local(0xFFFF,header,4);
 stream.page=object;stream.within=6;
 for(at=0;at<size;at+=n){n=size-at>16?16:size-at;if(!pool_stream_read_local(&stream,buf,n))return 0;crc=pool_crc_local(crc,buf,n);}
 return crc==pool_word_local(header+4);
}
static uint8_t chain(uint16_t head,uint16_t bytes){uint16_t page=head,n=(bytes+6+POOL_PAYLOAD-1)/POOL_PAYLOAD;
 while(n--){if(page<4||page>=POOL_PAGES||used(page))return 0;mark(page);page=next(page);pool_yield_local();}return page==POOL_NONE;
}
static uint8_t visit_patch(uint16_t object){if(object<4||object>=POOL_PAGES)return 0;
 if(used(object))return object_type(object)==2;
 if(object_type(object)&&object_type(object)!=2)return 0;
 if((!object_type(object)&&!check(object,POOL_PATCH))||pool_object_size_local(object)!=POOL_TONE_BYTES||!chain(object,POOL_TONE_BYTES))return 0;set_type(object,2);return 1;
}
static uint8_t visit_pattern(uint16_t object){uint16_t size;uint8_t data[2];if(object==POOL_NONE)return 1;if(object<4||object>=POOL_PAGES)return 0;
 if(used(object))return object_type(object)==1;
 if(object_type(object)&&object_type(object)!=1)return 0;
 size=pool_object_size_local(object);if(size<POOL_PATTERN_BYTES||size>POOL_PATTERN_BYTES+2048||((size-POOL_PATTERN_BYTES)&3)||(!object_type(object)&&!check(object,POOL_PATTERN))||!chain(object,size))return 0;
 set_type(object,1);if(!pool_object_read_local(object,POOL_PATCH_OFFSET,data,2))return 0;return visit_patch(pool_word_local(data));
}
static uint8_t visit_song(uint16_t object){uint8_t data[16],i;if(object==POOL_NONE)return 1;if(object<4||object>=POOL_PAGES)return 0;
 if(used(object))return object_type(object)==3;
 if(object_type(object)&&object_type(object)!=3)return 0;
 if(pool_object_size_local(object)!=POOL_SONG_BYTES||(!object_type(object)&&!check(object,POOL_SONG))||!chain(object,POOL_SONG_BYTES))return 0;
 set_type(object,3);if(!pool_object_read_local(object,19,data,16))return 0;for(i=0;i<8;i++)if(!visit_pattern(pool_word_local(data+i*2)))return 0;return 1;
}
/* Only explicit boot/song-loading screens opt in. Ordinary commits and
   performance launches never draw UI from the allocator. Twelve coarse
   steps cap the cost even for a large shared library; completion belongs
   to the loading caller after its metadata/preparation work is finished. */
static void graph_progress(uint16_t done,uint16_t total,uint8_t base){
#ifndef POOL_HOST
 uint8_t step;if(!*(volatile uint8_t *)0xACFE)return;
 step=base+(done*(11-base))/(total*2);
 if(step!=*(volatile uint8_t *)0xACFF)ui_loading(step,12);
#else
 (void)done;(void)total;(void)base;
#endif
}
static uint8_t visit_library(uint16_t object,uint8_t base){uint8_t data[2];uint16_t count,i;PoolStream stream;
 if(object==POOL_NONE)return 1;if(object<4||object>=POOL_PAGES||!check(object,POOL_LIBRARY)||!pool_object_read_local(object,0,data,2))return 0;count=pool_word_local(data);
 if(count>255||pool_object_size_local(object)!=2+count*2||!chain(object,2+count*2))return 0;
 if(!pool_stream_seek_local(&stream,object,2))return 0;
 for(i=0;i<count;i++){if(!pool_stream_read_local(&stream,data,2)||!visit_pattern(pool_word_local(data)))return 0;graph_progress(41+i,40+count,base);}return 1;
}
static uint16_t pool_reference_local(uint8_t offset) {return pool_word_local(pool_root+offset);}
static void pool_set_reference_local(uint8_t offset,uint16_t object) {pool_setword_local(pool_root+offset,object);}
static uint8_t collect(uint8_t fresh){uint8_t i,data[2],base=0;uint16_t total=40,library=pool_reference_local(POOL_LIBRARY_ROOT);
#ifndef POOL_HOST
 base=*(volatile uint8_t *)0xACFF;if(base>11)base=11;
#endif
 pool_error=0;memset(pool_used,0,sizeof(pool_used));if(fresh)memset(object_types,0,sizeof(object_types));pool_used[0]=15;
 if(library!=POOL_NONE&&pool_object_read_local(library,0,data,2)&&pool_word_local(data)<=255)total+=pool_word_local(data);
 for(i=0;i<8;i++){if(!visit_pattern(pool_reference_local(POOL_ACTIVE+i*2))){pool_error=2;return 0;}graph_progress(i+1,total,base);}
 for(i=0;i<POOL_SONGS;i++){if(!visit_song(pool_reference_local(POOL_SONG_REFS+i*2))){pool_error=2;return 0;}graph_progress(9+i,total,base);}
 if(!visit_pattern(pool_reference_local(POOL_PATTERN_CLIP))){pool_error=2;return 0;}
 if(!visit_library(pool_reference_local(POOL_LIBRARY_ROOT),base)){pool_error=2;return 0;}return 1;
}
uint8_t pool_collect(void) BANKED {return collect(1);}
uint8_t pool_reclaim(void) BANKED {return collect(0);}
uint8_t pool_native_map(uint16_t object,uint8_t *map) BANKED {uint8_t i,bank;uint16_t page,address;
 for(i=0;i<8;i++){
  if(object<4||object>=POOL_PAGES)return 0;
  bank=object<128?1:object<224?2:3;page=object<128?object:object<224?object-128:object-224;
  address=0xA000U+page*64+(i?2:8);map[0]=address;map[1]=address>>8;map[2]=bank;map+=3;object=next(object);
 }
 return object==POOL_NONE;
}
static void root_io(uint8_t copy,uint8_t writing){uint8_t i;for(i=0;i<2;i++){
 if(writing)pool_page_write_local(copy*2+i,0,pool_root+i*64,64);else pool_page_read_local(copy*2+i,0,pool_root+i*64,64);pool_yield_local();
}}
static uint8_t root_ok(void){return !memcmp(pool_root,"GBD1",4)&&pool_crc_local(0xFFFF,pool_root,126)==pool_word_local(pool_root+126);}
static void root_publish(uint8_t copy){uint8_t zero=0,commit='G';
 pool_page_write_local(copy*2,0,&zero,1);pool_page_write_local(copy*2,1,pool_root+1,63);pool_page_write_local(copy*2+1,0,pool_root+64,64);pool_page_write_local(copy*2,0,&commit,1);pool_yield_local();
}
/* Cached immutable objects skip CRC only: every commit still walks their
   chains and references, rejecting page/type aliases. Writes and allocation
   reuse invalidate the affected cache entries. Explicit collection and
   every mount force full CRC validation. Allocation stays blocked during
   publication so no old-generation page can be reused before both roots. */
uint8_t pool_commit(void) BANKED {uint8_t copy;uint16_t generation=pool_word_local(pool_root+4)+1;
 if(!collect(0)){pool_mount();pool_error=2;return 0;}
 pool_publishing=1;
 pool_setword_local(pool_root+4,generation);pool_setword_local(pool_root+126,pool_crc_local(0xFFFF,pool_root,126));
 for(copy=0;copy<2;copy++)root_publish(copy);
 pool_publishing=0;return 1;
}
void pool_format(void) BANKED {memset(pool_root,255,sizeof(pool_root));memcpy(pool_root,"GBD1",4);pool_setword_local(pool_root+4,0);pool_root[6]=pool_root[7]=0;pool_root[8]=4;pool_error=0;memset(pool_used,0,sizeof(pool_used));pool_used[0]=15;pool_commit();}
/* A damaged/zeroed root is not proof of an unused cartridge. Inspect every
   persistent pool byte before allowing first-use formatting. */
uint8_t pool_is_blank(void) BANKED {
#ifdef POOL_HOST
 uint16_t page;uint8_t at,i,buf[16],erased;
 pool_page_read_local(0,0,&erased,1);if(erased&&erased!=255)return 0;
 for(page=0;page<POOL_PAGES;page++){
  for(at=0;at<64;at+=16){
   pool_page_read_local(page,at,buf,16);for(i=0;i<16;i++)if(buf[i]!=erased)return 0;
  }
 }
 return 1;
#else
 uint16_t page;uint8_t at,erased,bank,equal;uint8_t *source;
 pool_page_read_local(0,0,&erased,1);if(erased&&erased!=255)return 0;
 for(page=0;page<POOL_PAGES;page++){
  bank=page_bank(page);source=page_address(page);
  for(at=0;at<64;at+=16){
   __critical {equal=ram_equal16(source,0,bank,erased);}
   if(!equal)return 0;source+=16;mixfill();
  }
 }
 return 1;
#endif
}
uint8_t pool_mount(void) BANKED {uint8_t valid0,valid1,selected;uint16_t gen0=0,gen1=0;
 pool_publishing=0;pool_error=0;root_io(0,0);valid0=root_ok();if(valid0)gen0=pool_word_local(pool_root+4);
 root_io(1,0);valid1=root_ok();if(valid1)gen1=pool_word_local(pool_root+4);
 if(!valid0&&!valid1){pool_error=2;return 0;}
 selected=valid1&&(!valid0||(int16_t)(gen1-gen0)>0);root_io(selected,0);
 if(pool_collect()){root_publish(selected^1);return 1;}
 /* A damaged new object cannot silently replace a recoverable previous root. */
 if(valid0&&valid1&&gen0!=gen1){root_io(selected^1,0);if(pool_collect()){root_publish(selected);return 1;}}pool_error=2;return 0;
}

/* Public banked entry points; internal walks stay in this ROM bank. */
void pool_page_read(uint16_t page,uint8_t offset,uint8_t *data,uint8_t size) BANKED {pool_page_read_local(page,offset,data,size);}
void pool_page_write(uint16_t page,uint8_t offset,const uint8_t *data,uint8_t size) BANKED {memset(object_types,0,sizeof(object_types));pool_page_write_local(page,offset,data,size);}
#ifndef POOL_HOST
void pool_yield(void) BANKED {pool_yield_local();}
#endif
uint16_t pool_word(const uint8_t *p) BANKED {return pool_word_local(p);}
void pool_setword(uint8_t *p,uint16_t n) BANKED {pool_setword_local(p,n);}
uint16_t pool_crc(uint16_t crc,const uint8_t *data,uint8_t size) BANKED {return pool_crc_local(crc,data,size);}
uint8_t pool_stream_seek(PoolStream *stream,uint16_t object,uint16_t offset) BANKED {return pool_stream_seek_local(stream,object,offset);}
uint8_t pool_stream_read(PoolStream *stream,uint8_t *data,uint8_t size) BANKED {return pool_stream_read_local(stream,data,size);}
/* Scan in the pool's own bank. Playback pays one bank trampoline for the
   complete scan rather than one per four-event read quantum. */
uint8_t pool_object_scan(uint16_t object,uint16_t offset,uint16_t count,uint8_t step,uint16_t *cursor,uint8_t *event) BANKED {
 PoolStream stream;uint16_t index=*cursor;uint8_t data[16],n,i;
 if(index>=count)return 0;if(!pool_stream_seek_local(&stream,object,offset+index*4))return 0;
 while(index<count){n=count-index>4?4:count-index;if(!pool_stream_read_local(&stream,data,n*4))return 0;
  for(i=0;i<n;i++,index++)if(data[i*4]==step&&data[i*4+1]){memcpy(event,data+i*4,4);*cursor=index+1;return 1;}}
 *cursor=count;return 0;
}
uint8_t pool_object_read(uint16_t object,uint16_t offset,uint8_t *data,uint16_t size) BANKED {return pool_object_read_local(object,offset,data,size);}
uint8_t pool_object_write(uint16_t object,uint16_t offset,const uint8_t *data,uint16_t size) BANKED {return pool_object_write_local(object,offset,data,size);}
uint16_t pool_object_size(uint16_t object) BANKED {return pool_object_size_local(object);}
uint16_t pool_free(void) BANKED {return pool_free_local();}
uint16_t pool_reference(uint8_t offset) BANKED {return pool_reference_local(offset);}
void pool_set_reference(uint8_t offset,uint16_t object) BANKED {pool_set_reference_local(offset,object);}

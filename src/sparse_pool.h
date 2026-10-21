#ifndef GAYBOY_SPARSE_POOL_H
#define GAYBOY_SPARSE_POOL_H
#include <stdint.h>
/* Bank zero is exclusively engine/UI memory. Banks 1..3 reserve the
   existing 2064-byte clipboard and a separate 3056-byte recovery area.
   The remaining 304 64-byte pages form one shared variable-size pool.
   Pages 0..3 hold redundant committed roots; object pages have 62 bytes
   of payload and a two-byte link. No note capacity is allocated for rests. */
#define POOL_PAGES 304U
#define POOL_PAGE_SIZE 64U
#define POOL_PAYLOAD 62U
#define POOL_ROOT_SIZE 128U
#define POOL_SONGS 32U
#define POOL_ACTIVE 16U
#define POOL_SONG_REFS 32U
#define POOL_LIBRARY_ROOT 96U
#define POOL_PATTERN_CLIP 98U
#define POOL_LIBRARY 'L'
#define POOL_PATTERN 'P'
#define POOL_PATCH 'T'
#define POOL_SONG 'S'
#define POOL_NONE 65535U
#define POOL_PATTERN_BYTES 102U
#define POOL_EVENTS_OFFSET 102U
#define POOL_PATCH_OFFSET 100U
#define POOL_TONE_BYTES 352U
#define POOL_TONE_LEGACY_BYTES 450U
#define POOL_SONG_LEGACY_BYTES 35U
#define POOL_SONG_BYTES 46U

/* Raw page I/O never addresses protected banks/regions. The platform
   implementation must restore RAM bank zero before enabling interrupts. */
#ifdef POOL_HOST
#define BANKED
#endif
void pool_page_read(uint16_t page,uint8_t offset,uint8_t *data,uint8_t size) BANKED;
void pool_page_write(uint16_t page,uint8_t offset,const uint8_t *data,uint8_t size) BANKED;
void pool_yield(void) BANKED;
extern uint8_t pool_root[POOL_ROOT_SIZE],pool_error;
extern uint8_t pool_used[(POOL_PAGES+7)/8];
uint16_t pool_word(const uint8_t *p) BANKED;
void pool_setword(uint8_t *p,uint16_t n) BANKED;
uint16_t pool_crc(uint16_t crc,const uint8_t *data,uint8_t size) BANKED;
typedef struct {uint16_t page;uint8_t within;} PoolStream;
uint8_t pool_stream_seek(PoolStream *stream,uint16_t object,uint16_t offset) BANKED;
uint8_t pool_stream_read(PoolStream *stream,uint8_t *data,uint8_t size) BANKED;
uint8_t pool_object_scan(uint16_t object,uint16_t offset,uint16_t count,uint8_t step,uint16_t *cursor,uint8_t *event) BANKED;
/* Eight source spans for an already validated native patch: address LE,
   RAM bank. First span skips the object header; later spans skip links. */
uint8_t pool_native_map(uint16_t object,uint8_t *map) BANKED;
uint8_t pool_mount(void) BANKED;
uint8_t pool_is_blank(void) BANKED;
void pool_format(void) BANKED;
uint8_t pool_collect(void) BANKED;
/* Runtime garbage reclamation reuses immutable-object CRC validation.
   Mount/explicit pool_collect always perform fresh corruption checks. */
uint8_t pool_reclaim(void) BANKED;
uint16_t pool_free(void) BANKED;
uint16_t pool_object_begin(uint8_t type,uint16_t size) BANKED;
uint8_t pool_object_write(uint16_t object,uint16_t offset,const uint8_t *data,uint16_t size) BANKED;
uint8_t pool_object_read(uint16_t object,uint16_t offset,uint8_t *data,uint16_t size) BANKED;
uint8_t pool_object_finish(uint16_t object) BANKED;
uint8_t pool_object_check(uint16_t object,uint8_t type) BANKED;
uint16_t pool_object_size(uint16_t object) BANKED;
uint8_t pool_commit(void) BANKED;
uint16_t pool_reference(uint8_t offset) BANKED;
void pool_set_reference(uint8_t offset,uint16_t object) BANKED;
#endif

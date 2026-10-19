#ifndef GAYBOY_SPARSE_STORE_H
#define GAYBOY_SPARSE_STORE_H
#include "sparse_pool.h"
extern uint8_t sparse_enabled,sparse_install_slot,sparse_song;
extern uint16_t sparse_slots[8],sparse_tones[8];
extern char sparse_song_name[17];
extern uint8_t sparse_patterns;
#define SPARSE_JOURNAL_REF 65534U
extern uint8_t sparse_journal_slot;
uint8_t sparse_journal_busy(void) BANKED;
uint8_t sparse_journal_retaining(void) BANKED;
uint8_t sparse_journal_read(uint16_t offset,uint8_t *data,uint16_t size) BANKED;
void sparse_journal_tones(uint16_t offset,uint8_t *data,uint16_t size) BANKED;
uint8_t sparse_journal_begin(uint8_t slot,const uint8_t *prefix,uint16_t bytes) BANKED;
void sparse_journal_service(void) BANKED;
uint8_t sparse_journal_flush(void) BANKED;
uint8_t sparse_journal_recover(void) BANKED;
void sparse_journal_edit_barrier(void) BANKED;
uint8_t sparse_boot(void) BANKED;
uint8_t sparse_snapshot(uint8_t slot) BANKED;
uint8_t sparse_restore(uint8_t slot) BANKED;
uint8_t sparse_activate(uint8_t slot) BANKED;
void sparse_request(uint8_t slot,uint8_t edit) BANKED;
void sparse_service(void) BANKED;
void sparse_prepare_service(void) BANKED;
uint8_t sparse_prepare_busy(void) BANKED;
uint8_t sparse_prepared_prefix(uint8_t slot,uint8_t *data) BANKED;
uint8_t sparse_prepared_apply(uint8_t slot) BANKED;
uint8_t sparse_prepared_tones(uint8_t slot) BANKED;
uint8_t sparse_prepared_stream(uint8_t slot,PoolStream *stream) BANKED;
uint8_t sparse_prepared_map(uint16_t object,uint8_t *data) BANKED;
uint8_t sparse_first_note(uint8_t track,uint8_t *event) BANKED;
uint8_t sparse_first_kick(void) BANKED;
void sparse_finish_install(void) BANKED;
uint8_t sparse_event(uint16_t index,uint8_t *event) BANKED;
uint8_t sparse_scan(uint8_t track,uint8_t step,uint16_t *cursor,uint8_t *event) BANKED;
void sparse_name(uint8_t slot,char *name) BANKED;
void sparse_get_song_name(uint8_t song,char *name) BANKED;
uint8_t sparse_save_song(uint8_t song) BANKED;
uint8_t sparse_load_song(uint8_t song) BANKED;
uint8_t sparse_delete_song(uint8_t song) BANKED;
uint16_t sparse_song_size(void) BANKED;
uint8_t sparse_clear_slot(uint8_t slot) BANKED;
uint8_t sparse_load_pattern(uint8_t slot) BANKED;
uint8_t sparse_save_pattern(uint8_t index) BANKED;
void sparse_library_name(uint8_t index,char *name) BANKED;
#endif

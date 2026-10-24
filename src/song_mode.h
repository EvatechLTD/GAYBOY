#ifndef SONG_MODE_H
#define SONG_MODE_H
#include <gb/gb.h>
#include <stdint.h>
#define SONG_PAGE 29
#define SONG_CAPACITY 158U
#define SONG_NONE 65535U
/* Timeline retains native sixteenths; the closest visible zoom is eighths. One record, not one record per visible cell. */
typedef struct {uint32_t start,length;uint8_t pad;} SongClip;
typedef struct {uint32_t cursor,base;uint16_t selected;uint8_t lane,zoom,head,gesture,used,error;} SongView;
extern __at (0xA4ED) SongView song_view;
extern uint8_t song_playing;
uint16_t song_count(void) BANKED;
uint8_t song_loop(void) BANKED;
void song_loop_set(uint8_t enabled) BANKED;
void song_read(uint16_t index,SongClip *clip) BANKED;
uint8_t song_put(uint16_t index,const SongClip *clip) BANKED;
void song_delete(uint16_t index) BANKED;
uint32_t song_end(void) BANKED;
uint16_t song_find(uint32_t at) BANKED;
uint32_t song_pattern_length(uint8_t pad) BANKED;
void song_pick_clear(void) BANKED;
void song_pick_begin(uint32_t at,uint8_t lane) BANKED;
void song_pick_box(uint32_t at,uint8_t lane,uint16_t unit) BANKED;
uint8_t song_pick_has(uint16_t i) BANKED;
uint8_t song_pick_edit(int16_t delta,uint8_t resizing) BANKED;
void song_open(void) BANKED;
void song_input(uint8_t p,uint8_t edge) BANKED;
void song_render(void) BANKED;
void song_start(uint8_t smooth) BANKED;
void song_stop(void) BANKED;
void song_service(void) BANKED;
void song_run(void) BANKED;
void song_irq_tick(uint8_t elapsed) NONBANKED;
#endif

#ifndef GAYBOY_SEQUENCER_H
#define GAYBOY_SEQUENCER_H
/* Standalone attack queue shares the inactive link TX buffer in sync OFF. */
extern __at (0xFF98) volatile uint8_t seqirqready;
extern __at (0xFF99) volatile uint8_t seqirqfired;
extern __at (0xFF9A) volatile uint16_t seqirqleft;
extern __at (0xFF9C) uint8_t seqirqstep[2];
extern __at (0xFF9E) uint8_t seqirqnote[2];
extern __at (0xFFA0) uint8_t seqirqregs[9];
extern __at (0xFFA9) uint8_t seqirqpan;
extern __at (0xFFAA) uint8_t seqirqsuppress;
extern __at (0xFFAE) uint8_t seqirqdirty;
void seq_irq_prepare(void) BANKED;
void seq_irq_refresh(uint8_t channel) BANKED;
void seq_irq_tick(uint8_t elapsed) NONBANKED;
#define SEQ_TRACKS 7
#define SEQ_NOTE_TRACKS 6
#define SEQ_STEPS 256
#define PAGE_COUNT 28
extern volatile uint16_t seqticks;
extern uint8_t seqflushpending,seqservicing;
extern uint8_t seqapending,seqamoved;
extern uint16_t seqaanchor;
extern uint8_t seqaoffset;
extern uint8_t seqgrouptrack,seqgroupx0,seqgroupx1,seqgroupy0,seqgroupy1;
uint8_t seq_group_contains(uint8_t step,uint8_t pitch) BANKED;
extern uint8_t seqvelocityhidden;
extern uint8_t seqplaying,seqtrack,seqmode,seqfocus,seqedit,seqmuted,seqsolo,seqhead;
extern uint16_t seqbpm,seqglobalbpm;
extern uint8_t seqswing,seqswingphase;
extern uint16_t seqthreshold;
extern uint16_t seqdefaultdur[SEQ_TRACKS];
extern uint8_t seqdefaultvel[SEQ_TRACKS];
extern __at (0xACFB) uint8_t seqfontdirty;
extern __at (0xACFC) uint8_t seqviewtrack;
extern uint8_t seqviewtop,seqviewbase,seqviewcols;
extern uint8_t seqzoom,seqbase,seqcols,seqrows,seqheight,seqgridheight,seqtilecount,seqtileoverflow;
extern uint8_t seqdrawvalid,seqscreen[360],seqgrid[64];
void seq_pixels(uint8_t navigation) BANKED;
void roll_invert_selection(uint8_t row) BANKED;
void seq_playhead(void) BANKED;
void seq_dimensions(void) BANKED;

extern uint16_t seqlength[SEQ_TRACKS];
extern uint8_t seqposition[SEQ_TRACKS],seqcursor[SEQ_TRACKS],seqpitch[SEQ_TRACKS],seqtop[SEQ_TRACKS];
extern uint8_t seqowned[SEQ_TRACKS],seqsource[SEQ_TRACKS];
extern uint32_t seqgateleft[SEQ_TRACKS];
void seq_open(void) BANKED;
void seq_mixer_mute(uint8_t track,uint8_t solo) BANKED;
void seq_frame(void) BANKED;
uint8_t seq_length_step(uint16_t end,uint16_t next) BANKED;
void seq_input(uint8_t p,uint8_t edge) BANKED;
void seq_render(void) BANKED;
void seq_settings_render(void) BANKED;
void seq_transport(void) BANKED;
extern uint8_t seqpopup;
uint8_t seq_region_copy(uint8_t cut) BANKED;
uint8_t seq_region_paste(uint8_t step,uint8_t pitch) BANKED;
void seq_copy(void) BANKED;
void seq_paste(void) BANKED;
void seq_clear_notes(uint8_t track) BANKED;
extern uint8_t genopen;
void gen_open(void) BANKED;
void gen_cancel(void) BANKED;
void gen_input(uint8_t p,uint8_t edge) BANKED;
void gen_render(void) BANKED;
#endif

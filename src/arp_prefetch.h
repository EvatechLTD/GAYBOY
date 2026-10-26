#ifndef GAYBOY_ARP_PREFETCH_H
#define GAYBOY_ARP_PREFETCH_H
#include <gb/gb.h>
#include <stdint.h>
#include <stddef.h>
typedef struct {uint8_t bits[16],vel[4],count,next,step,valid,onset;uint16_t duration;} EvalChord;
typedef char ArpCacheLayout[(sizeof(EvalChord)==27&&offsetof(EvalChord,onset)==24)?1:-1];
extern EvalChord eval_loopchord[3];
extern uint16_t eval_loopgeneration[3],eval_looplength[3];
extern uint8_t eval_chordnext[3];
void eval_prepare_chord(uint8_t c,uint8_t position,EvalChord *out,uint8_t *indices) BANKED;
void arp_prefetch_chords(void) BANKED;
#endif

/* Experimental timer engines. 0=hardware wave, 1=fast arp, 2=two DDS voices. */
#include "dds_notes.h"
uint8_t pitchdirty,drumsub,drumtail,seqfraction,pcmoutlevel=1;
uint8_t waveengine,arprate=2,softshape[2]={0,2},softnext;
uint8_t mixsamples[32],mixcounter;
volatile uint8_t mixready[2],mixbuffer[32],mixrunning,mixread,mixwrite;
volatile uint16_t engineblocks,mixunderruns;
void midi(uint8_t b);
void enginestop(void) BANKED;
void enginepitch(void) BANKED;
void enginenote(uint8_t note,uint8_t vel,uint8_t owner) BANKED;
void engineoff(uint8_t note) BANKED;
void enginesustain(uint8_t on) BANKED;
void mixfill(void);
void engineset(uint8_t mode) BANKED;
void engine_timer(void);

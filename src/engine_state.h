/* Experimental timer engines. 0=hardware wave, 1=fast arp, 2=two DDS voices. */
#include "dds_notes.h"
uint8_t pitchdirty,drumsub,drumtail,seqfraction,pcmoutlevel=1;
uint8_t waveengine,arprate=2,softshape[2]={0,2},softnext;
uint8_t softon[2],softheld[2],softnote[2],softvel[2],softage[2],softowned[2];
uint16_t softphase[2],softstep[2];
__at (0xD800) uint8_t softlut[2][32];
uint8_t mixsamples[32],mixcounter;
volatile uint8_t mixready[2],mixbuffer[32],mixrunning,mixread,mixwrite;
volatile uint16_t engineblocks,mixunderruns;
uint8_t fastnote[8],fastdown[8],faston[8],fastnext;
uint16_t fastfreq[2][8];
volatile uint8_t fastbank,fastcount[2],fastpos,fastclock;
void midi(uint8_t b);
void enginestop(void) BANKED;
void enginepitch(void) BANKED;
void enginenote(uint8_t note,uint8_t vel,uint8_t owner) BANKED;
void engineoff(uint8_t note) BANKED;
void enginesustain(uint8_t on) BANKED;
void mixfill(void);
void engineset(uint8_t mode) BANKED;
void engine_timer(void);

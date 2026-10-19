#ifndef SEQ_NATIVE_TYPES_H
#define SEQ_NATIVE_TYPES_H
typedef struct {uint8_t sample,bank;uint16_t start,end;} NativeSample;
typedef struct {uint8_t note,velocity;uint32_t gate;uint16_t base;uint8_t regs[5];} NativeVoice;
typedef struct {
 uint16_t generation,bpm,units;
 uint8_t slot,steps[7],params[4][26],mix[14],gates[4],muted,solo,kit;
 int16_t fine[3],bend[3];
 uint8_t wavecustom,waveinput[16],noiseinput[10],kickinput[8];
 uint16_t drummute,drumsolo;
 NativeVoice voice[4];
 NativeSample sample[16];
 uint8_t samplecount,mask,release,routebits,routemask;
 uint8_t waveform[16],noisereg[4],kickreg[5],noisechanged,kick;
 uint32_t noisegate[2],kickgate;
 uint8_t noisevelocity[2];
} NativeStep;
#endif

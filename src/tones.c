#pragma bank 13
#include "api.h"
#include "tones.h"
#include "mixer_shared.h"
extern uint8_t noisepatch[2][5],pulsekickpatch[8],drumkit;
void mixer_pattern_changed(void) BANKED;void seq_native_touch(void) NONBANKED;
/* Current hardware state uses compact 32-byte channel records.
   Only current hardware fields are populated. Unused cache bytes are zero. */
void tones_capture(void) BANKED {uint8_t c;memset(TONE_RAW,0,POOL_TONE_BYTES);for(c=0;c<4;c++){memcpy(TONE_RAW+c*32,param[c],26);TONE_RAW[c*32+26]=program[c];}TONE_RAW[128]=custom;memcpy(TONE_RAW+129,customwave,16);memcpy(TONE_RAW+145,finepitch,6);memcpy(TONE_RAW+151,noisepatch,10);TONE_RAW[161]=drumkit;TONE_RAW[162]=master;TONE_RAW[163]=power;TONE_RAW[164]='S';TONE_RAW[165]=1;memcpy(TONE_RAW+168,pulsekickpatch,8);eval_capture(TONE_RAW+176);}
static void apply(const uint8_t *raw,const uint8_t *mod){uint8_t c;if(raw[164]!='S'||raw[165]!=1||mod[0]!='S'||mod[1]!=1)return;seq_native_touch();for(c=0;c<4;c++){memcpy(param[c],raw+c*32,26);program[c]=raw[c*32+26];}custom=raw[128];memcpy(customwave,raw+129,16);memcpy(finepitch,raw+145,6);memcpy(noisepatch,raw+151,10);drumkit=raw[161];master=raw[162];power=raw[163];memcpy(pulsekickpatch,raw+168,8);eval_restore(mod);wavepending=1;eval_drum_dirty();seqirqdirty=1;globals();dirty=1;}
void tones_apply(void) BANKED {apply(TONE_RAW,TONE_RAW+176);}
void tones_apply_cached(void) BANKED {apply(TONE_CACHED_RAW,TONE_CACHED_FX);}
void tones_finalize(void) BANKED {seqirqdirty=1;eval_drum_dirty();}
uint8_t tones_apply_object(uint16_t object) BANKED {if(pool_object_size(object)!=POOL_TONE_BYTES||!pool_object_read(object,0,TONE_RAW,POOL_TONE_BYTES))return 0;if(TONE_RAW[164]!='S'||TONE_RAW[165]!=1)return 0;tones_apply();return 1;}
uint8_t tones_scatter_object(uint16_t object) BANKED {return tones_apply_object(object);}
void tones_pack(void) BANKED {} uint8_t tones_decode(void) BANKED {return 0;}
void tones_pack_begin(void) BANKED {} void tones_decode_begin(void) BANKED {} uint8_t tones_step(void) BANKED {return 2;}

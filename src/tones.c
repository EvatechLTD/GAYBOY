#pragma bank 13
#include "api.h"
#include "tones.h"
#include "mixer_shared.h"
extern uint8_t noisepatch[2][5],pulsekickpatch[8],drumkit;
void mixer_pattern_changed(void) BANKED;void seq_native_touch(void) NONBANKED;
/* Current hardware state uses compact 32-byte channel records.
   Only current hardware fields are populated. Unused cache bytes are zero. */
void tones_capture(void) BANKED {uint8_t c;memset(TONE_RAW,0,POOL_TONE_BYTES);for(c=0;c<4;c++){memcpy(TONE_RAW+c*32,param[c],26);TONE_RAW[c*32+26]=program[c];}TONE_RAW[128]=custom;memcpy(TONE_RAW+129,customwave,16);memcpy(TONE_RAW+145,finepitch,6);memcpy(TONE_RAW+151,noisepatch,10);TONE_RAW[161]=drumkit;TONE_RAW[162]=master;TONE_RAW[163]=power;TONE_RAW[164]='S';TONE_RAW[165]=1;memcpy(TONE_RAW+168,pulsekickpatch,8);eval_capture(TONE_RAW+176);coarse_capture(TONE_RAW);drum_map_capture(TONE_RAW+320);}
/* Compare against live settings, not a saved-pad identity: edits and MIDI can
   change those settings between launches. Unchanged patches keep runtime. */
static uint8_t changed_copy(uint8_t *to,const uint8_t *from,uint8_t n){if(!memcmp(to,from,n))return 0;memcpy(to,from,n);return 1;}
static void apply(const uint8_t *raw,const uint8_t *mod){uint8_t c,changed=0,drums=0,wavechanged,globalchanged;if(raw[164]!='S'||raw[165]!=1||mod[0]!='S'||mod[1]!=1)return;
 wavechanged=custom!=raw[128]||memcmp(customwave,raw+129,16)||param[2][14]!=raw[78];
 for(c=0;c<4;c++){changed|=changed_copy(param[c],raw+c*32,26);program[c]=raw[c*32+26];}
 changed|=changed_copy(&custom,raw+128,1);changed|=changed_copy(customwave,raw+129,16);changed|=changed_copy(finepitch,raw+145,6);
 drums|=changed_copy((uint8_t *)noisepatch,raw+151,10);drums|=changed_copy(&drumkit,raw+161,1);drums|=changed_copy(pulsekickpatch,raw+168,8);
 globalchanged=changed_copy(&master,raw+162,1);globalchanged|=changed_copy(&power,raw+163,1);
 eval_restore(mod);coarse_restore(raw,mod);
 if(wavechanged)wavepending=1;if(drums)eval_drum_dirty();if(changed||drums){seq_native_touch();seqirqdirty=1;}if(globalchanged)globals();dirty=1;}
void tones_apply(void) BANKED {apply(TONE_RAW,TONE_RAW+176);drum_map_restore(TONE_RAW+320);}
void tones_apply_buffer(const uint8_t *raw) BANKED {apply(raw,raw+176);drum_map_restore(raw+320);}
void tones_apply_cached(void) BANKED {apply(TONE_CACHED_RAW,TONE_CACHED_FX);drum_map_factory(drumkit);}
void tones_finalize(void) BANKED {seqirqdirty=1;eval_drum_dirty();}
uint8_t tones_apply_object(uint16_t object) BANKED {if(pool_object_size(object)!=POOL_TONE_BYTES||!pool_object_read(object,0,TONE_RAW,POOL_TONE_BYTES))return 0;if(TONE_RAW[164]!='S'||TONE_RAW[165]!=1)return 0;tones_apply();return 1;}
uint8_t tones_scatter_object(uint16_t object) BANKED {return tones_apply_object(object);}
void tones_pack(void) BANKED {} uint8_t tones_decode(void) BANKED {return 0;}
void tones_pack_begin(void) BANKED {} void tones_decode_begin(void) BANKED {} uint8_t tones_step(void) BANKED {return 2;}

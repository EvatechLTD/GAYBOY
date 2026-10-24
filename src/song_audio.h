#ifndef SONG_AUDIO_H
#define SONG_AUDIO_H
#include "song_mode.h"
typedef struct {
 uint16_t length[4],begin[4],end[4],arpwhole[3],arprest[3],arpscale[3],points[3];
 uint8_t patch[3][6],wave[16],drum[7],mode[3],order[3],retrig[3],master,power,lfo,lfowhole;
 uint16_t lfofraction;
} SongScene;
typedef struct {
 uint16_t cursor,wait,residual,pitch;
 uint8_t step,count,index,note,volume,tones[4][4];
} SongVoice;
typedef struct {
 volatile uint16_t clock,wait;
 uint16_t last,phase,bpm,units,remainder,stepleft,kickleft,lfoleft,lfofraction,clipindex,prefetch,total;
 volatile uint32_t position;uint32_t end;
 SongClip first,next,current;
 SongVoice voice[3];
 uint16_t drumcursor;
 uint8_t scene,drumstep,half,lfophase;volatile uint8_t done,need;uint8_t loop,origin,prepared,error;
} SongRuntime;
typedef char SongSceneSize[(sizeof(SongScene)==104)?1:-1];
typedef char SongRuntimeSize[(sizeof(SongRuntime)==162)?1:-1];
extern __at (0xA000) SongScene song_scenes[5];
extern __at (0xA300) SongRuntime song_runtime;
void song_cache_get(uint16_t at,uint8_t *out,uint8_t n) BANKED;
#endif

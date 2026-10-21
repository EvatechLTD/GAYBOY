#ifndef GAYBOY_DRUM_ROWS_H
#define GAYBOY_DRUM_ROWS_H
/* Presentation order changes without changing the audio voice IDs in notes. */
#define DRUM_VIEW_ROW(v) ((v)>=10?(v)-10:(v)+3)
#define DRUM_VOICE_ROW(r) ((r)<3?(r)+10:(r)-3)
#define DRUM_SCREEN_ROW(r) ((r)<3?(r):(r)+1)
#define DRUM_SCREEN_INDEX(y) ((y)<3?(y):(y)>=4&&(y)<14?(y)-1:255)
#endif

#ifndef GAYBOY_DRUM_ROWS_H
#define GAYBOY_DRUM_ROWS_H
/* Presentation order changes without changing the audio voice IDs in notes. */
#define DRUM_VIEW_ROW(v) ((v)>=10?(v)-10:(v)+3)
#define DRUM_VOICE_ROW(r) ((r)<3?(r)+10:(r)-3)
#endif

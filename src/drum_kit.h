#ifndef GAYBOY_DRUM_KIT_H
#define GAYBOY_DRUM_KIT_H
#define DRUM_KIT_SLOTS 8
#define DRUM_KIT_BYTES 160U
#define DRUM_MAP_BYTES 22U
extern uint8_t drummapkit,drumsourcekit[10],drumsourceslot[10],drumsourcebank[10];
extern uint16_t drumsourceoffset[10],drumsourcelength[10];
#define DRUM_MAPPED (drummapkit==drumkit)
void drum_map_factory(uint8_t kit) BANKED;
void drum_map_assign(uint8_t dest,uint8_t kit,uint8_t sample) BANKED;
void drum_map_capture(uint8_t *out) BANKED;
void drum_map_restore(const uint8_t *in) BANKED;
void drum_source_audition(uint8_t kit,uint8_t sample) BANKED;
void drum_file_open(uint8_t mode) BANKED;
void drum_file_capture_context(void) BANKED;
uint8_t drum_file_context(void) BANKED;
uint8_t drum_file_sample_context(void) BANKED;
void drum_file_context_name(uint8_t *name) BANKED;
uint8_t drum_kit_save(uint8_t slot) BANKED;
uint8_t drum_kit_load(uint8_t slot) BANKED;
void resident_kit_read(uint8_t slot,uint8_t *data) BANKED;
void resident_kit_write(uint8_t slot,const uint8_t *data) BANKED;
#endif

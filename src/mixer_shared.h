#ifndef MIXER_SHARED_H
#define MIXER_SHARED_H
typedef struct {uint8_t magic,slot,pending,quant,focus,edit,browser,naming,letter,padcache;uint16_t boundary;uint8_t level[7],pan[7];char name[17];uint16_t checksum;uint8_t checking,presaved,openempty,cachevalid,cacheslot,error,protectedslots;} Mixer;
extern __at (0xAC80) Mixer mx;
#define MIXER_LINK_AVAILABLE (syncmode==1&&!syncslave&&linkstate==2)
#define MIXER_LINK_VIEW (mixer_device&&MIXER_LINK_AVAILABLE)
#define RECORD 2560U
#define DATA 32U
#define OLD_DRUM 1184U
#define OLD_META 2208U
#define META 2080U
#define METASIZE 81U
#define VALID 0xBA
#define NOTE_VALID 0xB9
#define SPARSE_VALID 0xB8
#define OLD_VALID 0xB7
#define CACHE ((uint8_t *)0xB000)

extern uint8_t toneready;
void readpart(uint8_t s,uint16_t off,uint8_t *dst,uint16_t n) BANKED;
void writepart(uint8_t s,uint16_t off,const uint8_t *src,uint16_t n) BANKED;
uint8_t tag(uint8_t s) BANKED;
uint8_t valid(uint8_t s) BANKED;
void getname(uint8_t s,char *name) BANKED;
void defaults(void) BANKED;
void snapshot(uint8_t s) BANKED;
void autosnapshot(uint8_t s) BANKED;
uint8_t oldmetaok(const uint8_t *m) BANKED;
uint8_t metaok(const uint8_t *m) BANKED;
uint8_t migrate(uint8_t s) BANKED;
void prefetch(uint8_t s) BANKED;
void applymeta(const uint8_t *meta) BANKED;
void tailcopy(uint8_t *dst,const uint8_t *src,uint16_t size) BANKED;
uint8_t restore(uint8_t s,uint8_t cached) BANKED;
void mixer_tempo_edit(int16_t delta) BANKED;
void mixer_launch_request(uint8_t slot,uint8_t edit) BANKED;
void mixer_prepare_service(void) BANKED;
void mixer_prepare_cancel(void) BANKED;
uint8_t mixer_prepare_busy(void) BANKED;
void mixer_activate(uint8_t slot,uint8_t edit) BANKED;
#endif

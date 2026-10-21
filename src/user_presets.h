#ifndef GAYBOY_USER_PRESETS_H
#define GAYBOY_USER_PRESETS_H
#include <stdint.h>
#include "sparse_pool.h"
#define USER_BANKS 4
#define USER_BANK_SLOTS 8
#define USER_SLOTS 32
#define USER_DIRECTORY_BYTES 386U
#define USER_DIRECTORY_REF 124
#define USER_DIRECTORY_FLAG 128
#define USER_DIRECTORY_KIND 'B'
#define USER_TONE_KIND 'U'
#define USER_TONE_BYTES(c) ((c)<3?48U:(c)==3?46U:(c)==7?28U:25U)
uint16_t user_preset_reference(uint8_t slot) BANKED;
uint8_t user_preset_type(uint8_t slot) BANKED;
void user_preset_name(uint8_t slot,uint8_t *name) BANKED;
void user_bank_name(uint8_t bank,uint8_t *name) BANKED;
uint8_t user_preset_publish(uint8_t slot,uint16_t object,uint8_t instrument,const uint8_t *name) BANKED;
uint8_t user_preset_remove(uint8_t slot) BANKED;
uint8_t user_bank_clear(uint8_t bank) BANKED;
uint8_t user_preset_rename(uint8_t slot,const uint8_t *name) BANKED;
uint8_t user_bank_rename(uint8_t bank,const uint8_t *name) BANKED;
uint8_t user_preset_save(uint8_t slot,uint8_t instrument) BANKED;
uint8_t user_preset_load(uint8_t slot,uint8_t instrument) BANKED;
void tone_user_open(uint8_t mode) BANKED;
#endif

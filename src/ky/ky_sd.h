#ifndef KY_SD_H
#define KY_SD_H
#include <gb/gb.h>
#include <stdint.h>
#include "diskio.h"
extern uint8_t ky_timeout,ky_stage,ky_r1,ky_rawstatus,ky_block;
uint8_t ky_spi(uint8_t value) __naked;
void ky_control(uint8_t flags);
#endif

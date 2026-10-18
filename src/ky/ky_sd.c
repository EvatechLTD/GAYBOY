/* Original EDGB/KY SPI protocol, independently implemented from interface
   analysis of the original-series GBOS v4 (MD5 14763d546301eb45ecc74df85818571c).
   Only SPI control register 2 is selected. No flash writes or SD write commands.
   The caller disables ordinary SRAM before access, preventing a locked mapper
   from interpreting these ports as writes to a game's save RAM. */
#include "ky_sd.h"
#define PORT(a) (*(volatile uint8_t *)(a))
uint8_t ky_timeout,ky_stage,ky_r1,ky_rawstatus,ky_block,ky_flags=3;
uint8_t ky_spi(uint8_t value) __naked {
 value;
 __asm
 push bc
 ld (#0xBE00),a
 ld hl,#0xBF00
 ld b,#0
ky_spi_wait$:
 bit 6,(hl)
 jr nz,ky_spi_ready$
 dec b
 jr nz,ky_spi_wait$
 ld a,#1
 ld (_ky_timeout),a
 ld a,#255
 jr ky_spi_done$
ky_spi_ready$:
 ld a,(#0xBE00)
ky_spi_done$:
 .globl _ky_spi_reply
_ky_spi_reply::
 pop bc
 ret
 __endasm;
}
void ky_control(uint8_t flags){ky_flags=flags;PORT(0xBF00)=2;PORT(0xBF80)=flags;}
void ky_release(void){ky_control(ky_flags|1);ky_spi(255);}
uint8_t ky_command(uint8_t cmd,uint32_t arg){uint8_t i,r;ky_release();ky_control(ky_flags&0xFE);ky_spi(255);ky_spi(0x40|cmd);ky_spi(arg>>24);ky_spi(arg>>16);ky_spi(arg>>8);ky_spi(arg);ky_spi(cmd==0?0x95:cmd==8?0x87:1);r=255;for(i=0;i<16;i++){r=ky_spi(255);if(!(r&128)||ky_timeout)break;}ky_r1=r;return r;}
DSTATUS disk_initialize(void){uint8_t i,r,sdv2=0,ocr[4];uint16_t tries;
 DISABLE_RAM_MBC5;ky_timeout=ky_block=0;ky_rawstatus=PORT(0xBF00);ky_stage=1;ky_control(3);for(i=0;i<10;i++)ky_spi(255);
 ky_stage=2;if(ky_command(0,0)!=1||ky_timeout){ky_release();return STA_NOINIT;}
 ky_stage=3;r=ky_command(8,0x1AA);if(r==1){for(i=0;i<4;i++)ocr[i]=ky_spi(255);if(ocr[2]!=1||ocr[3]!=0xAA){ky_release();return STA_NOINIT;}sdv2=1;}else if(r!=5){ky_release();return STA_NOINIT;}
 ky_stage=4;for(tries=0;tries<1000;tries++){r=ky_command(55,0);if(r>1||ky_timeout)break;r=ky_command(41,sdv2?0x40000000UL:0);if(!r)break;}
 if(r||ky_timeout){ky_release();return STA_NOINIT;}
 ky_stage=5;if(sdv2){if(ky_command(58,0)){ky_release();return STA_NOINIT;}for(i=0;i<4;i++)ocr[i]=ky_spi(255);ky_block=!!(ocr[0]&0x40);}
 if(!ky_block&&ky_command(16,512)){ky_release();return STA_NOINIT;}ky_release();ky_control(1);ky_stage=6;return ky_timeout?STA_NOINIT:0;
}
DRESULT disk_readp(uint8_t *buff,uint32_t sector,uint16_t offset,uint16_t count){uint16_t i,tries;uint8_t r;
 if(offset>512||count>512-offset||(!buff&&count))return RES_PARERR;if(ky_timeout||ky_stage<6)return RES_NOTRDY;
 if(!ky_block&&sector>0x7FFFFFUL)return RES_PARERR;
 if(ky_command(17,ky_block?sector:sector<<9)){ky_release();return RES_ERROR;}
 r=255;for(tries=0;tries<8192;tries++){r=ky_spi(255);if(r!=255||ky_timeout)break;}
 if(r!=0xFE||ky_timeout){ky_release();return RES_ERROR;}
 for(i=0;i<512;i++){r=ky_spi(255);if(i>=offset&&i-offset<count)*buff++=r;}ky_spi(255);ky_spi(255);ky_release();return ky_timeout?RES_ERROR:RES_OK;
}

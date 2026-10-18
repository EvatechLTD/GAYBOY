#include <gb/gb.h>
#include <stdio.h>
#include <gbdk/console.h>
#include <string.h>
#include "ky_sd.h"
FATFS ky_fs;
DIR ky_dir;
FILINFO ky_info;
uint8_t ky_result,ky_count,ky_choice,ky_page,ky_showfile;
uint16_t ky_skip,ky_read;
uint32_t ky_filesize;
char ky_path[96],ky_names[8][13],ky_target[112];
uint8_t ky_attrs[8],ky_bytes[16];
uint8_t ky_next(void){do{ky_result=pf_readdir(&ky_dir,&ky_info);if(ky_result||!ky_info.fname[0])return 0;}while(ky_info.fname[0]=='.');return 1;}
void ky_list(void){uint16_t i;ky_count=ky_choice=0;ky_result=pf_opendir(&ky_dir,ky_path);if(ky_result)return;for(i=0;i<ky_skip;i++)if(!ky_next())return;while(ky_count<8&&ky_next()){strcpy(ky_names[ky_count],ky_info.fname);ky_attrs[ky_count]=ky_info.fattrib;ky_count++;}}
void ky_pathline(void){uint8_t i;const char *s=ky_path;if(!*s)s="/";else{for(i=0;ky_path[i];i++)if(ky_path[i]=='/')s=ky_path+i+1;}for(i=0;s[i]&&i<19;i++)putchar(s[i]);putchar('\n');}
void ky_hex(uint8_t n){putchar("0123456789ABCDEF"[n>>4]);putchar("0123456789ABCDEF"[n&15]);}
void ky_draw(void){uint8_t i;cls();printf("KY SD TEST 01\nREAD ONLY / EDGB\n");if(ky_result){printf("\nSD/FAT ERROR %u\nSTAGE %u R1 ",ky_result,ky_stage);ky_hex(ky_r1);printf("\nPORT ");ky_hex(ky_rawstatus);printf(" WAIT %u\n",ky_timeout);printf("\nSELECT RETRY\n\nREPORT THESE VALUES\nNO FLASH/SD WRITES");return;}
 if(ky_showfile){printf("\n%s\n%u BYTES READ\n",ky_names[ky_choice],ky_read);for(i=0;i<ky_read;i++){ky_hex(ky_bytes[i]);putchar(' ');if((i&3)==3)putchar('\n');}printf(ky_filesize==16?"\nA WAVE PREVIEW\nB RETURN":"\n16-BYTE GBW ONLY\nB RETURN");return;}
 ky_pathline();for(i=0;i<ky_count;i++)printf("%c%c%s\n",i==ky_choice?'>':' ',ky_attrs[i]&AM_DIR?'/':' ',ky_names[i]);if(!ky_count)printf("(EMPTY)\n");gotoxy(0,13);printf("A OPEN  B UP\nL/R FILE PAGE\nSELECT REMOUNT\nFAT16/32 8.3 NAMES");}
void ky_mount(void){NR30_REG=0;ky_showfile=0;ky_path[0]=0;ky_skip=0;ky_result=pf_mount(&ky_fs);if(!ky_result)ky_list();ky_draw();}
void ky_preview(void){uint8_t i;if(ky_read!=16||ky_filesize!=16)return;NR52_REG=0x80;NR50_REG=0x77;NR51_REG=0x44;NR30_REG=0;for(i=0;i<16;i++)((volatile uint8_t *)0xFF30)[i]=ky_bytes[i];NR30_REG=0x80;NR32_REG=0x20;NR33_REG=6;NR34_REG=0x87;}
void main(void){uint8_t p,last=0,edge;uint16_t n;DISPLAY_OFF;printf("KY SD TEST 01\nCHECKING SD...\n");DISPLAY_ON;ky_mount();while(1){wait_vbl_done();p=joypad();edge=p&~last;last=p;if(edge&J_SELECT){ky_mount();continue;}if(ky_result)continue;if(ky_showfile){if(edge&J_A)ky_preview();if(edge&J_B){NR30_REG=0;ky_showfile=0;ky_draw();}continue;}
 if((edge&J_UP)&&ky_choice){ky_choice--;ky_draw();}if((edge&J_DOWN)&&ky_choice+1<ky_count){ky_choice++;ky_draw();}
 if(edge&J_RIGHT){if(ky_count==8){ky_skip+=8;ky_list();if(!ky_count&&ky_skip){ky_skip-=8;ky_list();}ky_draw();}}if((edge&J_LEFT)&&ky_skip){ky_skip-=8;ky_list();ky_draw();}
 if(edge&J_B){n=strlen(ky_path);while(n&&ky_path[n-1]!='/')n--;if(n)n--;ky_path[n]=0;ky_skip=0;ky_list();ky_draw();}
 if((edge&J_A)&&ky_count){n=strlen(ky_path);if(n+strlen(ky_names[ky_choice])+2>=sizeof(ky_path))continue;strcpy(ky_target,ky_path);if(n)strcat(ky_target,"/");strcat(ky_target,ky_names[ky_choice]);if(ky_attrs[ky_choice]&AM_DIR){strcpy(ky_path,ky_target);ky_skip=0;ky_list();}else{ky_result=pf_open(ky_target);if(!ky_result){ky_filesize=ky_fs.fsize;ky_result=pf_read(ky_bytes,16,&ky_read);ky_showfile=!ky_result;}}ky_draw();}
 }}

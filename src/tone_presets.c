#pragma bank 40
#include "api.h"
#include "tones.h"
uint8_t tonepresetopen,w2program;
static uint8_t presetchoice;
extern uint8_t w2row,w2tablemode,w2tablelen,w2tablespeed;
extern int8_t w2tables[8][3];
static const char * const banks[10]={"TETRIS","MARIO LAND","ZELDA LA","POKEMON RB","KIRBY DL","METROID II","MEGA MAN","CASTLEVANIA","WARIO LAND","DK LAND"};
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20){uint8_t c=*s++;if(c>='a'&&c<='z')c-=32;*d++=c-32+(inv?96:0);}}
void tone_preset_open(void) BANKED {presetchoice=selected==4?w2program:program[selected];if(presetchoice>99)presetchoice=0;tonepresetopen=1;dirty=1;}
void tone_preset_render(void) BANKED {uint8_t i,n,start=presetchoice>3?presetchoice-3:0;char digits[4];if(start>93)start=93;memset(canvas,0,360);memset(canvas,96,20);text(0,0,"LOAD PRESET",1);text(1,2,banks[presetchoice/10],0);
 for(i=0;i<7;i++){n=start+i;digits[0]='0'+(n+1)/100;digits[1]='0'+((n+1)/10)%10;digits[2]='0'+(n+1)%10;digits[3]=0;text(0,4+i,digits,n==presetchoice);text(4,4+i,patch(n)->name,n==presetchoice);mixfill();}
 text(0,12,"U/D SOUND L/R BANK",0);text(0,14,"A LOAD  B CANCEL",0);
}
static void w2_preset(uint8_t n){Preset *p=patch(n);uint8_t i,c;
 w2program=n;w2settings[0]=24;w2settings[1]=p->v[1];w2settings[2]=p->v[3]?8+p->v[3]*8:120;w2settings[3]=(n%10==7||n%10==8)?24:0;w2settings[4]=p->v[14]&3;
 w2tablemode=!!(p->tconfig&3);w2tablelen=(p->tconfig>>2)+1;w2tablespeed=p->mod[0]?p->mod[0]:1;
 /* Copy the library's pitch/shape motion into W2's independent table. */
 for(i=0;i<8;i++){w2tables[i][0]=0;w2tables[i][1]=w2settings[4];w2tables[i][2]=15;}
 /* Use a temporary hardware table, then restore that channel unchanged. */
 {int8_t saved[8][3];memcpy(saved,tables[2],24);stocktable(2,p->table);for(i=0;i<8;i++)for(c=0;c<2;c++)w2tables[i][c]=c?(tables[2][i][1]&3):tables[2][i][0];memcpy(tables[2],saved,24);}
}
void tone_preset_input(uint8_t edge) BANKED {
 if(edge&(J_B|J_SELECT|J_START)){tonepresetopen=0;dirty=1;return;}
 if(edge&J_UP)presetchoice=presetchoice?presetchoice-1:99;
 if(edge&J_DOWN)presetchoice=(presetchoice+1)%100;
 if(edge&J_LEFT)presetchoice=(presetchoice+90)%100;
 if(edge&J_RIGHT)presetchoice=(presetchoice+10)%100;
 if(edge&J_A){if(selected<4){load(selected,presetchoice);finepitch[selected]=0;choice=presetchoice;}else{w2_preset(presetchoice);finepitch[4]=0;}tonepresetopen=0;}
 dirty=1;
}

uint8_t mono_rows(void) BANKED {return monoosc==4?EXP_COUNT:monoosc==3?11:monoosc==2?6:7;}
uint8_t mono_row(int8_t delta) BANKED {uint8_t r=cursor[7],max=mono_rows();if(monoosc==3){if(r==8)r=0;else if(r<8)r++;}r=delta<0?(r?r-1:max-1):(r+1)%max;if(monoosc==3){if(!r)return 8;if(r<9)r--;}return r;}
void mono_page(int8_t delta,uint8_t crossing) BANKED {monoedit=0;monoosc=(monoosc+(delta<0?4:1))%5;if(cursor[7]>=mono_rows())cursor[7]=mono_rows()-1;if(monoosc>=3)monocol=0;else if(crossing)monocol=delta<0?2:0;dirty=1;}

extern uint8_t ui_menu_allowed(uint8_t item) BANKED;
void ui_menu_step(int8_t delta) BANKED {do{navchoice=delta<0?(navchoice<=1?PAGE_COUNT-1:navchoice-1):(navchoice>=PAGE_COUNT-1?1:navchoice+1);}while(!ui_menu_allowed(navchoice));}

#pragma bank 63
#include "api.h"
#include "mixer_shared.h"
#include "mixer_drum_names.h"
#include "mixer_pads.h"
#include "link_control.h"
extern uint8_t mixer_hidden[8],mixer_device,syncrole;
uint8_t link_target(uint8_t track,uint8_t field) BANKED;
uint8_t link_pending(void) BANKED;
static uint8_t scroll;
static const char * const names[7]={"P3","P4","W3","N2","M2","W4","D2"};
static const char * const pans[4]={"--"," R"," L","LR"};
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
static void link_number(uint8_t x,uint8_t y,uint8_t n,uint8_t inv){char s[4];s[0]='0'+n/100;s[1]='0'+n/10%10;s[2]='0'+n%10;s[3]=0;text(x,y,s,inv);}
static uint8_t shown(uint8_t c){return !(mixer_hidden[4+(c>>3)]&(1U<<(c&7)));}
static uint8_t focus(uint8_t c,uint8_t f){return c<7?2+c*4+f:38+(c-7)*2+(f>1?1:f);}
static uint8_t first_strip(void){uint8_t c;for(c=0;c<20;c++)if(shown(c))return focus(c,0);return 0;}
static uint8_t pad(void){uint8_t c;for(c=0;c<8;c++)if(shown(c+20))return 30+c;return 0;}
void mixer_link_render(void) BANKED {uint8_t c,n=0,col=0,selected=mx.focus>=38&&mx.focus<64?7+(mx.focus-38)/2:mx.focus>=2&&mx.focus<30?(mx.focus-2)/4:255;
 /* An idle AUTO start discovers its peer before sending the selected pad. */
 if(mx.browser&128){if(!seqplaying)mx.browser=0;else if(!syncslave&&linkstate==2&&linkmirror.quant<=4&&link_command(mx.browser&7,4,0))mx.browser=0;}
 memset(canvas,0,360);memset(canvas,96,20);text(0,0,"MIXER",1);text(16,0,"LINK",1);
 text(0,2,seqplaying?"STOP":"PLAY",mx.focus==0);text(7,2,syncmode!=1?"WAIT LINK":syncslave?(seqplaying?"SLAVE MODE":"PLAY TO LINK"):linkstate==2?"CONNECTED":linkstate==3?"STALE":"WAIT LINK",0);
 text(0,3,"LAUNCH",0);text(8,3,linkmirror.quant==1?"1/8":linkmirror.quant==2?"1/4":linkmirror.quant==3?"1/2":"1/1",mx.focus==1);
 for(c=0;c<20;c++)if(shown(c)){if(c==selected)col=n;n++;}if(selected<20){if(col<scroll)scroll=col;if(col>=scroll+5)scroll=col-4;}else if(scroll>=n)scroll=0;
 n=0;for(c=0;c<20;c++){uint8_t f,x;if(!shown(c))continue;col=n++;if(col<scroll||col>=scroll+5)continue;x=4+(col-scroll)*3;
  f=focus(c,0);if(c<7)text(x,4,names[c],0);else text(x,4,mixer_drum_name(linkmirror.kit,c-7),0);
  if(c<7){text(x+1,5,linkmirror.muted&(1<<c)?"M":"-",mx.focus==f);text(x+1,6,linkmirror.solo&(1<<c)?"S":"-",mx.focus==f+1);link_number(x,8,linkmirror.level[c],mx.focus==f+2);text(x,12,pans[linkmirror.pan[c]&3],mx.focus==f+3);}
  else {uint16_t bit=1U<<(c-7);text(x+1,5,linkmirror.drummutemask&bit?"M":"-",mx.focus==f);text(x+1,6,linkmirror.drumsolomask&bit?"S":"-",mx.focus==f+1);}mixfill();
 }
 text(0,5,"M",0);text(0,6,"S",0);text(0,8,"VOL",0);text(0,12,"PAN",0);mixer_pads_render();
 text(0,17,syncmode!=1?"SELECT GAYBOY SYNC":syncslave?(seqplaying?"USE MASTER MIXER":"PLAY TO LINK"):linkstate==2?(link_pending()?"LINK COMMAND PENDING":"A PICK / HOLD A EDIT"):"CONNECTING...",0);
}
void mixer_link_input(uint8_t p,uint8_t edge) BANKED {uint8_t c,f;
 if(mx.focus<2){if(edge&(J_LEFT|J_RIGHT))mx.focus=mx.focus?0:1;if(edge&J_DOWN)mx.focus=first_strip();if(edge&J_UP)mx.focus=pad();
  if(edge&(J_A|J_B)){if(!mx.focus)seq_transport();else if(mx.focus==1)link_command(0,5,linkmirror.quant>=4?1:linkmirror.quant+1);}dirty=1;return;}
 if(mx.focus>=30&&mx.focus<38){if(edge&(J_LEFT|J_RIGHT))mixer_pads_move(edge&J_LEFT?-1:1);
  if(edge&J_UP)mx.focus=first_strip();else if(edge&J_A){if(!seqplaying){seq_transport();if(syncmode==1&&!syncslave&&seqplaying)mx.browser=128+mx.focus-30;}else link_command(mx.focus-30,4,0);}dirty=1;return;}
 c=mx.focus>=38?7+(mx.focus-38)/2:(mx.focus-2)/4;f=mx.focus>=38?(mx.focus-38)%2:(mx.focus-2)%4;
 if(c<7&&f>=2&&(p&(J_A|J_B))){int16_t v=link_target(c,f);if(!(edge&(J_UP|J_DOWN|J_LEFT|J_RIGHT)))return;if(edge&J_UP)v++;if(edge&J_DOWN)v--;if(edge&J_LEFT)v-=10;if(edge&J_RIGHT)v+=10;link_command(c,f,v<0?0:v>(f==2?127:3)?(f==2?127:3):v);dirty=1;return;}
 if(edge&(J_A|J_B))link_command(c,f,!link_target(c,f));
 if(edge&J_LEFT){uint8_t n=c;while(n){n--;if(shown(n)){c=n;break;}}}if(edge&J_RIGHT){uint8_t n=c;while(n<19){n++;if(shown(n)){c=n;break;}}}
 if(edge&J_UP){if(f)f--;else {mx.focus=0;dirty=1;return;}}if(edge&J_DOWN){if(f<(c<7?3:1))f++;else {mx.focus=pad();dirty=1;return;}}
 mx.focus=focus(c,f);dirty=1;
}

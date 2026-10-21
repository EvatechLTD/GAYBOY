#pragma bank 60
#include "api.h"
#include "mixer_shared.h"
#include "mixer_pads.h"
#include "link_control.h"
#include "mixer_font.h"
extern uint8_t mixer_hidden[8],mixer_device,mixer_pad_pages[2];
extern __at (0xACC4) uint8_t pad_image_playing;
extern __at (0xACC5) uint8_t pad_image_queued;
__at (0xAE40) uint8_t pad_names[8][5];
__at (0xA700) static uint8_t slots[5];
__at (0xAE94) static uint8_t cachedpage;
__at (0xAE95) static uint8_t cachedmask;
__at (0xAE96) static uint8_t cacheddevice;
__at (0xAEAA) static uint8_t cachedfocus;
static const uint8_t digits[8][5]={{2,6,2,2,7},{6,1,2,4,7},{6,1,2,1,6},{5,5,7,1,1},{7,4,6,1,6},{3,4,7,5,7},{7,1,2,2,2},{7,5,7,5,7}};
__at (0xACFA) uint8_t padbank;
__at (0xACC0) uint16_t padflash_started;
__at (0xACC2) uint8_t padflash_off;
__at (0xACC3) uint8_t padflash_slot;
static uint8_t padtile(uint8_t tile,uint8_t bank){return bank?(tile<24?168+tile:180+tile):(tile<32?64+tile:128+tile);}
static uint8_t column(uint8_t slot){uint8_t i;if(slot>=8)return 255;for(i=0;i<5;i++)if(slots[i]==slot)return i*4;return 255;}
static uint8_t hidden(void){uint8_t *p=mixer_hidden+(MIXER_LINK_VIEW?4:0);return (p[2]>>4)|(p[3]<<4);}
static uint8_t queued(void){return MIXER_LINK_VIEW?linkmirror.pending:mx.pending;}
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
static void padmap(uint8_t slot,uint8_t bank){uint8_t row,x,col=column(slot),ids[4];uint16_t at;if(col==255)return;
 for(row=0;row<2;row++){at=(uint16_t)(15+row)*20+col;for(x=0;x<4;x++){ids[x]=padtile(row*20+col+x,bank);visible[at+x]=canvas[at+x]=ids[x];}ui_upload_map(0x9800U+(uint16_t)(15+row)*32+col,ids,4);mixfill();}
}
void mixer_pad_restore(void) BANKED {if(padflash_off){padflash_off=0;padmap(padflash_slot,padbank);}}
void mixer_tick(void) BANKED {uint8_t off,q=queued();if(navopen){padflash_off=0;return;}
 if(page!=18||q>=8||!mx.padcache||q!=padflash_slot){mixer_pad_restore();return;}
 off=((uint16_t)(sys_time-padflash_started)>>4)&1;if(off!=padflash_off){padflash_off=off;padmap(q,padbank^off);}
}
static void toggle(uint8_t slot){uint8_t x,y,col=column(slot),*rows=(uint8_t *)0xAD00;if(col==255)return;
 for(y=0;y<16;y++){for(x=0;x<4;x++)rows[(uint16_t)y*20+col+x]^=255;if((y&3)==3)mixfill();}
}
static void outline(uint8_t slot,uint8_t selected){uint8_t y,col=column(slot),*rows=(uint8_t *)0xAD00;if(col==255)return;
 for(y=0;y<16;y++){uint8_t *d=rows+(uint16_t)y*20+col;if(!y||y==15)memset(d,selected?255:0,4);else if(selected){d[0]|=128;d[3]|=1;}else {d[0]&=127;d[3]&=254;}}
}
static void changed(uint8_t slot,uint8_t *columns){uint8_t x,col=column(slot);if(col==255)return;for(x=0;x<4;x++)columns[col+x]=1;}
static void upload(uint8_t bank,uint8_t *columns){uint8_t k,tx,y,buf[16],*src,*dst,*rows=(uint8_t *)0xAD00;
 for(k=0;k<2;k++)for(tx=0;tx<20;tx++)if(columns[tx]){src=rows+(k?160:0)+tx;dst=buf;for(y=0;y<8;y++){*dst++=*src;*dst++=*src;src+=20;}ui_upload_tile(padtile(k*20+tx,bank),buf,0);mixfill();}
}
void mixer_pads_render(void) BANKED {uint8_t i,j,n=0,pg=0,mask=hidden(),active=MIXER_LINK_VIEW?linkmirror.slot:mx.slot,play=seqplaying?active:255,q=queued(),focus=mx.focus>=30&&mx.focus<38?mx.focus-30:255,rebuild=0,columns[20],*rows=(uint8_t *)0xAD00;char name[17];
 n=5;pg=0;mask=0;mixer_pad_pages[!!MIXER_LINK_VIEW]=0;
 if(!pad_names_valid||cachedpage!=pg||cachedmask!=mask||cacheddevice!=!!MIXER_LINK_VIEW)rebuild=1;
 if(!MIXER_LINK_VIEW&&pad_names_valid&&mx.name[0]&&memcmp(pad_names[active],mx.name,5)){pad_names_valid=0;rebuild=1;}
 if(!pad_names_valid||cacheddevice!=!!MIXER_LINK_VIEW){for(i=0;i<8;i++){
  memset(name,0,17);if(MIXER_LINK_VIEW){if(linkmirror.namesvalid&(1<<i))memcpy(name,linkmirror.names[i],16);}else {getname(i,name);if(i==active&&mx.name[0])memcpy(name,mx.name,17);}
  if(!name[0])strcpy(name,MIXER_LINK_VIEW&&!(linkmirror.namesvalid&(1<<i))?"WAIT":"EMPTY");memcpy(pad_names[i],name,5);mixfill();}
 }
 if(!rebuild&&mx.padcache&&pad_image_playing==play&&pad_image_queued==q&&cachedfocus==focus)goto publish;
 mixer_pad_restore();memset(columns,0,20);
 if(rebuild){for(i=0;i<5;i++)slots[i]=i;
  memset(rows,0,320);
  for(i=0;i<5;i++){uint8_t s=slots[i],y;if(s>=8)continue;
   for(y=0;y<16;y++){uint16_t at=(uint16_t)y*20+i*4;
    if(y>=1&&y<=5){uint8_t g=digits[s][y-1],k;for(k=0;k<3;k++)if(g&(4>>k)){uint8_t x=14+k;rows[at+x/8]|=128>>(x&7);}}
    else if(y>=7&&y<14)for(j=0;j<4;j++){uint8_t c=pad_names[s][j],g=(c>=32&&c<=90)?mixerfont[c-32][y-7]:0,k;for(k=0;k<5;k++)if(g&(16>>k)){uint8_t x=4+j*6+k;rows[at+x/8]|=128>>(x&7);}}
    if((y&3)==3)mixfill();
   }mixfill();
  }outline(focus,1);memset(columns,1,20);
 }else {
  if(pad_image_playing!=play){changed(pad_image_playing,columns);changed(play,columns);}
  if(pad_image_queued!=q){changed(pad_image_queued,columns);changed(q,columns);}
  if(!mx.padcache){changed(play,columns);changed(q,columns);}
  if(cachedfocus!=focus){outline(cachedfocus,0);outline(focus,1);changed(cachedfocus,columns);changed(focus,columns);}
 }
 toggle(play);if(q!=play)toggle(q);if(ui_font_upload_pending)ui_transition_begin();upload(padbank,columns);
 if(q<8&&column(q)!=255){toggle(q);memset(columns,0,20);changed(q,columns);upload(padbank^1,columns);toggle(q);}
 if(q!=play)toggle(q);toggle(play);
 pad_names_valid=1;cachedpage=pg;cachedmask=mask;cacheddevice=!!MIXER_LINK_VIEW;cachedfocus=focus;pad_image_playing=play;pad_image_queued=q;padflash_slot=q;padflash_started=sys_time;mx.padcache=MIXER_LINK_VIEW?(linkmirror.slot==active&&linkmirror.pending==q):(mx.slot==active&&mx.pending==q);if(!mx.padcache)dirty=1;
 publish:
 memset(canvas+14*20,0,20);text(0,14,MIXER_LINK_VIEW?"LINKED":"LOCAL",0);text(9,14,"5 PATTERNS",0);
 if(play<8&&column(play)==255)text(14,14,"P>",0);if(q<8&&column(q)==255)text(17,14,"Q>",0);
 for(i=0;i<40;i++)canvas[15*20+i]=padtile(i,padbank);

 if(padflash_off&&q<8){uint8_t col=column(q);if(col!=255)for(i=0;i<2;i++)for(j=0;j<4;j++)canvas[(uint16_t)(15+i)*20+col+j]=padtile(i*20+col+j,padbank^1);}
 if(!n)text(0,16,"ALL PADS HIDDEN",0);
}

/* One horizontal pad sequence: local pads, then a negotiated peer's pads.
   Visibility filtering never changes the logical launch slot. */
void mixer_pads_move(int8_t delta) BANKED {uint8_t n,total=MIXER_LINK_AVAILABLE?10:5,id=(MIXER_LINK_VIEW?5:0)+mx.focus-30;
 for(n=0;n<total;n++){uint8_t device,slot,bit;id=(id+(delta<0?total-1:1))%total;device=id/5;slot=id%5;bit=20+slot;
  if(slot<5){if(device!=!!MIXER_LINK_VIEW){mixer_device=device;pad_names_valid=0;mx.padcache=0;}mx.focus=30+slot;return;}
 }
}

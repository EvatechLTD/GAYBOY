#pragma bank 60
#include "api.h"
#include "mixer_shared.h"
#include "mixer_pads.h"
#include "link_control.h"
#include "mixer_font.h"
extern uint8_t mixer_hidden[8],mixer_device;
extern __at (0xACC4) uint8_t pad_image_playing;
extern __at (0xACC5) uint8_t pad_image_queued;
__at (0xAE40) uint8_t pad_names[8][5];
__at (0xAE90) static uint8_t slots[4];
__at (0xAE94) static uint8_t cachedpage;
__at (0xAE95) static uint8_t cachedmask;
__at (0xAE96) static uint8_t cacheddevice;
__at (0xACFA) uint8_t padbank;
__at (0xACC0) uint16_t padflash_started;
__at (0xACC2) uint8_t padflash_off;
__at (0xACC3) uint8_t padflash_slot;
static uint8_t padtile(uint8_t tile,uint8_t bank){return bank?(tile<24?168+tile:180+tile):(tile<32?64+tile:128+tile);}
static uint8_t column(uint8_t slot){uint8_t i;for(i=0;i<4;i++)if(slots[i]==slot)return i*5;return 255;}
static uint8_t hidden(void){uint8_t *p=mixer_hidden+mixer_device*4;return (p[2]>>4)|(p[3]<<4);}
static uint8_t queued(void){return mixer_device?linkmirror.pending:mx.pending;}
static void text(uint8_t x,uint8_t y,const char *s,uint8_t inv){uint8_t *d=canvas+(uint16_t)y*20+x;while(*s&&x++<20)*d++=*s++-32+(inv?96:0);}
static void padmap(uint8_t slot,uint8_t bank){uint8_t row,x,col=column(slot),ids[5];uint16_t at;if(col==255)return;
 for(row=0;row<2;row++){at=(uint16_t)(14+row)*20+col;for(x=0;x<5;x++){ids[x]=padtile(row*20+col+x,bank);visible[at+x]=canvas[at+x]=ids[x];}ui_upload_map(0x9800U+(uint16_t)(14+row)*32+col,ids,5);mixfill();}
}
void mixer_pad_restore(void) BANKED {if(padflash_off){padflash_off=0;padmap(padflash_slot,padbank);}}
void mixer_tick(void) BANKED {uint8_t off,q=queued();if(navopen){padflash_off=0;return;}
 if(page!=18||q>=8||!mx.padcache||q!=padflash_slot){mixer_pad_restore();return;}
 off=((uint16_t)(sys_time-padflash_started)>>4)&1;if(off!=padflash_off){padflash_off=off;padmap(q,padbank^off);}
}
static void toggle(uint8_t slot){uint8_t x,y,col=column(slot),*rows=(uint8_t *)0xAD00;if(col==255)return;
 for(y=0;y<16;y++){for(x=0;x<5;x++)rows[(uint16_t)y*20+col+x]^=255;if((y&3)==3)mixfill();}
}
static void changed(uint8_t slot,uint8_t *columns){uint8_t x,col=column(slot);if(col==255)return;for(x=0;x<5;x++)columns[col+x]=1;}
static void upload(uint8_t bank,uint8_t *columns){uint8_t k,tx,y,buf[16],*src,*dst,*rows=(uint8_t *)0xAD00;
 for(k=0;k<2;k++)for(tx=0;tx<20;tx++)if(columns[tx]){src=rows+(k?160:0)+tx;dst=buf;for(y=0;y<8;y++){*dst++=*src;*dst++=*src;src+=20;}ui_upload_tile(padtile(k*20+tx,bank),buf,0);mixfill();}
}
void mixer_pads_render(void) BANKED {uint8_t i,j,n=0,pg=0,mask=hidden(),play=mixer_device?linkmirror.slot:mx.slot,q=queued(),rebuild=0,columns[20],*rows=(uint8_t *)0xAD00;char name[17];
 /* Determine the page from the focused logical pad after visibility filters. */
 for(i=0;i<8;i++)if(!(mask&(1<<i))){if(mx.focus==30+i)pg=n/4;n++;}
 if(mx.focus<30||mx.focus>=38)pg=pad_names_valid?cachedpage:0;
 if(pg>=(n+3)/4)pg=0;
 if(!pad_names_valid||cachedpage!=pg||cachedmask!=mask||cacheddevice!=mixer_device)rebuild=1;
 if(!mixer_device&&pad_names_valid&&mx.name[0]&&memcmp(pad_names[play],mx.name,5)){pad_names_valid=0;rebuild=1;}
 if(!pad_names_valid||cacheddevice!=mixer_device){for(i=0;i<8;i++){
  memset(name,0,17);if(mixer_device){if(linkmirror.namesvalid&(1<<i))memcpy(name,linkmirror.names[i],16);}else {getname(i,name);if(i==play&&mx.name[0])memcpy(name,mx.name,17);}
  if(!name[0]){name[0]='1'+i;name[1]=0;}memcpy(pad_names[i],name,5);mixfill();}
 }
 if(!rebuild&&mx.padcache&&pad_image_playing==play&&pad_image_queued==q)goto publish;
 mixer_pad_restore();memset(columns,0,20);
 if(rebuild){uint8_t count=0;memset(slots,255,4);for(i=0;i<8;i++)if(!(mask&(1<<i))){if(count/4==pg)slots[count%4]=i;count++;}
  memset(rows,0,320);
  for(i=0;i<4;i++){uint8_t s=slots[i],y;if(s>=8)continue;
   for(y=0;y<16;y++){uint16_t at=(uint16_t)y*20+i*5;rows[at]=128;rows[at+4]=1;if(!y||y==15)memset(rows+at,255,5);
    else if(y>=4&&y<11)for(j=0;j<5;j++){uint8_t c=pad_names[s][j],g=(c>=32&&c<=90)?mixerfont[c-32][y-4]:0,k;for(k=0;k<5;k++)if(g&(16>>k)){uint8_t x=5+j*6+k;rows[at+x/8]|=128>>(x&7);}}
    if((y&3)==3)mixfill();
   }mixfill();
  }memset(columns,1,20);
 }else {changed(pad_image_playing,columns);changed(pad_image_queued,columns);changed(play,columns);changed(q,columns);}
 toggle(play);if(q!=play)toggle(q);if(ui_font_upload_pending)ui_transition_begin();upload(padbank,columns);
 if(q<8&&column(q)!=255){toggle(q);memset(columns,0,20);changed(q,columns);upload(padbank^1,columns);toggle(q);}
 if(q!=play)toggle(q);toggle(play);
 pad_names_valid=1;cachedpage=pg;cachedmask=mask;cacheddevice=mixer_device;pad_image_playing=play;pad_image_queued=q;padflash_slot=q;padflash_started=sys_time;mx.padcache=mixer_device?(linkmirror.slot==play&&linkmirror.pending==q):(mx.slot==play&&mx.pending==q);if(!mx.padcache)dirty=1;
 publish:
 memset(canvas+12*20,0,20);text(0,12,"PATTERNS",0);canvas[12*20+10]=('0'+(n?pg+1:0))-32;text(11,12,"/",0);canvas[12*20+12]=('0'+((n+3)/4))-32;
 if(column(play)==255)text(14,12,"P>",0);if(q<8&&column(q)==255)text(17,12,"Q>",0);
 memset(canvas+13*20,0,20);for(i=0;i<4;i++)if(slots[i]<8)canvas[13*20+i*5+2]='1'+slots[i]-32+(mx.focus==30+slots[i]?96:0);
 for(i=0;i<40;i++)canvas[14*20+i]=padtile(i,padbank);
 if(padflash_off&&q<8){uint8_t col=column(q);if(col!=255)for(i=0;i<2;i++)for(j=0;j<5;j++)canvas[(uint16_t)(14+i)*20+col+j]=padtile(i*20+col+j,padbank^1);}
 memset(canvas+20,0,20);if(mx.focus>=30&&mx.focus<38){i=mx.focus-30;memset(name,0,17);if(mixer_device)memcpy(name,linkmirror.names[i],16);else getname(i,name);name[16]=0;text(0,1,name,0);}
 if(!n)text(0,16,"ALL PADS HIDDEN",0);
}

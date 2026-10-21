#pragma bank 60
#pragma opt_code_speed
#include "api.h"
extern const uint8_t limits[26];
extern uint8_t edited[4],lastcc,lastvalue;
void cc_apply(uint8_t c,uint8_t n,uint8_t x) BANKED {uint8_t i,v,mask;if(!syncmode){seqirqdirty=1;if(n==107)seqirqready=0;else if(n==50||n==63||n==120||n==123)seqirqready&=~(1<<c);}lastcc=n;lastvalue=x;edited[c]=1;dirty=1;
 if(n==120||n==123){keycount[c]=0;stop(c);held[c]=255;return;}if(n==64){if(c==2&&waveengine){enginesustain(x>=64);return;}sustain[c]=x>=64;if(!sustain[c]&&held[c]==255)stop(c);return;}
 if(n>=112&&n<=126)return;
 if(n<41||n>119)return;
 if(n>=70&&n<=101){i=n-70;if(!custom){stagewave();custom=1;}mask=customwave[i>>1];v=x>>3;customwave[i>>1]=(i&1)?((mask&0xf0)|v):((mask&15)|(v<<4));wavepending=1;return;}
 if(n==67||n==68){if(c==2&&waveengine)return;if(c<3){if(n==67)rawfreq[c]=(rawfreq[c]&0x780)|x;else rawfreq[c]=(rawfreq[c]&127)|((uint16_t)(x>>3)<<7);if(c==0){if(!pulsekickleft){NR13_REG=rawfreq[c];NR14_REG=(param[c][8]<<6)|(rawfreq[c]>>8);}}else if(c==1){NR23_REG=rawfreq[c];NR24_REG=(param[c][8]<<6)|(rawfreq[c]>>8);}else{NR33_REG=rawfreq[c];NR34_REG=(param[c][8]<<6)|(rawfreq[c]>>8);}}return;}
 if(n==69){if(x>=64)play(c,held[c]==255?basepitch[c]:held[c],velocity[c]?velocity[c]:127);return;}
 if(n==102){if(x<100)load(c,x);return;}
 if(n==103){panic();return;}
 if(n>=104&&n<=106){v=x>>4;if(n==104)master=(master&0x70)|v;else if(n==105)master=(master&7)|(v<<4);else vin=(x>=64)?0x88:0;globals();return;}
 if(n==107){power=x>=64;globals();return;}
 if(n>=108&&n<=111){c=n-108;mask=(1<<c)|(0x10<<c);route&=~mask;if(x&1)route|=1<<c;if(x&2)route|=0x10<<c;globals();return;}
 if(n>66)return;i=n-41;v=((uint16_t)x*(limits[i]+1))>>7;param[c][i]=v;
 if(i==21){mask=(1<<c)|(0x10<<c);route&=~mask;if(v&1)route|=1<<c;if(v&2)route|=0x10<<c;globals();}
 else if(i>=10&&i<=13){if(i==10)master=(master&0x70)|v;if(i==11)vin=(vin&0x80)|(v?8:0);if(i==12)master=(master&7)|(v<<4);if(i==13)vin=(vin&8)|(v?128:0);globals();}
 else if(i==14){custom=0;wavepending=1;}
 else if(i==23){sustain[c]=v;if(!v&&held[c]==255)stop(c);}
 else if(i==24){if(v)stop(c);}
 else if(i==22){if(v)stop(c);}
 else liveparam(c,i);
}

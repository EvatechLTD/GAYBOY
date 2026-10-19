#pragma bank 59
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
extern __at (0xAC6C) uint16_t seqstepunits;
extern __at (0xAC6E) uint16_t seqgateunits[7];
extern uint8_t seqgate[7];
void seq_clear_release(uint8_t track) BANKED;
uint32_t seq_gate_length(uint16_t units,uint8_t duration,uint8_t gate) BANKED;
/* Native pulse onsets avoid the generic instrument/FX dispatch stack. */
void seq_pulse_fire(uint8_t c,const uint8_t *e) BANKED {uint8_t i,j,n,v,pan,mask,bit=1<<c,fired=0;
 if(!syncmode){__critical {seqirqready&=~bit;if((seqirqfired&bit)&&seqirqstep[c]==seqposition[c]&&seqirqnote[c]==e[1])fired=bit;seqirqfired&=~bit;}}
 v=(mx.magic!=0xD3||mx.level[c]==127)?e[2]:mixer_velocity(c,e[2]);
 if(!v){seq_clear_release(c);return;}
 n=keycount[c];if(seqowned[c])for(i=0;i<n;i++)if(keystack[c][i]==seqowned[c]-1){for(j=i;j+1<n;j++){keystack[c][j]=keystack[c][j+1];keyvel[c][j]=keyvel[c][j+1];}keycount[c]=n-1;break;}
 seqsource[c]=seqposition[c];seqowned[c]=e[1];
 if(e[3]==1)seqgateleft[c]=seqgateunits[c];
 else if(seqgate[c]==100&&e[3]==2)seqgateleft[c]=(uint32_t)seqstepunits<<1;
 else if(seqgate[c]==100&&e[3]==4)seqgateleft[c]=(uint32_t)seqstepunits<<2;
 else if(seqgate[c]==100&&e[3]==8)seqgateleft[c]=(uint32_t)seqstepunits<<3;
 else seqgateleft[c]=seq_gate_length(seqstepunits,e[3],seqgate[c]);
 if(!seqgateleft[c])seqgateleft[c]=1;
 pan=mx.magic==0xD3?mx.pan[c]:3;param[c][21]=pan;
 if(c||!pulsekickleft){mask=c?0x22:0x11;route&=~mask;if(!param[c][9]){if(pan&1)route|=mask&15;if(pan&2)route|=mask&240;}NR51_REG=route;}
 if(!syncmode)seqirqsuppress=fired;
 if(!keycount[c]){keycount[c]=1;keystack[c][0]=e[1]-1;keyvel[c][0]=v;play(c,e[1]-1,v);}
 else keyevent(c,e[1]-1,v);
 if(!syncmode)seqirqsuppress=0;
}

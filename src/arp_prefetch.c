#pragma bank 47
#include "api.h"
#include "arp_prefetch.h"
extern uint8_t arp_active_mask,editbuffer_reading,chord[3][16];
extern uint16_t pattern_generation;
uint8_t arp_irq_future_needed(uint8_t c,uint8_t target) BANKED;
uint8_t arp_irq_future_stage(uint8_t c,uint8_t target,uint8_t next,uint8_t count,const uint8_t *indices,uint16_t swaps,uint16_t gen,uint8_t *cache) BANKED;
extern uint16_t editbuffer_swaps;
extern uint8_t editbuffer_valid;
static const uint8_t prefetch_bits[8]={1,2,4,8,16,32,64,128};
void eval_prepare_chord(uint8_t c,uint8_t position,EvalChord *out,uint8_t *indices) BANKED {uint16_t i,count,duration,remaining=1;uint8_t data[4],*e,low[4],rank,j,n,onset=0,total=0;out->next=(uint8_t)seqlength[c];count=seq_event_count(c);memset(out->bits,0,16);memset(low,255,4);for(i=0;i<count;i++){seq_event_get(c,i,data);e=data;duration=e[3]?e[3]:256;{uint16_t next=out->next?out->next:256,end=e[0]+duration;if(e[0]>position&&e[0]<next)next=e[0];if(end>position&&end<next)next=end;out->next=next;}if(e[1]&&e[0]<=position&&(uint16_t)position<e[0]+duration){n=e[1]-1;if(!(out->bits[n>>3]&prefetch_bits[n&7])){total++;for(rank=0;rank<4&&n>low[rank];rank++);if(rank<4){for(j=3;j>rank;j--){low[j]=low[j-1];out->vel[j]=out->vel[j-1];if(indices)indices[j]=indices[j-1];}low[rank]=n;out->vel[rank]=e[2];if(indices)indices[rank]=i;if(!rank)remaining=duration-(position-e[0]);}}out->bits[n>>3]|=prefetch_bits[n&7];if(e[0]==position)onset=1;mixfill();}if((i&3)==3)mixfill();}
 if(out->next>=seqlength[c])out->next=0;out->count=total;out->duration=remaining;out->step=position;out->valid=1;out->onset=onset; }

static uint8_t prefetch_busy;
void arp_prefetch_chords(void) BANKED{uint8_t c,target,reading,indices[4];uint16_t swaps,gen;EvalChord future;
 if(prefetch_busy||!editbuffer_valid)return;prefetch_busy=1;reading=editbuffer_reading;editbuffer_reading=1;
 for(c=0;c<3;c++)if((arp_active_mask&(1<<c))&&eval_chordnext[c]!=255){
  target=eval_chordnext[c];if(!arp_irq_future_needed(c,target))continue;swaps=editbuffer_swaps;gen=pattern_generation;
  eval_prepare_chord(c,target,&future,indices);
  if(swaps!=editbuffer_swaps||gen!=pattern_generation||eval_chordnext[c]!=target)continue;
  memcpy(&eval_loopchord[c],&future,sizeof(EvalChord));eval_loopgeneration[c]=gen;eval_looplength[c]=seqlength[c];
  arp_irq_future_stage(c,target,future.next,(future.onset||memcmp(future.bits,chord[c],16))?future.count:0,indices,swaps,gen,(uint8_t *)&eval_loopchord[c]);
 }
 editbuffer_reading=reading;prefetch_busy=0;
}

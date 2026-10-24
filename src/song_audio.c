#pragma bank 3
#pragma opt_code_speed
#include "api.h"
#include "mixer_shared.h"
#include "resident.h"
#include "song_audio.h"
#include "smooth_playback.h"
#include "mod_bypass.h"
extern const uint16_t notes[140];
extern uint8_t globalmod[10],seqtilesready;
void seq_audition_stop(void) BANKED;
static uint8_t audible(uint8_t c){uint8_t solos=seqsolo&95;if(drumsolomask)solos|=64;return !(seqmuted&(1<<c))&&(!solos||(solos&(1<<c)));}
extern uint8_t noisepatch[2][5],pulsekickpatch[8],tablemode[4],pattern_dirty,lfo_irq_mask;
extern volatile uint8_t editirq_enabled,editirq_running,drum_irq_active;
extern uint8_t editbuffer_reading;
extern uint16_t pattern_generation;
void editbuffer_reset(void) BANKED;
void storage_sorted_dirty(void) BANKED;
void editirq_clock_reset(void) NONBANKED;
void arp_irq_reset(void) NONBANKED;
void editirq_wave_capture(uint8_t *out) BANKED;
void wave_cache_invalidate(void) BANKED;
uint8_t eval_drum_pan(uint8_t c) BANKED;
uint8_t song_playing;
__at (0xA000) SongScene song_scenes[5];
__at (0xA300) SongRuntime song_runtime;
/* Exclusive read-only playback cache replaces the two edit snapshots only
   while editing and the ordinary sequencer are disabled. Persistent song
   data, clips, presets and resident notes never live in this cache. */
#define CACHE_BASE 0xAD00U
#define CACHE_SIZE 4864U
#define R song_runtime
static uint8_t cache_put(uint16_t at,const uint8_t *p,uint8_t n){if(at+n>CACHE_SIZE){R.error=2;return 0;}
 __critical{SWITCH_RAM_MBC5(2);memcpy((void *)(CACHE_BASE+at),p,n);SWITCH_RAM_MBC5(0);}return 1;}
void song_cache_get(uint16_t at,uint8_t *p,uint8_t n) BANKED {uint8_t b[16];
 /* Destination may itself be bank-zero SRAM. Stage through WRAM before
    restoring its bank; a direct memcpy would write the wrong RAM bank. */
 __critical{SWITCH_RAM_MBC5(2);memcpy(b,(void *)(CACHE_BASE+at),n);SWITCH_RAM_MBC5(0);}memcpy(p,b,n);
}
__at (0xA3C0) volatile uint8_t song_qread;
__at (0xA3C1) volatile uint8_t song_qwrite;
__at (0xA3C2) volatile uint16_t song_hwclock;
__at (0xA3C4) volatile uint16_t song_hwwait;
__at (0xA3C6) volatile uint32_t song_actual_position;
__at (0xA3CA) volatile uint8_t song_actual_scene;
__at (0xA3CB) volatile uint8_t song_actual_done;
__at (0xA3CC) volatile uint16_t song_underruns;
__at (0xA3CE) uint16_t song_qpointer;
#define QBASE ((uint8_t *)0xA500)
#define QSIZE 192U
#define QCOUNT 8
#define QHEADER 9
#define SIM ((uint8_t *)0xA3D0)
__at (0xA3B0) static uint8_t *write_pointer;
__at (0xA3B2) static uint8_t *write_frame;
__at (0xA3B4) static uint8_t write_count;
__at (0xA3B6) static SongScene *current_scene;
static uint8_t *frame(void){return QBASE+(uint16_t)song_qwrite*QSIZE;}
static void put_reg(uint8_t reg,uint8_t value){uint8_t *p=write_pointer;if(write_count>=91){R.error=2;return;}*p++=reg;*p++=value;write_pointer=p;write_count++;if(reg==0x21)SIM[0x11]=value;}
static void begin_frame(void){uint8_t *p=frame();write_frame=p;write_pointer=p+QHEADER;write_count=0;p[0]=R.clock;p[1]=R.clock>>8;}
static void finish_frame(void){uint8_t *p=write_frame;p[2]=write_count;p[3]=R.scene;memcpy(p+4,(const void *)&R.position,4);p[8]=R.done;song_qwrite=(song_qwrite+1)&7;}
static void plan_prefetch(void){SongClip c;if(R.need){if(R.prefetch<R.total)song_read(R.prefetch,&c);else{memset(&c,0,sizeof(c));c.pad=255;}R.next=c;R.need=0;}}
static uint8_t scale(uint16_t x){uint8_t q=x>>7;return q+((uint8_t)((x&127)+q)>=127);}
static uint8_t compile_track(uint8_t c,SongScene *s,uint16_t *used){uint16_t step,i,n=seqeventcounts[c],d;uint8_t e[4],packet[18],previous[18],count,j,k,note,onset,vel,amp;uint16_t f;int16_t v;
 s->begin[c]=*used;previous[0]=previous[1]=255;
 for(step=0;step<s->length[c];step++){
  memset(packet,0,18);packet[0]=step;count=onset=0;
  for(i=0;i<n;i++){seq_event_get(c,i,e);d=e[3]?e[3]:256U;
   if(!e[1]||e[0]>step||step>=(uint16_t)e[0]+d)continue;
   if(e[0]==step)onset=1;note=e[1]-1;
   for(j=0;j<count&&packet[2+j*4]<e[1];j++);
   if(j<count&&packet[2+j*4]==e[1])continue;
   if(s->mode[c]&&count==4){R.error=3;return 0;}
   if(j>=4)continue;if(count<4)count++;
   for(k=count-1;k>j;k--)memcpy(packet+2+k*4,packet+2+(k-1)*4,4);
   vel=mixer_velocity(c,e[2]);amp=scale((uint16_t)param[c][1]*vel);
   if(c==2){amp=vel?(vel>84?1:vel>42?2:3):0;if(amp&&param[2][15]){amp+=param[2][15]-1;if(amp>3)amp=3;}else amp=0;amp<<=5;}else amp<<=4;
   if(!audible(c)||param[c][9]||param[c][22]||!power)amp=0;
   v=note+(c==2?12:0);if(v<0)v=0;if(v>139)v=139;f=notes[v];
   if(finepitch[c])f=fine_apply(f,c,0);if(!(s->lfo&(1<<c))&&coarsepitch[c][0])f=coarse_apply(c,f);
   packet[2+j*4]=e[1];packet[3+j*4]=amp;packet[4+j*4]=f;packet[5+j*4]=f>>8;
  }
  if(!s->mode[c]&&count>1)count=1;packet[1]=count;
  if(step==0||onset||packet[1]!=previous[1]||memcmp(packet+2,previous+2,count*4)){
   if(!cache_put(*used,packet,2+count*4))return 0;*used+=2+count*4;memcpy(previous,packet,18);
  }
 }
 s->end[c]=*used;return 1;
}
static uint8_t compile_drums(SongScene *s,uint16_t *used){uint16_t step,i,n=seqeventcounts[6],left[2]={0,0},d,kg,f;uint8_t vel[2]={0,0},p[6],e[4],v[5],j,changed,ended,a,b,vol,pan,has_kick=0;
 s->begin[3]=*used;
 for(i=0;i<n;i++){seq_event_get(6,i,e);if(e[1]<11||e[1]>13){R.error=4;return 0;}if(e[1]==13)has_kick=1;}
 if(has_kick&&seqeventcounts[0]){R.error=5;return 0;}
 for(j=5;j<8;j++)if(!mod_bypass&&(MOD_LEVEL(j)||evalpatch[j][EV_DEPTH]||coarsepitch[j][1])){R.error=3;return 0;}
 s->drum[0]=(pulsekickpatch[4]<<4)|(pulsekickpatch[7]<<3)|pulsekickpatch[5];s->drum[1]=(pulsekickpatch[2]<<6)|((64-pulsekickpatch[6])&63);
 f=eval_drum_pitch(7,notes[pulsekickpatch[1]]);s->drum[2]=f;s->drum[3]=0xC0|(f>>8);
 for(j=0;j<3;j++){pan=eval_drum_pan(5+j);s->drum[4+j]=j==2?(pan&1?1:0)|(pan&2?16:0):(pan&1?8:0)|(pan&2?128:0);}
 for(step=0;step<s->length[3];step++){
  memset(p,0,6);p[0]=step;changed=ended=0;
  for(j=0;j<2;j++)if(left[j]&&!--left[j])ended=1;
  for(i=0;i<n;i++){seq_event_get(6,i,e);if(e[0]!=step||!audible(6)||((drummutemask&(1U<<(e[1]-1)))||(drumsolomask&&!(drumsolomask&(1U<<(e[1]-1))))))continue;d=e[3]?e[3]:256U;
   if(e[1]<13){j=e[1]-11;left[j]=d;vel[j]=mixer_velocity(6,e[2]);changed=1;}
   else{p[1]|=4;vol=mixer_velocity(6,e[2]);p[4]=(scale((uint16_t)eval_drum_level(7,pulsekickpatch[0])*vol)<<4)|pulsekickpatch[3];kg=(uint16_t)pulsekickpatch[6]*4;if(!kg)kg=4;if((uint32_t)R.units*d<kg)kg=R.units*d;p[5]=kg;}
  }
  a=!!left[0];b=!!left[1];if(b)p[1]|=32;
  if((changed||ended)&&(a||b)){
   for(j=0;j<5;j++)v[j]=a&&b?(noisepatch[0][j]+noisepatch[1][j]+1)>>1:noisepatch[b?1:0][j];
   if(a&&b)vol=scale(((uint16_t)eval_drum_level(5,noisepatch[0][0])*vel[0]+(uint16_t)eval_drum_level(6,noisepatch[1][0])*vel[1]+127)>>1);
   else vol=scale((uint16_t)eval_drum_level(b?6:5,v[0])*vel[b?1:0]);
   p[1]|=1;p[2]=vol?(vol<<4)|v[4]:8;p[3]=eval_drum_pitch(b?6:5,(v[1]<<4)|(v[3]<<3)|v[2]);
  }else if(ended||(!step&&!a&&!b))p[1]|=2;
  if(p[1]&7){if(!cache_put(*used,p,6))return 0;*used+=6;}
 }
 s->end[3]=*used;return 1;
}
static int8_t shape(uint8_t phase){uint8_t n;static const uint8_t sine[17]={0,6,12,19,24,30,36,41,45,49,53,56,59,61,63,64,64};
 switch(globalmod[4]){case 1:return (phase>>1)-64;case 2:return phase<128?64:-64;case 3:return (int8_t)((phase&0xC0)*73+37)/2;case 4:n=phase&63;if(phase&64)n=64-n;n=sine[n>>2];return phase&128?-(int8_t)n:n;default:return phase<128?(int16_t)phase-64:191-(int16_t)phase;}}
static int8_t amount(int8_t depth,int8_t value){int16_t x=(int16_t)depth*value;return x<0?-((-x)>>6):x>>6;}
static uint8_t compile_scene(uint8_t pad,uint16_t *used){SongScene *s=&song_scenes[pad];uint8_t c,i,div,point[2],*p;uint16_t scale;uint32_t numerator,denominator,q,period;
 if(seqmode||seqswing!=50||monomode||polymode||waveengine||seqeventcounts[3]||seqeventcounts[4]||seqeventcounts[5]){R.error=3;return 0;}
 memset(s,0,sizeof(*s));s->master=master;s->power=power;
 for(c=0;c<4;c++)s->length[c]=seqlength[c==3?6:c];
 for(c=0;c<3;c++){
  if(tablemode[c]||param[c][17]&&c==2||MOD_LEVEL(c)){R.error=3;return 0;}
  p=evalpatch[c];s->mode[c]=p[EV_MODE];s->order[c]=p[EV_ORDER];s->retrig[c]=p[EV_RETRIGGER];
  if(s->mode[c]>1||(s->mode[c]&&(s->order[c]==3||s->order[c]==7||s->order[c]==8||s->order[c]==9))){R.error=3;return 0;}
  if(!mod_bypass&&(p[EV_DEPTH]||coarsepitch[c][1])){
   if(p[EV_DEPTH]&&!(p[EV_SOURCES]&1)||coarsepitch[c][1]&&!coarsepitch[c][2]||finepitch[c]){R.error=3;return 0;}
   s->lfo|=1<<c;s->points[c]=*used;
   for(i=0;i<64;i++){point[0]=amount((int8_t)p[EV_DEPTH],shape(i<<2));point[1]=(int8_t)coarsepitch[c][0]+amount((int8_t)coarsepitch[c][1],shape(i<<2));if(!cache_put(*used,point,2))return 0;*used+=2;}
  }
  if(!p[EV_CLOCK]){period=960UL<<p[EV_DIV];scale=R.bpm;if(p[EV_TIMING]==1)period=period*2/3;else if(p[EV_TIMING]==2)period=period*3/2;}
  else{period=(uint32_t)(p[6]|((uint16_t)p[7]<<8))*1024UL;scale=1000;}
  if(period<scale*2UL)period=scale*2UL;s->arpwhole[c]=period/scale;s->arprest[c]=period%scale;s->arpscale[c]=scale;
  s->patch[c][0]=(param[0][4]<<4)|(param[0][5]<<3)|param[0][6];s->patch[c][1]=c==2?param[2][16]:(param[c][0]<<6)|param[c][7];
  s->patch[c][2]=(param[c][2]<<3)|param[c][3];s->patch[c][3]=128|(param[c][8]<<6);s->patch[c][4]=(mx.pan[c]&1?1<<c:0)|(mx.pan[c]&2?16<<c:0);
  if(!compile_track(c,s,used))return 0;
 }
 editirq_wave_capture(s->wave);
 if(!compile_drums(s,used))return 0;
 div=globalmod[6];if(globalmod[7]){denominator=globalmod[8]==1?160:globalmod[8]==2?360:240;if(div<=8)numerator=(uint32_t)R.bpm<<(8-div);else{numerator=R.bpm;denominator<<=div-8;}q=(numerator<<16)/denominator;}else q=(uint32_t)globalmod[5]*15360UL;
 s->lfowhole=q>>16;s->lfofraction=q;return 1;
}

static uint8_t rank_next(uint8_t c){SongVoice *v=(SongVoice *)&R.voice[c];SongScene *s=current_scene;uint8_t i=v->index,n=v->count,rank;
 if(n<2){v->index=0;return 0;}
 switch(s->order[c]){
 case 1:rank=n-1-i%n;break;
 case 2:case 4:case 10:rank=i%(n*2-2);if(rank>=n)rank=n*2-2-rank;if(s->order[c]==4)rank=n-1-rank;else if(s->order[c]==10)rank=rank&1?n-1-(rank>>1):rank>>1;break;
 case 3:case 7:case 8:case 9:rank=DIV_REG%n;break;
 case 5:rank=i%n;rank=rank&1?n-1-(rank>>1):rank>>1;break;
 case 6:rank=i%n;rank=rank&1?(n-1)/2+(rank+1)/2:(n-1)/2-rank/2;break;
 default:rank=i%n;break;
 }
 v->index=(i+1)%((s->order[c]==2||s->order[c]==4||s->order[c]==10)?n*2-2:n);return rank;
}
static uint16_t arp_wait(uint8_t c){SongScene *s=current_scene;SongVoice *v=(SongVoice *)&R.voice[c];uint16_t n=s->arpwhole[c];
 if(s->arprest[c]>v->residual){n++;v->residual+=s->arpscale[c]-s->arprest[c];}else v->residual-=s->arprest[c];return n?n:1;
}
static void off(uint8_t c){R.voice[c].note=0;R.voice[c].volume=0;if(c==0){put_reg(0x12,8);put_reg(0x14,128);}else if(c==1){put_reg(0x17,8);put_reg(0x19,128);}else put_reg(0x1a,0);}
static uint16_t pitch(uint8_t c,uint8_t note,uint16_t ordinary){uint8_t point[2];int16_t n,f;SongScene *s=current_scene;
 if(!(s->lfo&(1<<c)))return ordinary;song_cache_get(s->points[c]+(uint16_t)(R.lfophase>>2)*2,point,2);n=note+(int8_t)point[1];if(n<0)n=0;if(n>127)n=127;if(c==2)n+=12;f=notes[n]+(int8_t)point[0];return f<0?0:f>2047?2047:f;
}
void song_emit(uint8_t c,uint8_t index) BANKED {SongVoice *v=(SongVoice *)&R.voice[c];SongScene *s=current_scene;uint8_t *p=v->tones[index],i,vol=p[1],*h=s->patch[c];uint16_t f= pitch(c,p[0]-1,p[2]|((uint16_t)p[3]<<8));
 v->note=p[0];v->volume=vol;v->pitch=f;route=(route&~((1<<c)|(16<<c)))|h[4];put_reg(0x25,route);
 if(c==0){put_reg(0x10,h[0]);put_reg(0x11,h[1]);put_reg(0x12,vol?vol|h[2]:8);put_reg(0x13,f);put_reg(0x14,h[3]|(f>>8));}
 else if(c==1){put_reg(0x16,h[1]);put_reg(0x17,vol?vol|h[2]:8);put_reg(0x18,f);put_reg(0x19,h[3]|(f>>8));}
 else{put_reg(0x1a,0);for(i=0;i<16;i++)put_reg(0x30+i,s->wave[i]);put_reg(0x1b,h[1]);put_reg(0x1c,vol);put_reg(0x1a,128);put_reg(0x1d,f);put_reg(0x1e,h[3]|(f>>8));}
}
static void group(uint8_t c){SongVoice *v=(SongVoice *)&R.voice[c];SongScene *s=current_scene;uint8_t h[2],previous=v->count;
 if(v->cursor>=s->end[c])return;song_cache_get(v->cursor,h,2);if(h[0]!=v->step)return;
 v->cursor+=2;v->count=h[1];if(!v->count){off(c);v->wait=65535U;return;}
 song_cache_get(v->cursor,(uint8_t *)v->tones,v->count*4);v->cursor+=v->count*4;
 if(!s->mode[c]||s->retrig[c]||!previous){v->index=0;v->residual=0;song_emit(c,s->mode[c]?rank_next(c):0);v->wait=s->mode[c]?arp_wait(c):65535U;}
}
void song_drum_emit(void) BANKED {uint8_t p[6],*h=current_scene->drum;SongScene *s=current_scene;
 if(R.drumcursor>=s->end[3])return;song_cache_get(R.drumcursor,p,6);if(p[0]!=R.drumstep)return;R.drumcursor+=6;
 if(p[1]&1){route=(route&~0x88)|h[p[1]&32?5:4];put_reg(0x25,route);put_reg(0x20,0);put_reg(0x21,p[2]);put_reg(0x22,p[3]);put_reg(0x23,128);}
 else if(p[1]&2){if(!(SIM[0x11]&7)){put_reg(0x21,8);put_reg(0x23,128);}}
 if(p[1]&4){R.kickleft=p[5]?p[5]:256;route=(route&~0x11)|h[6];put_reg(0x25,route);put_reg(0x10,h[0]);put_reg(0x11,h[1]);put_reg(0x12,p[4]);put_reg(0x13,h[2]);put_reg(0x14,h[3]);}
}
static void quiet(void){off(0);off(1);off(2);put_reg(0x21,8);put_reg(0x23,128);R.kickleft=0;}
static void scene(uint8_t pad){uint8_t c;SongScene *s;
 R.scene=pad;if(pad>=5){quiet();return;}s=&song_scenes[pad];current_scene=s;put_reg(0x26,s->power?128:0);put_reg(0x24,s->master);
 if(R.kickleft){put_reg(0x12,8);put_reg(0x14,128);R.kickleft=0;}
 R.drumstep=0;R.drumcursor=s->begin[3];song_drum_emit();
 for(c=0;c<3;c++){R.voice[c].step=R.voice[c].count=R.voice[c].index=0;R.voice[c].residual=0;R.voice[c].wait=65535U;R.voice[c].cursor=s->begin[c];group(c);}
}
static void next_clip(void){
 uint8_t same=R.scene==R.next.pad&&R.current.start+R.current.length==R.next.start;R.current=R.next;R.clipindex=R.prefetch;R.prefetch++;R.need=1;if(!same)scene(R.current.pad);
}
static void step(void){uint8_t c;SongScene *s;
 {R.position++;
  if(R.position>=R.end){
   if(!R.loop){quiet();R.done=1;return;}
   R.position=0;R.next=R.first;R.prefetch=0;R.need=0;
   if(!R.next.start){next_clip();return;}R.current.pad=255;scene(255);return;
  }
  if(R.scene<5&&R.position>=R.current.start+R.current.length&&(R.need||R.prefetch>=R.total||R.position!=R.next.start||R.scene!=R.next.pad)){scene(255);}
  if(!R.need&&R.prefetch<R.total&&R.position==R.next.start){uint8_t same=R.scene==R.next.pad&&R.current.start+R.current.length==R.next.start;next_clip();if(!same)return;}
 }
 if(R.scene>=5)return;s=current_scene;
 if((uint16_t)R.drumstep+1>=s->length[3]){R.drumstep=0;R.drumcursor=s->begin[3];}else R.drumstep++;song_drum_emit();
 for(c=0;c<3;c++){if((uint16_t)R.voice[c].step+1>=s->length[c]){R.voice[c].step=0;R.voice[c].cursor=s->begin[c];}else R.voice[c].step++;group(c);}
}
static void deadline(uint8_t boundary){uint16_t wait,phase=R.phase;uint8_t c;
 if(boundary){R.stepleft=R.units;while(phase>=R.bpm){phase-=R.bpm;R.stepleft--;}R.stepleft+=R.remainder>phase;}
 wait=R.stepleft;if(!wait)wait=1;if(R.kickleft&&R.kickleft<wait)wait=R.kickleft;
 if(R.scene<5){for(c=0;c<3;c++)if(current_scene->mode[c]&&R.voice[c].count&&R.voice[c].wait<wait)wait=R.voice[c].wait;if(current_scene->lfo&&R.lfoleft<wait)wait=R.lfoleft;}
 R.wait=wait?wait:1;
}
void song_audio_due(void) BANKED {uint8_t c,boundary=0;uint16_t elapsed=R.clock-R.last,f,before;SongScene *s;R.last=R.clock;
 if(R.done){R.wait=65535U;return;}
 if(R.kickleft){if(R.kickleft<=elapsed){R.kickleft=0;put_reg(0x12,8);put_reg(0x14,128);}else R.kickleft-=elapsed;}
 if(R.stepleft>elapsed)R.stepleft-=elapsed;else R.stepleft=0;
 for(c=0;c<3;c++)if(R.voice[c].wait>elapsed)R.voice[c].wait-=elapsed;else R.voice[c].wait=0;
 if(R.lfoleft>elapsed)R.lfoleft-=elapsed;else R.lfoleft=0;
 R.phase+=elapsed*R.bpm;
 while(R.phase>=15360U){R.phase-=15360U;boundary=1;step();if(R.done){R.wait=65535U;return;}}
 if(R.scene<5){s=current_scene;
  for(c=0;c<3;c++)if(s->mode[c]&&R.voice[c].count&&!R.voice[c].wait){song_emit(c,rank_next(c));R.voice[c].wait=arp_wait(c);}
  if(!R.lfoleft){R.lfoleft=8;before=R.lfofraction;R.lfofraction+=s->lfofraction;R.lfophase+=s->lfowhole+(R.lfofraction<before);before=R.lfofraction;R.lfofraction+=s->lfofraction;R.lfophase+=s->lfowhole+(R.lfofraction<before);
   if(s->lfo)for(c=0;c<3;c++)if((s->lfo&(1<<c))&&R.voice[c].note){f=pitch(c,R.voice[c].note-1,R.voice[c].pitch);if(f!=R.voice[c].pitch){R.voice[c].pitch=f;if(c==0){put_reg(0x13,f);put_reg(0x14,(s->patch[c][3]&127)|(f>>8));}else if(c==1){put_reg(0x18,f);put_reg(0x19,(s->patch[c][3]&127)|(f>>8));}else{put_reg(0x1d,f);put_reg(0x1e,(s->patch[c][3]&127)|(f>>8));}}}
  }
 }
 deadline(boundary);
}
void song_program(uint8_t *p,uint8_t n) __naked {p;n;
 __asm
 or a,a
 ret z
 ld b,a
 ld h,d
 ld l,e
song_program_loop$:
 ld a,(hl+)
 ld c,a
 ld a,(hl+)
 ldh (c),a
 dec b
 jr nz,song_program_loop$
 ret
 __endasm;
}
/* The IRQ commits only a prepared byte program and its published playhead.
   No clip searches, pitch math, banked SRAM reads or scene reconstruction. */
void song_audio_commit(void) BANKED __naked {
 __asm
 ld a,(#_song_actual_done)
 or a,a
 jr nz,song_commit_ended$
 ld a,(#_song_qread)
 ld b,a
 ld a,(#_song_qwrite)
 cp b
 jr nz,song_commit_ready$
 ld hl,#_song_underruns
 inc (hl)
 jr nz,song_commit_empty$
 inc hl
 inc (hl)
song_commit_empty$:
 ld hl,#_song_hwwait
 ld (hl),#1
 inc hl
 ld (hl),#0
 ret
song_commit_ended$:
 ld hl,#_song_hwwait
 ld (hl),#255
 inc hl
 ld (hl),#255
 ret
song_commit_ready$:
 ld a,(#_song_qpointer)
 ld l,a
 ld a,(#_song_qpointer+1)
 ld h,a
 inc hl
 inc hl
 ld a,(hl+)
 ld b,a
 ld a,(hl+)
 ld (#_song_actual_scene),a
 ld de,#_song_actual_position
 .rept 4
 ld a,(hl+)
 ld (de),a
 inc de
 .endm
 ld a,(hl+)
 ld (#_song_actual_done),a
 ld a,b
 ld d,h
 ld e,l
 call _song_program
 ld a,(#_song_qpointer)
 ld l,a
 ld a,(#_song_qpointer+1)
 ld h,a
 ld de,#192
 add hl,de
 ld a,h
 cp #0xab
 jr nz,song_commit_pointer$
 ld hl,#0xa500
song_commit_pointer$:
 ld a,l
 ld (#_song_qpointer),a
 ld a,h
 ld (#_song_qpointer+1),a
 ld a,(#_song_qread)
 inc a
 and #7
 ld (#_song_qread),a
 ld b,a
 ld a,(#_song_actual_done)
 or a,a
 jr nz,song_commit_ended$
 ld a,(#_song_qwrite)
 cp b
 jr z,song_commit_empty$
 ld a,(hl+)
 ld c,a
 ld b,(hl)
 ld a,(#_song_hwclock)
 ld e,a
 ld a,(#_song_hwclock+1)
 ld d,a
 ld a,c
 sub a,e
 ld c,a
 ld a,b
 sbc a,d
 ld b,a
 or a,c
 jr nz,song_commit_wait$
 inc bc
song_commit_wait$:
 ld a,c
 ld (#_song_hwwait),a
 ld a,b
 ld (#_song_hwwait+1),a
 ret
 __endasm;
}
void song_irq_tick(uint8_t elapsed) NONBANKED __naked {elapsed;
 __asm
 ld e,a
 or a,a
 ret z
 ld hl,#_song_hwclock
 ld a,(hl)
 add a,e
 ld (hl+),a
 ld a,(hl)
 adc a,#0
 ld (hl+),a
 ld a,(hl)
 sub a,e
 ld (hl+),a
 ld a,(hl)
 sbc a,#0
 ld (hl-),a
 jr c,song_due$
 or (hl)
 ret nz
song_due$:
 ld e,#b_song_audio_commit
 ld hl,#_song_audio_commit
 call ___sdcc_bcall_ehl
 ret
 __endasm;
}
static void fill(uint8_t budget){while(budget--&&!R.done&&((song_qwrite+1)&7)!=song_qread){
 R.clock+=R.wait;begin_frame();song_audio_due();plan_prefetch();finish_frame();
}}
void song_timer(void) NONBANKED {song_irq_tick(1);}
void song_start(uint8_t smooth) BANKED {uint8_t original=mx.slot,mask=0,c,err;uint16_t i,n,used=0,bpm=seqbpm;SongClip clip;
 if(song_playing){song_stop();return;}if(seqplaying){song_view.error=6;return;}if(syncmode){song_view.error=7;return;}
 n=song_count();if(!n){song_view.error=1;return;}
 song_pick_clear();seq_audition_stop();if(pattern_dirty)sparse_snapshot(original);panic();memset((void *)&R,0,sizeof(R));R.origin=original;R.scene=255;R.bpm=bpm;R.units=15360U/bpm;R.remainder=15360U-R.units*bpm;
 for(i=0;i<n;i++){song_read(i,&clip);if(clip.pad>=5||!clip.length||clip.start+clip.length<clip.start){song_view.error=8;return;}mask|=1<<clip.pad;}
 if(smooth)smooth_playback_begin();else smooth_playback_preparing=1;
 for(c=0;c<5;c++)if(mask&(1<<c)){if(!sparse_restore(c)){R.error=3;break;}seqbpm=bpm;if(!compile_scene(c,&used))break;}
 err=R.error;sparse_restore(original);seqbpm=bpm;smooth_playback_preparing=0;editbuffer_reset();arp_irq_reset();editirq_enabled=editirq_running=lfo_irq_mask=drum_irq_active=0;seqirqdirty=seqirqready=seqirqfired=0;
 if(err){song_view.error=err;smooth_playback_update();return;}
 R.end=song_end();R.total=n;R.loop=song_loop();song_read(0,(SongClip *)&R.first);R.current=R.first;
 R.prefetch=R.first.start?0:1;R.next=R.first;
 if(R.prefetch<n)song_read(R.prefetch,(SongClip *)&R.next);
 song_qread=song_qwrite=0;song_qpointer=0xa500;song_hwclock=0;song_hwwait=1;song_actual_done=0;song_actual_scene=255;song_actual_position=0;song_underruns=0;memset(SIM,0,48);
 R.clock=R.last=R.phase=0;R.lfoleft=8;R.stepleft=R.units+(R.remainder!=0);R.prepared=mask;R.wait=R.stepleft;song_view.error=0;
 begin_frame();scene(R.first.start?255:R.first.pad);deadline(0);finish_frame();fill(6);
 __critical{remove_TIM(engine_timer);add_TIM(song_timer);editirq_clock_reset();TMA_REG=TIMA_REG=252;IF_REG&=~TIM_IFLAG;seqplaying=song_playing=1;TAC_REG=4;song_audio_commit();}
 dirty=1;
}
void song_stop(void) BANKED {uint8_t original=R.origin;uint16_t bpm=R.bpm;
 __critical{TAC_REG=0;remove_TIM(song_timer);add_TIM(engine_timer);song_playing=0;seqplaying=0;}NR12_REG=NR22_REG=NR42_REG=8;NR14_REG=NR24_REG=NR44_REG=128;NR30_REG=0;panic();editbuffer_reset();storage_sorted_dirty();sparse_restore(original);wave_cache_invalidate();seqbpm=bpm;seqirqdirty=1;seqdrawvalid=seqtilesready=0;song_view.selected=SONG_NONE;song_view.error=0;song_pick_clear();rd=wr;st=count=0;
 *(uint8_t *)0xA475=0;*(uint8_t *)0xA4D0=0;smooth_playback_update();dirty=1;
}
void song_service(void) BANKED {uint32_t position,width;if(song_actual_done){song_stop();return;}fill(2);
 position=song_actual_position;if(!smooth_playback_active&&song_view.cursor!=position){song_view.cursor=position;width=256;if(position<song_view.base||position-song_view.base>=width)dirty=1;}
}

extern volatile uint8_t padqueue[32],padread,padwrite,padsampled;
void song_run(void) BANKED {uint8_t p,edge;uint16_t frame=sys_time;
 while(song_playing){song_service();if(!song_playing)break;
  while(padread!=padwrite){p=padqueue[padread];padread=(padread+1)&31;edge=p&~lastpad;song_input(p,edge);lastpad=p;if(!song_playing)break;}
  if(!song_playing)break;
  if(frame!=sys_time){frame=sys_time;lastframe=frame;
   if(!smooth_playback_active&&dirty){fill(6);dirty=0;song_render();ui_flush();}
  }
 }
}

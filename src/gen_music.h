#ifndef GAYBOY_GEN_MUSIC_H
#define GAYBOY_GEN_MUSIC_H
/* Pure musical rules, shared with the host regression harness.
   Steps are sixteenths; bar length follows the sequencer meter. */
static const uint8_t gen_scales[3][7]={
 {0,2,4,5,7,9,11},{0,2,3,5,7,8,10},{0,2,3,5,7,9,10}
};
static const uint8_t gen_progressions[4][4]={
 {0,0,0,0},{0,3,0,3},{0,4,5,3},{1,4,0,0}
};
static uint8_t gen_hash(uint16_t seed,uint16_t position){
 uint16_t h=seed^(position*0x9E37U+0x7F4AU);
 h^=h>>7;h*=0x2C1BU;h^=h>>9;h*=0x297DU;h^=h>>8;return (uint8_t)h;
}
/* Variation is audible in a one-bar loop. It changes dynamics only, and its
   seed never moves attacks out of the selected rhythm. */
static uint8_t gen_drum_variation(uint8_t velocity,uint16_t step,uint8_t variation,uint16_t seed){
 if(variation&&gen_hash(seed,step)%4<variation){
  velocity=(uint16_t)velocity*3/4;if(!velocity)velocity=1;
 }
 return velocity;
}
static uint8_t gen_bar_steps(uint8_t beats,uint8_t denominator){return beats*(16/denominator);}
/* Euclidean hits are distributed evenly, including a hit at the origin.
   Rotation moves onsets later; it never changes the hit count. */
static uint8_t gen_onset(uint16_t step,uint8_t bar,uint8_t rhythm,uint8_t hits,uint8_t rotation){
 uint8_t p=(step%bar+bar-rotation%bar)%bar;
 switch(rhythm){
 case 0:return !(p%4);
 case 1:return !(p%2);
 case 2:return 1;
 case 3:return p%4==2;
 case 4:return p%16==0||p%16==6||p%16==12;
 case 5:return p%16==4||p%16==12;
 default:if(hits>bar)hits=bar;return ((uint16_t)p*hits)%bar<hits;
 }
}
static uint16_t gen_chord_steps(uint8_t bar,uint8_t change){
 return change<2?4U<<change:(uint16_t)bar*(1U<<(change-2));
}
/* CHANGES follows harmonic rhythm; other masks remain independent of pitch. */
static uint8_t gen_rhythm_onset(uint16_t step,uint8_t bar,uint8_t rhythm,uint8_t hits,uint8_t rotation,uint8_t change){
 return rhythm==7?!(step%gen_chord_steps(bar,change)):gen_onset(step,bar,rhythm,hits,rotation);
}
/* Simultaneous diatonic triads, in root position or either inversion.
   Pentatonic melody uses natural-minor harmony so triads retain their quality. */
static void gen_chord_notes(uint16_t step,uint8_t bar,uint8_t progression,uint8_t change,
 uint8_t root,uint8_t scale,uint8_t octave,uint8_t inversion,uint8_t variation,
 uint16_t seed,uint8_t *notes){
 static const uint8_t thirds[]={0,2,4,7,9};
 uint8_t i,degree,chord=gen_progressions[progression][(step/gen_chord_steps(bar,change))%4];
 uint16_t pitch[3];
 if(scale==3)scale=1;
 if(variation&&gen_hash(seed,step)%4<variation)inversion=(inversion+1+gen_hash(seed,step+1)%2)%3;
 for(i=0;i<3;i++){
  degree=chord+thirds[i+inversion];
  pitch[i]=(octave+1U)*12+root+(degree/7)*12+gen_scales[scale][degree%7];
 }
 while(pitch[2]>127)for(i=0;i<3;i++)pitch[i]-=12;
 for(i=0;i<3;i++)notes[i]=(uint8_t)pitch[i]+1;
}
/* A two-bar motif repeats over the harmony. Variation changes pitch only,
   at weak positions near phrase endings; rhythm remains an explicit mask. */
static uint8_t gen_pitch(uint16_t step,uint8_t bar,uint8_t role,uint8_t progression,
 uint8_t change,uint8_t contour,uint8_t variation,uint8_t root,uint8_t scale,
 uint8_t octave,uint16_t seed){
 uint8_t chord,phase,r,degree,third,index,offset,pc;uint16_t note,motif=step%(bar*2U);
 chord=gen_progressions[progression][(step/gen_chord_steps(bar,change))%4];
 phase=(motif*8)/(bar*2U);r=gen_hash(seed,motif);
 switch(contour){
 case 0:index=0;break;
 case 1:index=phase;break;
 case 2:index=7-phase;break;
 case 3:index=phase<4?phase:7-phase;break;
 default:index=(phase+(r%3))%5;break;
 }
 index+=gen_hash(seed,0)%3;
 if(variation&&step>=bar*2U&&step%bar>=bar*3U/4U&&step%4){
  if(gen_hash(seed,step/bar)%4<variation)index+=(gen_hash(seed,step)%3);
 }
 if(role==1){degree=chord;if(step%4&&index%3==2)degree+=4;}
 else if(role==2)degree=chord+(index%3)*2;
 else if(!(step%4))degree=chord+(index%3)*2;
 else degree=chord+index;
 third=scale==3?1:scale;
 offset=(degree/7)*12+gen_scales[third][degree%7];
 /* Pentatonic removes the two non-pentatonic minor degrees. */
 if(scale==3){pc=offset%12;if(pc==2)offset-=2;else if(pc==8)offset--;}
 note=(octave+1U)*12+root+offset;
 while(note>127)note-=12;
 return (uint8_t)note+1;
}
/* A zero event duration encodes 256 steps in sparse storage. */
static uint8_t gen_duration(uint16_t step,uint16_t length,uint8_t bar,uint8_t rhythm,
 uint8_t hits,uint8_t rotation,uint8_t setting,uint8_t change){
 uint16_t duration=1,next=step+1,limit;
 if(setting<5)duration=1U<<setting;else duration=length-step;
 limit=step+duration;if(limit>length)limit=length;
 while(next<limit&&!gen_rhythm_onset(next,bar,rhythm,hits,rotation,change))next++;
 return (uint8_t)(next-step);
}

#endif

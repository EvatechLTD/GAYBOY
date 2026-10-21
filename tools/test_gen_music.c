#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include "../src/gen_music.h"
int main(void){
 unsigned bar,r,h,rot,s,role,scale,root,oct,contour,progression;
 const unsigned masks[6]={0x1111,0x5555,0xffff,0x4444,0x1041,0x1010};
 for(r=0;r<6;r++)for(s=0;s<16;s++)
  assert(gen_onset(s,16,r,5,0)==!!(masks[r]&(1U<<s)));
 for(bar=1;bar<=96;bar++)for(h=0;h<=bar;h++)for(rot=0;rot<bar;rot++){
  unsigned count=0;
  for(s=0;s<bar;s++)count+=gen_onset(s,bar,6,h,rot);
  assert(count==h);
 }
 for(bar=1;bar<=96;bar++)for(r=0;r<7;r++)for(s=0;s<256;s++){
  unsigned setting;
  if(!gen_onset(s,bar,r,5,3))continue;
  for(setting=0;setting<6;setting++){
   unsigned d=gen_duration(s,256,bar,r,5,3,setting,2),j;
   if(!d)d=256;
   assert(d>=1&&s+d<=256);
   for(j=s+1;j<s+d;j++)assert(!gen_onset(j,bar,r,5,3));
   if(setting<5)assert(d<=(1U<<setting));
  }
 }
 /* Every scale, key and register remains in scale, including high octaves. */
 for(scale=0;scale<4;scale++)for(root=0;root<12;root++)for(oct=0;oct<8;oct++)
 for(role=0;role<3;role++)for(contour=0;contour<5;contour++)
 for(progression=0;progression<4;progression++)for(s=0;s<256;s++){
  unsigned n=gen_pitch(s,16,role,progression,2,contour,3,root,scale,oct,999);
  unsigned pc=(n-1+120-root)%12,mask;
  assert(n>=1&&n<=128);
  mask=scale==0?0xab5:scale==1?0x5ad:scale==2?0x6ad:0x4a9;
  assert(mask&(1U<<pc));
 }
 /* Dynamics variation works in the first bar and responds to adjacent seeds. */
 {
  unsigned altered=0,different=0;
  for(s=0;s<16;s+=2){
   assert(gen_drum_variation(100,s,0,1)==100);
   altered+=gen_drum_variation(100,s,1,1)!=100;
   different+=gen_drum_variation(100,s,1,1)!=gen_drum_variation(100,s,1,2);
   assert(gen_drum_variation(1,s,3,1)>=1);
  }
  assert(altered&&different);
 }
 /* Triads preserve quality and all three pitches through both inversions. */
 for(scale=0;scale<4;scale++)for(root=0;root<12;root++)for(oct=0;oct<8;oct++)
 for(progression=0;progression<4;progression++)for(contour=0;contour<3;contour++)for(s=0;s<64;s+=16){
  uint8_t notes[3];unsigned i,mode=scale==3?1:scale;
  unsigned degree=gen_progressions[progression][s/16],mask=0,expected=0;
  gen_chord_notes(s,16,progression,2,root,scale,oct,contour,0,1,notes);
  assert(notes[0]>=1&&notes[0]<notes[1]&&notes[1]<notes[2]&&notes[2]<=128);
  for(i=0;i<3;i++){
   mask|=1U<<((notes[i]-1+120-root)%12);
   expected|=1U<<gen_scales[mode][(degree+i*2)%7];
  }
  assert(mask==expected);
 }
 for(bar=1;bar<=96;bar++)for(h=0;h<5;h++)for(s=0;s<256;s++){
  if(!gen_rhythm_onset(s,bar,7,0,0,h))continue;
  assert(s%gen_chord_steps(bar,h)==0);
  {unsigned duration=gen_duration(s,256,bar,7,0,0,5,h);
   if(!duration)duration=256;
   assert(duration==(gen_chord_steps(bar,h)<256-s?gen_chord_steps(bar,h):256-s));
  }
 }
 /* Minor and Dorian share i; their IV distinguishes the sixth degree. */
 {
  uint8_t minor[3],dorian[3];
  gen_chord_notes(0,16,1,2,9,1,3,0,0,1,minor);
  gen_chord_notes(0,16,1,2,9,2,3,0,0,1,dorian);
  for(s=0;s<3;s++)assert(minor[s]==dorian[s]);
  gen_chord_notes(16,16,1,2,9,1,3,0,0,1,minor);
  gen_chord_notes(16,16,1,2,9,2,3,0,0,1,dorian);
  assert(dorian[0]==minor[0]&&dorian[1]==minor[1]+1&&dorian[2]==minor[2]);
 }
 /* Harmonic rhythm includes quarter/half notes and meter-aware bars. */
 assert(gen_chord_steps(12,0)==4&&gen_chord_steps(12,1)==8);
 assert(gen_chord_steps(12,2)==12&&gen_chord_steps(12,3)==24&&gen_chord_steps(12,4)==48);
 for(s=0;s<16;s+=4){
  unsigned n=gen_pitch(s,16,1,2,0,3,0,0,0,2,1);
  assert((n-1)%12==gen_scales[0][gen_progressions[2][s/4]]);
 }
 /* Stable motifs repeat exactly when harmony is held and variation is off. */
 for(role=0;role<3;role++)for(s=0;s<224;s++)
  assert(gen_pitch(s,16,role,0,2,3,0,9,1,3,7)==
         gen_pitch(s+32,16,role,0,2,3,0,9,1,3,7));
 /* Bass downbeats follow the actual progression's roots. */
 for(scale=0;scale<3;scale++)for(progression=0;progression<4;progression++)for(s=0;s<64;s+=4){
  unsigned n=gen_pitch(s,16,1,progression,2,3,0,0,scale,2,1);
  assert((n-1)%12==gen_scales[scale][gen_progressions[progression][s/16]]);
 }
 puts("PASS: rhythm masks, all Euclidean counts/rotations, bounded nonoverlapping lengths, all keys/scales/registers, motif repetition, bass harmony, triads and inversions");
 return 0;
}

#ifndef GAYBOY_SEQUENCER_LIMITS_H
#define GAYBOY_SEQUENCER_LIMITS_H
#define SEQ_NOTE_MINIMUM(c) (((c)==2||(c)==TWINK_TRACK)?24:36)
/* The native period counters reach C2 (pulse) and C1 (Wave). The DSP
   renderer's 2048 Hz output requires its existing B5 pitch ceiling. */
static uint8_t seq_note_maximum(uint8_t c){
 if(experimental_mode){if(c==2&&(evalwaveactive?expconfig[0]:evalwavefx[0]))return 83;if(c==4&&eval_mono_fx()[0])return 83;}
 return 127;
}
#endif

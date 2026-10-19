/* Three cells per strip; ROM-only labels, no audio-path work. */
static const char *mixer_drum_name(uint8_t kit,uint8_t voice){
 static const char * const amen[]={"KK1","KK2","KK3","SC1","SC2","HC1","CL1","KC1","CY1","PSH","NHH","NSN","PK"};
 static const char * const drums[]={"KIK","SNR","CHH","OHH","CLP","LTM","HTM","PRC","---","---","NHH","NSN","PK"};
 if(!kit)return amen[voice];if(voice==7)return kit==1||kit==3?"COW":kit==4?"TAM":"RIM";return drums[voice];
}

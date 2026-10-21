static const uint8_t native_ids[4][20]={{0,1,2,3,4,5,6,7,8,21,25},{0,1,2,3,7,8,21,25},{14,15,16,8,21,25},{1,2,3,18,19,20,7,8,21,25}};
static const uint8_t native_counts[]={11,8,6,10},kickmax[]={15,96,3,7,7,7,64,1},noisemax[]={15,15,7,1,7};
static uint8_t native_value(uint8_t id){if(id==26)return seqgate[selected];if(id==10)return master&7;if(id==12)return(master>>4)&7;if(id==11)return !!(vin&8);if(id==13)return !!(vin&128);return param[selected][id];}
static int16_t clamp(int16_t n,int16_t lo,int16_t hi){return n<lo?lo:n>hi?hi:n;}
static int16_t delta(uint8_t e){return e&J_UP?1:e&J_DOWN?-1:e&J_RIGHT?10:e&J_LEFT?-10:0;}
static uint8_t tone_count(uint8_t c){return c<4?native_counts[c]+4-((c!=2&&evalpatch[c][EV_LEVEL_MODE]==128)?2:0):(c==7?13:10)-(evalpatch[c][EV_LEVEL_MODE]==128?1:0);}

static uint8_t tone_id(uint8_t c,uint8_t row){uint8_t i,n=0,id;const uint8_t kick[]={0,1,102,2,3,4,5,6,7,106},noise[]={0,1,102,2,3,4,106};if(row<3)return 103+row;row-=3;if(c<4){if(row==1)return 102;row=row<1?row:row-1;for(i=0;i<native_counts[c];i++){id=native_ids[c][i];if(c!=2&&evalpatch[c][EV_LEVEL_MODE]==128&&(id==2||id==3))continue;if(n++==row)return id;}return 25;}for(i=0;i<(c==7?10:7);i++){id=c==7?kick[i]:noise[i];if(evalpatch[c][EV_LEVEL_MODE]==128&&id==(c==7?3:4))continue;if(n++==row)return id;}return 106;}


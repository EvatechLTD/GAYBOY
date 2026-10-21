/* Fixed-width text fields: numeric values align right, labels/sources left. */
static void field_text(uint8_t x,uint8_t y,uint8_t width,const char *s,uint8_t inv,uint8_t right){
 uint8_t n=0,i,*d=canvas+(uint16_t)y*20+x;while(s[n]&&n<width)n++;
 for(i=0;i<width;i++)d[i]=inv?96:0;if(right)d+=width-n;
 for(i=0;i<n;i++)d[i]=s[i]-32+(inv?96:0);
}
static void field_number(uint8_t x,uint8_t y,uint8_t width,int16_t value,uint8_t inv){
 static const uint16_t places[]={10000,1000,100,10,1};char s[7];uint8_t i,n=0,d,started=0;uint16_t v=value<0?0U-(uint16_t)value:value;
 if(value<0)s[n++]='-';for(i=0;i<5;i++){d=0;while(v>=places[i]){v-=places[i];d++;}if(d||i==4)started=1;if(started)s[n++]='0'+d;}s[n]=0;field_text(x,y,width,s,inv,1);
}
static void field_ratio(uint8_t y,uint16_t numerator,uint16_t denominator,uint8_t inv){
 static const uint16_t places[]={100,10,1};char s[8];uint8_t side,i,n=0,d,started;uint16_t value;
 for(side=0;side<2;side++){value=side?denominator:numerator;started=0;for(i=0;i<3;i++){d=0;while(value>=places[i]){value-=places[i];d++;}if(d||i==2)started=1;if(started)s[n++]='0'+d;}if(!side)s[n++]='/';}s[n]=0;field_text(12,y,8,s,inv,1);
}

static void field_center(uint8_t x,uint8_t y,uint8_t width,const char *s,uint8_t inv){uint8_t n=0;while(s[n]&&n<width)n++;field_text(x,y,width,"",inv,0);field_text(x+(width-n)/2,y,n,s,inv,0);}

/* Removed instruments retain inert entry points for legacy tone import. */
void modreset(void){} void monoroute(void){} void monorefresh(void){}
void monoapply(uint8_t c){(void)c;} void monostart(uint8_t n,uint8_t v){(void)n;(void)v;}
void monocut(void){} void monorelease(void){} void modframe(void){}
void monoevent(uint8_t t,uint8_t a,uint8_t b){(void)t;(void)a;(void)b;}
void monoframe(void){} void monoenable(void){} uint8_t monopitch(uint8_t c,uint8_t n){(void)c;return n;}

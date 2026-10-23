#ifndef MOD_BYPASS_H
#define MOD_BYPASS_H
/* Session-wide performance bypass. Saved instrument/modulation data is intact. */
extern uint8_t mod_bypass;
#define MOD_LEVEL(c) (!mod_bypass && evalpatch[c][EV_LEVEL_MODE]==128)
void eval_mod_enable(uint8_t enabled) BANKED;
void eval_mod_refresh_audio(void) BANKED;
#endif

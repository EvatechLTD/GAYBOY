extern volatile uint8_t lfo_irq_mask;
void lfo_irq_prepare(uint8_t force) BANKED;
void lfo_irq_tick(uint8_t elapsed) NONBANKED;
uint8_t lfo_irq_owned(uint8_t c) NONBANKED;
uint8_t lfo_irq_active(void) NONBANKED;
uint16_t lfo_irq_pitch(uint8_t c,uint16_t note) NONBANKED;
void lfo_irq_note(uint8_t c) NONBANKED;

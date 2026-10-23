/* Scale returns1 on success; otherwise a specific, atomic rejection reason. */
static const char *seq_scale_error(uint8_t code){
 return code==6?"PATTERN EVENT LIMIT":code==3?"/2 NEEDS EVEN STEPS":code==4?"MAX LENGTH 256 STEPS":code==5?"NOTES WOULD OVERLAP":"SELECT NOTES FIRST";
}

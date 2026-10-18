/* SameBoy 1.0.4 browser adapter. SameBoy: Lior Halphon, Expat/MIT license.
 * Compatible function names retain the existing site's input and save UI. */
#include <emscripten/emscripten.h>
#include <stdlib.h>
#include <string.h>
#include "Core/gb.h"
#include "browser_bootrom.h"
#define API EMSCRIPTEN_KEEPALIVE
#define AUDIO_MAX 4096
typedef struct {
 GB_gameboy_t gb;
 uint32_t pixels[160*144];
 int16_t audio[AUDIO_MAX*2];
 unsigned frames,capacity,events;
 uint64_t clocks;
 uint32_t ram_hash;
 GB_palette_t palette;
} Player;
typedef struct { unsigned size; uint8_t *data; } File;
static Player *player(GB_gameboy_t *gb){return GB_get_user_data(gb);}
static uint32_t rgb(GB_gameboy_t *gb,uint8_t r,uint8_t g,uint8_t b){return 0xff000000u|r|(g<<8)|(b<<16);}
static void vblank(GB_gameboy_t *gb,GB_vblank_type_t type){player(gb)->events|=1;}
static void sample(GB_gameboy_t *gb,GB_sample_t *s){
 Player *p=player(gb);
 if(p->frames<p->capacity){
  p->audio[p->frames*2]=s->left;p->audio[p->frames*2+1]=s->right;
  if(++p->frames==p->capacity)p->events|=2;
 }
}
API Player *emulator_new_simple(const uint8_t *rom,unsigned size,int rate,int frames,int curve){
 if(frames<1||frames>AUDIO_MAX)return NULL;
 Player *p=calloc(1,sizeof(*p));if(!p)return NULL;
 GB_init(&p->gb,GB_MODEL_DMG_B);GB_set_user_data(&p->gb,p);
 GB_set_rgb_encode_callback(&p->gb,rgb);GB_set_pixels_output(&p->gb,p->pixels);
 GB_set_vblank_callback(&p->gb,vblank);GB_set_sample_rate(&p->gb,rate);
 GB_set_highpass_filter_mode(&p->gb,GB_HIGHPASS_ACCURATE);
 GB_apu_set_sample_callback(&p->gb,sample);
 GB_load_boot_rom_from_buffer(&p->gb,browser_bootrom,sizeof(browser_bootrom));
 GB_load_rom_from_buffer(&p->gb,rom,size);p->capacity=frames;
 /* Execute the authentic hardware initialization off-screen. Discard its
    logo frames and chime, then let the cartridge take over the LCD. */
 uint64_t startup=0;
 while(!p->gb.boot_rom_finished && startup<8ULL*8388608)startup+=GB_run(&p->gb);
 if(!p->gb.boot_rom_finished){GB_free(&p->gb);free(p);return NULL;}
 uint64_t handoff=0;
 while((GB_safe_read_memory(&p->gb,0xFF40)&0x80) && handoff<6ULL*140448)
  handoff+=GB_run(&p->gb);
 for(unsigned i=0;i<160*144;i++)p->pixels[i]=0xffa1e8d5;
 p->frames=p->events=0;
 return p;
}
API void emulator_delete(Player *p){GB_free(&p->gb);free(p);}
API double emulator_get_ticks_f64(Player *p){return p->clocks/2.0;}
API unsigned emulator_run_until_f64(Player *p,double until){
 if(p->frames==p->capacity)p->frames=0;p->events=0;
 while(p->clocks<(uint64_t)(until*2)&&!p->events)p->clocks+=GB_run(&p->gb);
 if(p->clocks>=(uint64_t)(until*2))p->events|=4;return p->events;
}
API void *get_frame_buffer_ptr(Player *p){return p->pixels;}
API unsigned get_frame_buffer_size(Player *p){return sizeof(p->pixels);}
API void *get_audio_buffer_ptr(Player *p){return p->audio;}
API unsigned get_audio_buffer_capacity(Player *p){return p->frames*4;}
API void emulator_set_bw_palette_simple(Player *p,unsigned type,uint32_t w,uint32_t l,uint32_t d,uint32_t b){
 /* SameBoy stores shades black-to-white and retains the palette pointer. */
 uint32_t colors[5]={b,d,l,w,w};
 for(unsigned i=0;i<5;i++){p->palette.colors[i].r=colors[i];p->palette.colors[i].g=colors[i]>>8;p->palette.colors[i].b=colors[i]>>16;}
 GB_set_palette(&p->gb,&p->palette);
}
#define KEY(name,value) API void set_joyp_##name(Player *p,int down){GB_set_key_state(&p->gb,value,!!down);}
KEY(up,GB_KEY_UP) KEY(down,GB_KEY_DOWN) KEY(left,GB_KEY_LEFT) KEY(right,GB_KEY_RIGHT)
KEY(A,GB_KEY_A) KEY(B,GB_KEY_B) KEY(start,GB_KEY_START) KEY(select,GB_KEY_SELECT)
API unsigned joypad_new(void){return 1;}
API void joypad_delete(unsigned ignored){}
API void emulator_set_default_joypad_callback(Player *p,unsigned ignored){}
static uint8_t *ram(Player *p,size_t *size){return GB_get_direct_access(&p->gb,GB_DIRECT_ACCESS_CART_RAM,size,NULL);}
API File *ext_ram_file_data_new(Player *p){size_t size;ram(p,&size);File *f=calloc(1,sizeof(*f));f->size=size;f->data=malloc(size);return f;}
API void *get_file_data_ptr(File *f){return f->data;}
API unsigned get_file_data_size(File *f){return f->size;}
API void file_data_delete(File *f){free(f->data);free(f);}
/* Public beat links contain data only: a full, version-pinned machine state. */
API File *emulator_beat_file_new(Player *p){
 File *f=calloc(1,sizeof(*f));if(!f)return NULL;
 f->size=GB_get_save_state_size(&p->gb);f->data=malloc(f->size);
 if(!f->data){free(f);return NULL;}GB_save_state_to_buffer(&p->gb,f->data);return f;
}
API int emulator_beat_load(Player *p,const uint8_t *data,unsigned size){
 if(size!=GB_get_save_state_size(&p->gb))return -1;
 int result=GB_load_state_from_buffer(&p->gb,data,size);
 if(!result){p->clocks=0;p->frames=p->events=0;for(unsigned i=0;i<160*144;i++)p->pixels[i]=0xffa1e8d5;}
 return result;
}
API void emulator_write_ext_ram(Player *p,File *f){size_t size;uint8_t *data=ram(p,&size);if(f->size==size)memcpy(f->data,data,size);}
API void emulator_read_ext_ram(Player *p,File *f){size_t size;uint8_t *data=ram(p,&size);if(f->size==size)memcpy(data,f->data,size);}
API int emulator_was_ext_ram_updated(Player *p){
 size_t size;uint8_t *data=ram(p,&size);uint32_t hash=2166136261u;
 for(size_t i=0;i<size;i++)hash=(hash^data[i])*16777619u;
 if(hash==p->ram_hash)return 0;p->ram_hash=hash;return 1;
}
/* Tutorial checkpoints use the core's full machine state, including cart RAM. */
typedef struct { size_t size; uint8_t *data; uint64_t clocks; uint32_t pixels[160*144]; } Checkpoint;
API Checkpoint *emulator_checkpoint_new(Player *p){
 Checkpoint *s=calloc(1,sizeof(*s));if(!s)return NULL;
 s->size=GB_get_save_state_size(&p->gb);s->data=malloc(s->size);
 if(!s->data){free(s);return NULL;}
 GB_save_state_to_buffer(&p->gb,s->data);s->clocks=p->clocks;
 memcpy(s->pixels,p->pixels,sizeof(s->pixels));return s;
}
API int emulator_checkpoint_restore(Player *p,Checkpoint *s){
 int result=GB_load_state_from_buffer(&p->gb,s->data,s->size);
 if(!result){p->clocks=s->clocks;p->frames=p->events=0;memcpy(p->pixels,s->pixels,sizeof(p->pixels));}
 return result;
}
API void emulator_checkpoint_delete(Checkpoint *s){if(s){free(s->data);free(s);}}
/* Read-only ROM observations drive tutorial success conditions. */
API unsigned emulator_observe_mem(Player *p,unsigned address){
 /* CPU bus reads during OAM DMA return the DMA bus byte, not the variable.
    Observe without side effects or bus contention. Tutorial SRAM symbols
    always live in bank zero, even while a pattern copy maps another bank. */
 if(address>=0xA000&&address<0xC000){
  size_t size;uint8_t *data=ram(p,&size);
  return address-0xA000<size?data[address-0xA000]:0;
 }
 return GB_safe_read_memory(&p->gb,address);
}
API unsigned emulator_read_mem(Player *p,unsigned address){return GB_read_memory(&p->gb,address);}
API void emulator_write_mem(Player *p,unsigned address,unsigned value){GB_write_memory(&p->gb,address,value);}
API unsigned emulator_get_wave_frequency(Player *p){return p->gb.apu.wave_channel.sample_length;}
API void emulator_set_sample_rate(Player *p,unsigned rate){GB_set_sample_rate(&p->gb,rate);p->frames=0;}

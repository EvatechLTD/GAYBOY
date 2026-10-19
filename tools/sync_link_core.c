/* SameBoy bit-level cable harness; callbacks match upstream libretro wiring. */
#include <emscripten/emscripten.h>
#include <stdlib.h>
#include <string.h>
#include "Core/gb.h"
#include "Core/memory.h"
#include "browser_bootrom.h"
static GB_gameboy_t machines[2];
static uint64_t clocks[2], target;
static uint32_t pixels[2][160*144];
static bool outgoing[2];
static bool cable_connected=true;
static unsigned edges;
static bool profiling;static unsigned profile[65536];
static unsigned wire_bits,wire_byte,wire_clocks,wire_aborts,wire_unarmed_edges;
static bool wire_active;
static unsigned rx_base,rx_values[256];
static unsigned id(GB_gameboy_t *gb);
static unsigned trace_count;
static struct {unsigned cycle,value;} trace[32768];
static unsigned event_count,watch_boundary,watch_launch,watch_positions,watch_ticks,watch_clock;
static unsigned min_sp[2]={0xffff,0xffff};
static unsigned watch_drum_on,watch_mix_read,watch_mix_write,watch_drum_mix;
static unsigned pcm_pending[2],pcm_buffer[2][2];
static struct {unsigned cycle,side,tag,value,positions,clock,ticks;} events[262144];
static void event(GB_gameboy_t *gb,unsigned tag,unsigned value){
 if(!watch_positions||event_count>=262144)return;
 unsigned i=event_count++;
 events[i].cycle=(unsigned)clocks[id(gb)];events[i].side=id(gb);events[i].tag=tag;events[i].value=value;
 events[i].positions=GB_safe_read_memory(gb,watch_positions)|(GB_safe_read_memory(gb,watch_positions+1)<<8)|(GB_safe_read_memory(gb,watch_positions+6)<<16);
 events[i].clock=GB_safe_read_memory(gb,watch_clock)|(GB_safe_read_memory(gb,watch_clock+1)<<8);
 events[i].ticks=GB_safe_read_memory(gb,watch_ticks)|(GB_safe_read_memory(gb,watch_ticks+1)<<8);
}
static bool writes(GB_gameboy_t *gb,uint16_t addr,uint8_t value){
 if(rx_base&&addr==rx_base+258&&value)event(gb,0x600,(gb->mbc_rom_bank<<16)|gb->pc);
 if(id(gb)==1&&addr==0xffc5)event(gb,0x702,value);
 if(id(gb)==1&&addr==0xffdf)event(gb,0x704,value|(GB_safe_read_memory(gb,0xffe1)<<8));
 if(id(gb)==1&&rx_base&&addr>=rx_base&&addr<rx_base+256)event(gb,0x705,value);
 if(addr==0xffc7)event(gb,0x500,value); /* Oscillator clock due, before wire arbitration. */
 if((addr==0xff14||addr==0xff19||addr==0xff1e||addr==0xff23)&&(value&128))event(gb,addr,value);
 if(watch_drum_on){unsigned side=id(gb);
  if(addr>=watch_drum_on&&addr<watch_drum_on+2&&value==1)pcm_pending[side]|=1u<<(addr-watch_drum_on);
  if(addr==0xff1e&&(value&128)&&gb->pc>=0x4000&&gb->mbc_rom_bank==(watch_drum_mix>>16)){
   unsigned buffer=GB_safe_read_memory(gb,watch_mix_read)&1;
   if(pcm_buffer[side][buffer]){event(gb,0x400,pcm_buffer[side][buffer]);pcm_buffer[side][buffer]=0;}
  }
 }
 if(addr==0xff02&&value==0x81)event(gb,0xff01,GB_safe_read_memory(gb,0xff01));
 if(id(gb)==1&&rx_base&&addr>=rx_base&&addr<rx_base+256)rx_values[(value>=0x80&&value<0xf0)?(0x80|(value&63)):value]++;
 if(id(gb)==1&&addr==0xffe1&&trace_count<32768){trace[trace_count].cycle=(unsigned)clocks[0];trace[trace_count++].value=0x200+value;}
 if(id(gb)==0&&trace_count<32768){
  unsigned tag=0;
  if(addr==0xff02&&value==0x81){
   if(wire_active)wire_aborts++;
   wire_active=true;wire_bits=wire_byte=0;tag=GB_safe_read_memory(gb,0xff01);
  }
  else if((addr==0xff14||addr==0xff19)&&(value&0x80))tag=0x100+(addr==0xff19);
  if(tag){trace[trace_count].cycle=(unsigned)clocks[0];trace[trace_count++].value=tag;}
 }
 return true;
}
static void sample(GB_gameboy_t *gb,GB_sample_t *value){}
static uint32_t rgb(GB_gameboy_t *gb,uint8_t r,uint8_t g,uint8_t b){return 0xff000000u|r|(g<<8)|(b<<16);}
static unsigned id(GB_gameboy_t *gb){return gb == &machines[1];}
static void start(GB_gameboy_t *gb,bool bit){outgoing[id(gb)]=bit;}
static bool end(GB_gameboy_t *gb){unsigned i=id(gb);/* Two internal clocks still sample the peer's data pin. SameBoy's external
   edge API rejects an internally clocked peer, so do not feed it an external
   edge in that case. Electrical clock contention needs real-hardware checks. */
 bool peer_internal=GB_safe_read_memory(&machines[1-i],0xff02)&1;
 if(cable_connected&&!peer_internal&&!(GB_safe_read_memory(&machines[1-i],0xff02)&0x80))wire_unarmed_edges++;
 bool bit=!cable_connected?true:peer_internal?outgoing[1-i]:GB_serial_get_data_bit(&machines[1-i]);
 if(cable_connected&&!peer_internal)GB_serial_set_data_bit(&machines[1-i],outgoing[i]);edges++;
 if(i==0){wire_byte=(wire_byte<<1)|outgoing[i];if(++wire_bits==8){wire_active=false;if((wire_byte>=0x80&&wire_byte<0xf0)||wire_byte==0xf8)wire_clocks++;}}
 return bit;}
EMSCRIPTEN_KEEPALIVE void link_init(const uint8_t *rom,unsigned size){
 for(unsigned i=0;i<2;i++){
  GB_init(&machines[i],GB_MODEL_DMG_B);
  GB_load_rom_from_buffer(&machines[i],rom,size);
  GB_load_boot_rom_from_buffer(&machines[i],browser_bootrom,sizeof(browser_bootrom));
  GB_set_pixels_output(&machines[i],pixels[i]);
  GB_set_sample_rate(&machines[i],48000);
  GB_apu_set_sample_callback(&machines[i],sample);
  GB_set_rgb_encode_callback(&machines[i],rgb);
  GB_set_serial_transfer_bit_start_callback(&machines[i],start);
  GB_set_serial_transfer_bit_end_callback(&machines[i],end);
  GB_set_write_memory_callback(&machines[i],writes);
  size_t size;void *ram=GB_get_direct_access(&machines[i],GB_DIRECT_ACCESS_CART_RAM,&size,NULL);memset(ram,0,size);
 }
}
/* Replace one endpoint to compare with a reference clock ROM. */
EMSCRIPTEN_KEEPALIVE void link_load_rom(unsigned i,const uint8_t *rom,unsigned size){
 GB_load_rom_from_buffer(&machines[i],rom,size);
 GB_reset(&machines[i]);
}
EMSCRIPTEN_KEEPALIVE const uint32_t *link_pixels(unsigned i){return pixels[i];}
EMSCRIPTEN_KEEPALIVE void link_run(unsigned frames){
 target+=(uint64_t)frames*140448;
 while(clocks[0]<target||clocks[1]<target){unsigned i=clocks[0]>clocks[1];unsigned pc=machines[i].pc,bank=pc<0x4000?0:machines[i].mbc_rom_bank;
  unsigned address=pc|(pc<0x4000?0:bank<<16);
  if(watch_drum_mix&&address==watch_drum_mix&&pcm_pending[i]){
   pcm_buffer[i][GB_safe_read_memory(&machines[i],watch_mix_write)&1]=pcm_pending[i];pcm_pending[i]=0;
  }
  if(watch_positions&&i==1&&(address==watch_boundary||address==watch_launch))event(&machines[i],address==watch_boundary?0x300:0x301,GB_safe_read_memory(&machines[i],0xac8a));
  if(watch_positions&&machines[i].sp<min_sp[i])min_sp[i]=machines[i].sp;
  unsigned delta=GB_run(&machines[i]);clocks[i]+=delta;if(profiling&&i==0&&pc<0x8000&&bank<64)profile[bank*1024+((pc&0x3fff)>>4)]+=delta;}
}
EMSCRIPTEN_KEEPALIVE void link_watch_events(unsigned boundary,unsigned launch,unsigned positions,unsigned ticks,unsigned clock){watch_boundary=boundary;watch_launch=launch;watch_positions=positions;watch_ticks=ticks;watch_clock=clock;event_count=0;wire_unarmed_edges=0;}
EMSCRIPTEN_KEEPALIVE unsigned link_event_count(void){return event_count;}
EMSCRIPTEN_KEEPALIVE unsigned link_min_sp(unsigned i){return min_sp[i];}
EMSCRIPTEN_KEEPALIVE void link_watch_pcm(unsigned on,unsigned read,unsigned write,unsigned mix){
 watch_drum_on=on;watch_mix_read=read;watch_mix_write=write;watch_drum_mix=mix;
 memset(pcm_pending,0,sizeof(pcm_pending));memset(pcm_buffer,0,sizeof(pcm_buffer));
}
EMSCRIPTEN_KEEPALIVE const void *link_events(void){return events;}
EMSCRIPTEN_KEEPALIVE unsigned link_read(unsigned i,unsigned at){return GB_safe_read_memory(&machines[i],at);}
EMSCRIPTEN_KEEPALIVE void link_write(unsigned i,unsigned at,unsigned value){GB_write_memory(&machines[i],at,value);}
/* Fixture access to bank-zero state must not depend on the RAM bank at the
   exact CPU instruction where a host frame ends. Never use for link I/O. */
EMSCRIPTEN_KEEPALIVE unsigned link_state_read(unsigned i,unsigned at){
 if(at>=0xa000&&at<0xc000){size_t size;uint8_t *ram=GB_get_direct_access(&machines[i],GB_DIRECT_ACCESS_CART_RAM,&size,NULL);return ram[at-0xa000];}
 return GB_safe_read_memory(&machines[i],at);
}
EMSCRIPTEN_KEEPALIVE void link_state_write(unsigned i,unsigned at,unsigned value){
 if(at>=0xa000&&at<0xc000){size_t size;uint8_t *ram=GB_get_direct_access(&machines[i],GB_DIRECT_ACCESS_CART_RAM,&size,NULL);ram[at-0xa000]=value;return;}
 GB_write_memory(&machines[i],at,value);
}
EMSCRIPTEN_KEEPALIVE void link_set_connected(unsigned connected){cable_connected=connected!=0;}
EMSCRIPTEN_KEEPALIVE void link_key(unsigned i,unsigned key,unsigned down){GB_set_key_state(&machines[i],key,down);}
EMSCRIPTEN_KEEPALIVE unsigned link_edges(void){return edges;}
EMSCRIPTEN_KEEPALIVE unsigned link_pc(unsigned i){return machines[i].pc;}
EMSCRIPTEN_KEEPALIVE unsigned link_unarmed_edges(void){return wire_unarmed_edges;}
EMSCRIPTEN_KEEPALIVE unsigned link_wire_clocks(void){return wire_clocks;}
EMSCRIPTEN_KEEPALIVE unsigned link_wire_aborts(void){return wire_aborts;}
EMSCRIPTEN_KEEPALIVE void link_watch_rx(unsigned base){rx_base=base;}
EMSCRIPTEN_KEEPALIVE unsigned link_rx_count(unsigned value){return rx_values[value];}
EMSCRIPTEN_KEEPALIVE unsigned link_trace_count(void){return trace_count;}
EMSCRIPTEN_KEEPALIVE unsigned link_trace_cycle(unsigned i){return trace[i].cycle;}
EMSCRIPTEN_KEEPALIVE unsigned link_trace_value(unsigned i){return trace[i].value;}

EMSCRIPTEN_KEEPALIVE void link_profile_start(void){memset(profile,0,sizeof(profile));profiling=true;}
EMSCRIPTEN_KEEPALIVE unsigned link_profile(unsigned index){profiling=false;return profile[index];}

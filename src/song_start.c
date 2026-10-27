#pragma bank 60
#include "api.h"
#include "song_link.h"
#include "song_mode.h"
/* Cold transport entry leaves the deadline compiler/commit bank bounded. */
void song_start(uint8_t smooth) BANKED {
 dirty=1;if(song_playing){song_stop();return;}if(song_link_active){song_link_finish();return;}
 if(seqplaying){song_view.error=6;return;}if(syncmode==1){song_link_request(smooth);return;}if(syncmode&&syncmode!=SYNC_TWINK){song_view.error=7;return;}
 if(song_prepare(smooth,seqbpm,smooth?0:song_view.cursor&~15UL)){
  song_status(1);__critical{song_arm();song_go();}
 }
}

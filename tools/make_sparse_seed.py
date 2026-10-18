"""Embed a sparse demo save for fresh cartridge initialization (bank 46)."""
from pathlib import Path
from binascii import crc_hqx


def generate(battery, output):
    data = Path(battery).read_bytes()
    if len(data) != 32768:
        raise ValueError('Expected a 32 KiB battery image')
    pages = bytearray(data[8192:16384] + data[16384:22528] + data[24576:29696])
    if pages[:4] != b'GBD1':
        raise ValueError('Seed is not a sparse save')
    # Normal library capacity is unaffected by this single-ROM-bank payload.
    end = len(pages)
    while end > 256 and not any(pages[end - 64:end]):
        end -= 64
    pages = pages[:end]
    if len(pages) > 12000:
        raise ValueError('Demo fixture is too large for seed ROM bank 46')
    for offset in (0, 128):
        pages[offset + 6] = 1
        pages[offset + 126:offset + 128] = crc_hqx(pages[offset:offset + 126], 65535).to_bytes(2, 'little')
    rows = [','.join(str(v) for v in pages[i:i + 32]) for i in range(0, len(pages), 32)]
    source = '#pragma bank 46\n#include "../src/api.h"\nstatic const uint8_t seed[]={\n' + ',\n'.join(rows) + '\n};\n'
    source += '''uint8_t sparse_seed_install(void) BANKED {
 uint16_t page;uint8_t copy,at,n,buf[16],zero=0,commit='G';
 for(page=4;page<sizeof(seed)/64;page++){
  if(!(page&15))ui_loading(3+(page*6)/(sizeof(seed)/64),12);
  for(at=0;at<64;at+=16){memcpy(buf,seed+page*64+at,16);pool_page_write(page,at,buf,16);}
 }
 for(copy=0;copy<2;copy++){
  pool_page_write(copy*2,0,&zero,1);
  for(at=1;at<64;at+=n){n=64-at>16?16:64-at;memcpy(buf,seed+(uint16_t)copy*128+at,n);pool_page_write(copy*2,at,buf,n);}
  for(at=0;at<64;at+=16){memcpy(buf,seed+(uint16_t)copy*128+64+at,16);pool_page_write(copy*2+1,at,buf,16);}
  pool_page_write(copy*2,0,&commit,1);
 }
 return 1;
}
'''
    Path(output).write_text(source)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('battery', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    generate(args.battery, args.output)

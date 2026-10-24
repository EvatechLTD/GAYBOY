"""Embed five resident patterns, their song, kits and presets in a demo ROM."""
from pathlib import Path


def generate(battery, output):
    data = Path(battery).read_bytes()
    if len(data) != 32768 or data[32768-128:32768-124] != b'GSR1':
        raise ValueError('Expected a 32 KiB GSR1 resident battery image')
    # Include the song fragments inside the five resident records. Exclude
    # volatile renderer/audio scratch and both editing clipboards.
    root = bytearray(data[-128:])
    root[7] = 0  # Start on pad one; all five patterns remain available.
    root[9] = 0  # No pattern clipboard is included in this demo.
    segments = [(1, 0xA000, data[8192:16384]),
                (2, 0xA000, data[16384:19712]),
                (3, 0xA000, data[24576:26656]),
                (3, 0xBF80, root)]
    source = '#pragma bank 4\n#include "api.h"\n'
    for i, (_, _, payload) in enumerate(segments):
        rows = [','.join(str(v) for v in payload[j:j+32])
                for j in range(0, len(payload), 32)]
        source += f'static const uint8_t seed{i}[]={{\n' + ',\n'.join(rows) + '\n};\n'
    source += '''static void install(uint8_t bank,uint16_t address,const uint8_t *data,uint16_t size){
 uint16_t at;uint8_t buf[16];
 for(at=0;at<size;at+=16){
  memcpy(buf,data+at,16);
  __critical{SWITCH_RAM_MBC5(bank);memcpy((void *)(address+at),buf,16);SWITCH_RAM_MBC5(0);}
 }
}
void sparse_seed_install(void) BANKED {
'''
    # Root is last, so an interrupted install is retried on the next boot.
    for i, (bank, address, payload) in enumerate(segments[:-1]):
        source += f' install({bank},{address},seed{i},sizeof(seed{i}));\n'
    source += ''' install(3,0xBF90,seed3+16,sizeof(seed3)-16);
 install(3,0xBF80,seed3,16);
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

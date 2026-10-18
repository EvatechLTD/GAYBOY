from pathlib import Path
import re,numpy as np
rows=re.findall(r'\{([0-9,]+)\}',Path('src/mono_waves.h').read_text())
waves=[]
for row in rows:
 data=[int(x) for x in row.split(',')];waves.append(np.array([v for x in data for v in (x>>4,x&15)],float))
for pulsebank in range(2):
 source=waves if not pulsebank else [np.array([15 if i<w else 0 for i in range(32)],float) for w in range(1,33)]
 for group in range(2):
  packed=[]
  for res in range(group*2,group*2+2):
   for wave in source:
    centered=wave-wave.mean();spectrum=np.fft.rfft(centered)
    for cut in range(16):
     cutoff=0.55*(16/0.55)**(cut/15);k=np.arange(17);gain=1/np.sqrt(1+(k/cutoff)**8)
     bump=np.exp(-((k-cutoff)/(0.25*cutoff+0.4))**2);gain*=1+res*0.8*bump
     result=np.fft.irfft(spectrum*gain,n=32)
     peak=max(abs(result).max(),7.5);result=result*7.5/peak+7.5
     if cut==15 and res==0:result=wave
     samples=np.clip(np.rint(result),0,15).astype(int)
     packed.extend(int(samples[i]*16+samples[i+1]) for i in range(0,32,2))
  bank=5+group+pulsebank*2
  Path(f'src/exp_waves{bank}.c').write_text(f'#pragma bank {bank}\n#include <stdint.h>\nconst uint8_t expwaves{bank}[16384]={{'+','.join(map(str,packed))+'};\n')

# Sample-domain coefficients are copied from a separate bank, never calculated
# inside the audio producer. Signed byte tables are indexed by sample XOR 128.
alpha=[[x>>(7-cut) for x in range(-128,128)] for cut in range(8)]
resonance=[[max(-24,min(24,(x*res)>>1)) for x in range(-128,128)] for res in range(8)]
feedback=[[(x*fb)>>4 for x in range(-128,128)] for fb in range(13)]
wet=[[(x*mix)>>4 for x in range(-128,128)] for mix in range(16)]
def table(name,rows,typ='int8_t'):
 return f'const {typ} {name}[{len(rows)}][{len(rows[0])}]={{'+','.join('{'+','.join(map(str,row))+'}' for row in rows)+'};\n'
code='#pragma bank 4\n#include "api.h"\n'
for name,rows in [('alphadata',alpha),('resdata',resonance),('feedbackdata',feedback),('wetdata',wet)]:code+=table(name,rows)
code+='void exp_tables(void) BANKED {memcpy(expalpha,alphadata[expconfig[21]],256);memcpy(expreslut,resdata[expconfig[22]],256);memcpy(expfeedback,feedbackdata[expconfig[25]],256);memcpy(expwet,wetdata[expconfig[24]],256);expdelayenabled=!!expconfig[23];}\n'
Path('src/exp_coefficients.c').write_text(code)
interpolation=[[(a*(16-frac)+b*frac+8)>>4 for a in range(16) for b in range(16)] for frac in range(16)]
amplitude=[[( (a*2-15)*gain+1024)//128 for a in range(16)] for gain in range(65)]
code='#pragma bank 9\n#include "api.h"\n'+table('interpdata',interpolation,'uint8_t')+table('ampdata',amplitude,'uint8_t')
code+='uint8_t expmapfrac=255,expmapgain=255;\nvoid exp_maps(uint8_t frac,uint8_t gain) BANKED {if(expmapfrac!=frac){memcpy(expinterp,interpdata[frac],256);expmapfrac=frac;}if(expmapgain!=gain){memcpy(expampmap,ampdata[gain],16);expmapgain=gain;}}\n'
Path('src/exp_maps.c').write_text(code)

from pathlib import Path
import wave, numpy as np, ast
root=Path(__file__).resolve().parents[1]
folder=root/'breaks/AMEN172chop/processed-lsdj'
names=['KK1','KK2','KK3','SC1','SC2','HC1','CL1','KC1','CY1','PSH']
banks={16:[],19:[],20:[]}; samplebanks=[]; offsets=[]; lengths=[]; which=16
for name in names:
 with wave.open(str(folder/(name+'.wav')),'rb') as w:
  assert w.getnchannels()==1 and w.getsampwidth()==2 and w.getframerate()==11468
  pcm=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(np.int32)
 # Preserve the source's native sample positions and amplitude. DMG wave RAM is 4 bit.
 x=((pcm+32768)>>12).astype(np.uint8)
 x=np.pad(x,(0,(-len(x))%32),constant_values=8)
 # DMG trigger reads wave index 1 first. Put the final nibble in index 0,
 # so the hardware's 1..31,0 traversal emits the original sample order.
 x=np.roll(x.reshape(-1,32),1,axis=1).reshape(-1)
 packed=(x[::2]<<4)|x[1::2]
 limit=15000 if which==16 else 16300
 if len(banks[which])+len(packed)>limit:which={16:19,19:20}[which]
 samplebanks.append(which);offsets.append(len(banks[which])); lengths.append(len(packed));banks[which].extend(packed.tolist())
# Labels share sample bank; each tile row contains three 8x8 tiles.
glyphs=eval(compile(ast.Expression(next(n.value for n in ast.parse((root/'tools/make_ui_font.py').read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='glyphs' for t in n.targets))),'font','eval'),{'__builtins__':{}})
labels=np.zeros((136,24),dtype=np.uint8)
for row,name in enumerate(names+['NHH','NSN','PK']):
 for j,c in enumerate(name):
  g=glyphs.get(c,['00000']*7)
  for y,bits in enumerate(g):
   for x,v in enumerate(bits):labels[row*8+y,1+j*6+x]=int(v)*3
labelbytes=[]
for ty in range(17):
 for tx in range(3):
  for y in range(8):
   bits=sum(int(labels[ty*8+y,tx*8+x]>0)<<(7-x) for x in range(8));labelbytes.extend([bits,bits])
def arr(a):return ','.join(map(str,a))
def fast_fetch(bank,voice):
 banked=' BANKED' if bank!=16 else ''
 s='void drum_fast'+str(bank)+str(voice)+'(void)'+banked+' __naked { __asm\n push bc\n'
 s+=' ld hl,#0x'+format(0xAC42+voice*2,'04x')+'\n ld a,(hl+)\n ld h,(hl)\n ld l,a\n ld de,#_drumdata'+str(bank)+'\n add hl,de\n ld de,#0x'+format(0xAC00+voice*16,'04x')+'\n'
 s+=' .rept 16\n ld a,(hl+)\n ld (de),a\n inc e\n .endm\n pop bc\n ret\n __endasm; }\n'
 return s
exec((root/"tools/make_iconic_kits.py").read_text())
for bank, data in banks.items():
 suffix='' if bank==16 else str(bank)
 s='#pragma bank '+str(bank)+'\n#include "api.h"\nconst uint8_t drumdata'+str(bank)+'[]={'+arr(data or [136])+'};\n'
 for voice in range(2):s+=fast_fetch(bank,voice)
 if bank==16:
  s+='const uint8_t drumlabels[]={'+arr(labelbytes)+'};\n'
  s+='void drum_fetch19(uint16_t offset,uint8_t *dst) BANKED;\nvoid drum_fetch20(uint16_t offset,uint8_t *dst) BANKED;\n'
  for other in kit_banks:
   s+=f"void drum_fetch{other}(uint16_t offset,uint8_t *dst) BANKED;\n"
  s+="void kits_label(uint8_t row,uint8_t *dst) BANKED;\n"
  for voice in range(2):
   for other in (19,20,*kit_banks):s+='void drum_fast'+str(other)+str(voice)+'(void) BANKED;\n'
   s+='void drum_fetch'+str(voice)+'(void) BANKED {uint8_t bank=*(uint8_t *)0x'+format(0xAC4B+voice,'04x')+';'+''.join(f'if(bank=={b}){{drum_fast{b}{voice}();return;}}' for b in kit_banks)+'if(bank==19)drum_fast19'+str(voice)+'();else if(bank==20)drum_fast20'+str(voice)+'();else drum_fast16'+str(voice)+'();}\n'
  s+='void drum_fetch(uint8_t bank,uint16_t offset,uint8_t *dst) BANKED {if(bank==32){drum_fetch32(offset,dst);return;}if(bank==33){drum_fetch33(offset,dst);return;}if(bank==34){drum_fetch34(offset,dst);return;}if(bank==35){drum_fetch35(offset,dst);return;}if(bank==36){drum_fetch36(offset,dst);return;}if(bank==39){drum_fetch39(offset,dst);return;}if(bank==62){drum_fetch62(offset,dst);return;}if(bank==19)drum_fetch19(offset,dst);else if(bank==20)drum_fetch20(offset,dst);else memcpy(dst,drumdata16+offset,16); }\nvoid drum_label(uint8_t row,uint8_t *dst) BANKED {if(drumkit){kits_label(row,dst);return;}memcpy(dst,drumlabels+(uint16_t)row*48,48); }\n'
 else:s+='void drum_fetch'+str(bank)+'(uint16_t offset,uint8_t *dst) BANKED {memcpy(dst,drumdata'+str(bank)+'+offset,16); }\n'
 (root/('src/drum_samples'+suffix+'.c')).write_text(s)
(root/'src/drum_samples.h').write_text('const uint8_t amenbank[10]={'+arr(samplebanks)+'};\nconst uint16_t amenoffset[10]={'+arr(offsets)+'};\nconst uint16_t amenlength[10]={'+arr(lengths)+'};\n')
with (root/'src/drum_samples.h').open('a') as f:f.write(kitmeta)
print('Drum kit:',len(names),'prepared 11468 Hz samples,',sum(len(x) for x in banks.values()),'packed bytes')

# Consistent role labels for all eight-slot machine kits; legacy rows 9/10 silent.
labels=np.zeros((136,24),dtype=np.uint8)
for row,name in enumerate(['KIK','SNR','CHH','OHH','CLP','TLO','THI','PRC','--','--','NHH','NSN','PK']):
 for j,c in enumerate(name):
  for y,bits in enumerate(glyphs.get(c,['00000']*7)):
   for x,v in enumerate(bits):labels[row*8+y,1+j*6+x]=int(v)*3
labelbytes=[]
for ty in range(17):
 for tx in range(3):
  for y in range(8):
   bits=sum(int(labels[ty*8+y,tx*8+x]>0)<<(7-x) for x in range(8));labelbytes.extend([bits,bits])
(root/'src/kit_labels.h').write_text('const uint8_t kitlabels[]={'+arr(labelbytes)+'};\n')

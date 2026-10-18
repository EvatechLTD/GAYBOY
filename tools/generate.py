from pathlib import Path
import math,json
p=Path('src')
games=['Tetris','Mario Land','Zelda LA','Pokemon RB','Kirby DL','Metroid II','Mega Man','Castlevania','Wario Land','DK Land']
roles=['Lead','Pluck','Bass','Arp','Bell','Soft','Organ','Zap','Kick','Snare']
rows=[]
for g,game in enumerate(games):
 for r,role in enumerate(roles):
  # Hand-voiced role families, with different duty/envelope/timbre per game bank.
  kind=3 if r>=8 else (2 if r in [2,4,6] else 0)
  vals=[(g+r)%4, [12,15,13,11,10,8,12,15,15,12][r],0,[0,2,0,1,3,4,0,1,2,3][r],0,0,0,0,0,0,1+(g%3),0,0,0,(g*3+r)%16,1+(g%3),0,0,5+(g%3),int(r==9),3 if r==8 else 1,3,0,0,0,2]
  if r==7: vals[4:7]=[2+g%4,1,3]
  rows.append(dict(id=len(rows),name=f'{game} {role}',voice=kind,values=vals,tmode=1 if r in [3,6,7,8,9] else 0,tlen=8,table=[[([0,4,7,12,7,4,0,-12][k] if r in [3,6] else [12,7,0,0,0,0,0,0][k] if r==7 else 0),(g+k)% (16 if kind in [2,3] else 4),(1 if k%2 else 2) if r==9 else 3] for k in range(8)],mod=[2+(g%4),[0,0,0,1,2,0,3,4,0,0][r],int(r in [0,3,6]),1 if r in [0,5,6] else 0,2 if r in [7,8] else 0,[0,8,0,0,12,0,0,6,4,6][r]]))
(p/'presets.json').write_text(json.dumps(rows,indent=2)+'\n')
# Share identical stock tables; working copies remain independent in RAM.
stocktables=[]
for row in rows:
 if row['table'] not in stocktables:stocktables.append(row['table'])
# Bit-pack stock settings; expand one requested patch into a RAM cache.
fields=[[r['voice']]+r['values']+r['mod']+[r['tmode']|((r['tlen']-1)<<2),stocktables.index(r['table'])] for r in rows]
base=[min(col) for col in zip(*fields)]
width=[(max(col)-lo).bit_length() for col,lo in zip(zip(*fields),base)]
size=(sum(width)+7)//8
columns=[[],[],[]]
for table in stocktables:
 for c in range(3):
  values=[step[c] for step in table]
  if values not in columns[c]:columns[c].append(values)
assert [len(c) for c in columns]==[3,14,2]
out=['/* Generated stock patches, losslessly packed to leave room for modulation. */','#include "api.h"']
for name,values in zip(['stockpitch','stockshape','stockpan'],columns):
 if name=='stockshape':
  packed=[[row[0],3 if max(row)<=3 else 15] for row in values]
  assert all([(r[0]+i)&r[1] for i in range(8)]==original for r,original in zip(packed,values))
  out.append('const int8_t stockshape[][2]={'+','.join('{'+','.join(map(str,row))+'}' for row in packed)+'};')
 else:out.append('const int8_t '+name+'[][8]={'+','.join('{'+','.join(map(str,row))+'}' for row in values)+'};')
indices=[]
for table in stocktables:
 ids=[columns[c].index([step[c] for step in table]) for c in range(3)]
 indices.append(ids[0]|(ids[1]<<2)|(ids[2]<<6))
out.append('const uint8_t stocktables[]={'+','.join(map(str,indices)))
out.extend(['};','const uint8_t patchbase[]={'+','.join(map(str,base))+'};','const uint8_t patchwidth[]={'+','.join(map(str,width))+'};','const uint8_t patchdata[100][%d]={'%size])
for row in fields:
 bits=pos=0
 for value,lo,w in zip(row,base,width):bits|=(value-lo)<<pos;pos+=w
 out.append('{'+','.join(str((bits>>(8*i))&255) for i in range(size))+'},')
out.extend(['};','const char *patchgames[]={'+','.join(json.dumps(g) for g in games)+'};','const char *patchroles[]={'+','.join(json.dumps(r) for r in roles)+'};','Preset patchcache; uint8_t patchindex=255;','Preset *patch(uint8_t n) BANKED {uint8_t i,j,bit=0,v,x=0,*dst=&patchcache.voice;const char *s;if(n==patchindex)return &patchcache;for(i=0;i<35;i++){v=0;for(j=0;j<patchwidth[i];j++,bit++)if(patchdata[n][bit>>3]&(1<<(bit&7)))v|=1<<j;dst[i]=v+patchbase[i];}s=patchgames[n/10];while(*s)patchcache.name[x++]=*s++;patchcache.name[x++]=32;s=patchroles[n%10];while(*s)patchcache.name[x++]=*s++;patchcache.name[x]=0;patchindex=n;return &patchcache;}'])
(p/'presets.h').write_text('\n'.join(out)+'\n')
# Wave note n has exactly the pulse divider of note n+12, including low notes.
freq=[max(0,min(2047,round(2048-131072/(440*2**((n-69)/12))))) for n in range(140)]
(p/'notes.h').write_text('const uint16_t notes[140]={'+','.join(map(str,freq))+'};\n')

# 16-bit DDS phase increments for an 8192 Hz sample stream (MIDI 0..107).
dds=[round(440*2**((n-69)/12)*8) for n in range(108)]
(p/'dds_notes.h').write_text('const uint16_t ddsnotes[108]={'+','.join(map(str,dds))+'};\n')

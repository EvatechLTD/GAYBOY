"""Convert prepared PCM WAV cycles to native Game Boy waves (16-byte .GBW).
Example: python tools/prepare_ky_waves.py samples -o build/ky-sd/WAVES
Use --start/--frames to select a cycle from a longer recording. This format is
one repeating waveform, not a drum kit or a full PCM sample player.
"""
from pathlib import Path
import argparse, math, re, wave

def convert(path, start=0, frames=None):
 with wave.open(str(path),'rb') as wav:
  width=wav.getsampwidth();channels=wav.getnchannels();total=wav.getnframes()
  if width not in (1,2,3,4):raise ValueError('Expected 8/16/24/32-bit integer PCM')
  if start<0 or start>=total:raise ValueError('Cycle start is outside the WAV')
  count=total-start if frames is None else frames
  if count<2 or start+count>total:raise ValueError('Cycle must contain at least two available frames')
  if count>1000000:raise ValueError('Select a cycle with --start and --frames (maximum 1,000,000 frames)')
  wav.setpos(start);raw=wav.readframes(count)
  if len(raw)!=count*width*channels:raise ValueError('Truncated WAV data')
  values=[]
  for i in range(count):
   value=0
   for c in range(channels):
    j=(i*channels+c)*width
    value+=(raw[j]-128) if width==1 else int.from_bytes(raw[j:j+width],'little',signed=True)
   values.append(value/channels)
 mean=sum(values)/count;values=[x-mean for x in values]
 sampled=[]
 for i in range(32):
  x=i*count/32;j=int(x);f=x-j;sampled.append(values[j]*(1-f)+values[(j+1)%count]*f)
 peak=max(abs(x) for x in sampled)
 samples=[max(0,min(15,round(7.5+x*7.5/peak))) if peak else 8 for x in sampled]
 return bytes((samples[i]<<4)|samples[i+1] for i in range(0,32,2))

def collect(inputs):
 files=[]
 for item in inputs:
  p=Path(item)
  if p.is_dir():files.extend(sorted(x for x in p.rglob('*') if x.is_file() and x.suffix.lower()=='.wav'))
  elif p.is_file() and p.suffix.lower()=='.wav':files.append(p)
  else:raise ValueError('Not a WAV or directory: '+str(p))
 return sorted(set(files),key=lambda p:str(p).lower())

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('inputs',nargs='+');parser.add_argument('-o','--output',type=Path,required=True)
 parser.add_argument('--start',type=int,default=0);parser.add_argument('--frames',type=int)
 args=parser.parse_args()
 try:
  files=collect(args.inputs)
  if not files:raise ValueError('No WAV files found')
  prepared=[];used={p.name.upper() for p in args.output.iterdir()} if args.output.exists() else set()
  for p in files:
   stem=re.sub('[^A-Z0-9_]','_',p.stem.upper())[:8] or 'WAVE';name=stem;n=1
   while (name+'.GBW').upper() in used or (args.output/(name+'.GBW')).exists():
    suffix=str(n);name=stem[:8-len(suffix)]+suffix;n+=1
   used.add((name+'.GBW').upper());prepared.append((name+'.GBW',convert(p,args.start,args.frames),p))
  args.output.mkdir(parents=True,exist_ok=True)
  for name,data,src in prepared:
   (args.output/name).write_bytes(data);print(str(src)+' -> '+str(args.output/name))
 except (ValueError,wave.Error,OSError) as e:parser.exit(1,str(e)+'\n')
if __name__=='__main__':main()

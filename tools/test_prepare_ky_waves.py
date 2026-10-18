import importlib.util,math,struct,tempfile,wave,subprocess,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('prep','tools/prepare_ky_waves.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)
 for width in (1,2,3,4):
  p=root/('sine'+str(width)+'.wav');peak=(1<<(width*8-1))-1
  vals=[round(math.sin(2*math.pi*i/64)*peak) for i in range(64)]
  raw=b''.join(bytes((x+128,)) if width==1 else x.to_bytes(width,'little',signed=True) for x in vals)
  with wave.open(str(p),'wb') as w:w.setnchannels(1);w.setsampwidth(width);w.setframerate(32000);w.writeframes(raw)
  packed=prep.convert(p);assert len(packed)==16
  samples=[v for x in packed for v in (x>>4,x&15)]
  assert min(samples)==0 and max(samples)==15 and samples[8]==15 and samples[24]==0
  assert len(prep.convert(p,8,32))==16
 # Opposite stereo channels cancel to silence, with no divide by zero.
 p=root/'stereo.wav'
 with wave.open(str(p),'wb') as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(32000);w.writeframes(b''.join(struct.pack('<hh',x,-x) for x in range(64)))
 assert prep.convert(p)==bytes([0x88]*16)
 out=root/'out';out.mkdir();(out/'SINE1.GBW').write_bytes(b'preserved')
 result=subprocess.run([sys.executable,'tools/prepare_ky_waves.py',str(root),'-o',str(out)],capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 assert (out/'SINE1.GBW').read_bytes()==b'preserved' and len(list(out.glob('*.GBW')))==6
 try:prep.convert(p,1000)
 except ValueError:pass
 else:raise AssertionError('Expected invalid cycle start rejection')
print('PASS: PCM8/16/24/32, stereo, cyclic resampling, range normalization, cycle selection, batch export and no overwrite')

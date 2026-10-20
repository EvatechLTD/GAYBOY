"""WASAPI output-loopback capture; never selects an input/microphone device."""
from array import array
import time,wave
import pyaudiowpatch as pa

class LoopbackAudio:
 def __init__(self,path):
  self.path=path;self.audio=pa.PyAudio();self.stream=None;self.writer=None
  self.frames=0;self.peak=0;self.first_sample_unix_ns=None;self.status_flags=0;self.error=None
  self.device=self.audio.get_default_wasapi_loopback()
  if not self.device.get('isLoopbackDevice'):raise RuntimeError('Default device is not an output loopback.')
  self.rate=int(self.device['defaultSampleRate']);self.channels=int(self.device['maxInputChannels'])
  if not self.channels:raise RuntimeError('No output-loopback audio channels.')
 def start(self):
  self.writer=wave.open(str(self.path),'wb');self.writer.setnchannels(self.channels);self.writer.setsampwidth(2);self.writer.setframerate(self.rate)
  def callback(data,count,clock,status):
   try:
    now=time.time_ns()
    if self.first_sample_unix_ns is None:
     adc,current=clock.get('input_buffer_adc_time',0),clock.get('current_time',0)
     latency=current-adc if adc>0 and current>=adc else count/self.rate
     self.first_sample_unix_ns=now-round(latency*1e9)
    self.writer.writeframesraw(data);self.frames+=count;self.status_flags|=status
    if data:self.peak=max(self.peak,max(abs(x) for x in array('h',data)))
    return None,pa.paContinue
   except Exception as error:self.error=str(error);return None,pa.paAbort
  try:self.stream=self.audio.open(format=pa.paInt16,channels=self.channels,rate=self.rate,input=True,input_device_index=self.device['index'],frames_per_buffer=1024,stream_callback=callback)
  except Exception:self.stop();raise
  return self
 def stop(self):
  if self.stream:
   if self.stream.is_active():self.stream.stop_stream()
   self.stream.close();self.stream=None
  if self.writer:self.writer.close();self.writer=None
  self.audio.terminate()
 def summary(self):
  return dict(device=self.device['name'],kind='WASAPI output loopback',path=str(self.path),sample_rate=self.rate,channels=self.channels,sample_frames=self.frames,peak=self.peak,first_sample_unix_ns=self.first_sample_unix_ns,status_flags=self.status_flags,error=self.error)

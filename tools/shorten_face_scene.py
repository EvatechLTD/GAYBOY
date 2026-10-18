"""Remove one of the two 128 BPM bars in the living-BMO close-up."""
import json
import subprocess
from frame_native_demo import ROOT

source=ROOT/'recordings/GAYBOY-45sec-full-intro-mixer-demo.mp4'
output=ROOT/'recordings/GAYBOY-short-face-full-intro-demo.mp4'
start=19.8
end=start+1.875
filters=(
    '[0:v]split[v0][v1];[0:a]asplit[a0][a1];'
    f'[v0]trim=end={start},setpts=PTS-STARTPTS[va];'
    f'[v1]trim=start={end},setpts=PTS-STARTPTS[vb];'
    f'[a0]atrim=end={start},asetpts=PTS-STARTPTS,afade=t=out:st={start-.005}:d=0.005[aa];'
    f'[a1]atrim=start={end},asetpts=PTS-STARTPTS,afade=t=in:d=0.005[ab];'
    '[va][aa][vb][ab]concat=n=2:v=1:a=1[v][a]')
subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),
    '-filter_complex_threads','1','-filter_complex',filters,'-map','[v]','-map','[a]',
    '-c:v','libx264','-preset','fast','-threads','2','-crf','16','-pix_fmt','yuv420p',
    '-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)],check=True)
meta=json.loads(source.with_suffix('.json').read_text())
meta.update(source=str(source),duration_seconds=43.125,
    final_edit='Only change: living BMO close-up reduced from two bars to one; remaining video retained',
    removed_face_interval=[start,end],face_duration_before=3.75,face_duration_after=1.875)
for cue in meta['caption_timeline']:
    if cue[0]>=end:cue[0]-=end-start
meta['outro_at']-=end-start
output.with_suffix('.json').write_text(json.dumps(meta,indent=2))
print(str(output),flush=True)

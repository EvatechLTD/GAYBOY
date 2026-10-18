"""Whole intro at native pace; mixer fader, direct DRUM cut, short free ending."""
import json
import subprocess
from PIL import Image
from frame_native_demo import ROOT, shell, mobile_outro


def main():
    source=ROOT/'recordings/GAYBOY-program-demo-172-mixer-volume.mp4'
    intro=ROOT/'recordings/GAYBOY-60sec-intro-drums-teal-capture.mp4'
    output=ROOT/'recordings/GAYBOY-45sec-full-intro-mixer-demo.mp4'
    meta=json.loads(source.with_suffix('.json').read_text())
    stages={s['event']:s for s in meta['stages']}
    intro_end=25.9 # all scenes and logo reveal; only shorten the prompt hold
    launch=stages['drums entered at loop boundary']['frame']/59.7275
    drum=stages['drum sequencer visible']['frame']/59.7275
    cuts=[(3.,3.+16*60/172/4),(launch,drum)]
    removed=sum(b-a for a,b in cuts)
    program_end=45-intro_end+removed
    assert program_end<=meta['duration_seconds']
    spans=[(0.,cuts[0][0]),(cuts[0][1],launch),(drum,program_end)]
    def mapped(t):
        assert all(not a<t<b for a,b in cuts),t
        return intro_end+t-sum(b-a for a,b in cuts if b<=t)
    def at(event):return mapped(stages[event]['frame']/59.7275)
    for event in meta['button_events']:
        t=event['frame']/59.7275
        # Only the explicitly unwanted track-navigation passage is omitted.
        if launch<=t<drum:continue
        mapped(t)
    cues=[(0.,'Pocket-sized. Mildly unreasonable.\nMeet your next musical distraction.'),
          (intro_end,'Live note editing.\nSecond thoughts welcome.'),
          (at('extended second bass note live'),'Stretch notes. Keep the groove.\nTiny keys. Long attention span.'),
          (at('mixer page entered'),'Real-time mixer faders.\nA little louder. A lot less polite.'),
          (at('adjusted pulse volume in mixer'),'Patterns queue on the beat.\nImpatience sold separately.'),
          (at('drum sequencer visible'),'Load 4-bit wave samples.\nGive tiny drums a big problem.'),
          (at('added kick on downbeat'),'Live drum editing.\nSmall screen. Big kick energy.'),
          (43.,'mobile-play.png')]
    assert cues[-2][0]<43
    folder=ROOT/'build/full-intro-45';folder.mkdir(exist_ok=True)
    listing=['ffconcat version 1.0']
    for i,(start,copy) in enumerate(cues):
        im=mobile_outro(ROOT/'build/808-shell'/copy) if copy.endswith('.png') else shell(copy)
        bg=Image.new('RGBA',im.size,'black');bg.alpha_composite(im)
        name=f'chapter-{i:02d}.png';bg.convert('RGB').save(folder/name)
        end=cues[i+1][0] if i+1<len(cues) else 45.
        assert end>start,(start,end)
        listing.extend([f"file '{name}'",f'duration {end-start:.9f}'])
    listing.append(f"file '{name}'")
    chapters=folder/'chapters.ffconcat';chapters.write_text('\n'.join(listing)+'\n')
    filters=[f'[0:v]trim=end={intro_end},setpts=PTS-STARTPTS,crop=960:864:60:560,scale=560:504:flags=neighbor,fps=60[iv]',
             f'[0:a]atrim=end={intro_end},asetpts=PTS-STARTPTS,afade=t=out:st={intro_end-.005}:d=0.005[ia]',
             '[1:v]split=3[v0][v1][v2]','[1:a]asplit=3[a0][a1][a2]']
    for i,(start,end) in enumerate(spans):
        filters.append(f'[v{i}]trim=start={start}:end={end},setpts=PTS-STARTPTS,scale=560:504:flags=neighbor,fps=60[sv{i}]')
        filters.append(f'[a{i}]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,afade=t=in:d=0.005,afade=t=out:st={end-start-.005}:d=0.005[sa{i}]')
    filters.extend(['[iv][sv0][sv1][sv2]concat=n=4:v=1:a=0[lcd]',
        '[2:v]fps=60,scale=1080:1920:flags=neighbor[body]',
        "[body][lcd]overlay=260:316:enable='lt(t,43)':eof_action=pass,trim=duration=45[v]",
        '[ia][sa0][sa1][sa2]concat=n=4:v=0:a=1,apad,atrim=duration=45,afade=t=out:st=44.985:d=0.015[a]'])
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(intro),'-i',str(source),
        '-f','concat','-safe','0','-i',str(chapters),'-filter_complex_threads','1',
        '-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t','45',
        '-c:v','libx264','-preset','fast','-threads','2','-crf','16','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)],check=True)
    meta.update(duration_seconds=45,size=[1080,1920],intro_source_interval=[0,intro_end],
        intro_speed=1,program_speed=1,source=str(source),removed_source_intervals=cuts,
        program_source_end=program_end,caption_timeline=cues,
        direct_mixer_to_drum=True,outro_at=43,
        intro_edit='Complete uninterrupted intro, including train; shorten press-play hold only')
    output.with_suffix('.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(dict(output=str(output),intro_seconds=intro_end,
        mixer_at=at('mixer page entered'),drum_at=at('drum sequencer visible'),
        last_hat_at=at('added open hat accent'),program_end=program_end)),flush=True)


if __name__=='__main__':main()

"""Thirty-second vertical shell edit of the approved 172 BPM performance."""
import json
import argparse
from pathlib import Path
import subprocess
from PIL import Image
from frame_native_demo import ROOT, shell, mobile_outro


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seconds',type=int,choices=(30,45),default=30)
    args=ap.parse_args();duration=args.seconds
    source=ROOT/'recordings/GAYBOY-program-demo-172-pulse-focus.mp4'
    intro=ROOT/'recordings/GAYBOY-60sec-intro-drums-teal-capture.mp4'
    output=ROOT/'recordings/GAYBOY-30sec-BMO-172-repaced.mp4'
    if duration==45:output=ROOT/'recordings/GAYBOY-45sec-BMO-172-demo.mp4'
    meta=json.loads(source.with_suffix('.json').read_text())
    old=json.loads(intro.with_suffix('.json').read_text())
    folder=ROOT/'build/30sec-shell-repaced';folder.mkdir(exist_ok=True)
    if duration==45:folder=ROOT/'build/45sec-shell';folder.mkdir(exist_ok=True)
    # The repeated 32-step phrase permits a two-bar musical edit during the
    # idle pulse view. Keep every button action, then one finished drum loop.
    cut_start=3.
    cut_length=32*60/172/4
    cut_end=cut_start+cut_length
    program_end=meta['duration_seconds'] if duration==45 else 25.15
    repeat_duration=cut_length if duration==45 else 0
    performance=program_end-cut_length+repeat_duration
    intro_duration=duration-performance
    outro_at=37. if duration==45 else 28.
    def mapped(frame):
        t=frame/59.7275
        assert not cut_start<t<cut_end,('An action would be removed',t)
        return intro_duration+t-(cut_length if t>=cut_end else 0)
    for event in meta['button_events']:mapped(event['frame'])
    stages={s['event']:s for s in meta['stages']}
    cues=[
        (0.,'Pocket-sized. Mildly unreasonable.\nMeet your next musical distraction.'),
        (intro_duration,'Live note editing.\nSecond thoughts welcome.'),
        (mapped(stages['extended second bass note live']['frame']),
         'Stretch notes. Keep the groove.\nTiny keys. Long attention span.'),
        (mapped(stages['mixer page entered']['frame']),
         'Patterns queue on the beat.\nImpatience sold separately.'),
        (mapped(stages['drum sequencer visible']['frame']),
         'Load 4-bit wave samples.\nGive tiny drums a big problem.'),
        (mapped(stages['added kick on downbeat']['frame']),
         'Live drum editing.\nSmall screen. Big kick energy.'),
        (mapped(next(s['frame'] for s in meta['stages'] if s['event']=='added open hat accent')),
         'Accents optional.\nQuestionable restraint included.'),
        (outro_at,'mobile-play.png')]
    if duration==45:cues.append((41.,'mobile-download.png'))
    listing=['ffconcat version 1.0']
    for i,(at,copy) in enumerate(cues):
        im=(mobile_outro(ROOT/'build/808-shell'/copy) if copy.endswith('.png') else shell(copy))
        bg=Image.new('RGBA',im.size,'black');bg.alpha_composite(im)
        filename=folder/f'chapter-{i:02d}.png';bg.convert('RGB').save(filename)
        end=cues[i+1][0] if i+1<len(cues) else float(duration)
        listing.extend([f"file '{filename.name}'",f'duration {end-at:.9f}'])
    listing.append(f"file '{filename.name}'")
    chapters=folder/'chapters.ffconcat';chapters.write_text('\n'.join(listing)+'\n')
    original_intro=old['intro_duration_seconds']
    audio_intro_start=original_intro-intro_duration*172/128
    filters=(
        f'[0:v]trim=end={original_intro},setpts=(PTS-STARTPTS)*{intro_duration/original_intro},'
        'crop=960:864:60:560,scale=560:504:flags=neighbor,fps=60[iv];'
        '[1:v]split[p1][p2];'
        f'[p1]trim=end={cut_start},setpts=PTS-STARTPTS,scale=560:504:flags=neighbor,fps=60[v1];'
        f'[p2]trim=start={cut_end}:end={program_end},setpts=PTS-STARTPTS,'
        'scale=560:504:flags=neighbor,fps=60[v2];'
        '[iv][v1][v2]concat=n=3:v=1:a=0[lcd];'
        '[2:v]fps=60,scale=1080:1920:flags=neighbor[body];'
        f"[body][lcd]overlay=260:316:enable='lt(t,{outro_at})':eof_action=pass,trim=duration={duration}[v];"
        f'[0:a]atrim=start={audio_intro_start}:end={original_intro},asetpts=PTS-STARTPTS,'
        f'atempo={172/128},apad,atrim=duration={intro_duration},'
        f'afade=t=out:st={intro_duration-.005}:d=0.005[ia];'
        '[1:a]asplit[a1][a2];'
        f'[a1]atrim=end={cut_start},asetpts=PTS-STARTPTS,afade=t=in:d=0.005,'
        f'afade=t=out:st={cut_start-.005}:d=0.005[aa];'
        f'[a2]atrim=start={cut_end}:end={program_end},asetpts=PTS-STARTPTS,'
        'afade=t=in:d=0.005[ab];'
        '[ia][aa][ab]concat=n=3:v=0:a=1,apad,atrim=duration=30,afade=t=out:st=29.985:d=0.015[a]')
    if duration==45:
        # Choose shorter shots rather than accelerating the original animation
        # or soundtrack. Retain the complete happy reveal and prompt loop.
        head_duration=intro_duration-7.5
        tail_start=original_intro-7.5
        filters=(
            '[0:v]split[i1][i2];'
            f'[i1]trim=end={head_duration},setpts=PTS-STARTPTS,crop=960:864:60:560,'
            'scale=560:504:flags=neighbor,fps=60[iv1];'
            f'[i2]trim=start={tail_start}:end={original_intro},setpts=PTS-STARTPTS,'
            'crop=960:864:60:560,scale=560:504:flags=neighbor,fps=60[iv2];'
            '[1:v]split[p1][p2];'
            f'[p1]trim=end={cut_start},setpts=PTS-STARTPTS,scale=560:504:flags=neighbor,fps=60[v1];'
            f'[p2]trim=start={cut_end}:end={program_end},setpts=PTS-STARTPTS,'
            'scale=560:504:flags=neighbor,fps=60[v2];'
            f'[iv1][iv2][v1][v2]concat=n=4:v=1:a=0,tpad=stop_mode=clone:stop_duration={repeat_duration}[lcd];'
            '[2:v]fps=60,scale=1080:1920:flags=neighbor[body];'
            f"[body][lcd]overlay=260:316:enable='lt(t,{outro_at})':eof_action=pass,trim=duration=45[v];"
            '[0:a]asplit[i1a][i2a];'
            f'[i1a]atrim=end={head_duration},asetpts=PTS-STARTPTS,afade=t=out:st={head_duration-.005}:d=0.005[ia1];'
            f'[i2a]atrim=start={tail_start}:end={original_intro},asetpts=PTS-STARTPTS,'
            'afade=t=in:d=0.005,afade=t=out:st=7.495:d=0.005[ia2];'
            '[1:a]asplit=3[a1][a2][a3];'
            f'[a1]atrim=end={cut_start},asetpts=PTS-STARTPTS,afade=t=in:d=0.005,'
            f'afade=t=out:st={cut_start-.005}:d=0.005[aa];'
            f'[a2]atrim=start={cut_end}:end={program_end},asetpts=PTS-STARTPTS,'
            f'afade=t=in:d=0.005,afade=t=out:st={program_end-cut_end-.005}:d=0.005[ab];'
            f'[a3]atrim=start={program_end-repeat_duration}:end={program_end},asetpts=PTS-STARTPTS,'
            'afade=t=in:d=0.005[ac];'
            '[ia1][ia2][aa][ab][ac]concat=n=5:v=0:a=1,apad,atrim=duration=45,'
            'afade=t=out:st=44.985:d=0.015[a]')
    print(json.dumps(dict(intro_seconds=intro_duration,live_music_bpm=172,
                         removed_idle_seconds=cut_length,caption_timeline=cues)),flush=True)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(intro),'-i',str(source),
        '-f','concat','-safe','0','-i',str(chapters),'-filter_complex_threads','1',
        '-filter_complex',filters,'-map','[v]','-map','[a]','-t',str(duration),
        '-c:v','libx264','-preset','fast','-threads','2','-crf','16','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)],check=True)
    meta.update(duration_seconds=duration,size=[1080,1920],source=str(source),
        presentation='Centered BMO teal DMG shell, backlit teal LCD, black background',
        intro_duration_seconds=intro_duration,intro_visual_speed=1 if duration==45 else original_intro/intro_duration,
        live_music_bpm=172,program_speed=1,
        removed_idle_interval=[cut_start,cut_end],all_button_actions_preserved=True,
        caption_timeline=cues,outro_at=outro_at,program_source_end=program_end,
        outro='Actual full-screen mobile website; absolutely free; browser + .gb download; URL',
        final_playback='One complete finished loop; two-second mobile website ending',
        audio_edits='Intro at 172 BPM with pitch preserved; two repeated idle bars removed; 5 ms seam fades')
    if duration==45:
        meta.update(intro_source_intervals=[[0,head_duration],[tail_start,original_intro]],
            final_playback='Four original finished loops plus two extra drum loops; eight-second free screen',
            audio_edits='Original intro soundtrack at native speed; live program at 172 BPM; two idle bars removed; two finished bars appended; 5 ms seam fades')
    output.with_suffix('.json').write_text(json.dumps(meta,indent=2))
    print(f'Saved {output}',flush=True)


if __name__=='__main__':main()


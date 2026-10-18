"""Second intro composition, continued at its original 128 BPM."""
from kit_demo import KitDemo
from seq_storage_helpers import read_tracks, write_tracks, write_word


class HeightsDemo(KitDemo):
    high_tom_step = 10
    def prepare_parts(self, incomplete=False):
        super().prepare_parts(incomplete)
        tracks=read_tracks(self.p,self.s)
        melody=[81,77,72,0,76,79,84,79,74,77,82,0,81,77,76,72]
        roots=[41,41,36,36,46,46,41,36]
        tracks[0]=[[i*2+offset,n+1,100 if i%4==0 else 90,2]
                   for offset in (0,32) for i,n in enumerate(melody) if n]
        tracks[1]=[[i*4+offset,r+13,127,3] for offset in (0,32)
                   for i,r in enumerate(roots)
                   if not incomplete or i*4 not in (4,12)]
        # At 128 BPM the long tom/kick tails occupy three steps. Leave room
        # for the high tom at 10 without exceeding the two PCM voices.
        tracks[6]=[[step,row+1,velocity,duration]
                   for row,steps,velocity,duration in (
                       (0,(0,8),100,3),(1,(4,12),90,3),(2,(2,7,14),60,1),
                       (3,(15,),55,1),(4,(5,),55,2),(5,(7,),65,3))
                   for step in steps]
        tracks[6].sort(key=lambda e:(e[0],e[1]))
        write_tracks(self.p,self.s,tracks)
        write_word(self.p,self.s['_seqlength'],64)
        write_word(self.p,self.s['_seqbpm'],128)
        self.p.memory[self.s['_seqtop']]=88
        self.composition.update(bpm=128,key='F major',harmony='F / C / Bb / F C',
            lengths=[64,64,32,16,64,64,16],sparse_events=tracks,
            visible_bass='Complete F3 at step 4 and C3 at step 12',
            melody_source='Exact happymelody and happyroots from src/intro.c')

    def prepare(self):
        yield from super().prepare()
        self.p.memory[self.s['_seqpitch']+1]=53
        self.p.memory[self.s['_seqtop']+1]=59
        self.p.memory[self.s['_seqcursor']+1]=4
        self.p.memory[self.s['_seqdrawvalid']]=0
        self.p.memory[self.s['_dirty']]=1

    def run(self):
        self.label('Same melody. Same 128 BPM.\nComplete the bass as the loop plays.')
        yield from self.until(.35)
        yield from self.tap('b')
        assert any(e[:2]==[4,54] for e in read_tracks(self.p,self.s)[1])
        self.stage_times.append({'frame':self.frames,'event':'plotted F3 bass step 4 live'})
        for _ in range(8):yield from self.tap('right')
        for _ in range(5):yield from self.tap('down')
        yield from self.tap('b')
        assert any(e[:2]==[12,49] for e in read_tracks(self.p,self.s)[1])
        self.stage_times.append({'frame':self.frames,'event':'plotted C3 bass step 12 live'})
        yield from self.until(3.1)
        self.label('Queue the drums early.\nFlashing means waiting for the bar.')
        yield from self.choose(18)
        yield from self.tap('up');yield from self.tap('right')
        while self.v('seqposition',1)<48:yield
        assert self.v('seqposition',1)<60
        yield from self.tap('a')
        self.stage_times.append({'frame':self.frames,'event':'drum pattern queued early'})
        for _ in range(300):
            if self.p.memory[self.s['_mx']+1]==1:break
            yield
        assert self.p.memory[self.s['_mx']+1]==1 and self.v('seqmuted')==0
        assert self.transition_snapshot[:2]==[63,63],self.transition_snapshot
        self.stage_times.append({'frame':self.frames,'event':'full-loop drum launch',
                                  'outgoing_positions':self.transition_snapshot})
        yield from self.mix_demo()
        yield from self.tap('b')
        yield from self.track(6)
        self.stage_times.append({'frame':self.frames,'event':'drum pattern visible'})
        yield from self.live_drum_edits()
        self.label('F / C / Bb / F C.\nLet the finished groove play.')
        yield from self.until(getattr(self,'duration_limit',45)-.05)


class DMXHeightsDemo(HeightsDemo):
    kit_id = 5
    kit_name = 'Oberheim DMX'
    kit_bank = 36
    opening_caption = 'Live note editing.\nSecond thoughts, on the next loop.'

    def label(self, text):
        for trigger, copy in (
            ('Same melody.', self.opening_caption),
            ('Queue the drums', 'Queued patterns. Locked to the bar.\nImpatience sold separately.'),
            ('Drums in front.', 'Real-time mixer faders.\nGive the drummer a fighting chance.'),
            ('Both pulses', 'Two pulse channels. Room to breathe.\nEveryone gets a turn being loud.'),
            (f'{self.kit_name} is playing.', 'Load 4-bit wave samples.\nGive tiny drums a big problem.'),
            ('Add percussion', 'Live drum editing.\nThe groove can handle your ideas.'),
            ('Kick, snare,', 'Two sample voices. Custom kits.\nTiny machine. Questionable restraint.'),
            ('F / C / Bb', '64-step melodies. Custom samples.\nPocket-sized. Mildly unreasonable.'),
        ):
            if text.startswith(trigger):
                text=copy
                break
        super().label(text)

    def prepare_parts(self, incomplete=False):
        super().prepare_parts(incomplete)
        tracks=read_tracks(self.p,self.s)
        # DMX hats last two steps and toms four at 128 BPM. Separate their
        # tails so the live additions preserve the kick and backbeat.
        tracks[6]=[[step,row+1,velocity,duration]
                   for row,steps,velocity,duration in (
                       (0,(0,8),100,2),(1,(4,12),90,2),(2,(2,6,14),60,2),
                       (3,(3,),55,2),(4,(5,),55,2),(5,(7,),65,4))
                   for step in steps]
        tracks[6].sort(key=lambda e:(e[0],e[1]))
        write_tracks(self.p,self.s,tracks)
        self.composition['sparse_events']=tracks


class EightOhEightDemo(DMXHeightsDemo):
    kit_id = 1
    kit_name = 'TR-808'
    kit_bank = 32

    def prepare_parts(self, incomplete=False):
        super().prepare_parts(incomplete)
        tracks=read_tracks(self.p,self.s)
        # Clap backbeat at 4/12. A short snare pickup keeps all eight sounds
        # represented. The long 808 kick leaves only one other PCM voice.
        tracks[6]=[[step,row+1,velocity,duration]
                   for row,steps,velocity,duration in (
                       (0,(0,8),100,6),(1,(3,),60,1),(2,(2,6,14),60,1),
                       (3,(15,),55,1),(4,(4,12),90,2),(5,(7,),65,3))
                   for step in steps]
        tracks[6].sort(key=lambda e:(e[0],e[1]))
        write_tracks(self.p,self.s,tracks)
        self.composition.update(sparse_events=tracks,backbeat='808 claps at steps 4 and 12',
                                snare_role='Short pickup at step 3')


class LinnHeightsDemo(DMXHeightsDemo):
    kit_id = 4
    kit_name = 'LinnDrum'
    kit_bank = 35
    high_tom_step = 14
    percussion_step = 10

    def prepare_parts(self, incomplete=False):
        super().prepare_parts(incomplete)
        tracks=read_tracks(self.p,self.s)
        # Open hat carries the second half; high/low toms make a descending
        # end-of-bar fill. Keep the sample tails inside two PCM voices.
        tracks[6]=[[step,row+1,velocity,duration]
                   for row,steps,velocity,duration in (
                       (0,(0,8),100,2),(1,(3,),60,2),(2,(2,6),60,2),
                       (3,(9,),55,6),(4,(4,12),90,2),(5,(15,),65,1))
                   for step in steps]
        tracks[6].sort(key=lambda e:(e[0],e[1]))
        write_tracks(self.p,self.s,tracks)
        self.composition.update(sparse_events=tracks,backbeat='Claps at steps 4 and 12',
                                snare_role='Short pickup at step 3')


class NativeIntroDemo(DMXHeightsDemo):
    kit_id = 0
    kit_name = 'Intro native drums'
    kit_bank = 16
    expected_native_drums = True

    def prepare_parts(self, incomplete=False):
        super().prepare_parts(incomplete)
        tracks=read_tracks(self.p,self.s)
        tracks[3]=[[step,37,127,1] for step in (0,8)]
        tracks[6]=[[step,11,127,1] for step in (1,5,7,9,13,15)]
        tracks[6]+=[[step,12,127,1] for step in (4,12)]
        tracks[6].sort(key=lambda e:(e[0],e[1]))
        write_tracks(self.p,self.s,tracks)
        # Exact NR42/NR43 voices from happymusic()/percussion() in intro.c:
        # kick 61/64, snare 72/37, hats 31/15.
        base=self.s['_param']+3*26
        for field,value in {1:6,2:0,3:1,8:0,9:0,18:6,19:0,20:4,21:2,22:0}.items():
            self.p.memory[base+field]=value
        self.p.memory[self.s['_noisepatch']:self.s['_noisepatch']+10]=[3,1,5,0,1,7,3,7,0,2]
        self.p.memory[self.s['_seqgate']+3]=100
        for channel in (3,6):
            self.p.memory[self.s['_mx']+12+channel]=127
            self.p.memory[self.s['_mx']+19+channel]=2
        self.p.memory[self.s['_drumrow']]=10
        self.p.memory[self.s['_seqcursor']+6]=3
        self.p.memory[self.s['_seqdefaultvel']+6]=127
        self.composition.update(drumkit='Native intro noise voices',kit_sounds=3,
            sparse_events=tracks,drum_source='Exact second intro cue; no PCM kit',
            drum_registers={'kick':[0x61,0x64],'snare':[0x72,0x37],'hat':[0x31,0x15]},
            final_kick_steps=[0,8],final_snare_steps=[4,12],
            final_hat_steps=[1,3,5,7,9,11,13,15])

    def observe_audio(self):
        if not hasattr(self,'observed_noise'):self.observed_noise=set()
        pair=(self.p.noise_envelope,self.p.noise_timbre)
        if pair in ((0x61,0x64),(0x72,0x37),(0x31,0x15)):
            self.observed_noise.add(pair)

    def mix_demo(self):
        yield from super().mix_demo()
        # Return from the pad to P1 mute, then P2 mute using actual controls.
        yield from self.tap('up')
        for _ in range(3):yield from self.tap('up')
        assert self.p.memory[self.s['_mx']+4]==2
        yield from self.tap('a')
        yield from self.tap('right');yield from self.tap('a')
        assert self.v('seqmuted')==3
        self.stage_times.append({'frame':self.frames,'event':'both pulses muted before drum view'})
        self.label('Solo the rhythm.\nTwo pulses politely step aside.')
        for _ in range(4):yield from self.tap('down')
        yield from self.tap('right')
        assert self.p.memory[self.s['_mx']+4]==31

    def live_drum_edits(self):
        assert self.v('seqtrack')==6 and self.v('seqmuted')==3
        assert self.v('drumrow')==10
        self.label('Native drums. Loadable 4-bit samples.\nYour pocket has range.')
        while self.v('seqcursor',6)<3:yield from self.tap('right')
        yield from self.wait(40)
        yield from self.tap('b')
        self.stage_times.append({'frame':self.frames,'event':'restored intro hat at step 3 live'})
        self.label('Live step editing.\nA couple of hats. No wardrobe crisis.')
        yield from self.wait(60)
        for _ in range(8):yield from self.tap('right')
        yield from self.tap('b')
        tracks=read_tracks(self.p,self.s)
        assert sorted(e[0] for e in tracks[6] if e[1]==11)==self.composition['final_hat_steps']
        assert sorted(e[0] for e in tracks[6] if e[1]==12)==[4,12]
        assert [e[0] for e in tracks[3]]==[0,8]
        self.composition['final_drum_events']=tracks[6]
        self.stage_times.append({'frame':self.frames,'event':'exact intro drum pattern completed'})
        self.label('Same intro groove. Still running.\nGood timing. Minimal drama.')
        yield from self.until(self.outro_start_live)
        # The website is already full-screen while these real controls restore
        # both pulses. Transport keeps running; no arrangement restart.
        yield from self.track(0)
        yield from self.chord('select','b')
        yield from self.track(1)
        yield from self.chord('select','b')
        assert self.v('seqmuted')==0
        self.stage_times.append({'frame':self.frames,'event':'whole arrangement restored during website outro'})

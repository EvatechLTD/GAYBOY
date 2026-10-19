"""Thirty-second performance: trigger a prepared full pattern, then show drums."""
from intro_song import IntroSongDemo


class QuickDemo(IntroSongDemo):
    bass_track = 2
    def prepare_parts(self, incomplete=False):
        from seq_storage_helpers import read_tracks,write_tracks,write_word
        tracks=read_tracks(self.p,self.s)
        # A one-bar pentatonic lead sits over the longer C/F/Am backing. The
        # visible lead and drum loops remain entirely inside the 16-step grid.
        tracks[0]=[[step,note+1,velocity,1] for step,note,velocity in
                   [(0,67,100),(2,64,90),(6,72,90),(8,69,100),(12,76,90),(14,72,90)]
                   ]
        if incomplete:tracks[2]=[event for event in tracks[2] if event[0] not in (4,12)]
        for c in (3,6):tracks[c]=[event for event in tracks[c] if event[0]<16]
        write_tracks(self.p,self.s,tracks)
        for c in (0,3,6):write_word(self.p,self.s['_seqlength']+c*2,16)
        write_word(self.p,self.s['_seqdefaultdur']+4,3)
        self.p.memory[self.s['_seqtop']]=76
        self.p.memory[self.s['_seqpitch']]=72
        self.p.memory[self.s['_seqcursor']]=6
        self.p.memory[self.s['_seqtop']+self.bass_track]=59
        self.p.memory[self.s['_seqpitch']+self.bass_track]=48
        self.p.memory[self.s['_seqcursor']+self.bass_track]=4
        self.composition.update(lengths=[16,64,32,16,64,64,16],
                                visible_bass='C/F/Am roots; complete steps 4 and 12 live',
                                sparse_events=tracks)

    def prepare(self):
        # Save the melodic arrangement as pad 1 using the real Save screen.
        self.prepare_parts(incomplete=True)
        self.p.memory[self.s['_seqmuted']] = 72
        yield from self.choose(20)
        yield from self.tap('b')
        yield from self.choose(18)
        yield from self.tap('up')
        yield from self.tap('right')
        yield from self.tap('a')
        assert self.p.memory[self.s['_mx']+1] == 1
        # Populate the second, empty pad with the same score and active drums.
        IntroSongDemo.__init__(self,self.p,self.s)
        self.prepare_parts()
        self.p.memory[self.s['_seqmuted']] = 0
        yield from self.choose(20)
        yield from self.tap('b')
        yield from self.choose(18)
        yield from self.tap('up')
        yield from self.tap('a')
        assert self.p.memory[self.s['_mx']+1] == 0
        assert self.v('seqmuted') == 72
        # Queue on the final bar; preparation launches at the next available 1/1 grid.
        self.p.memory[self.s['_mx']+3] = 4
        yield from self.choose(8)
        yield from self.track(self.bass_track)
        assert self.v('seqcols') == 16
        self.p.memory[self.s['_seqcursor']+self.bass_track]=4
        self.p.memory[self.s['_seqpitch']+self.bass_track]=48
        self.p.memory[self.s['_seqtop']+self.bass_track]=59
        self.p.memory[self.s['_seqdrawvalid']]=0
        self.p.memory[self.s['_dirty']]=1
        yield from self.wait(45)
        self.transition_snapshot = None
        def boundary(_):
            self.transition_snapshot = [self.v('seqposition',c) for c in range(7)]
        address=self.s['_seq_pattern_release']
        self.p.hook_register(address>>16,address&65535,boundary,None)
        yield from self.chord('select','a')
        assert self.v('seqplaying')

    def until(self,seconds):
        while self.frames < round(seconds*59.7275): yield

    def run(self):
        from seq_storage_helpers import read_tracks
        self.label('Two bass notes missing.\nFill the gaps while the loop plays.')
        assert self.v('seqtrack') == self.bass_track and self.v('seqcols') == 16
        yield from self.until(.5)
        yield from self.tap('b')
        assert any(event[:2]==[4,49] for event in read_tracks(self.p,self.s)[self.bass_track])
        self.stage_times.append({'frame':self.frames,'event':'plotted bass step 4 with B'})
        for _ in range(8):yield from self.tap('right')
        for _ in range(5):yield from self.tap('up')
        yield from self.until(2)
        yield from self.tap('b')
        assert any(event[:2]==[12,54] for event in read_tracks(self.p,self.s)[self.bass_track])
        self.stage_times.append({'frame':self.frames,'event':'plotted bass step 12 with B'})
        self.label('The next pass plays the new notes.\nSame screen. Same running loop.')
        yield from self.until(6)
        self.label('Queue the drums early.\nFlashing means waiting for the bar.')
        yield from self.choose(18)
        yield from self.tap('up')
        yield from self.tap('right')
        while self.v('seqposition',1) < 48: yield
        assert self.v('seqposition',1) < 60, 'Missed the full-loop queue window'
        yield from self.tap('a')
        self.stage_times.append({'frame':self.frames,'event':'drum pattern queued early'})
        for _ in range(300):
            if self.p.memory[self.s['_mx']+1] == 1: break
            yield
        assert self.p.memory[self.s['_mx']+1] == 1
        assert self.v('seqmuted') == 0
        assert self.transition_snapshot is not None
        assert all(position % 16 == 15 for position in self.transition_snapshot[:4]+self.transition_snapshot[6:]), self.transition_snapshot
        self.stage_times.append({'frame':self.frames,'event':'drums entered through pattern pad 2'})
        self.stage_times.append({'frame':self.frames,'event':'bar handoff verified','outgoing_positions':self.transition_snapshot})
        assert self.frames/59.7275 < 15
        self.label('Solid means playing.\nThe drums land on a bar boundary.')
        yield from self.mix_demo()
        yield from self.until(11)
        yield from self.tap('b')  # Pattern pad's direct Edit action, no menu detour.
        assert self.v('page') == 8
        yield from self.track(6)
        assert self.v('seqtrack') == 6
        self.stage_times.append({'frame':self.frames,'event':'drum pattern visible'})
        self.label('Drums are playing.\nFollow the hats and backbeat.')
        yield from self.live_drum_edits()
        yield from self.until(30)
        assert self.v('seqplaying')

    def live_drum_edits(self):
        yield from self.wait(0)

    def mix_demo(self):
        yield from self.wait(0)

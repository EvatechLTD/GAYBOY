"""TR-909 performance: eight kit sounds, with two added on camera."""
from quick_demo import QuickDemo
from seq_storage_helpers import read_tracks, write_tracks, write_word


class KitDemo(QuickDemo):
    bass_track = 1
    high_tom_step = 9
    percussion_step = 15
    kit_id = 2
    kit_name = 'TR-909'
    kit_bank = 33

    def prepare_parts(self, incomplete=False):
        super().prepare_parts(incomplete)
        tracks = read_tracks(self.p, self.s)
        # Consistent bass velocity; sustain comes from decay, not excessive gain.
        bass = [[e[0], e[1], 127, e[3]] for e in tracks[2]]
        tracks[1] = [e[:] for e in bass] + [[e[0]+32, *e[1:]] for e in bass]
        tracks[2] = []
        tracks[3] = []
        # Backbeat and hats first; leave the high tom and percussion empty.
        tracks[6] = [[step, row+1, velocity, 1] for row, steps, velocity in (
            (0, (0, 8), 100), (1, (4, 12), 90), (2, (2, 6, 14), 60),
            (3, (10,), 55), (4, (12,), 55), (5, (7,), 65)) for step in steps]
        tracks[6].sort(key=lambda e: (e[0], e[1]))
        write_tracks(self.p, self.s, tracks)
        write_word(self.p, self.s['_seqdefaultdur']+2, 3)
        write_word(self.p, self.s['_seqdefaultdur']+12, 1)
        self.p.memory[self.s['_seqgate']+1] = 90
        self.p.memory[self.s['_param']+26] = 2
        self.p.memory[self.s['_param']+27] = 7
        self.p.memory[self.s['_param']+29] = 7
        self.p.memory[self.s['_seqdefaultvel']+1] = 127
        # Keep the lead audible at reduced gain without overpowering the kit.
        self.p.memory[self.s['_param']+1] = 12
        self.p.memory[self.s['_param']+3] = 3
        # Both saved scenes begin at 30% mixer gain; drums retain full gain.
        for channel in (0, 1):
            self.p.memory[self.s['_mx']+12+channel] = 38
        self.p.memory[self.s['_drumrow']] = 6
        self.p.memory[self.s['_seqcursor']+6] = 9
        self.composition.update(drumkit=self.kit_name, bass_channel='P2 (PCM-independent)',
                                sparse_events=tracks, kit_sounds=8, p1_envelope='fall',
                                pulse_mixer_start=38, pulse_mixer_target=64,
                                mixer_scale=127,
                                bass_patch={'duty_percent':50, 'volume':7,
                                            'envelope':'fall', 'period':7, 'velocity':127},
                                lead_patch={'volume':12, 'envelope':'fall', 'period':3})

    def mix_demo(self):
        self.label('Drums in front. Pulses at 30%.\nRaise both with the mixer faders.')
        assert self.v('page') == 18
        # From pattern pad 2, Up returns to P1 pan; Up selects its fader.
        yield from self.tap('up')
        yield from self.tap('up')
        for channel in (0, 1):
            assert self.p.memory[self.s['_mx']+4] == 4+channel*4
            assert self.p.memory[self.s['_mx']+12+channel] == 38
            yield from self.key('b', True)
            for _ in range(2):
                yield from self.tap('right')
            for _ in range(6):
                yield from self.tap('up')
            yield from self.key('b', False)
            assert self.p.memory[self.s['_mx']+12+channel] == 64
            self.stage_times.append({'frame':self.frames, 'event':'raised pulse mixer fader live',
                                     'channel':channel, 'from':38, 'to':64, 'scale':127})
            if channel == 0:
                yield from self.tap('right')
        self.label('Both pulses at 50%.\nNow hear the drums in the mix.')
        yield from self.wait(45)
        # Return to pad 2's Edit action without launching another pattern.
        yield from self.tap('down')
        yield from self.tap('down')
        yield from self.tap('right')
        assert self.p.memory[self.s['_mx']+4] == 31

    def prepare(self):
        yield from self.choose(23)
        while self.v('kitchoice') != self.kit_id:
            yield from self.tap('down')
        yield from self.tap('a')
        assert self.v('drumkit') == self.kit_id
        yield from super().prepare()
        self.sounds_heard = set()
        def pcm(_):
            for voice in range(2):
                if self.v('drumon', voice) and self.v('drumbankvoice', voice) == self.kit_bank:
                    self.sounds_heard.add(self.v('drumsamplevoice', voice))
        address = self.s['_drum_pack']
        self.p.hook_register(address >> 16, address & 65535, pcm, None)

    def live_drum_edits(self):
        assert self.p.memory[self.s['_mx']+1] == 1
        assert self.v('seqcols') == 16 and self.v('drumrow') == 6
        self.label(f'{self.kit_name} is playing.\nAdd a high tom to the groove.')
        while self.v('seqcursor',6) < self.high_tom_step:
            yield from self.tap('right')
        yield from self.wait(35)
        yield from self.tap('b')
        assert any(e[:2] == [self.high_tom_step, 7] for e in read_tracks(self.p, self.s)[6]), (self.v('seqcursor',6), self.v('drumrow'), self.v('seqhead'),read_tracks(self.p,self.s)[6])
        self.stage_times.append({'frame':self.frames, 'event':f'added high tom step {self.high_tom_step} live with B'})
        yield from self.wait(90)
        self.label('Add percussion to the groove.\nAll eight kit sounds, one running loop.')
        yield from self.tap('down')
        for _ in range(abs(self.percussion_step-self.high_tom_step)):
            yield from self.tap('right' if self.percussion_step>self.high_tom_step else 'left')
        yield from self.tap('b')
        tracks = read_tracks(self.p, self.s)
        assert any(e[:2] == [self.percussion_step, 8] for e in tracks[6])
        assert {e[1] for e in tracks[6]} == set(range(1, 9)), tracks[6]
        self.stage_times.append({'frame':self.frames, 'event':f'added percussion step {self.percussion_step} live with B'})
        self.composition['final_drum_events'] = tracks[6]
        yield from self.wait(180)
        assert self.sounds_heard == set(range(8)), self.sounds_heard
        self.stage_times.append({'frame':self.frames, 'event':f'all eight {self.kit_name} samples verified playing',
                                 'sample_slots':sorted(self.sounds_heard)})
        self.label('Kick, snare, hats, clap, toms, perc.\nLet the finished groove play.')
        yield from self.until(max(30, self.frames/59.7275+2))

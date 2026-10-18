"""An intro-derived four-bar score and a live, button-driven arrangement demo.

Prepared notes/timbres are loaded into an isolated emulator fixture before capture.
Playback, track navigation, zoom and layer entrances then use actual buttons.
"""
from song_demo import SongDemo


def score():
    lead = [67,64,0,72,69,65,76,72,76,0,72,71,69,64,67,0,
            67,64,0,72,69,65,76,74,76,0,72,71,69,67,64,60]
    roots = [36,36,41,41,45,45,45,45] * 2
    tracks = {i: [] for i in range(7)}
    for i, note in enumerate(lead):
        if note:
            # A little breathing space; final C sustains through the turnaround.
            tracks[0].append((i*2, note, 100 if i%4==0 else 90, 2 if i==31 else 1))
    for step in range(1,64,2):
        # Intro's major/minor broken chords, with rests in the answering phrase.
        if step >= 32 and step % 8 == 7: continue
        minor = step%32 >= 16
        offsets = [0,3,7,12] if minor else [0,4,7,12]
        tracks[1].append((step, roots[step//4]+24+offsets[step%4], 82 if step%4==1 else 70, 1))
    for beat, root in enumerate(roots[:8]):
        tracks[2].append((beat*4, root+12, 95, 3))
    # Brief, low-frequency noise kicks; no sustained chromatic noise track.
    for step in [0,6,10,16,22,26]:
        tracks[3].append((step,36,92 if step%16==0 else 72,1))
    percussion = [(step,10,42 if step%4==1 else 30,1) for step in range(1,32,2)]
    percussion += [(step,11,82 if step%16==4 else 74,1) for step in [4,12,20,28]]
    return tracks, percussion


class IntroSongDemo(SongDemo):
    def __init__(self,p,symbols):
        super().__init__(p,symbols)
        self.prepared_score = True
        self.stage_times = []
        def put(name,values):
            address = self.s['_'+name]
            p.memory[address:address+len(values)] = values
        tracks,percussion = score()
        sparse = '_seqevents_lo' in self.s
        if sparse:
            import struct
            events=[];counts=[];offsets=[]
            for track in range(7):
                offsets.append(len(events))
                rows = ([(step,row+1,vel,dur) for step,row,vel,dur in percussion]
                        if track==6 else [(step,note+1,vel,dur) for step,note,vel,dur in tracks[track]])
                rows.sort()
                counts.append(len(rows));events.extend(rows)
            raw=[value for event in events for value in event]
            raw += [0]*(2048-len(raw))
            put('seqevents_lo',raw[:1024]);put('seqevents_hi',raw[1024:])
            put('seqeventcounts',list(struct.pack('<7H',*counts)))
            put('seqeventoffsets',list(struct.pack('<7H',*offsets)))
            put('seqlength',list(struct.pack('<7H',64,64,32,32,64,64,32)))
        else:
            for name in ['seqnotes','seqvelocity','seqduration']:
                put(name,[0]*384)
            for track,notes in tracks.items():
                for step,note,velocity,duration in notes:
                    for name,value in [('seqnotes',note+1),('seqvelocity',velocity),('seqduration',duration)]:
                        p.memory[self.s['_'+name]+track*64+step]=value
            put('seqlength',[64,64,32,32,64,64,32])
        put('seqbpm',[95,0])
        put('seqgate',[88,65,90,35,80,80,80])
        put('seqtop',[79,79,64,48,79,79,60])
        put('seqpitch',[72,72,53,36,72,72,60])
        put('seqmuted',[78])  # Only the lead starts audible; reveal the arrangement.
        if not sparse:
            for name in ['noisehits','noisevel','noisedur']:
                put(name,[0]*128)
            for step,row,velocity,duration in percussion:
                i=step*2+row-10
                for name,value in [('noisehits',1),('noisevel',velocity),('noisedur',duration)]:
                    p.memory[self.s['_'+name]+i]=value
        # Match the intro's 25% duty, downward envelopes and restrained balance.
        for channel,volume in [(0,10),(1,5),(3,8)]:
            address=self.s['_param']+26*channel
            for field,value in {0:1,1:volume,2:0,3:1,4:0,5:0,6:0,8:0,9:0,21:3,22:0}.items():
                p.memory[address+field]=value
        p.memory[self.s['_param']+26*3+18]=6
        p.memory[self.s['_param']+26*3+19]=0
        p.memory[self.s['_param']+26*3+20]=5
        p.memory[self.s['_param']+26*2+15]=2
        # Quiet hats and a short snare, close to the intro noise envelopes.
        put('noisepatch',[7,1,5,1,1,8,3,7,0,2])
        put('seqdrawvalid',[0]);put('dirty',[1])
        self.composition = {'key':'C major / A minor','bpm':95,
            'harmony':'C / F / Am / Am, two beats each; four-bar melodic variation',
            'lengths':[64,64,32,32,64,64,32],
            'tracks':tracks,'noise_percussion':percussion}

    def label(self,text):
        self.story=text
        self.stage_times.append({'frame':self.frames,'story':text})

    def bars(self,n):
        yield from self.wait(round(n*4*60/95*59.7275))

    def track(self,target):
        for _ in range(8):
            if self.v('seqtrack')==target:return
            yield from self.chord('select','right')
        raise RuntimeError('Track navigation failed')

    def run(self):
        self.label('A theme from the intro.\n64 steps, with room to answer.')
        yield from self.choose(8)
        yield from self.chord('select','down')
        yield from self.chord('select','down')
        yield from self.chord('select','a')
        assert self.v('seqplaying')
        yield from self.bars(4)
        self.label('C / F / Am / Am.\nA 32-step bass follows the roots.')
        yield from self.track(2)
        yield from self.chord('select','b')
        yield from self.bars(4)
        self.label('A quiet broken-chord answer.\n64 steps; fewer notes in half two.')
        yield from self.track(1)
        yield from self.chord('select','b')
        yield from self.bars(4)
        self.label('Short kicks. Soft hats. Backbeat.\n32 steps, with varied accents.')
        yield from self.track(3)
        yield from self.chord('select','b')
        yield from self.track(6)
        yield from self.chord('select','b')
        yield from self.bars(4)
        self.label('The second phrase changes.\nThe harmony holds it together.')
        yield from self.track(0)
        yield from self.bars(4)
        self.label('Let it breathe.\nFour bars before it comes home.')
        yield from self.choose(18)
        yield from self.bars(4)
        assert self.v('seqplaying') and not self.v('seqmuted') & 79

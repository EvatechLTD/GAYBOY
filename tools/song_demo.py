"""A real-button song-building performance. Memory is read only for UI feedback."""
class SongDemo:
    def __init__(self, p, symbols):
        self.p, self.s = p, symbols
        self.story = ''
        self.log = []
        self.done = False
        self.frames = 0
        self.sequence = self.run()

    def v(self, name, i=0):
        return self.p.memory[self.s['_' + name] + i]

    def step(self):
        if not self.done:
            try: next(self.sequence)
            except StopIteration: self.done = True
            self.frames += 1

    def wait(self, n):
        for _ in range(n): yield

    def key(self, key, down):
        mask = {'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'select':64,'start':128}[key]
        (self.p.button_press if down else self.p.button_release)(key)
        self.log.append({'frame':self.frames,'button':key,'down':down})
        for _ in range(600):
            yield
            if bool(self.v('lastpad') & mask) == down: break
        else: raise RuntimeError('UI did not acknowledge ' + key)
        
    def tap(self, key):
        yield from self.key(key, True)
        yield from self.key(key, False)

    def chord(self, modifier, key):
        yield from self.key(modifier, True)
        yield from self.tap(key)
        yield from self.key(modifier, False)

    def choose(self, target):
        yield from self.key('start', True)
        for _ in range(600):
            if self.v('navopen'): break
            yield
        for _ in range(32):
            if self.v('navchoice') == target: break
            yield from self.tap('down')
        assert self.v('navchoice') == target
        yield from self.key('start', False)
        yield from self.wait(8)
        assert self.v('page') == target, (target, self.v('page'))

    def pitch(self, target):
        # Piano column allows pitch scrolling without entering header/velocity UI.
        yield from self.tap('left')
        assert self.v('seqhead') == 6
        while self.v('seqpitch', self.v('seqtrack')) != target:
            yield from self.tap('up' if self.v('seqpitch', self.v('seqtrack')) < target else 'down')
        yield from self.tap('right')

    def melody(self, pitches):
        track = self.v('seqtrack')
        for i, pitch in enumerate(pitches):
            # Set pitches on grid; these melodies stay inside its visible register.
            while self.v('seqpitch',track) != pitch:
                yield from self.tap('up' if self.v('seqpitch',track)<pitch else 'down')
            if self.v('seqdefaultdur',track) == 1:
                yield from self.chord('b','right')
            else:
                yield from self.tap('b')
            assert self.v('seqnotes',track*64+i*4) == pitch+1
            if i < len(pitches)-1:
                while self.v('seqcursor',track) < (i+1)*4:
                    yield from self.tap('right')

    def run(self):
        self.story = "Let's make a song.\nStart with a pulse melody."
        yield from self.choose(16)
        yield from self.tap('a')
        assert self.v('experimental_mode')
        yield from self.choose(8)
        yield from self.chord('select','a')
        assert self.v('seqplaying')
        yield from self.melody([60,64,67,64])
        self.story = 'A second pulse answers.\nThe loop keeps playing as I edit.'
        yield from self.chord('select','right')
        yield from self.melody([60,60,64,62])
        self.story = 'Wave bass underneath.\nHold B + move to stretch notes.'
        yield from self.chord('select','right')
        yield from self.pitch(48)
        yield from self.melody([48,48,55,53])
        self.story = 'Noise adds a little grit.\nThen a second wave line.'
        yield from self.chord('select','right')
        yield from self.melody([60,60,60,60])
        yield from self.chord('select','right')
        assert self.v('seqtrack') == 5
        yield from self.melody([60,64,67,64])
        self.story = 'Sample drums + synthesized hats.\nNow it has a heartbeat.'
        yield from self.chord('select','right')
        assert self.v('seqtrack') == 6
        for row, steps in [(0,[0,8]),(3,[4,12]),(10,[0,2,4,6,8,10,12,14])]:
            while self.v('drumrow') != row:
                yield from self.tap('down' if self.v('drumrow') < row else 'up')
            for step in steps:
                while self.v('seqcursor',6) != step:
                    yield from self.tap('left' if self.v('seqcursor',6)>step else 'right')
                yield from self.tap('b')
        self.story = 'Zoom out. Mute the drums.\nBring the beat back in.'
        yield from self.chord('select','down')
        yield from self.chord('select','b')
        yield from self.wait(25)
        yield from self.chord('select','b')
        # Separate mono mode is exclusive by design, rather than a seventh layered voice.
        self.story = 'MONO5 is a separate synth mode.\nA quick solo detour.'
        yield from self.tap('select')
        yield from self.tap('left')
        yield from self.tap('left')
        assert self.v('seqfocus') == 9
        yield from self.chord('b','up')
        yield from self.tap('select')
        assert self.v('seqtrack') == 4
        yield from self.melody([60,64,67,64])
        yield from self.wait(20)
        yield from self.tap('select')
        yield from self.tap('left')
        yield from self.tap('left')
        yield from self.chord('b','down')
        yield from self.tap('select')
        self.story = 'Back to the full arrangement.\nMix, pan, and save the idea.'
        yield from self.choose(18)
        yield from self.tap('down')  # pulse 1 mute
        yield from self.tap('right') # solo
        yield from self.tap('a')
        yield from self.wait(20)
        yield from self.tap('a')
        yield from self.tap('right') # volume
        yield from self.chord('b','left')
        yield from self.tap('right') # pan
        yield from self.chord('b','down')
        yield from self.choose(20)
        yield from self.tap('b')
        assert self.v('page') == 18 and self.v('seqplaying')
        self.story = 'A whole song can start\nwith one tiny loop.'
        yield from self.wait(480)

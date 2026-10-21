"""Discrete-level drum synthesis. Only writes standalone DRUMSAMPLES assets."""
from pathlib import Path
import json
import wave
import numpy as np

ROOT = Path(__file__).resolve().parent / 'DIRECT4BIT'
RATE = 11468
# Integer oscillator values are doubled DAC amplitudes: all 16 native levels.
LUT = np.array([1,3,5,7,11,13,13,15,15,13,13,11,7,5,3,1,
                -1,-3,-5,-7,-11,-13,-13,-15,-15,-13,-13,-11,-7,-5,-3,-1])

def osc(t, frequency, phase=0):
    positions = np.cumsum(np.broadcast_to(frequency, t.shape)) / RATE
    return LUT[(np.floor(positions * 32).astype(int) + phase) % 32]

def env(t, decay):
    return np.rint(255*np.exp(-t/decay)).astype(int)

def scale(x, e):
    return np.rint(x * e / 255).astype(int)

def codes(x):
    return np.clip(np.floor_divide(x+16, 2), 0, 15).astype(np.uint8)

def decode(q):
    return (q.astype(float)-7.5)/7.5

def render(role, hard, drive):
    t = np.arange(round([.48,.25,.085,.31,.24,.30,.23,.17][role]*RATE))/RATE
    rng = np.random.default_rng(808909 + hard*100 + role)
    n = rng.integers(-7, 9, len(t))*2-1
    # Integer differences emphasize noise in the playable upper band.
    bright = np.clip(n-np.roll(n, 1), -15, 15)
    if role == 0:
        f = (61 if hard else 53)+(155 if hard else 125)*np.exp(-t/.014)
        body = osc(t, f)
        harmonic = osc(t, f*2)
        x = scale(body, env(t,.14 if hard else .18))
        x += scale(harmonic, env(t,.095)//3)
        x += scale(bright, env(t,.003)//3)
    elif role == 1:
        x = scale(osc(t, 185+85*np.exp(-t/.012)), env(t,.065))
        x += scale(osc(t, 335), env(t,.04)//3)
        x += scale(bright, env(t,.075)*(3 if hard else 2)//2)
    elif role in (2,3):
        # XOR pulse oscillators produce a discrete metallic source directly.
        pulses = [osc(t,f*(1.06 if hard else 1))>0 for f in (421,587,823,1249,1853,2683)]
        metal = np.logical_xor.reduce(pulses).astype(int)*30-15
        x = scale(metal+bright//2,env(t,.021 if role==2 else .105))
    elif role == 4:
        e = np.zeros(len(t),dtype=int)
        for start in (0,.011,.023):
            e += np.where(t>=start,env(np.maximum(t-start,0),.008),0)
        e += np.where(t>=.026,env(np.maximum(t-.026,0),.055)//2,0)
        x = scale(bright,e)
    elif role in (5,6):
        f = (112 if role==5 else 176)*(1.12 if hard else 1)+65*np.exp(-t/.018)
        x = scale(osc(t,f),env(t,.095))+scale(osc(t,f*1.58),env(t,.07)//3)
    elif hard:
        x = scale(osc(t,830)+osc(t,1470)//2+osc(t,2270)//3,env(t,.024))
    else:
        square = np.where(osc(t,540)>0,15,-15)+np.where(osc(t,800)>0,15,-15)
        x = scale(square,env(t,.055))
    x = np.rint(x*drive).astype(int)
    x[:4] = scale(x[:4],np.array([0,85,170,255]))
    fade = min(96,len(x))
    x[-fade:] = scale(x[-fade:],np.linspace(255,0,fade).astype(int))
    # No high-resolution audio master: the synthesis result is DAC codes.
    return codes(x)

def score(q, role):
    x=decode(q)
    n=min(len(x),round(.08*RATE))
    attack=x[:n]-np.mean(x[:n])
    power=np.abs(np.fft.rfft(attack*np.hanning(n)))**2
    f=np.fft.rfftfreq(n,1/RATE)
    lo,hi=[(35,450),(140,4400),(1800,5000),(1800,5000),(700,4400),(80,600),(120,850),(400,3200)][role]
    share=float(power[(f>=lo)&(f<=hi)].sum()/max(power.sum(),1e-12))
    rms=float(np.sqrt(np.mean(attack**2)))
    # Reward loudness inside each sound's useful band; constrain spectral damage.
    return rms*share**2, rms, share

def wav(path,q):
    # PCM container maps native codes to 16 exact values; no audio processing.
    pcm=((q.astype(np.int32)*2-15)*2184).astype('<i2')
    with wave.open(str(path),'wb') as w:
        w.setparams((1,2,RATE,0,'NONE','not compressed'))
        w.writeframes(pcm.tobytes())

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    combined=[]
    timeline=[]
    cursor=0
    for hard,name in enumerate(('SLAP808','SLAM909')):
        folder=ROOT/name
        folder.mkdir(exist_ok=True)
        bank=bytearray(); entries=[]; audition=[]
        roles=['KICK','SNARE','CLOSED_HAT','OPEN_HAT','CLAP','LOW_TOM','HIGH_TOM','RIM' if hard else 'COWBELL']
        for role,label in enumerate(roles):
            candidates=[(render(role,hard,d),d) for d in (1,1.25,1.5,1.8,2.2,2.7,3.3)]
            q,drive=max(candidates,key=lambda item:score(item[0],role)[0])
            objective,rms,share=score(q,role)
            stem=f'{role+1:02d}-{label}'
            wav(folder/(stem+'.wav'),q)
            padded=np.pad(q,(0,(-len(q))%32),constant_values=8)
            rotated=np.roll(padded.reshape(-1,32),1,axis=1).reshape(-1)
            packed=((rotated[::2]<<4)|rotated[1::2]).tobytes()
            (folder/(stem+'.4bit')).write_bytes(packed)
            entries.append(dict(slot=role+1,role=label,offset=len(bank),length=len(packed),samples=len(q),drive=drive,attack_rms_dbfs=round(float(20*np.log10(rms)),2),attack_useful_band_power_fraction=round(share,4),candidate_count=len(candidates)))
            bank.extend(packed)
            gap=np.full(round(RATE*.4),8,dtype=np.uint8)
            chunk=np.concatenate((q,gap))
            audition.append(chunk); combined.append(chunk)
            timeline.append(dict(kit=name,hit=label,start_seconds=round(cursor/RATE,4)))
            cursor+=len(chunk)
        silence=len(bank); bank.extend(bytes([0x88])*16)
        assert len(bank)<16300
        (folder/'kit-bank.bin').write_bytes(bank)
        (folder/'kit.json').write_text(json.dumps(dict(name=name,rate=RATE,bits=4,method='integer oscillators, integer envelopes, discrete noise; select drive by scoring final DAC codes',packing='high nibble first; 32-sample frames rotated right one',bytes=len(bank),sounds=entries,unused_rows=[dict(offset=silence,length=16)]*2),indent=2)+'\n')
        wav(folder/'LISTEN-hits-once.wav',np.concatenate(audition))
        print(name,len(bank),'bytes; selected drives:',[s['drive'] for s in entries])
    wav(ROOT/'LISTEN-ALL-16-HITS-ONCE.wav',np.concatenate(combined))
    (ROOT/'audition-order.json').write_text(json.dumps(timeline,indent=2)+'\n')
    print('Audition:',ROOT/'LISTEN-ALL-16-HITS-ONCE.wav')

if __name__=='__main__':
    main()

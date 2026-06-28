from config import ORGANIC, STEADY
import numpy as np
from soundbase import Sound
import ambient_renderer as ar

class Rain(Sound):
    def __init__(self):
        super().__init__("rain", STEADY)

    def render(self):
        return ar.white_noise(5) * 0.01


class Wind(Sound):
    def __init__(self):
        super().__init__("wind", STEADY)

    def render(self):
        return ar.wind_track(7)


class Bird(Sound):
    def __init__(self):
        super().__init__("bird", ORGANIC)
    
    def render(self):
        gap = np.zeros(int(np.random.uniform(3, 7))*self.sr) # generate silence
        call = ar.bird_call(self.sr) # generate bird chirp
        return np.concatenate([gap, call])


class Cricket(Sound):
    def __init__(self):
        super().__init__("cricket", STEADY)
    
    def render(self):
        return ar.cricket_track(7)

class Beetle(Sound):
    def __init__(self):
        super().__init__("beetle", STEADY)
    
    def render(self):
        return ar.beetle_track(7)


class Frog(Sound):
    def __init__(self):
        super().__init__("frog", ORGANIC)
    
    def render(self):
        gap = np.zeros(int(np.random.uniform(1.5, 4.5))*self.sr)
        trill = ar.grey_treefrog_trill(
            duration=np.random.uniform(0.5, 1.2),
            sample_rate=self.sr,
            rate=np.random.uniform(38, 55)          # rate varies call to call
        )

        return np.concatenate([gap, trill])


class Woodpecker(Sound):
    def __init__(self):
        super().__init__("woodpecker", ORGANIC)
    
    def render(self):
        knock_dur = 0.03

        knock = ar.biquad_bandpass(ar.white_noise(knock_dur, self.sr), self.sr, f_cutoff=1200, Q=12)

        env = ar.attack_decay(len(knock), self.sr, attack=0.0005, tau=0.01, peak=0.8)
        knock = knock * env

        roll = ar.pulse_train(knock, rate=20, duration=np.random.uniform(0.6, 1.0), sample_rate=self.sr)
        roll = roll * np.linspace(1.0, 0.4, len(roll))

        gap = np.zeros(int(np.random.uniform(1, 3))*self.sr)

        return np.concatenate([gap, roll])


class SavannahGrass(Sound):
    def __init__(self):
        super().__init__("savannah grass", ORGANIC)
    
    def render(self):
        return ar.savannah_grass(7)
    
class Cicada(Sound):
    def __init__(self):
        super().__init__("cicada", ORGANIC)
    
    def render(self):
        return ar.cicada_drone(7)


class DistantCall(Sound):
    def __init__(self):
        super().__init__("distant call", ORGANIC)
    
    def render(self):
        call = ar.distant_call(self.sr, freq=np.random.uniform(120,260), duration=np.random.uniform(0.6,1.4))
        gap = np.zeros((int(np.random.uniform(6, 16) * self.sr)))
        return np.concatenate([call, gap])


class ThunderStrike(Sound):
    def __init__(self):
        super().__init__("thunder strike", ORGANIC)
    
    def render(self):
        return ar.thunder_strike_track(duration=np.random.uniform(5, 7))

class River(Sound):
    def __init__(self):
        super().__init__("river", ORGANIC)
    
    def render(self):
        return ar.river_track(np.random.uniform(4,5))


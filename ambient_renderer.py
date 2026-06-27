import numpy as np
import sounddevice as sd


def one_pole_lowpass(sample: np.ndarray, sample_rate: int = 44_100, cutoff: float = 500) -> np.ndarray:
    alpha = 1 - np.exp(-2 * np.pi * cutoff / sample_rate)
    y = np.zeros_like(sample)
    prev = 0.0
    for n in range(len(sample)):
        prev = prev + alpha * (sample[n] - prev)
        y[n] = prev
    return y

def cascaded_lowpass(sample: np.ndarray, sample_rate: int = 44_100, cutoff: float = 500, stages: int = 4) -> np.ndarray:
    out = sample
    for _ in range(stages):
        out = one_pole_lowpass(out, sample_rate, cutoff)
    return out

def low_frequency_oscillator(duration: float= 5, phase: float= 0.0, 
                             frequency: float = 1, sample_rate: int = 44_100) -> np.ndarray:
    n = np.arange(int(duration * sample_rate))
    return np.sin(2 * np.pi * frequency * n / sample_rate + phase)

def tremolo_gain(sample: np.ndarray, sample_rate: float = 44_100, base_gain: float = 0.5,
                 depth: float = 0.2, frequency: int = 1) -> np.ndarray:
    sample_len = len(sample)
    gain = np.zeros_like(sample)
    lfo = low_frequency_oscillator(sample_len/sample_rate, frequency=frequency)
    gain = base_gain * (1 + depth * lfo)
    
    return sample * gain

def white_noise(duration:float = 5.0, sample_rate: int = 44_100, gain: float = 1) -> np.ndarray:
    # Generate random values between -1 and 1
    # well, literally just random unordered/abstract signal == noise
    noise = np.random.uniform(-1, 1, int(sample_rate * duration))
    return noise*gain

# --- for wind like sounds --- #
def brown_noise(duration: float = 5.0, sample_rate: int = 44_100,
                gain: float = 3.2, leak: float = 0.02) -> np.ndarray:
    previous_value = 0.0

    w_noise = white_noise(duration, sample_rate)
    r_noise = np.zeros_like(w_noise)

    for n in range(len(w_noise)):
        previous_value = (previous_value + leak * w_noise[n]) / (1 + leak)
        r_noise[n] = previous_value
    
    r_noise = cascaded_lowpass(r_noise, sample_rate=44100, cutoff=400)
    
    return r_noise * gain

def exp_sweep(f_start: float, f_end: float, duration: float, sample_rate: int = 44_100) -> np.ndarray:
    n = np.arange(int(duration * sample_rate))
    t = n / sample_rate
    freq = f_start * (f_end / f_start) ** (t / duration)      # exponential glide
    phase = 2 * np.pi * np.cumsum(freq) / sample_rate
    return np.sin(phase)

def attack_decay(length: int, sample_rate: int, attack: float = 0.008, tau: float = 0.04, peak: float = 0.18) -> np.ndarray:
    n = np.arange(length)
    t = n / sample_rate
    return np.where(t < attack, peak * (t / attack), peak * np.exp(-(t - attack) / tau))

def sin_wave(freq: float = 440, duration: float = 5, sample_rate: int =44_100) -> np.ndarray:
    n = np.arange(int(duration*sample_rate))
    return np.sin(2*np.pi*freq*n/sample_rate)

def biquad_bandpass(sample: np.ndarray, sample_rate: int = 44_100,
                    f_cutoff: float = 120, Q: float = 5.0) -> np.ndarray: # RBJ bandpass (constant skirt)
    omega = 2*np.pi*f_cutoff/sample_rate
    alpha = np.sin(omega)/(2*Q)
    cw = np.cos(omega)

    b0, b1, b2 = alpha, 0.0, -alpha
    a0, a1, a2 = 1+alpha, -2*cw, 1-alpha
    b0,b1,b2,a1,a2 = b0/a0,b1/a0,b2/a0,a1/a0,a2/a0

    out = np.zeros_like(sample)
    x1=x2=y1=y2=0.0

    for n in range(len(sample)):
        out[n]=b0*sample[n]+b1*x1+b2*x2-a1*y1-a2*y2
        x2,x1=x1,sample[n]
        y2,y1=y1,out[n]

    return out

def pulse_train(grain, rate, duration, sample_rate=44_100, jitter=0.0) -> np.ndarray:
    out=np.zeros(int(duration*sample_rate)); step=sample_rate/rate; pos=0.0
    while int(pos)<len(out):
        p=int(pos); end=min(p+len(grain),len(out))
        out[p:end]+=grain[:end-p]
        pos+=step*(1+np.random.uniform(-jitter,jitter))
    return out

def force_fadeout(x, sample_rate, fade_ms=15):
    fade_len = int(fade_ms/1000 * sample_rate)
    fade_len = min(fade_len, len(x))
    fade = np.linspace(1.0, 0.0, fade_len)
    x = x.copy()
    x[-fade_len:] *= fade
    return x


def bumpy_decay_envelope(length, sample_rate, base_tau=2.5, n_bumps=4):
    t = np.arange(length) / sample_rate
    env = np.exp(-t / base_tau)                     # smooth overall decay trend

    for _ in range(n_bumps):
        t0 = np.random.uniform(0, t[-1] * 0.6)       # bump can start anywhere in first 60%
        tau_b = np.random.uniform(0.15, 0.45)
        amp_b = np.random.uniform(0.3, 0.7)
        bump = np.where(t >= t0, amp_b * np.exp(-(t - t0) / tau_b), 0.0)
        env = env + bump

    return env / np.max(env)     


def time_varying_lowpass(x, sample_rate, fc_start=14000, fc_end=120, stages=4, gamma=0.4):
    n = len(x)
    duration = n / sample_rate
    t = np.arange(n) / sample_rate
    
    x_norm = t / duration
    warped = x_norm ** gamma          # gamma < 1 pushes the curve forward — fast early, slow later

    fc = fc_start * (fc_end / fc_start) ** warped

    fc = fc_start * (fc_end / fc_start) ** (t / duration)        # smooth per-sample schedule
    alpha = 1 - np.exp(-2 * np.pi * fc / sample_rate)             # smooth per-sample alpha

    y = np.zeros_like(x)
    prevs = [0.0] * stages

    for i in range(n):
        val = x[i]
        a = alpha[i]
        for s in range(stages):
            prevs[s] = prevs[s] + a * (val - prevs[s])
            val = prevs[s]
        y[i] = val

    return y

# <----- Bird ----->

def chirp_note(f_start: float, f_end: float, duration: float, sample_rate: int = 44_100, peak: float = 0.18) -> np.ndarray:
    tone = exp_sweep(f_start, f_end, duration, sample_rate)
    env = attack_decay(len(tone), sample_rate, peak=peak)
    return tone * env

def bird_call(sample_rate: int = 44_100, freq_lo: float = 1800, freq_hi: float = 4200) -> np.ndarray:
    n_notes = np.random.randint(1, 4)   # randomize bird chirp
    pieces = [] # <-- bird chirp container
    base = np.random.uniform(freq_lo, freq_hi)

    for _ in range(n_notes):
        f_start = base * np.random.uniform(0.85, 1.15)
        f_end = f_start * np.random.uniform(1.15, 1.45)     # sweep upward
        dur = np.random.uniform(0.06, 0.13)
        pieces.append(chirp_note(f_start, f_end, dur, sample_rate))
        gap = np.zeros(int(np.random.uniform(0.03, 0.08) * sample_rate))
        pieces.append(gap)

    return np.concatenate(pieces) # <--- concatenate all the clip into one track

def birds_track(duration: float, sample_rate: int = 44_100, density: float = 0.5, gain: float = 1) -> np.ndarray:
    total_samples = int(duration * sample_rate)
    out = np.zeros(total_samples)

    pos = 0
    while pos < total_samples:
        gap_seconds = np.random.exponential(scale=3.0 / (density + 0.05)) # <--- calculate silence gap first
        pos += int(gap_seconds * sample_rate) # <--- update index after silence
        if pos >= total_samples: # <--- check if current index already the end or pass the end of sample index
            break
        call = bird_call(sample_rate) # generate bird chirp
        end = min(pos + len(call), total_samples) # determine the end of clip index, clip it to the sample len
        out[pos:end] += call[: end - pos] # add it to the track

    return out * gain


# <----- Cricket ----->
def cricket_track(duration: int = 10, sample_rate: int = 44_100, gain: float = 1)-> np.ndarray:
    grain_duration = 0.012 # <--- add it as const, update it if need more control of it (the dev is just lazy)

    # this is the main thing that make the cricket sound;
    # update it as you like if you think it's still not good enough, like yourself (JK ^_~)
    grain = sin_wave(freq=4500, duration=grain_duration, sample_rate=sample_rate)
    env = attack_decay(len(grain), sample_rate, attack=0.001, tau=0.004, peak=0.5)
    grain = grain * env
    song = pulse_train(grain, rate=30, duration=duration, jitter=0.05, sample_rate=sample_rate)

    # breathing effect, just to make it more realistic.
    song = tremolo_gain(song, depth=0.4)

    return song * gain

# <----- Bird ----->
def beetle_track(duration: int = 10, sample_rate: int = 44_100, gain: float = 1.0) -> np.ndarray:
    grain = biquad_bandpass(white_noise(duration), sample_rate, fc=2500, Q=2)
    env = attack_decay(len(grain), sample_rate, tau=0.008)
    grain = grain * env
    rasp  = pulse_train(grain, rate=18, duration=duration, jitter=0.3)

    return rasp * gain


# <----- Woodpecker ----->
def woodpecker_track(duration: float = 10, clip_duration: float = 0.6,
               sample_rate: int = 44_100, rate: float = 20, gain: float = 1.0)-> np.ndarray:
    knock_dur = 0.03 # <--- again, still just const, it can be added as param if you like; note: keep it fast

    # create the knock from white noise and add biquad bandpass
    knock = biquad_bandpass(white_noise(knock_dur, sample_rate), sample_rate, fc=1200, Q=12)

    # i think it's more realistic if it has attack decay env
    env = attack_decay(len(knock), sample_rate, attack=0.0005, tau=0.01, peak=0.8)
    knock = knock * env

    track = np.zeros(int(duration * sample_rate))
    t = 0

    # generating track with KNOCKS!!!
    while t < len(track):
        roll = pulse_train(knock, rate=rate, duration=clip_duration, sample_rate=sample_rate)
        roll = roll * np.linspace(1.0, 0.4, len(roll))
        end = min(t + len(roll), len(track))
        track[t:end] += roll[:end - t]

        gap_seconds = np.random.uniform(1, 3) # <---- the silence always randomize every iteration
        t += int(gap_seconds * sample_rate)

    return track * gain

# <----- frog ----->
def frog_grain(sample_rate: int = 44_100) -> np.ndarray:
    grain_dur = 0.018
    n = int(grain_dur * sample_rate)

    pure = sin_wave(2200, grain_dur, sample_rate)                          # tonal component
    noisy = biquad_bandpass(white_noise(grain_dur, sample_rate), sample_rate, f_cutoff=2200, Q=4)  # raspy component

    grain = 0.6 * pure + 0.4 * noisy                                   # blend: more tone than noise
    env = attack_decay(n, sample_rate, attack=0.001, tau=0.006, peak=0.7)
    return grain * env

def grey_treefrog_trill(duration: float = 0.8, sample_rate: int =44_100, rate=45) -> np.ndarray:
    grain = frog_grain(sample_rate)
    trill = pulse_train(grain, rate=rate, duration=duration, sample_rate=sample_rate, jitter=0.04)
    trill *= np.linspace(0.7, 1.0, len(trill))   # slight swell into the trill, not a hard cutoff
    return trill

def grey_treefrog_track(duration: float = 10.0, sample_rate: int =44_100, gain: float = 1.0) -> np.ndarray:
    track = np.zeros(int(duration * sample_rate))
    t = 0
    while t < len(track):
        trill = grey_treefrog_trill(
            duration=np.random.uniform(0.5, 1.2),
            sample_rate=sample_rate,
            rate=np.random.uniform(38, 55)          # rate varies call to call
        )
        end = min(t + len(trill), len(track))
        track[t:end] += trill[: end - t]

        gap_seconds = np.random.uniform(1.5, 4.5)    # silence between calls
        t += int(gap_seconds * sample_rate)
    
    return track * gain

# <----- River ------>
def river_bed(duration: float, sample_rate: int =44_100, f_cutoff= 1200, Q: float=1.5) -> np.ndarray:
    noise = white_noise(duration, sample_rate)
    bed = biquad_bandpass(noise, sample_rate, f_cutoff=f_cutoff, Q=Q)   # low Q = broad, washy, not ringy

    # gentle flow-rate wobble — water volume drifting slightly, much faster/subtler than ocean swell
    mod = 1 + 0.15 * low_frequency_oscillator(duration, frequency=0.3, sample_rate=sample_rate)
    return bed * mod * 0.4 # ← put const cause lazy adding another param

def ripple_grain(sample_rate: int = 44_100) -> np.ndarray:
    grain_dur = np.random.uniform(0.02, 0.05)
    fc = np.random.uniform(1200, 4500)              # bright, varies ripple to ripple
    Q = np.random.uniform(3, 8)
    grain = biquad_bandpass(white_noise(grain_dur, sample_rate), sample_rate, fc=fc, Q=Q)
    env = attack_decay(len(grain), sample_rate, attack=0.003, tau=grain_dur*0.5,
                        peak=np.random.uniform(0.12, 0.3))
    return grain * env

def river_ripples(total, sample_rate=44_100, density=1.0) -> np.ndarray:
    track = np.zeros(int(total * sample_rate))
    t = 0
    while t < len(track):
        grain = ripple_grain(sample_rate)
        end = min(t + len(grain), len(track))
        track[t:end] += grain[:end - t]

        gap_seconds = np.random.exponential(scale=0.04 / density)   # very small gaps = near-continuous
        t += int(gap_seconds * sample_rate)
    return track

def river_track(total: float = 10.0, sample_rate: int = 44_100, density: float = 1.0, gain: float = 1.0) -> np.ndarray:
    bed = river_bed(total, sample_rate)
    ripples = river_ripples(total, sample_rate, density)
    track = bed + ripples
    return track * gain


# <----- Grass Rustle ----->
def grass_bed(duration: float, sample_rate: int = 44_100) -> np.ndarray:
    noise = white_noise(duration, sample_rate)
    bed = biquad_bandpass(noise, sample_rate, fc=2500, Q=1.2)   # bright, broad — papery, not woody

    # sway amplitude — faster cycle than wind's slow gusts, grass moves quicker than air pressure builds
    mod = 0.5 + 0.5 * low_frequency_oscillator(duration, frequency=0.15, sample_rate=sample_rate)
    return bed * mod * 0.3 # ← put const cause lazy adding another param

def crinkle_grain(sample_rate: int = 44_100) -> np.ndarray:
    grain_dur = np.random.uniform(0.008, 0.02)       # short and dry — much shorter than a river ripple
    fc = np.random.uniform(2500, 6000)               # bright/papery, higher than river's range
    grain = biquad_bandpass(white_noise(grain_dur, sample_rate), sample_rate, fc=fc, Q=np.random.uniform(2,5))
    env = attack_decay(len(grain), sample_rate, attack=0.001, tau=grain_dur*0.3, peak=np.random.uniform(0.05,0.15))
    return grain * env

def grass_rustle(duration: float, sample_rate: int =44_100, wind_level: float =0.5) -> np.ndarray:
    track= np.zeros(int(duration*sample_rate))
    t = 0
    while t < len(track):
        grain = crinkle_grain(sample_rate)
        end = min(t+len(grain), len(track))
        track[t:end] += grain[:end-t]
        gap = np.random.exponential(scale=0.08/(wind_level+0.1))   # windier → denser crinkles
        t += int(gap * sample_rate)
    return track

def savannah_grass(duration: float = 10, sample_rate: int =44_100, wind_level: float =0.5, gain: float = 1) -> np.ndarray:
    return grass_bed(duration, sample_rate) + grass_rustle(duration, sample_rate, wind_level) * gain


# <------ wildlife call ------>;
def cicada_drone(duration: float, sample_rate: int = 44_100, rate: int =22, f_cutoff: float = 3800) -> np.ndarray:
    noise = biquad_bandpass(white_noise(duration, sample_rate), sample_rate, f_cutoff, Q=8)
    pulse = 0.5 + 0.5*low_frequency_oscillator(duration, frequency=rate, sample_rate=sample_rate)
    drift = 0.15*low_frequency_oscillator(duration, frequency=0.2, sample_rate=sample_rate)
    return noise * (pulse + drift) * 0.25

def distant_call(sample_rate: int =44_100, freq: float =180, duration: float =1) -> np.ndarray:
    n = np.arange(int(duration*sample_rate))
    t = n/sample_rate
    f = freq * (0.6)**(t/duration)                    # strong downward droop
    pure = np.sin(2*np.pi*np.cumsum(f)/sample_rate)
    rasp = biquad_bandpass(white_noise(duration, sample_rate), sample_rate, fc=freq*1.3, Q=2)
    call = 0.75*pure + 0.25*rasp
    env = attack_decay(len(call), sample_rate, attack=duration*0.15, tau=duration*0.4, peak=0.5)
    return call * env

def savannah_wildlife(duration: float = 10, sample_rate: int =44_100, density: float = 0.5 , gain: float = 1) -> np.ndarray:
    track = cicada_drone(duration, sample_rate)            # continuous bed, always present
    t = 0
    while t < len(track):
        call = distant_call(sample_rate, freq=np.random.uniform(120,260), duration=np.random.uniform(0.6,1.4)) # <--- freq and duration range can be updated
        end = min(t+len(call), len(track))
        track[t:end] += call[:end-t]
        gap = np.random.uniform(6, 18) / (density+0.1)   # long silences between far-off calls
        t += int(gap*sample_rate)
    return track * gain


# <------  THUNDER STRIKEEE!!! YEAH ----->
def thunder_strike_track(duration: float = 10, clip_duration:float =6.5, sample_rate: int = 44_100, onset = 0.6, gain: float = 1) -> np.ndarray:
    pad = int(onset * sample_rate)
    body_len = int((clip_duration - onset) * sample_rate)

    noise = white_noise(clip_duration - onset, sample_rate)
    env = bumpy_decay_envelope(body_len, sample_rate)
    shaped = noise * env

    filtered = time_varying_lowpass(shaped, sample_rate, fc_start=10000, fc_end=60)

    track = np.zeros(int(duration * sample_rate))
    track[pad:pad+len(filtered)] = filtered
    return track * gain


# <------ WIND ------>
def wind_track(duration: float = 10, gain: float = 1) -> np.ndarray:
    track = brown_noise(duration, gain=4)
    return tremolo_gain(track) * gain

def thunder_storm(duration: float = 10) -> np.ndarray:
    out = wind_track(duration)
    out += white_noise(duration, gain=0.1)
    out += thunder_strike_track(duration, gain=4)
    out += grey_treefrog_track(duration)
    return out

# def night_rain(duration: float = 10.0):
#     wind = brown_noise(duration, gain=4)
#     rain = white_noise(duration, gain=0.7)
#     wind = tremolo_gain(wind, 44_100)
#     bird = birds_track(duration, gain=0)
#     out = wind+rain+bird
#     return out

# def open_meadow(duration: float = 10.0):
#     wind = brown_noise(duration, gain=4)
#     rain = white_noise(duration, gain=0.1)
#     wind = tremolo_gain(wind, 44_100)
#     bird = birds_track(duration, gain=6)
#     cricket = cricket_sound(duration)
#     out = wind+rain+bird+cricket
#     return out

# def forest_dawn():
#     pass

# def savannah_scene(total=30.0, sample_rate=44_100, wind_level=0.4, wildlife_density=0.5):
#     grass = savannah_grass(total, sample_rate, wind_level)
#     wildlife = savannah_wildlife(total, sample_rate, wildlife_density)
#     return grass + wildlife

if __name__== "__main__":
    out = thunder_storm()

    sd.play(out, 44_100)
    sd.wait()
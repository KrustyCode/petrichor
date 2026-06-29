# this is should be the audio engine that will be integrated with interface or app.py
import numpy as np
import threading
import sounddevice as sd
import config

"""
Ambient soundscape engine — real-time, block-based mixer.

Design
------
Audio is produced in fixed blocks of BLOCK frames. sounddevice pulls
one block per callback. We never stream a long file; instead every layer owns
a short buffer that is read from (and refreshed) on the fly.

Each Sound owns:
    container : the most recently rendered float32 buffer (ANY length)
    index     : read cursor into that container (where we left off last block)
    kind      : ORGANIC  -> re-render a NEW buffer every time the cursor runs
                            out, with randomized pitch/duration (organic feel).
                            Bake the silent GAP into the front of event sounds
                            (droplets, birds) so timing varies too.
                STEADY   -> loop the SAME buffer (cursor wraps mod len) and only
                            re-render when a param changes (dirty flag).

Two distinct indices — don't conflate them:
    BLOCK = size of self.out, the output handed to sounddevice. Fixed.
    self.index   = per-sound read cursor. Wraps mod len(container),

Filling one output block may cross a container boundary (a sound can end
mid-block, leaving < BLOCK samples). So add_into() copies in PIECES: take
what's left, refresh/wrap, take more, until the block is full.
"""

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class Engine:
    def __init__(self, sr=config.SR, block=config.BLOCK):
        self.sr = sr
        self.block = block
        self.out = np.zeros(block, dtype=np.float32)    # the 1024-frame output
        self.sounds = {}                                # name -> Sound
        self.master = 0.9
        self.lock = threading.Lock()                    # guard param vs callback
        self.stream = None

    def add_sound(self, sound):
        self.sounds[sound.name] = sound

    def set_level(self, name, level):
        with self.lock:
            s = self.sounds[name]
            s.level = float(level)

    # called by sounddevice on the audio thread; must be fast & non-blocking
    def _callback(self, outdata, frames, time_info, status):
        if status:
            print("stream status:", status)
        with self.lock:
            self.out.fill(0.0)                          # start block from silence
            for s in self.sounds.values():
                s.add_into(self.out)                    # sum each layer in
            self.out *= self.master
            np.clip(self.out, -1.0, 1.0, out=self.out)  # avoid clipping/wrap
        outdata[:, 0] = self.out                        # mono -> (frames, ch)

    def start(self):
        # 1) start every renderer thread so buffers start filling up NOW,
        #    before the audio device is even opened
        for s in self.sounds.values():
            s.start_renderer()
 
        # 2) prime: block here (main thread, no deadline pressure) until each
        #    sound has produced at least one real buffer
        for s in self.sounds.values():
            ok = s.prime(timeout=2.0)
            if not ok:
                print(f"warning: '{s.name}' did not produce a buffer in time")
 
        # 3) only now open the stream -- first callback already has real data
        self.stream = sd.OutputStream(
            samplerate=self.sr,
            blocksize=self.block,
            channels=config.CHANNELS,
            dtype="float32",
            callback=self._callback,
        )
        self.stream.start()
    
    def pause(self):
        if self.stream and self.stream.active:
            self.stream.stop()
        # renderer threads keep running -- queues stay topped up, so resume
        # is instant with no re-priming needed
 
    def resume(self):
        if self.stream and not self.stream.active:
            self.stream.start()
 
    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        for s in self.sounds.values():
            s.stop_renderer()
 

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import time
    import sounds as s
    eng = Engine()
    eng.add_sound(s.Rain())
    eng.add_sound(s.Wind())
    eng.add_sound(s.Bird())
    eng.add_sound(s.Cricket())
    eng.add_sound(s.Woodpecker())
    eng.add_sound(s.Frog())
    eng.add_sound(s.SavannahGrass())
    eng.add_sound(s.Cicada())
    eng.add_sound(s.DistantCall())
    eng.add_sound(s.ThunderStrike())

    eng.set_level("rain", 0.2)
    eng.set_level("wind", 0.6)
    eng.set_level("bird", 0.0)   # try raising this after a few seconds
    eng.set_level("cicada", 0.2)
    eng.set_level("woodpecker", 0.5)
    eng.set_level("frog", 0.7)

    eng.start()
    print("playing — Ctrl+C to stop")
    try:
        time.sleep(4)
        eng.set_level("bird", 0.5)   # param change -> takes effect next block
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        eng.stop()
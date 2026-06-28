import config
import numpy as np
from config import ORGANIC, QUEUE_DEPTH, SR
import time
import queue
import threading

class Sound:
    def __init__(self, name, kind, sr=SR):
        self.name = name
        self.kind = kind
        self.sr = sr
 
        self.current = np.zeros(0, dtype=np.float32)   # buffer audio thread reads from
        self.index = 0                                  # read cursor into self.current
        self.level = 0.0                                # gain, 0..1
 
        self.params = {}
        self.dirty = True                               # STEADY: "params changed, re-render"
        self._param_lock = threading.Lock()             # guards params/dirty (UI thread vs renderer thread)
 
        self.queue = queue.Queue(maxsize=QUEUE_DEPTH)    # renderer -> audio handoff (thread-safe)
 
        self._running = False
        self._thread = None
 
    # -- override per sound ---------------------------------------------
    def render(self):
        """
        Build and RETURN a float32 ndarray (roughly unit amplitude; gain is
        applied later via self.level). Runs on the renderer thread only --
        never on the audio thread. Safe to be "slow" (a few ms) here.
 
        ORGANIC: randomize pitch/duration/gap each call.
        STEADY : read self.params (take the lock briefly) and build from it.
        """
        raise NotImplementedError
 
    # -- renderer thread (background) ------------------------------------
    def _renderer_loop(self):
        while self._running:
            if self.kind == ORGANIC:
                buf = self.render()
                assert buf is not None, f"{self.name}.render() returned None!"
                try:
                    self.queue.put(buf, timeout=0.5)   # blocks if queue is full (backpressure)
                except queue.Full:
                    pass  # consumer is behind; drop and try again next pass
            else:  # STEADY
                with self._param_lock:
                    need_render = self.dirty
                    self.dirty = False
                if not need_render:
                    time.sleep(0.02)   # nothing changed -> idle, don't burn CPU
                    continue
                buf = self.render()
                assert buf is not None, f"{self.name}.render() returned None!"
                # replace (don't accumulate) pending buffers for STEADY sounds
                while not self.queue.empty():
                    try:
                        self.queue.get_nowait()
                    except queue.Empty:
                        break
                try:
                    self.queue.put(buf, timeout=0.5)
                except queue.Full:
                    pass
 
    def start_renderer(self):
        self._running = True
        self._thread = threading.Thread(target=self._renderer_loop, daemon=True)
        self._thread.start()
 
    def stop_renderer(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self._thread = None
 
    def prime(self, timeout=2.0):
        """
        Block on the MAIN thread (before sd stream starts) until at least one
        real buffer is ready. This is what prevents the very first callback
        from finding an empty container.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.current = self.queue.get(timeout=0.05)
                self.index = 0
                return True
            except queue.Empty:
                continue
        return False  # renderer didn't produce anything in time -- caller should know
 
    # -- audio thread only: must be FAST, never call render(), never block --
    def _advance(self):
        if self.kind == ORGANIC:
            if self.index >= len(self.current):
                try:
                    self.current = self.queue.get_nowait()   # pre-rendered already -> instant
                    self.index = 0
                except queue.Empty:
                    # renderer fell behind: contribute silence this block rather
                    # than block/crash. (If this keeps happening, raise QUEUE_DEPTH
                    # or speed up render().)
                    self.current = np.zeros(0, dtype=np.float32)
        else:  # STEADY
            if self.index >= len(self.current) and len(self.current) > 0:
                self.index = 0   # loop the buffer we already have
            try:
                self.current = self.queue.get_nowait()   # swap in a fresher buffer if ready
                self.index = 0
            except queue.Empty:
                pass
 
    def add_into(self, out):
        """Mix this layer's contribution into out[] (length BLOCK)."""
        if self.level <= 0.0:
            return
        n = len(out)
        filled = 0
        while filled < n:
            self._advance()
            buf = self.current
            if len(buf) == 0:
                break
            remaining = len(buf) - self.index
            take = min(n - filled, remaining)
            out[filled:filled + take] += buf[self.index:self.index + take] * self.level
            self.index += take
            filled += take
 
    # -- called from the UI/control thread ---------------------------------
    def set_params(self, **kw):
        with self._param_lock:
            self.params.update(kw)
            self.dirty = True
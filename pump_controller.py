import time


class PumpController:
    """
    Minimal pump controller with hysteresis and min run/off timers.
    - If level <= on_threshold and min_off time has elapsed -> start pump
    - Once running, keep pump on for at least min_run seconds
    - Stop when level >= off_threshold and min_run elapsed
    """

    def __init__(self, on_threshold: float, off_threshold: float, min_run_seconds: int, min_off_seconds: int):
        assert off_threshold > on_threshold, "off_threshold must be greater than on_threshold"
        self.on_thresh = float(on_threshold)
        self.off_thresh = float(off_threshold)
        self.min_run = int(min_run_seconds)
        self.min_off = int(min_off_seconds)
        self._running = False
        self._last_change = 0.0
        self._last_off = 0.0

    def is_running(self) -> bool:
        return self._running

    def _can_start(self) -> bool:
        return (time.time() - self._last_off) >= self.min_off

    def _start(self):
        self._running = True
        self._last_change = time.time()

    def _stop(self):
        self._running = False
        self._last_change = time.time()
        self._last_off = self._last_change

    def tick(self, level_percent: float):
        now = time.time()
        if not self._running:
            if level_percent <= self.on_thresh and self._can_start():
                self._start()
        else:
            if (now - self._last_change) < self.min_run:
                return
            if level_percent >= self.off_thresh:
                self._stop()

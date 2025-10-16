import time


class PumpController:
    """
    Minimal pump controller with hysteresis and min run/off timers.
    - If level <= on_threshold and min_off time has elapsed -> start pump
    - Once running, keep pump on for at least min_run seconds
    - Stop when level >= off_threshold and min_run elapsed
    - Optional hard_off_percent: stop immediately if level >= hard_off_percent (safety override)
    """

    def __init__(self, on_threshold: float, off_threshold: float, min_run_seconds: int, min_off_seconds: int, hard_off_percent: float | None = None):
        assert off_threshold > on_threshold, "off_threshold must be greater than on_threshold"
        self.on_thresh = float(on_threshold)
        self.off_thresh = float(off_threshold)
        self.min_run = int(min_run_seconds)
        self.min_off = int(min_off_seconds)
        self.hard_off = float(hard_off_percent) if hard_off_percent is not None else None
        self._running = False
        self._last_change = 0.0
        # Initialize last_off far in the past so the first start after boot isn't blocked by min_off
        self._last_off = -1e9

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
            # Safety override: stop immediately if a hard off threshold is defined and exceeded
            if self.hard_off is not None and level_percent >= self.hard_off:
                self._stop()
                return
            # Normal minimum run enforcement
            if (now - self._last_change) < self.min_run:
                return
            if level_percent >= self.off_thresh:
                self._stop()

import time
from datetime import datetime
from typing import Optional


class PumpController:
    def __init__(
        self,
        relay,
        on_threshold: float,
        off_threshold: float,
        min_run_seconds: int,
        min_off_seconds: int,
        soft_start_delay_seconds: int = 0,
        status_publish_period_s: int = 10,
        logger=None,
    ):
        assert off_threshold > on_threshold, "off_threshold must be greater than on_threshold for hysteresis"
        self.relay = relay
        self.on_thresh = on_threshold
        self.off_thresh = off_threshold
        self.min_run = min_run_seconds
        self.min_off = min_off_seconds
        self.soft_start = soft_start_delay_seconds
        self.logger = logger

        self._last_change = 0.0
        self._last_off = 0.0
        self._running = False
        self._soft_start_target: Optional[float] = None

    def is_running(self) -> bool:
        return self._running

    def can_start(self) -> bool:
        return (time.time() - self._last_off) >= self.min_off

    def _start(self):
        if self.soft_start > 0:
            self._soft_start_target = time.time() + self.soft_start
        else:
            self.relay.on()
            self._running = True
            self._last_change = time.time()
            if self.logger:
                self.logger.log_event(datetime.now(), 'PUMP_ON')

    def _stop(self):
        self.relay.off()
        self._running = False
        self._last_change = time.time()
        self._last_off = self._last_change
        if self.logger:
            self.logger.log_event(datetime.now(), 'PUMP_OFF')

    def tick(self, level_percent: float):
        now = time.time()

        # Handle pending soft-start
        if self._soft_start_target is not None:
            if now >= self._soft_start_target:
                self.relay.on()
                self._running = True
                self._last_change = now
                if self.logger:
                    self.logger.log_event(datetime.now(), 'PUMP_ON')
                self._soft_start_target = None
            # While waiting for soft start, do not evaluate other logic
            return

        if not self._running:
            # Decide to start based on hysteresis ON threshold and min off time
            if level_percent <= self.on_thresh and self.can_start():
                self._start()
        else:
            # Enforce minimum run time
            if (now - self._last_change) < self.min_run:
                return
            # Decide to stop based on hysteresis OFF threshold
            if level_percent >= self.off_thresh:
                self._stop()

    def shutdown(self):
        # Ensure pump is off
        if self._running:
            self._stop()

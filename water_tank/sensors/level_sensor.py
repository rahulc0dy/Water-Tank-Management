import random
import time
from collections import deque
from statistics import mean, median
from typing import Deque, Optional


class LevelSensor:
    """
    Provides a normalized level percentage [0..100]. Supports:
    - digital_threshold: reads a GPIO digital input where 1 means above threshold; maps to 0/100 with smoothing.
    - analog_percent: expects an external adapter to set self._sim_level or override read_raw_percent().
    - For simulation, we generate a slowly varying level.
    """

    def __init__(self, gpio, sensor_type: str, pin: Optional[int], smoothing_cfg: dict, calibration: dict, simulate: bool = False):
        self.gpio = gpio
        self.type = sensor_type
        self.pin = pin
        self.simulate = simulate
        self.window = max(1, int(smoothing_cfg.get('window', 5)))
        self.period_ms = int(smoothing_cfg.get('period_ms', 1000))
        self.method = smoothing_cfg.get('method', 'median_ma')
        self.buffer: Deque[float] = deque(maxlen=self.window)
        self._last_sample = 0.0
        self._sim_level = 50.0
        self._sim_trend = -0.1
        self.cal_min = float(calibration.get('min_percent', 0))
        self.cal_max = float(calibration.get('max_percent', 100))

        if self.type == 'digital_threshold' and self.pin is not None:
            # Configure pin as input; pull-up/down choice depends on sensor wiring; default no pull here.
            try:
                pud = getattr(self.gpio, 'PUD_UP', None)
                self.gpio.setup(self.pin, self.gpio.IN, pull_up_down=pud)
            except Exception:
                self.gpio.setup(self.pin, self.gpio.IN)

    def read_raw_percent(self) -> float:
        if self.simulate:
            # Simple simulation: drift level and bounce at 0/100
            self._sim_level += self._sim_trend + random.uniform(-0.05, 0.05)
            if self._sim_level <= 0:
                self._sim_level = 0
                self._sim_trend = +0.2
            elif self._sim_level >= 100:
                self._sim_level = 100
                self._sim_trend = -0.2
            return self._sim_level

        if self.type == 'digital_threshold':
            if self.pin is None:
                return 0.0
            val = self.gpio.input(self.pin)
            return 100.0 if val else 0.0
        elif self.type == 'analog_percent':
            # Placeholder: in real use, integrate with ADC or ultrasonic driver to get percent
            return max(0.0, min(100.0, self._sim_level))
        else:
            # Custom types should override this method
            return max(0.0, min(100.0, self._sim_level))

    def _smooth(self, value: float) -> float:
        if self.method == 'none' or self.window <= 1:
            return value
        self.buffer.append(value)
        if self.method == 'ma':
            return mean(self.buffer)
        if self.method == 'median':
            return median(self.buffer)
        if self.method == 'median_ma':
            # Median of recent, then average with previous mean for smoothing
            med = median(self.buffer)
            return (med + mean(self.buffer)) / 2.0
        return mean(self.buffer)

    def sample(self):
        now = time.time() * 1000
        if now - self._last_sample >= self.period_ms:
            raw = self.read_raw_percent()
            smoothed = self._smooth(raw)
            # clamp to calibration range then normalize 0..100
            smoothed = max(self.cal_min, min(self.cal_max, smoothed))
            if self.cal_max > self.cal_min:
                smoothed = 100.0 * (smoothed - self.cal_min) / (self.cal_max - self.cal_min)
            self.buffer.append(smoothed)
            self._last_sample = now

    def get_level_percent(self) -> float:
        if not self.buffer:
            # Prime buffer with initial reading
            val = self.read_raw_percent()
            self.buffer.append(val)
            return val
        return max(0.0, min(100.0, self.buffer[-1]))

    def set_sim_level(self, percent: float):
        self._sim_level = max(0.0, min(100.0, percent))

    def shutdown(self):
        pass

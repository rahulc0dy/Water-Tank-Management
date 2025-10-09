import time
from typing import Optional


class MockGPIO:
    BCM = 'BCM'
    BOARD = 'BOARD'
    IN = 'IN'
    OUT = 'OUT'
    PUD_UP = 'PUD_UP'
    PUD_DOWN = 'PUD_DOWN'

    def __init__(self):
        self.mode = self.BCM
        self.pins = {}
        self.pull = {}
        self.levels = {}

    def setmode(self, mode):
        self.mode = mode

    def setup(self, pin: int, direction: str, pull_up_down: Optional[str] = None, initial: Optional[int] = None):
        self.pins[pin] = direction
        self.pull[pin] = pull_up_down
        if initial is not None:
            self.levels[pin] = 1 if initial else 0

    def input(self, pin: int) -> int:
        return self.levels.get(pin, 0)

    def output(self, pin: int, value: int):
        self.levels[pin] = 1 if value else 0

    def cleanup(self):
        pass


def get_gpio(simulate: bool, mode: str = 'BCM'):
    if simulate:
        gpio = MockGPIO()
        gpio.setmode(mode)
        return gpio
    try:
        import RPi.GPIO as RGPIO  # type: ignore
        RGPIO.setmode(RGPIO.BCM if mode == 'BCM' else RGPIO.BOARD)
        return RGPIO
    except Exception:
        # Fallback to mock if running off Pi
        gpio = MockGPIO()
        gpio.setmode(mode)
        return gpio

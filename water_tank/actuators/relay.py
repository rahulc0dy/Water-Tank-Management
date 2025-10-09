import time


class Relay:
    def __init__(self, gpio, pin: int, active_high: bool = False):
        self.gpio = gpio
        self.pin = pin
        self.active_high = active_high
        self.state = False
        initial = 1 if (self.active_high and self.state) else 0
        try:
            self.gpio.setup(self.pin, self.gpio.OUT, initial=initial)
        except Exception:
            self.gpio.setup(self.pin, self.gpio.OUT)
            self.gpio.output(self.pin, initial)

    def on(self):
        self.state = True
        self.gpio.output(self.pin, 1 if self.active_high else 0)

    def off(self):
        self.state = False
        self.gpio.output(self.pin, 0 if self.active_high else 1)

    def is_on(self) -> bool:
        return self.state

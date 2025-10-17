import RPI.GPIO as _GPIO


# ---------- Relay control ----------

def relay_on(pin, is_active_high = False):
    _GPIO.output(pin, _GPIO.HIGH if is_active_high else _GPIO.LOW)


def relay_off(pin, is_active_high = False):
    _GPIO.output(pin, _GPIO.LOW if is_active_high else _GPIO.HIGH)
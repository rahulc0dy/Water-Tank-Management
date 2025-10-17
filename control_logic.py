import time

import RPI.GPIO as _GPIO

from config import *
from data_collection import append_row
from sensors import read_ultrasonic_sensor


def normal_mode(smoothing, stop):
    while not stop:
        # Read sensor(s)
        try:
            distance_cm = read_ultrasonic_sensor(ULTRASONIC_TRIG_PIN, ULTRASONIC_ECHO_PIN)
        except Exception:
            # sensor read failed; skip this iteration
            time.sleep(LOOP_PERIOD_S)
            continue

        # Convert distance to a normalized level percentage (0..100)
        # clamp distance between full and empty
        d = max(min(distance_cm, ULTRA_EMPTY_DISTANCE_CM), ULTRA_FULL_DISTANCE_CM)
        pct = 100.0 * (1.0 - (d - ULTRA_FULL_DISTANCE_CM) / (ULTRA_EMPTY_DISTANCE_CM - ULTRA_FULL_DISTANCE_CM))
        smoothing.append(pct)
        smoothed_pct = sum(smoothing) / len(smoothing)

        # Determine pump status (read actual relay pin state)
        relay_state = _GPIO.input(PUMP_RELAY_PIN)
        # translate to boolean based on active high/low
        pump_on = bool(relay_state == _GPIO.HIGH) if RELAY_ACTIVE_HIGH else bool(relay_state == _GPIO.LOW)

        # Log data
        append_row(smoothed_pct, pump_on)

        # wait until next loop
        time.sleep(LOOP_PERIOD_S)


def leak_detection_mode():
    pass
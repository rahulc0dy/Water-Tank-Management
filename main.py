import os
import signal
import sys
import time
from collections import deque
from datetime import datetime, date, timedelta

import RPi.GPIO as GPIO

from actuators import *
from config import *
from sensors import read_ultrasonic_sensor
from data_collection import init_log, append_row
from collections import deque


def configure_hardware():
    GPIO.setmode(GPIO_MODE)

    GPIO.setup(ULTRASONIC_TRIG_PIN, GPIO.OUT)
    GPIO.setup(ULTRASONIC_ECHO_PIN, GPIO.IN)
    GPIO.output(ULTRASONIC_TRIG_PIN, GPIO.LOW)

    GPIO.setup(PUMP_RELAY_PIN, GPIO.OUT)
    initial_off_level = GPIO.LOW if RELAY_ACTIVE_HIGH else GPIO.HIGH
    GPIO.setup(PUMP_RELAY_PIN, GPIO.OUT, initial=initial_off_level)
    relay_off(PUMP_RELAY_PIN, RELAY_ACTIVE_HIGH)



def main():

    configure_hardware()
    # prepare data log
    init_log()

    # smoothing buffer for water level readings
    smoothing = deque(maxlen=SMOOTHING_WINDOW)

    # Graceful shutdown
    stop = False

    def handle_sig(signum, frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    last_status = 0.0

    try:
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
            relay_state = GPIO.input(PUMP_RELAY_PIN)
            # translate to boolean based on active high/low
            pump_on = bool(relay_state == GPIO.HIGH) if RELAY_ACTIVE_HIGH else bool(relay_state == GPIO.LOW)

            # Log data
            append_row(smoothed_pct, pump_on)

            # wait until next loop
            time.sleep(LOOP_PERIOD_S)
    finally:
        relay_off(PUMP_RELAY_PIN, RELAY_ACTIVE_HIGH)
        GPIO.cleanup()


if __name__ == "__main__":
    sys.exit(main())

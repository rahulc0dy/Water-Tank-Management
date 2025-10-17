import os
import signal
import sys

import RPi.GPIO as GPIO

from actuators import *
from config import *
from control_logic import normal_mode
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

    try:
        normal_mode(smoothing, stop)
    finally:
        relay_off(PUMP_RELAY_PIN, RELAY_ACTIVE_HIGH)
        GPIO.cleanup()


if __name__ == "__main__":
    sys.exit(main())

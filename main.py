import os
import signal
import sys
import time
from collections import deque
from datetime import datetime, date, timedelta

import RPi.GPIO as GPIO

from actuators import *

# GPIO numbering mode
GPIO_MODE = GPIO.BCM  # or GPIO.BOARD

# Relay configuration
PUMP_RELAY_PIN = 27     # Relay input pin controlling pump contactor/SSR
RELAY_ACTIVE_HIGH = False  # Most 5V relay boards are active-low

# Ultrasonic sensor configuration
ULTRASONIC_TRIG_PIN = 23
ULTRASONIC_ECHO_PIN = 24
ULTRA_FULL_DISTANCE_CM = 15.0
ULTRA_EMPTY_DISTANCE_CM = 115.0
ULTRA_PINGS = 5
ULTRA_TIMEOUT_S = 0.03

# Control thresholds and timers
ON_THRESHOLD_PERCENT = 25   # Turn pump ON at/below this level
OFF_THRESHOLD_PERCENT = 80  # Turn pump OFF at/above this level
HARD_OFF_PERCENT = 99.0     # Safety override: force immediate OFF at/above this level
MIN_RUN_SECONDS = 180       # Minimum runtime once started
MIN_OFF_SECONDS = 120       # Minimum off time between starts

# Level smoothing
SMOOTHING_WINDOW = 5        # moving average window (samples)
LOOP_PERIOD_S = 1.0         # main loop period
STATUS_EVERY_S = 1         # how often to print status

# Tank & analytics
TANK_CAPACITY_L = 1000.0    # liters; set to your tank size
DATA_DIR = 'data'
LOG_FILE = os.path.join(DATA_DIR, 'log.csv')

# Leak detection (no flow meter)
LEAK_SCAN_HOUR = 2          # 24h clock; daily scan start
LEAK_SCAN_MINUTE = 0
LEAK_SCAN_DURATION_MIN = 45 # minutes
LEAK_DROP_THRESHOLD_PCT = 2.0  # if level drops >= this during scan -> possible leak
LEAK_ENABLE = True
# ===== End settings =====


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
            # Actual Control Logic Here
            pass
    finally:
        relay_off(PUMP_RELAY_PIN, RELAY_ACTIVE_HIGH)
        GPIO.cleanup()


if __name__ == "__main__":
    sys.exit(main())

import os
import signal
import sys
import time
from collections import deque
from datetime import datetime, date, timedelta

import RPi.GPIO as _GPIO

# ---------- Sensor reading ----------

def read_ultrasonic_sensor(trig_pin, echo_pin):
    """
    Read the ultrasonic sensor
    :return: distance in cm
    """
    _GPIO.output(trig_pin, _GPIO.LOW)
    time.sleep(0.00001)
    _GPIO.output(trig_pin, _GPIO.HIGH)
    time.sleep(0.00001)
    _GPIO.output(trig_pin, _GPIO.LOW)

    while _GPIO.input(echo_pin) == 0:
        emit_time = time.time()
    while _GPIO.input(echo_pin) == 1:
        bounce_back_time = time.time()

    pulse_duration = bounce_back_time - emit_time
    distance = round(pulse_duration * 17150, 2)
    return distance


if __name__ == "__main__":
    distance_read = read_ultrasonic_sensor()
    print("Distance:", str(distance_read), "cm")

import os
import signal
import sys
import time
from collections import deque
from datetime import datetime, date, timedelta

import RPi.GPIO as GPIO  # Requires running on Raspberry Pi
from pump_controller import PumpController

"""
Ultra-simple water tank manager (still only 2 files) with restored features:
- Automatic pump ON/OFF with hysteresis and min run/off timers (PumpController)
- Optional ultrasonic level sensing (digital or ultrasonic)
- Smoothed level readings (moving average)
- Leak detection scan (nightly window, no flow meter)
- Daily/weekly consumption tracking and simple prediction
- Lightweight CSV logging

Edit the constants below, then run:  python3 main.py
"""

# ===== User-editable settings =====
# GPIO numbering mode
GPIO_MODE = GPIO.BCM  # or GPIO.BOARD

# Sensor selection: 'digital' or 'ultrasonic'
SENSOR_MODE = 'ultrasonic'

# Pins
LEVEL_SENSOR_PIN = 17   # Used when SENSOR_MODE == 'digital'
PUMP_RELAY_PIN = 27     # Relay input pin controlling pump contactor/SSR
RELAY_ACTIVE_HIGH = False  # Most 5V relay boards are active-low

# Ultrasonic settings (used when SENSOR_MODE == 'ultrasonic')
ULTRASONIC_TRIG_PIN = 23
ULTRASONIC_ECHO_PIN = 24
ULTRA_FULL_DISTANCE_CM = 15.0    # Distance sensor->water at FULL
ULTRA_EMPTY_DISTANCE_CM = 115.0  # Distance sensor->water at EMPTY
ULTRA_PINGS = 5                  # median of this many pings per sample
ULTRA_TIMEOUT_S = 0.03

# Control thresholds and timers
ON_THRESHOLD_PERCENT = 25   # Turn pump ON at/below this level
OFF_THRESHOLD_PERCENT = 80  # Turn pump OFF at/above this level
MIN_RUN_SECONDS = 180       # Minimum runtime once started
MIN_OFF_SECONDS = 120       # Minimum off time between starts

# Level smoothing
SMOOTHING_WINDOW = 5        # moving average window (samples)
LOOP_PERIOD_S = 1.0         # main loop period
STATUS_EVERY_S = 10         # how often to print status

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


# ---------- Sensor reading ----------

def _map_distance_to_percent(d_cm: float) -> float:
    d_cm = max(ULTRA_FULL_DISTANCE_CM, min(ULTRA_EMPTY_DISTANCE_CM, d_cm))
    span = (ULTRA_EMPTY_DISTANCE_CM - ULTRA_FULL_DISTANCE_CM)
    if span <= 0:
        return 0.0
    pct = 100.0 * (ULTRA_EMPTY_DISTANCE_CM - d_cm) / span
    return max(0.0, min(100.0, pct))


def _ultra_ping_cm() -> float:
    # Send 10us trigger pulse
    GPIO.output(ULTRASONIC_TRIG_PIN, GPIO.LOW)
    time.sleep(0.000002)
    GPIO.output(ULTRASONIC_TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(ULTRASONIC_TRIG_PIN, GPIO.LOW)

    # Wait for echo high
    start = time.monotonic()
    while GPIO.input(ULTRASONIC_ECHO_PIN) == 0:
        if time.monotonic() - start > ULTRA_TIMEOUT_S:
            return float('inf')
    # Measure high pulse
    start = time.monotonic()
    while GPIO.input(ULTRASONIC_ECHO_PIN) == 1:
        if time.monotonic() - start > ULTRA_TIMEOUT_S:
            return float('inf')
    width = time.monotonic() - start
    return (width * 34300.0) / 2.0  # cm


def _read_ultrasonic_percent() -> float:
    vals = []
    for _ in range(max(1, int(ULTRA_PINGS))):
        d = _ultra_ping_cm()
        if d != float('inf'):
            vals.append(d)
        time.sleep(0.02)
    if not vals:
        return 0.0 if SENSOR_MODE == 'digital' else 0.0
    # median
    vals.sort()
    d = vals[len(vals)//2]
    return _map_distance_to_percent(d)


def _read_digital_percent() -> float:
    val = GPIO.input(LEVEL_SENSOR_PIN)
    return 100.0 if val else 0.0


def read_level_percent_raw() -> float:
    if SENSOR_MODE == 'ultrasonic':
        return _read_ultrasonic_percent()
    else:
        return _read_digital_percent()


# ---------- Relay control ----------

def relay_on():
    GPIO.output(PUMP_RELAY_PIN, GPIO.HIGH if RELAY_ACTIVE_HIGH else GPIO.LOW)


def relay_off():
    GPIO.output(PUMP_RELAY_PIN, GPIO.LOW if RELAY_ACTIVE_HIGH else GPIO.HIGH)


# ---------- Analytics helpers ----------

def ensure_log_header():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('timestamp,level_percent,pump_on\n')


def append_log(ts: datetime, level_pct: float, pump_on: bool):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{ts.isoformat()},{level_pct:.2f},{1 if pump_on else 0}\n")


def main():
    # GPIO setup
    GPIO.setmode(GPIO_MODE)

    if SENSOR_MODE == 'ultrasonic':
        GPIO.setup(ULTRASONIC_TRIG_PIN, GPIO.OUT)
        GPIO.setup(ULTRASONIC_ECHO_PIN, GPIO.IN)
        GPIO.output(ULTRASONIC_TRIG_PIN, GPIO.LOW)
    else:
        GPIO.setup(LEVEL_SENSOR_PIN, GPIO.IN, pull_up_down=getattr(GPIO, 'PUD_UP', None))

    # Initialize relay output to OFF
    initial_level = GPIO.HIGH if (RELAY_ACTIVE_HIGH is True and False) else GPIO.LOW
    GPIO.setup(PUMP_RELAY_PIN, GPIO.OUT, initial=initial_level)
    relay_off()

    controller = PumpController(
        on_threshold=ON_THRESHOLD_PERCENT,
        off_threshold=OFF_THRESHOLD_PERCENT,
        min_run_seconds=MIN_RUN_SECONDS,
        min_off_seconds=MIN_OFF_SECONDS,
    )

    # Smoothing buffer
    smooth_buf = deque(maxlen=max(1, int(SMOOTHING_WINDOW)))

    # Analytics state
    ensure_log_header()
    today = date.today()
    today_consumed_l = 0.0
    last_level = None
    week_history = deque(maxlen=7)  # (date, liters)

    # Leak scan state
    scanned_today = False
    scan_active = False
    scan_end_time = 0.0
    scan_start_level = 0.0

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
            now = time.time()
            now_dt = datetime.now()

            # Daily rollover
            if date.today() != today:
                # push yesterday into history
                week_history.append((today, today_consumed_l))
                today = date.today()
                today_consumed_l = 0.0
                scanned_today = False

            # Read and smooth level
            raw = read_level_percent_raw()
            smooth_buf.append(raw)
            level_pct = sum(smooth_buf) / len(smooth_buf)

            # Leak scan scheduling
            if LEAK_ENABLE and not scan_active:
                sched = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=LEAK_SCAN_HOUR, minutes=LEAK_SCAN_MINUTE)
                if not scanned_today and now_dt >= sched:
                    # Start scan only if pump is not urgently needed (above ON threshold) and currently off
                    if level_pct > ON_THRESHOLD_PERCENT and not controller.is_running():
                        scan_active = True
                        scan_end_time = now + (LEAK_SCAN_DURATION_MIN * 60.0)
                        scan_start_level = level_pct
                        print(f"[{now_dt.isoformat()}] Leak scan started for {LEAK_SCAN_DURATION_MIN} min (pump forced OFF)")

            if scan_active:
                # Force pump off during scan
                relay_off()
                # Do not tick controller (holds current state); ensure controller interprets as off
                # End scan when time elapsed
                if now >= scan_end_time:
                    scan_active = False
                    scanned_today = True
                    drop = max(0.0, scan_start_level - level_pct)
                    if drop >= LEAK_DROP_THRESHOLD_PCT:
                        print(f"[{now_dt.isoformat()}] POSSIBLE TANK LEAK: level dropped {drop:.2f}% during scan without pump.")
                    else:
                        print(f"[{now_dt.isoformat()}] Leak scan complete: drop {drop:.2f}% (no leak detected)")
            else:
                # Normal control
                controller.tick(level_pct)
                if controller.is_running():
                    relay_on()
                else:
                    relay_off()

            # Consumption tracking (only when level drops; ignores periods when pump raises level)
            if last_level is not None:
                delta = level_pct - last_level
                if delta < 0:  # consumption
                    consumed_l = TANK_CAPACITY_L * (-delta) / 100.0
                    today_consumed_l += consumed_l
            last_level = level_pct

            # Status and logging
            if now - last_status >= STATUS_EVERY_S:
                # Weekly stats
                hist_vals = [lit for _, lit in week_history]
                # Include current day partial
                hist_vals_with_today = hist_vals + [today_consumed_l]
                week_total = sum(hist_vals_with_today)
                avg_daily = (sum(hist_vals_with_today) / max(1, len(hist_vals_with_today)))
                days_remaining = (TANK_CAPACITY_L * (level_pct / 100.0)) / avg_daily if avg_daily > 0 else float('inf')
                print(
                    f"[{now_dt.isoformat()}] Level={level_pct:5.1f}%  Pump={'ON' if controller.is_running() else 'OFF'}  "
                    f"Today={today_consumed_l:.1f}L  7d={week_total:.1f}L  Avg/day={avg_daily:.1f}L  "
                    f"Est.days left={'∞' if days_remaining==float('inf') else f'{days_remaining:.1f}'}"
                )
                append_log(now_dt, level_pct, controller.is_running())
                last_status = now

            time.sleep(LOOP_PERIOD_S)
    finally:
        relay_off()
        GPIO.cleanup()


if __name__ == "__main__":
    sys.exit(main())

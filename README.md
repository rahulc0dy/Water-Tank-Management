Water Tank Management (2-file edition with full features)

Overview
- Only 2 files used:
  - main.py: GPIO setup, sensor reading (digital or ultrasonic), smoothing, control loop, analytics, leak scan, logging
  - pump_controller.py: Hysteresis and minimum run/off timers
- No YAML or CLI flags; configure via constants at the top of main.py.

Features
- Automatic pump control: ON at/below threshold, OFF at/above threshold
- Hysteresis + min run/off timers to avoid chattering
- Safety hard-off override at a configurable percent to prevent overfill (HARD_OFF_PERCENT)
- Smoothed level readings (moving average)
- Leak detection scan (scheduled nightly; no flow meter required)
- Daily/weekly consumption tracking (liters) and predicted days remaining (consumption counted only when pump is OFF)
- Optional ultrasonic sensor support (HC-SR04/JSN-SR04T) or simple digital level input
- Lightweight CSV logging to data/log.csv

Hardware
- Raspberry Pi 4 Model B
- One of:
  - Digital water level sensor (float switch/threshold) on a GPIO input
  - Ultrasonic sensor (HC-SR04/JSN-SR04T): TRIG to GPIO, ECHO via safe 5V→3.3V level shifting
- Relay module to drive a pump contactor/SSR (do NOT drive motors directly from GPIO)

Safety
- Use an opto-isolated relay or a contactor with proper ratings.
- Add thermal protection and a fuse/breaker on the motor circuit.
- Water + electricity is dangerous. Proceed only if qualified.

Install
1) Python 3.9+
2) On Raspberry Pi:
   sudo apt update && sudo apt install -y python3-rpi.gpio
   # or using pip in a venv: pip install -r requirements.txt

Configure (edit constants in main.py)
- GPIO_MODE (BCM/BOARD)
- SENSOR_MODE: 'digital' or 'ultrasonic'
- Pins: LEVEL_SENSOR_PIN (digital) or ULTRASONIC_TRIG_PIN/ULTRASONIC_ECHO_PIN (ultrasonic)
- Ultrasonic calibration: ULTRA_FULL_DISTANCE_CM, ULTRA_EMPTY_DISTANCE_CM
- Control: ON_THRESHOLD_PERCENT, OFF_THRESHOLD_PERCENT, MIN_RUN_SECONDS, MIN_OFF_SECONDS
- Smoothing: SMOOTHING_WINDOW
- Tank capacity: TANK_CAPACITY_L (for consumption and prediction)
- Leak scan: LEAK_* constants (hour/minute/duration/threshold)

Run
python3 main.py

Notes
- Ensure ECHO pin is level-shifted to 3.3V for ultrasonic sensors.
- Logging is appended to data/log.csv; the folder is created automatically.
- Prediction uses the average of up to the last 7 days of consumption.

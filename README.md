Water Tank Management for Raspberry Pi

Overview
- Controls a pump based on tank level with robust protections.
- Features: level hysteresis (separate ON/OFF thresholds), minimum run/off timers, smoothed sensor readings, leak detection mode (no flow meter), daily/weekly consumption tracking, and optional scheduled leak scans.
- Runs on Raspberry Pi 4 with GPIO; also supports a simulation/mock mode for development on Windows.

Hardware
- Raspberry Pi 4 Model B
- Level sensor (float/ultrasonic/analog via ADC). This code expects a digital GPIO level or a numeric level via an adapter.
- Relay module to switch pump contactor/SSR (never power the motor directly from Pi GPIO).
- 5V supply for Pi; separate motor power with proper protection (fuse, breaker, thermal protector).

Safety
- Use an opto-isolated relay or a contactor with proper ratings.
- Add thermal protection and a fuse/breaker on the motor circuit.
- Consider a soft-start or VFD for large motors.
- Water + electricity is dangerous. Proceed only if qualified.

Install
1. Ensure Python 3.9+ on Raspberry Pi.
2. Copy the project to the Pi. On Windows you can run in simulate mode.
3. Install requirements if any (RPi.GPIO on Raspberry Pi only).

Config
See config.yaml for tunables: pins, thresholds, timings, tank capacity, schedules.

Run
- Windows (simulate):
  python main.py --simulate
- Raspberry Pi:
  python main.py

Leak detection
- Manual scan:
  python main.py --leak-scan 45   # minutes
- Scheduled automatic scans run during low-use hours if configured.

Data
- Logs are written under ./data/ as CSV files for levels and events. Daily/weekly summaries are computed automatically.

Modularity
- water_tank/
  - hardware/: GPIO abstraction (real or mock)
  - sensors/: Level sensor with smoothing
  - actuators/: Relay
  - control/: PumpController with hysteresis and timers
  - analytics/: leak detection and consumption
  - util/: configuration, time, and simple scheduler

Note
- Without a flow meter, leak mode distinguishes tank leaks by isolating outlets during the scan window and watching the tank level. If level falls while outlets are disabled ⇒ tank leak likely. If level holds in scan but falls in normal operation ⇒ downstream usage or leak.

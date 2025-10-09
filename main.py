import argparse
import signal
import sys
import threading
import time
from datetime import datetime, timedelta

from water_tank.util.config import load_config
from water_tank.hardware.gpio import get_gpio
from water_tank.sensors.level_sensor import LevelSensor
from water_tank.actuators.relay import Relay
from water_tank.control.pump_controller import PumpController
from water_tank.analytics.logger import DataLogger
from water_tank.analytics.leak_detection import LeakDetection
from water_tank.util.scheduler import NightlyScheduler


shutdown_event = threading.Event()


def handle_signal(signum, frame):
    shutdown_event.set()


def main():
    parser = argparse.ArgumentParser(description="Water Tank Management")
    parser.add_argument("--simulate", action="store_true", help="Run with Mock GPIO and simulated sensor")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--leak-scan", type=int, default=None, help="Run a one-off leak scan now for N minutes")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.simulate:
        cfg['hardware']['simulate'] = True

    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Hardware abstraction
    gpio = get_gpio(simulate=cfg['hardware'].get('simulate', False), mode=cfg['hardware'].get('gpio_mode', 'BCM'))

    # Sensor and actuator
    sensor = LevelSensor(
        gpio=gpio,
        sensor_type=cfg['sensor']['type'],
        pin=cfg['hardware']['pins'].get('level_sensor_pin'),
        smoothing_cfg=cfg['sensor'].get('smoothing', {}),
        calibration=cfg['sensor'].get('calibration', {}),
        simulate=cfg['hardware'].get('simulate', False),
    )

    relay = Relay(
        gpio=gpio,
        pin=cfg['hardware']['pins']['pump_relay_pin'],
        active_high=cfg['hardware'].get('relay_active_high', False),
    )

    logger = DataLogger(cfg['analytics'])

    controller = PumpController(
        relay=relay,
        on_threshold=cfg['pump_control']['on_threshold_percent'],
        off_threshold=cfg['pump_control']['off_threshold_percent'],
        min_run_seconds=cfg['pump_control']['min_run_seconds'],
        min_off_seconds=cfg['pump_control']['min_off_seconds'],
        soft_start_delay_seconds=cfg['pump_control'].get('soft_start_delay_seconds', 0),
        status_publish_period_s=cfg['pump_control'].get('status_publish_period_s', 10),
        logger=logger,
    )

    leak = LeakDetection(sensor=sensor, controller=controller, logger=logger, cfg=cfg['leak_detection'])

    # Nightly scheduler for leak scans
    scheduler = NightlyScheduler(cfg['leak_detection'].get('nightly_scan', {}), leak.start_scheduled_scan)

    loop_period = cfg['runtime'].get('loop_period_ms', 1000) / 1000.0

    # Optional one-off leak scan
    if args.leak_scan is not None:
        leak.start_manual_scan(minutes=args.leak_scan)

    last_status = 0.0

    try:
        while not shutdown_event.is_set():
            now = time.time()

            # Update sensor smoothing buffer
            sensor.sample()
            level_pct = sensor.get_level_percent()

            # Run controller decision
            controller.tick(level_pct)

            # Log level
            logger.log_level(datetime.now(), level_pct, controller.is_running())

            # Scheduler checks
            scheduler.tick(datetime.now())

            # Leak detection state machine
            leak.tick(datetime.now())

            # Periodic status
            if now - last_status >= cfg['pump_control'].get('status_publish_period_s', 10):
                print(f"[{datetime.now().isoformat()}] Level={level_pct:5.1f}%  Pump={'ON' if controller.is_running() else 'OFF'}  Mode={leak.state}")
                last_status = now

            time.sleep(loop_period)
    finally:
        print("Shutting down...")
        controller.shutdown()
        relay.off()
        sensor.shutdown()
        gpio.cleanup()
        logger.flush()


if __name__ == "__main__":
    sys.exit(main())

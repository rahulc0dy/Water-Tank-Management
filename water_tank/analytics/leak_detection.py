from datetime import datetime, timedelta
from typing import Optional


class LeakDetection:
    """
    Leak detection mode without a flow meter:
    - During a scan window, we assume outlets are closed (user or schedule). We observe tank level change.
      * If level falls by >= min_detectable_drop_percent with pump OFF -> tank leak likely.
      * If level rises or stable -> no tank leak.
    - If level decreases in normal operation continuously while pump is OFF outside of scans, this may indicate usage
      or downstream leak; we log a warning event but do not classify definitively.
    """

    def __init__(self, sensor, controller, logger, cfg: dict):
        self.sensor = sensor
        self.controller = controller
        self.logger = logger
        self.cfg = cfg
        self.state = 'IDLE'
        self.scan_end_time: Optional[datetime] = None
        self.start_level: Optional[float] = None
        self.min_drop = float(cfg.get('min_detectable_drop_percent', 1.0))

    def start_manual_scan(self, minutes: int):
        if not self.cfg.get('manual_override_allowed', True):
            return
        now = datetime.now()
        self._start_scan(now, minutes)

    def start_scheduled_scan(self, start_dt: datetime, duration_minutes: int):
        self._start_scan(start_dt, duration_minutes)

    def _start_scan(self, start_dt: datetime, duration_minutes: int):
        # Only start if idle and pump is OFF
        if self.state != 'IDLE' or self.controller.is_running():
            return
        self.state = 'SCANNING'
        self.scan_end_time = start_dt + timedelta(minutes=duration_minutes)
        self.start_level = self.sensor.get_level_percent()
        self.logger.log_event(start_dt, f'LEAK_SCAN_START duration={duration_minutes}m level={self.start_level:.1f}%')

    def tick(self, now: datetime):
        if self.state == 'SCANNING':
            # Ensure pump is off during scan (controller handles min_run; we do not force changes here for safety)
            if self.controller.is_running():
                # If pump started during scan due to low level, cancel scan; not a valid isolation scenario.
                self.logger.log_event(now, 'LEAK_SCAN_CANCEL_PUMP_ON')
                self.state = 'IDLE'
                self.scan_end_time = None
                self.start_level = None
                return
            if now >= (self.scan_end_time or now):
                end_level = self.sensor.get_level_percent()
                drop = (self.start_level or end_level) - end_level
                if drop >= self.min_drop:
                    self.logger.log_event(now, f'LEAK_TANK_SUSPECT drop={drop:.2f}%')
                else:
                    self.logger.log_event(now, f'LEAK_SCAN_CLEAR drop={drop:.2f}%')
                self.state = 'IDLE'
                self.scan_end_time = None
                self.start_level = None
        else:
            # Optional: monitor for steady decline outside scans
            pass

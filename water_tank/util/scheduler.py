from datetime import datetime, time as dtime, timedelta


class NightlyScheduler:
    def __init__(self, cfg: dict, callback):
        self.enabled = bool(cfg.get('enabled', False))
        self.start_hour = int(cfg.get('start_hour', 2))
        self.duration_minutes = int(cfg.get('duration_minutes', 45))
        self.callback = callback
        self._last_run_date = None

    def tick(self, now: datetime):
        if not self.enabled:
            return
        # Run once per day at or after the configured hour
        target = datetime.combine(now.date(), dtime(self.start_hour, 0))
        if now >= target and self._last_run_date != now.date():
            self.callback(now, self.duration_minutes)
            self._last_run_date = now.date()

import csv
import os
from datetime import datetime, date
from typing import List, Tuple


class DataLogger:
    def __init__(self, cfg: dict):
        self.data_dir = cfg.get('data_dir', 'data')
        self.level_log = os.path.join(self.data_dir, cfg.get('level_log_csv', 'levels.csv'))
        self.events_log = os.path.join(self.data_dir, cfg.get('events_log_csv', 'events.csv'))
        self.summary_csv = os.path.join(self.data_dir, cfg.get('summary_csv', 'summaries.csv'))
        self.capacity_l = float(cfg.get('tank_capacity_liters', 1000))
        self._level_buffer: List[Tuple[datetime, float, bool]] = []
        self._event_buffer: List[Tuple[datetime, str]] = []

        # Ensure headers
        if not os.path.exists(self.level_log):
            with open(self.level_log, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['timestamp', 'level_percent', 'pump_on'])
        if not os.path.exists(self.events_log):
            with open(self.events_log, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['timestamp', 'event'])
        if not os.path.exists(self.summary_csv):
            with open(self.summary_csv, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['date', 'daily_consumption_liters', 'weekly_consumption_liters'])

    def log_level(self, ts: datetime, level_percent: float, pump_on: bool):
        self._level_buffer.append((ts, level_percent, pump_on))
        if len(self._level_buffer) >= 30:  # flush periodically
            self.flush()

    def log_event(self, ts: datetime, event: str):
        self._event_buffer.append((ts, event))
        if len(self._event_buffer) >= 5:
            self.flush()

    def flush(self):
        if self._level_buffer:
            with open(self.level_log, 'a', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                for row in self._level_buffer:
                    w.writerow([row[0].isoformat(), f"{row[1]:.2f}", int(row[2])])
            self._level_buffer.clear()
        if self._event_buffer:
            with open(self.events_log, 'a', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                for row in self._event_buffer:
                    w.writerow([row[0].isoformat(), row[1]])
            self._event_buffer.clear()
        # Update summaries daily
        self._update_summaries()

    def _update_summaries(self):
        # Load today's and last 7 days levels to compute consumption
        if not os.path.exists(self.level_log):
            return
        today = date.today()
        levels: List[Tuple[datetime, float]] = []
        with open(self.level_log, 'r', encoding='utf-8') as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    ts = datetime.fromisoformat(row['timestamp'])
                    lvl = float(row['level_percent'])
                except Exception:
                    continue
                if (today - ts.date()).days <= 7:
                    levels.append((ts, lvl))
        if not levels:
            return
        # Sort by time
        levels.sort(key=lambda x: x[0])
        # Estimate consumption as sum of decreases when pump is off.
        daily = {}
        prev = None
        for ts, lvl in levels:
            d = ts.date()
            daily.setdefault(d, 0.0)
            if prev is not None:
                drop = max(0.0, prev - lvl)
                daily[d] += drop
            prev = lvl
        daily_liters = (daily.get(today, 0.0) / 100.0) * self.capacity_l
        weekly_liters = (sum(daily.values()) / 100.0) * self.capacity_l

        # Overwrite today's summary row
        summaries = {}
        if os.path.exists(self.summary_csv):
            with open(self.summary_csv, 'r', encoding='utf-8') as f:
                r = csv.DictReader(f)
                for row in r:
                    summaries[row['date']] = row
        summaries[str(today)] = {
            'date': str(today),
            'daily_consumption_liters': f"{daily_liters:.1f}",
            'weekly_consumption_liters': f"{weekly_liters:.1f}",
        }
        with open(self.summary_csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['date', 'daily_consumption_liters', 'weekly_consumption_liters'])
            w.writeheader()
            for k in sorted(summaries.keys()):
                w.writerow(summaries[k])

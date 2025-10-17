
"""Data collection utilities for Water Tank Management.

Provides simple CSV logging with the columns:
  timestamp, water_level, pump_status

Functions:
  init_log() -> ensures data directory & CSV header exist
  append_row(water_level, pump_on, timestamp=None) -> append one row
  read_last_rows(n=10) -> read last n rows as list of dicts
"""

from __future__ import annotations

import csv
import os
from collections import deque
from datetime import datetime
from typing import List, Dict, Optional

from config import DATA_DIR, LOG_FILE


def _ensure_data_dir():
	"""Create the data directory if it doesn't exist."""
	data_dir = os.path.dirname(LOG_FILE) or DATA_DIR
	if data_dir and not os.path.exists(data_dir):
		os.makedirs(data_dir, exist_ok=True)


def init_log() -> None:
	"""Ensure the CSV log exists and has the header.

	If the file is missing, create it and write the header row.
	"""
	_ensure_data_dir()

	# If file doesn't exist or is empty, write header
	need_header = True
	if os.path.exists(LOG_FILE):
		try:
			if os.path.getsize(LOG_FILE) > 0:
				need_header = False
		except OSError:
			# if we can't stat the file, attempt to create it
			need_header = True

	if need_header:
		with open(LOG_FILE, "w", newline="", encoding="utf-8") as fh:
			writer = csv.writer(fh)
			writer.writerow(["timestamp", "water_level", "pump_status"])


def append_row(water_level: float, pump_on: bool, timestamp: Optional[datetime] = None) -> None:
	"""Append a row to the CSV log.

	Args:
		water_level: water level value (usually percent or cm) -- stored as float
		pump_on: True if pump is on, False otherwise
		timestamp: optional datetime for the record (defaults to now UTC)
	"""
	if timestamp is None:
		timestamp = datetime.utcnow()

	_ensure_data_dir()

	row = [timestamp.isoformat(), float(water_level), "on" if pump_on else "off"]

	# Append to file
	with open(LOG_FILE, "a", newline="", encoding="utf-8") as fh:
		writer = csv.writer(fh)
		writer.writerow(row)


def read_last_rows(n: int = 10) -> List[Dict[str, str]]:
	"""Read the last `n` rows from the CSV log and return them as dicts.

	This is efficient for large files because it only keeps `n` rows in memory.
	"""
	if not os.path.exists(LOG_FILE):
		return []

	with open(LOG_FILE, "r", newline="", encoding="utf-8") as fh:
		reader = csv.DictReader(fh)
		dq = deque(maxlen=n)
		for row in reader:
			dq.append(row)

	return list(dq)


if __name__ == "__main__":
	# Quick smoke test when run directly
	init_log()
	append_row(42.5, False)
	print("Last rows:", read_last_rows(5))

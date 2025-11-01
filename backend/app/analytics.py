"""Utility helpers to compute dashboard analytics from telemetry samples."""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

CAPACITY_LITERS = float(os.getenv("WATERTANK_CAPACITY_LITERS", "0") or 0)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(float(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1]
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return False


def _prepare_samples(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for sample in samples:
        ts = _parse_timestamp(sample.get("timestamp"))
        if ts is None:
            continue
        try:
            level = float(sample.get("water_level_percent"))
        except (TypeError, ValueError):
            continue
        try:
            pump_state = int(float(sample.get("pump_state", 0)))
        except (TypeError, ValueError):
            pump_state = 0
        leak = _to_bool(sample.get("leak_detected", False))
        cleaned.append(
            {
                "timestamp": ts,
                "water_level_percent": level,
                "pump_state": pump_state,
                "leak_detected": leak,
                "raw_payload": sample.get("raw_payload", ""),
            }
        )
    cleaned.sort(key=lambda entry: entry["timestamp"])
    return cleaned


def _usage_events(clean_samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for idx in range(1, len(clean_samples)):
        prev = clean_samples[idx - 1]
        curr = clean_samples[idx]
        drop = prev["water_level_percent"] - curr["water_level_percent"]
        if drop <= 0:
            continue
        events.append({"timestamp": curr["timestamp"], "amount": drop})
    return events


def _format_usage(amount_percent: float) -> Dict[str, float]:
    payload: Dict[str, float] = {"percent": round(amount_percent, 3)}
    if CAPACITY_LITERS > 0:
        payload["liters"] = round(amount_percent / 100.0 * CAPACITY_LITERS, 3)
    return payload


def compute_dashboard_metrics(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    clean_samples = _prepare_samples(samples)
    if not clean_samples:
        return {
            "latest": None,
            "sample_count": 0,
            "usage": {
                "last_24h": _format_usage(0.0),
                "all_time": _format_usage(0.0),
                "per_hour": [],
                "per_day": [],
            },
            "water_levels": [],
            "pump_state_summary": {"on": 0, "off": 0},
            "leak_events": 0,
        }

    usage_events = _usage_events(clean_samples)
    now = datetime.utcnow()
    window_start = now - timedelta(hours=24)

    usage_24h = sum(
        event["amount"] for event in usage_events if event["timestamp"] >= window_start
    )
    usage_all_time = sum(event["amount"] for event in usage_events)

    hourly_totals: Dict[int, float] = defaultdict(float)
    for event in usage_events:
        hourly_totals[event["timestamp"].hour] += event["amount"]

    daily_totals: Dict[str, float] = defaultdict(float)
    for event in usage_events:
        key = event["timestamp"].date().isoformat()
        daily_totals[key] += event["amount"]

    water_levels = [
        {
            "timestamp": sample["timestamp"].isoformat(),
            "water_level_percent": round(sample["water_level_percent"], 3),
            **(
                {
                    "water_level_liters": round(
                        sample["water_level_percent"] / 100.0 * CAPACITY_LITERS,
                        3,
                    )
                }
                if CAPACITY_LITERS > 0
                else {}
            ),
        }
        for sample in clean_samples[-500:]
    ]

    latest_sample = clean_samples[-1]

    pump_on = sum(1 for sample in clean_samples if sample["pump_state"] == 1)
    pump_off = len(clean_samples) - pump_on
    leak_events = sum(1 for sample in clean_samples if sample["leak_detected"])

    hourly_usage = [
        {
            "hour": hour,
            **_format_usage(hourly_totals.get(hour, 0.0)),
        }
        for hour in range(24)
    ]

    daily_usage = [
        {"date": date_key, **_format_usage(total)}
        for date_key, total in sorted(daily_totals.items())
    ]

    return {
        "latest": {
            "timestamp": latest_sample["timestamp"].isoformat(),
            "water_level_percent": round(latest_sample["water_level_percent"], 3),
            "pump_state": latest_sample["pump_state"],
            "leak_detected": latest_sample["leak_detected"],
            **(
                {
                    "water_level_liters": round(
                        latest_sample["water_level_percent"] / 100.0 * CAPACITY_LITERS,
                        3,
                    )
                }
                if CAPACITY_LITERS > 0
                else {}
            ),
        },
        "sample_count": len(clean_samples),
        "usage": {
            "last_24h": _format_usage(usage_24h),
            "all_time": _format_usage(usage_all_time),
            "per_hour": hourly_usage,
            "per_day": daily_usage,
        },
        "water_levels": water_levels,
        "pump_state_summary": {"on": pump_on, "off": pump_off},
        "leak_events": leak_events,
    }

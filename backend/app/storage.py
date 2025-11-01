"""File-backed telemetry storage shared between automation and the API."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional


class FileBackedTelemetryStore:
    """Minimal JSON file store keeping a bounded history of samples."""

    def __init__(self, path: Path, maxlen: int) -> None:
        self._path = path
        self._maxlen = max(0, maxlen)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    # Internal helpers -------------------------------------------------
    def _read_all(self) -> List[dict]:
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []
        if isinstance(payload, list):
            return payload
        return []

    def _write_all(self, records: List[dict]) -> None:
        records = records[-self._maxlen :] if self._maxlen else records
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(records, handle)
        tmp_path.replace(self._path)

    # Public API -------------------------------------------------------
    def append(self, record: dict) -> None:
        records = self._read_all()
        records.append(record)
        self._write_all(records)

    def latest(self) -> Optional[dict]:
        records = self._read_all()
        if not records:
            return None
        return records[-1]

    def history(self, limit: Optional[int] = None) -> List[dict]:
        records = self._read_all()
        if limit is not None and limit > 0:
            return records[-limit:]
        return records


def default_store(maxlen: Optional[int] = None) -> FileBackedTelemetryStore:
    """Convenience factory using environment or sensible defaults."""
    history_size = maxlen if maxlen is not None else int(
        os.getenv("WATERTANK_HISTORY_SIZE", "0")
    )
    default_path_str = os.getenv(
        "WATERTANK_DATA_FILE",
        str(Path(__file__).resolve().parent.parent / "var" / "telemetry.json"),
    )
    default_path = Path(default_path_str)
    return FileBackedTelemetryStore(default_path, history_size)

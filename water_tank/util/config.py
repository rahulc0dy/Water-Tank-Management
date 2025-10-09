import os
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:  # minimal fallback without PyYAML
    yaml = None
    import json


def load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    if path.endswith('.yaml') or path.endswith('.yml'):
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML config. Install pyyaml or provide JSON.")
        cfg = yaml.safe_load(text)
    else:
        cfg = json.loads(text)

    # Ensure data directory exists
    analytics = cfg.get('analytics', {})
    data_dir = analytics.get('data_dir', 'data')
    os.makedirs(data_dir, exist_ok=True)
    return cfg

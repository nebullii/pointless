"""Profile loading."""

import json
from pathlib import Path


def load_profile(name: str) -> dict:
    path = Path(__file__).resolve().parents[1] / "profiles" / f"{name}.json"
    return json.loads(path.read_text())

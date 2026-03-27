"""Settings load/save round-trip."""

import json
from pathlib import Path

from spaceguard.settings_store import default_settings, load_settings, save_settings


def test_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    d = default_settings()
    d["disk_warn_gb"] = 2.5
    save_settings(d, path=p)
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert raw["disk_warn_gb"] == 2.5
    loaded = load_settings(path=p)
    assert loaded["disk_warn_gb"] == 2.5

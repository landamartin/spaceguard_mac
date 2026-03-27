"""Load/save settings JSON with atomic replace."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

APP_DIR_NAME = "SpaceGuard"
SETTINGS_FILENAME = "settings.json"
SCHEMA_VERSION = 1


def app_support_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / APP_DIR_NAME


def settings_path() -> Path:
    return app_support_dir() / SETTINGS_FILENAME


def default_settings() -> dict[str, Any]:
    """Default settings dict (includes schema_version)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "disk_warn_gb": 1.0,
        "disk_crit_gb": 0.5,
        "swap_warn_mb": 500.0,
        "swap_crit_mb": 1000.0,
        "enable_disk_trigger": True,
        "enable_swap_trigger": True,
        "check_interval_sec": 45,
        "consecutive_checks_required": 2,
        "prompt_cooldown_min": 10,
        "ignore_cooldown_min": 45,
        "notifications_only": False,
        "start_at_login": False,
        "show_tray_icon": True,
        "cleanup_presets": {
            "global_caches": True,
            "logs": True,
            "firefox_cache": True,
            "vscode_cache": True,
            "cursor_cache": True,
            "electron_slack": True,
            "electron_figma": True,
        },
        "custom_paths": [],
        "_shown_welcome": False,
    }


def _migrate(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply migrations from older schema_version; returns merged dict."""
    ver = raw.get("schema_version", 0)
    out = deepcopy(raw)
    if ver < 1:
        out.setdefault("schema_version", SCHEMA_VERSION)
    out["schema_version"] = SCHEMA_VERSION
    # Merge missing keys from defaults
    defaults = default_settings()
    for k, v in defaults.items():
        if k not in out:
            out[k] = deepcopy(v)
    if "cleanup_presets" in out and isinstance(out["cleanup_presets"], dict):
        for k, v in defaults["cleanup_presets"].items():
            out["cleanup_presets"].setdefault(k, v)
    else:
        out["cleanup_presets"] = deepcopy(defaults["cleanup_presets"])
    if not isinstance(out.get("custom_paths"), list):
        out["custom_paths"] = []
    return out


def load_settings(path: Path | None = None) -> dict[str, Any]:
    """Load settings from disk or return defaults (also writes first-run file)."""
    p = path or settings_path()
    if not p.exists():
        data = default_settings()
        save_settings(data, path=p)
        return data
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raw = {}
    except (OSError, json.JSONDecodeError):
        raw = {}
    return _migrate(raw)


def save_settings(data: dict[str, Any], path: Path | None = None) -> None:
    """Atomically write settings JSON."""
    p = path or settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    fd, tmp = tempfile.mkstemp(
        dir=p.parent,
        prefix=".settings.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

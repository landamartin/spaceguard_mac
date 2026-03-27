"""Safe cleanup: selected preset paths and user custom paths."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

# Guard: refuse obvious system roots (do not use /private/var — resolved paths under
# TMPDIR often live there on macOS and would be rejected incorrectly).
_FORBIDDEN_PREFIXES = (
    "/System",
    "/usr",
    "/bin",
    "/sbin",
    "/Library",
)


def _expand_presets(presets: dict[str, bool]) -> list[Path]:
    """Return list of absolute paths for enabled preset cleanups."""
    home = Path.home()
    out: list[Path] = []

    if presets.get("global_caches"):
        out.append(home / "Library" / "Caches")

    if presets.get("logs"):
        out.append(home / "Library" / "Logs")

    if presets.get("firefox_cache"):
        profiles = home / "Library" / "Application Support" / "Firefox" / "Profiles"
        if profiles.is_dir():
            for p in profiles.iterdir():
                if p.is_dir():
                    for name in ("cache2", "startupCache"):
                        c = p / name
                        if c.exists():
                            out.append(c)

    if presets.get("vscode_cache"):
        base = home / "Library" / "Application Support" / "Code"
        out.extend(
            [
                base / "Cache",
                base / "CachedData",
            ]
        )

    if presets.get("cursor_cache"):
        base = home / "Library" / "Application Support" / "Cursor"
        out.extend(
            [
                base / "Cache",
                base / "CachedData",
            ]
        )

    if presets.get("electron_slack"):
        base = home / "Library" / "Application Support" / "Slack"
        out.extend(
            [
                base / "Cache",
                base / "Code Cache",
            ]
        )

    if presets.get("electron_figma"):
        base = home / "Library" / "Application Support" / "Figma"
        out.extend(
            [
                base / "Cache",
                base / "Code Cache",
            ]
        )

    return out


def validate_custom_path(expanded: Path, home: Path) -> tuple[bool, str]:
    """Return (ok, reason). Paths must be under home and not forbidden roots."""
    try:
        resolved = expanded.resolve()
    except OSError as e:
        return False, str(e)
    home_r = home.resolve()
    try:
        resolved.relative_to(home_r)
    except ValueError:
        return False, "Path must be inside your home directory"
    s = str(resolved)
    for bad in _FORBIDDEN_PREFIXES:
        if s == bad or s.startswith(bad + os.sep):
            return False, "Path is not allowed (system location)"
    if resolved == home_r:
        return False, "Cannot use home directory itself"
    return True, ""


def collect_targets(settings: dict[str, Any]) -> tuple[list[Path], list[str]]:
    """Build ordered unique list of paths to remove; second list is skip reasons."""
    presets = settings.get("cleanup_presets") or {}
    paths = _expand_presets(presets)
    home = Path.home()

    for raw in settings.get("custom_paths") or []:
        if not isinstance(raw, str) or not raw.strip():
            continue
        exp = Path(os.path.expanduser(raw.strip()))
        ok, _reason = validate_custom_path(exp, home)
        if ok:
            paths.append(exp)
        # invalid custom paths are skipped silently here; UI should pre-validate

    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        try:
            rp = p.resolve()
        except OSError:
            rp = p
        if rp in seen:
            continue
        seen.add(rp)
        unique.append(p)
    return unique, []


def remove_path(path: Path) -> tuple[bool, str]:
    """Remove file or directory; return (ok, message)."""
    if not path.exists():
        return True, "missing (skipped)"
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=False)
        else:
            path.unlink()
    except OSError as e:
        return False, str(e)
    return True, "ok"


def run_cleanup(settings: dict[str, Any]) -> tuple[list[tuple[str, bool, str]], int]:
    """
    Run cleanup; return list of (path_str, ok, detail) and failure count.
    """
    targets, _ = collect_targets(settings)
    results: list[tuple[str, bool, str]] = []
    failures = 0
    for p in targets:
        ok, detail = remove_path(p)
        results.append((str(p), ok, detail))
        if not ok:
            failures += 1
    return results, failures


def restart_noisy_daemons_via_osascript() -> tuple[bool, str]:
    """
    Ask macOS for admin once and run killall for analyticsd/searchpartyd.
    Returns (success, message).
    """
    inner = "killall analyticsd 2>/dev/null; killall searchpartyd 2>/dev/null; exit 0"
    script = f'do shell script "{inner}" with administrator privileges'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return True, "requested"

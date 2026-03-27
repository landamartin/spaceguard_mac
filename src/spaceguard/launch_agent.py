"""Install/remove Launch Agent for start-at-login (macOS)."""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

PLIST_LABEL = "com.spaceguard.mac"
PLIST_NAME = f"{PLIST_LABEL}.plist"


def launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def plist_path() -> Path:
    return launch_agents_dir() / PLIST_NAME


def build_plist(program_args: list[str], working_directory: str | None) -> dict:
    data: dict = {
        "Label": PLIST_LABEL,
        "ProgramArguments": program_args,
        "RunAtLoad": True,
        "KeepAlive": False,
    }
    if working_directory:
        data["WorkingDirectory"] = working_directory
    return data


def _find_project_root() -> Path | None:
    """Directory containing ``pyproject.toml``, if any (dev / editable install)."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def current_program_arguments() -> tuple[list[str], str | None]:
    """Arguments to re-launch this app: ``python -m spaceguard`` style."""
    exe = sys.executable
    root = _find_project_root()
    wd = str(root) if root else os.getcwd()
    return ([exe, "-m", "spaceguard"], wd)


def install_launch_agent() -> tuple[bool, str]:
    """Write Launch Agent plist and load it."""
    launch_agents_dir().mkdir(parents=True, exist_ok=True)
    args, wd = current_program_arguments()
    payload = build_plist(args, wd)
    p = plist_path()
    try:
        with p.open("wb") as f:
            plistlib.dump(payload, f)
    except OSError as e:
        return False, str(e)
    try:
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(p)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        pass
    try:
        r = subprocess.run(
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(p)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0 and r.stderr:
            return False, r.stderr.strip()
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return True, str(p)


def remove_launch_agent() -> tuple[bool, str]:
    """Unload and delete plist."""
    p = plist_path()
    try:
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(p)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        pass
    try:
        if p.exists():
            p.unlink()
    except OSError as e:
        return False, str(e)
    return True, "removed"


def is_launch_agent_installed() -> bool:
    return plist_path().exists()


def install_launch_agent_for_app_bundle(app_executable: Path) -> tuple[bool, str]:
    """Use bundled .app main binary (no ``-m``)."""
    launch_agents_dir().mkdir(parents=True, exist_ok=True)
    args = [str(app_executable)]
    payload = build_plist(args, None)
    p = plist_path()
    try:
        with p.open("wb") as f:
            plistlib.dump(payload, f)
    except OSError as e:
        return False, str(e)
    try:
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(p)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        pass
    try:
        r = subprocess.run(
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(p)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0 and r.stderr:
            return False, r.stderr.strip()
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return True, str(p)


def copy_plist_template_to_user(template_path: Path) -> tuple[bool, str]:
    """Copy pre-rendered plist from docs (e.g. hand-edited paths) and bootstrap."""
    dest = plist_path()
    try:
        shutil.copy2(template_path, dest)
    except OSError as e:
        return False, str(e)
    try:
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(dest)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        pass
    try:
        r = subprocess.run(
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(dest)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0 and r.stderr:
            return False, r.stderr.strip()
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return True, str(dest)

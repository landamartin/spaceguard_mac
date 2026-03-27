"""Disk free space and swap usage (macOS)."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class DiskSwapMetrics:
    """Snapshot of disk free space (root volume) and swap used."""

    disk_free_gb: float
    swap_used_mb: float | None  # None if sysctl parse failed


def get_disk_free_gb(path: str = "/") -> float:
    """Free space in GiB for the volume containing ``path`` (``statvfs``)."""
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    return free / (1024**3)


_SWAP_USED_RE = re.compile(
    r"used\s*=\s*([0-9.]+)\s*([KMkmg])",
    re.IGNORECASE,
)


def parse_swap_used_mb(sysctl_output: str) -> float | None:
    """Parse ``sysctl vm.swapusage`` stdout; return MiB used or None."""
    m = _SWAP_USED_RE.search(sysctl_output)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).upper()
    if unit == "K":
        return val / 1024.0
    if unit == "M":
        return val
    if unit == "G":
        return val * 1024.0
    return None


def get_swap_used_mb() -> float | None:
    """Return swap used in MiB via ``sysctl vm.swapusage``, or None on failure."""
    try:
        out = subprocess.check_output(
            ["sysctl", "vm.swapusage"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_swap_used_mb(out)


def sample_metrics() -> DiskSwapMetrics:
    """Read current disk free (/) and swap used."""
    disk = get_disk_free_gb("/")
    swap = get_swap_used_mb()
    return DiskSwapMetrics(disk_free_gb=disk, swap_used_mb=swap)

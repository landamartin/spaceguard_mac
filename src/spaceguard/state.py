"""Tray severity and debounced alert state (testable pure logic)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from spaceguard.monitor import DiskSwapMetrics


class TrayLevel(StrEnum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


def tray_level(metrics: DiskSwapMetrics, settings: dict[str, Any]) -> TrayLevel:
    """Disk/swap severity for menu bar icon (critical overrides warning)."""
    disk = metrics.disk_free_gb
    swap = metrics.swap_used_mb
    if disk < float(settings["disk_crit_gb"]):
        return TrayLevel.CRITICAL
    if swap is not None and swap > float(settings["swap_crit_mb"]):
        return TrayLevel.CRITICAL
    if disk < float(settings["disk_warn_gb"]):
        return TrayLevel.WARNING
    if swap is not None and swap > float(settings["swap_warn_mb"]):
        return TrayLevel.WARNING
    return TrayLevel.OK


def pressure_active(metrics: DiskSwapMetrics, settings: dict[str, Any]) -> bool:
    """True when disk or swap crosses warning thresholds (respects enable flags)."""
    if settings.get("enable_disk_trigger", True) and metrics.disk_free_gb < float(
        settings["disk_warn_gb"]
    ):
        return True
    if settings.get("enable_swap_trigger", True) and metrics.swap_used_mb is not None:
        if metrics.swap_used_mb > float(settings["swap_warn_mb"]):
            return True
    return False


@dataclass
class AlertState:
    consecutive_pressure_ticks: int = 0
    last_prompt_monotonic: float | None = None
    last_ignore_monotonic: float | None = None


def step_should_prompt(
    *,
    now: float,
    pressure: bool,
    consecutive_required: int,
    prompt_cooldown_sec: float,
    ignore_cooldown_sec: float,
    state: AlertState,
) -> tuple[AlertState, bool]:
    """
    Advance debounce state; return (new_state, should_prompt).

    Caller should call ``record_prompt_shown`` / ``record_ignore`` after UI.
    """
    new = AlertState(
        consecutive_pressure_ticks=state.consecutive_pressure_ticks,
        last_prompt_monotonic=state.last_prompt_monotonic,
        last_ignore_monotonic=state.last_ignore_monotonic,
    )
    if pressure:
        new.consecutive_pressure_ticks = state.consecutive_pressure_ticks + 1
    else:
        new.consecutive_pressure_ticks = 0

    if new.consecutive_pressure_ticks < consecutive_required:
        return new, False

    if new.last_ignore_monotonic is not None:
        if now - new.last_ignore_monotonic < ignore_cooldown_sec:
            return new, False

    if new.last_prompt_monotonic is not None:
        if now - new.last_prompt_monotonic < prompt_cooldown_sec:
            return new, False

    return new, True


def record_prompt_shown(state: AlertState, now: float) -> AlertState:
    """After any cleanup prompt (dialog or notification action)."""
    return AlertState(
        consecutive_pressure_ticks=0,
        last_prompt_monotonic=now,
        last_ignore_monotonic=state.last_ignore_monotonic,
    )


def record_ignore(state: AlertState, now: float) -> AlertState:
    """User dismissed prompt without cleaning."""
    return AlertState(
        consecutive_pressure_ticks=0,
        last_prompt_monotonic=now,
        last_ignore_monotonic=now,
    )


def record_cleanup_completed(state: AlertState, now: float) -> AlertState:
    """User ran cleanup from prompt or menu."""
    return AlertState(
        consecutive_pressure_ticks=0,
        last_prompt_monotonic=now,
        last_ignore_monotonic=None,
    )

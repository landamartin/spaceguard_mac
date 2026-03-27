"""Tests for tray severity and alert debounce."""

from spaceguard.monitor import DiskSwapMetrics
from spaceguard.state import (
    AlertState,
    TrayLevel,
    pressure_active,
    record_ignore,
    step_should_prompt,
    tray_level,
)


def test_tray_level_ok() -> None:
    s = {
        "disk_warn_gb": 1.0,
        "disk_crit_gb": 0.5,
        "swap_warn_mb": 500.0,
        "swap_crit_mb": 1000.0,
    }
    m = DiskSwapMetrics(disk_free_gb=50.0, swap_used_mb=10.0)
    assert tray_level(m, s) == TrayLevel.OK


def test_tray_level_critical_disk() -> None:
    s = {
        "disk_warn_gb": 1.0,
        "disk_crit_gb": 0.5,
        "swap_warn_mb": 500.0,
        "swap_crit_mb": 1000.0,
    }
    m = DiskSwapMetrics(disk_free_gb=0.4, swap_used_mb=0.0)
    assert tray_level(m, s) == TrayLevel.CRITICAL


def test_pressure_active_respects_flags() -> None:
    s = {
        "disk_warn_gb": 10.0,
        "disk_crit_gb": 0.5,
        "swap_warn_mb": 500.0,
        "swap_crit_mb": 1000.0,
        "enable_disk_trigger": False,
        "enable_swap_trigger": True,
    }
    m = DiskSwapMetrics(disk_free_gb=1.0, swap_used_mb=0.0)
    assert pressure_active(m, s) is False


def test_debounce_requires_consecutive() -> None:
    st = AlertState()
    t0 = 10_000.0
    st2, prompt = step_should_prompt(
        now=t0,
        pressure=True,
        consecutive_required=2,
        prompt_cooldown_sec=600.0,
        ignore_cooldown_sec=600.0,
        state=st,
    )
    assert prompt is False
    st3, prompt2 = step_should_prompt(
        now=t0 + 1.0,
        pressure=True,
        consecutive_required=2,
        prompt_cooldown_sec=600.0,
        ignore_cooldown_sec=600.0,
        state=st2,
    )
    assert prompt2 is True


def test_prompt_cooldown_blocks() -> None:
    st = AlertState()
    t0 = 1000.0
    st.consecutive_pressure_ticks = 2
    st.last_prompt_monotonic = t0
    st2, prompt = step_should_prompt(
        now=t0 + 60.0,
        pressure=True,
        consecutive_required=1,
        prompt_cooldown_sec=600.0,
        ignore_cooldown_sec=600.0,
        state=st,
    )
    assert prompt is False


def test_record_ignore() -> None:
    st = AlertState(last_prompt_monotonic=10.0)
    st2 = record_ignore(st, 20.0)
    assert st2.last_ignore_monotonic == 20.0

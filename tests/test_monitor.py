"""Tests for disk/swap monitoring helpers."""

from spaceguard.monitor import get_disk_free_gb, parse_swap_used_mb


def test_parse_swap_used_mb_variants() -> None:
    sample = "vm.swapusage: total = 2048.00M  used = 512.50M  free = 1535.50M"
    assert parse_swap_used_mb(sample) == 512.5
    assert parse_swap_used_mb("used = 1.25G") == 1.25 * 1024.0
    assert parse_swap_used_mb("used = 1024K") == 1024.0 / 1024.0
    assert parse_swap_used_mb("") is None


def test_get_disk_free_gb_positive() -> None:
    g = get_disk_free_gb("/")
    assert g > 0.0

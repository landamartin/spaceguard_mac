"""Cleanup path validation."""

from pathlib import Path

from spaceguard.cleanup import validate_custom_path


def test_custom_must_be_under_home(tmp_path: Path) -> None:
    home = tmp_path / "u"
    home.mkdir()
    ok, msg = validate_custom_path(tmp_path / "other" / "x", home)
    assert ok is False
    assert "home" in msg.lower()


def test_custom_allowed_subdir(tmp_path: Path) -> None:
    home = tmp_path / "u"
    home.mkdir()
    target = home / "Library" / "Caches" / "foo"
    target.mkdir(parents=True)
    ok, _msg = validate_custom_path(target, home)
    assert ok is True

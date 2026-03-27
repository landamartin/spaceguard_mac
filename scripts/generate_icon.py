#!/usr/bin/env python3
"""Build ``resources/SpaceGuard.icns`` from a simple vector-style PNG set (Pillow + iconutil)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "resources"
ICONSET = RES / "SpaceGuard.iconset"
ICNS = RES / "SpaceGuard.icns"


def draw_icon(size: int) -> Image.Image:
    """Menu-bar style mark: shield + disk motif on a rounded tile."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    m = max(1, size // 14)
    # Deep space blue tile
    draw.rounded_rectangle(
        [m, m, size - m, size - m],
        radius=max(2, size // 6),
        fill=(22, 33, 62, 255),
        outline=(100, 200, 180, 255),
        width=max(1, size // 64),
    )
    cx, cy = size // 2, size // 2
    r = int(size * 0.26)
    # Mint “disk” ring
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(45, 212, 191, 255),
        outline=(180, 255, 240, 200),
        width=max(1, size // 48),
    )
    r2 = int(r * 0.42)
    draw.ellipse(
        [cx - r2, cy - r2, cx + r2, cy + r2],
        fill=(22, 33, 62, 255),
    )
    return img


def main() -> int:
    if sys.platform != "darwin":
        print("iconutil requires macOS; copy a .icns from another machine or skip.", file=sys.stderr)
        return 1
    if shutil.which("iconutil") is None:
        print("iconutil not found (install Xcode CLT).", file=sys.stderr)
        return 1

    RES.mkdir(parents=True, exist_ok=True)
    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir(parents=True)

    sizes: list[tuple[str, int]] = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    for name, dim in sizes:
        draw_icon(dim).save(ICONSET / name, "PNG")

    subprocess.run(
        ["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)],
        check=True,
    )
    shutil.rmtree(ICONSET, ignore_errors=True)
    print(ICNS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

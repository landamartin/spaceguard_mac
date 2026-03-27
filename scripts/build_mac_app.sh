#!/usr/bin/env bash
set -euo pipefail

# Build a standalone macOS .app with Nuitka + PySide6, custom icon, bundle id, ad-hoc sign.
#
# Usage:
#   ./scripts/build_mac_app.sh
#
# Output: ./dist/SpaceGuard.app
#
# Apple Silicon: for a native arm64 binary, use an arm64 Python with uv, e.g.
#   UV_PYTHON=/opt/homebrew/bin/python3.13 uv sync --all-groups
#   UV_PYTHON=/opt/homebrew/bin/python3.13 ./scripts/build_mac_app.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

UV="${UV:-uv}"
if ! command -v "$UV" >/dev/null 2>&1; then
  echo "uv not found; install from https://github.com/astral-sh/uv" >&2
  exit 1
fi

"$UV" sync --all-groups

ICNS="$ROOT/resources/SpaceGuard.icns"
if [[ ! -f "$ICNS" ]]; then
  echo "Generating icon…"
  "$UV" run python "$ROOT/scripts/generate_icon.py"
fi

APP_NAME="SpaceGuard"
OUT_APP="$ROOT/dist/${APP_NAME}.app"
# Nuitka names the bundle from the source folder (spaceguard → spaceguard.app)
NUITKA_APP="$ROOT/dist/spaceguard.app"

rm -rf "$OUT_APP" "$NUITKA_APP"

# PySide6: only Qt plugin families this app needs (QtWidgets + tray + drawn icons).
# Drops tls (Qt network/SSL), QML, multimedia, WebEngine, SQL, etc. — see
# `nuitka --help-plugins` → pyside6. SpaceGuard imports only QtCore/QtGui/QtWidgets.
# Override if needed: INCLUDE_QT_PLUGINS=platforms,styles,... ./scripts/build_mac_app.sh
: "${INCLUDE_QT_PLUGINS:=platforms,styles,iconengines,imageformats}"

echo "Running Nuitka (several minutes on first run; ccache speeds rebuilds)…"
"$UV" run python -m nuitka \
  --assume-yes-for-downloads \
  --standalone \
  --macos-create-app-bundle \
  --macos-app-name="$APP_NAME" \
  --macos-app-icon="$ICNS" \
  --macos-app-version=0.1.0 \
  --macos-app-mode=ui-element \
  --enable-plugin=pyside6 \
  --include-qt-plugins="$INCLUDE_QT_PLUGINS" \
  --noinclude-qt-translations \
  --include-package=spaceguard \
  --output-filename=SpaceGuard \
  --output-dir="$ROOT/dist" \
  "$ROOT/src/spaceguard"

if [[ ! -d "$NUITKA_APP" ]]; then
  echo "Expected bundle not found: $NUITKA_APP" >&2
  exit 1
fi

mv "$NUITKA_APP" "$OUT_APP"

INFO="$OUT_APP/Contents/Info.plist"
if [[ -f "$INFO" ]]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.spaceguard.mac" "$INFO" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.spaceguard.mac" "$INFO"
  /usr/libexec/PlistBuddy -c "Add :NSHighResolutionCapable bool true" "$INFO" 2>/dev/null || true
fi

echo "Ad-hoc signing…"
codesign --force --deep --sign - "$OUT_APP"

echo "Done: $OUT_APP"
file "$OUT_APP/Contents/MacOS/$APP_NAME"
echo "Install: drag to /Applications, or: open \"$OUT_APP\""
echo "First launch may require: right-click → Open (ad-hoc signature)."

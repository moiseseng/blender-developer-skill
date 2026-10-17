#!/usr/bin/env bash
# Run a bundled Blender script headless.
#   scripts/blender_run.sh <script.py> [file.blend] -- [script args]
# Finds Blender via $BLENDER_BIN, PATH, or the macOS/Linux default install locations.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
find_blender() {
  if [ -n "${BLENDER_BIN:-}" ] && [ -x "$BLENDER_BIN" ]; then echo "$BLENDER_BIN"; return; fi
  if command -v blender >/dev/null 2>&1; then command -v blender; return; fi
  for c in /Applications/Blender.app/Contents/MacOS/Blender \
           "$HOME/Applications/Blender.app/Contents/MacOS/Blender" \
           /usr/local/bin/blender /opt/homebrew/bin/blender /usr/bin/blender \
           /snap/bin/blender; do
    [ -x "$c" ] && { echo "$c"; return; }
  done
  # Versioned macOS installs (Blender 4.2.app, Blender 5.2.app ...): newest first.
  ls -d /Applications/Blender*.app/Contents/MacOS/Blender 2>/dev/null | sort -V | tail -1
}
BLENDER="$(find_blender)"
[ -n "$BLENDER" ] || { echo "Blender not found. Set BLENDER_BIN=/path/to/blender" >&2; exit 2; }
[ $# -ge 1 ] || { echo "usage: $0 <script.py> [file.blend] -- [args]" >&2; exit 2; }
SCRIPT="$1"; shift
case "$SCRIPT" in /*) ;; *) [ -f "$SCRIPT" ] || SCRIPT="$HERE/blender/$SCRIPT" ;; esac
BLEND=""
if [ $# -ge 1 ] && [ "$1" != "--" ]; then BLEND="$1"; shift; fi
[ "${1:-}" = "--" ] && shift
if [ -n "$BLEND" ]; then
  exec "$BLENDER" -b "$BLEND" --python "$SCRIPT" -- "$@"
else
  exec "$BLENDER" -b --python "$SCRIPT" -- "$@"
fi

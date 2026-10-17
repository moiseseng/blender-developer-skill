#!/usr/bin/env bash
# Check the toolchain blender-3d-team expects, and smoke-test the bundled scripts on a cube.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ok=0; bad=0
pass() { printf '  ✓ %s\n' "$1"; ok=$((ok+1)); }
fail() { printf '  ✗ %s\n' "$1"; bad=$((bad+1)); }
echo "blender-3d-team doctor"

BLENDER="$(BLENDER_BIN="${BLENDER_BIN:-}" bash -c 'source /dev/stdin <<<"$(sed -n "/^find_blender()/,/^}/p" "'"$HERE"'/blender_run.sh")"; find_blender')"
if [ -n "$BLENDER" ] && [ -x "$BLENDER" ]; then
  VER="$("$BLENDER" --version 2>/dev/null | head -1)"
  pass "Blender: $VER ($BLENDER)"
  case "$VER" in *" 4."[2-9]*|*" 5."*|*" 6."*) ;; *) fail "Blender 4.2 LTS or newer is required (scripts use the 4.1+ shading API and EEVEE Next)";; esac
else
  fail "Blender not found (set BLENDER_BIN=/path/to/blender or install from blender.org)"
fi

MCP_DIR="$(ls -d "$HOME/Library/Application Support/Blender/"*/extensions/*/mcp 2>/dev/null | sort -V | tail -1)"
if [ -n "$MCP_DIR" ]; then
  pass "Blender MCP extension: $(grep -E '^version' "$MCP_DIR/blender_manifest.toml" 2>/dev/null | head -1) at $MCP_DIR"
else
  printf '  · Blender MCP extension not found under ~/Library/Application Support/Blender/*/extensions (optional: live Blender control; https://www.blender.org/lab/mcp-server/)\n'
fi

command -v git >/dev/null 2>&1 && pass "git $(git --version | awk '{print $3}')" || fail "git missing (xcode-select --install)"
command -v python3 >/dev/null 2>&1 && pass "python3 $(python3 --version | awk '{print $2}')" || fail "python3 missing"
command -v gh >/dev/null 2>&1 && pass "gh $(gh --version | head -1 | awk '{print $3}')" || printf '  · gh optional (push repos)\n'
command -v ffmpeg >/dev/null 2>&1 && pass "ffmpeg (turntable video)" || printf '  · ffmpeg optional: brew install ffmpeg (turntable .mp4; PNG frames work without it)\n'
command -v gltf-validator >/dev/null 2>&1 && pass "gltf-validator" || printf '  · gltf-validator optional (Khronos glTF validation)\n'

if [ -n "$BLENDER" ] && [ "${1:-}" != "--quick" ]; then
  TMP="$(mktemp -d)"
  if "$BLENDER" -b --python "$HERE/blender/_tests/smoke.py" -- "$TMP" >"$TMP/log.txt" 2>&1 && grep -q "SMOKE_OK" "$TMP/log.txt"; then
    pass "smoke test: audit + export + render on a cube ($TMP)"
  else
    fail "smoke test failed; see $TMP/log.txt"
    grep -E "Error|Traceback|line [0-9]+" "$TMP/log.txt" | head -5 | sed 's/^/      /'
  fi
fi
echo
[ "$bad" = 0 ] && echo "All checks passed." || { echo "$bad check(s) failed."; exit 1; }

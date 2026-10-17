#!/usr/bin/env bash
# SessionStart hook: inject the routing skill so the 3D-team workflow is known from the first message.
# Output follows the Claude Code SessionStart contract:
#   {"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}
set -u
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
SKILL="$ROOT/skills/using-blender-3d-team/SKILL.md"
[ -f "$SKILL" ] || exit 0

# Strip only the leading YAML frontmatter block; a later '---' (horizontal rule) is content.
BODY="$(awk 'fm < 2 && /^---[[:space:]]*$/ { fm++; next } fm >= 2 { print }' "$SKILL")"

CONTEXT="<blender-3d-team>
The blender-3d-team plugin is installed. Its routing skill follows. Read the relevant phase skill before acting on any 3D modeling, texturing, Blender or asset-delivery request.
Plugin root: $ROOT
Phase skills: Skill tool as blender-3d-team:<name> (or read <plugin root>/skills/<name>/SKILL.md). Role agents: Agent tool with subagent_type blender-3d-team:<role>.

$BODY
</blender-3d-team>"

if command -v python3 >/dev/null 2>&1; then
  CONTEXT="$CONTEXT" python3 -c 'import json, os, sys; sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": os.environ["CONTEXT"]}}) + "\n")'
  exit 0
fi

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/}"
  s="${s//$'\t'/\\t}"
  s="$(printf '%s' "$s" | tr -d '\000-\010\013\014\016-\037')"
  printf '%s' "$s"
}
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$(json_escape "$CONTEXT")"

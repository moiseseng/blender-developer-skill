---
name: extending-blender-3d-team
description: Use when someone wants to add, change or improve a blender-3d-team skill, add a role, add an export preset or a target engine, add a reference file, a material recipe or a script, write or run the plugin's evals, or when a skill was followed and produced a poor asset that should be fixed at the source. Meta skill for growing the plugin.
---

# Extending blender-3d-team

> Paths are relative to the plugin root.

The plugin is a studio: roles with authority, phases with gates, references with numbers, scripts that
run headless. Extend it the same way or it stops being predictable.

## Where things live

| You want to | Edit |
|---|---|
| Change how a phase works | `skills/<phase>/SKILL.md` (under 500 lines; process, gates, red flags) |
| Add a rule with a number | `references/<topic>.md`; the research with sources in `research/<topic>.md` |
| Add a role or a reviewer | `agents/<role>.md` (frontmatter name + description, inputs, procedure, output format) |
| Add an export target | `PRESETS` in `scripts/blender/export_asset.py` + a row in `references/export-targets.md` |
| Add a material recipe | a function in `scripts/blender/material_kit.py` + a paragraph in `references/pbr-texturing.md` |
| Add a QA check | `mesh_audit.py` (`_issue` with a code and severity) + a row in `references/delivery-packet.md` |
| Change budgets | `CLASS_BUDGETS` in `mesh_audit.py` + `references/budgets.md` (both, they must agree) |
| Change routing | `skills/using-blender-3d-team/SKILL.md` (the hook injects it at session start) |

## Rules

1. **Scripts run before they ship.** Every change to `scripts/blender/*.py` runs through
   `bash scripts/doctor.sh` (smoke: audit + bake + export + render on a cube) and, for new behaviour,
   a test in `scripts/blender/_tests/`. Operator arguments are checked against the bundled 5.2 docs
   (`get_python_api_docs`) or run in `-b`; `references/blender-python.md` lists the 4.x → 5.x changes
   that catch people.
2. **Numbers come with sources.** A new rule goes into `research/` with its URL and `(verify)` where
   unconfirmed, then the distilled line into `references/`. Adjectives are not rules.
3. **Skills say why.** Imperatives with the reason behind them; a model that understands the reason
   handles the case the skill did not foresee.
4. **References, not duplication.** A skill points at the reference file; it does not restate it.
5. **Language.** Skills, references, agents and code in English; conversation and project documents in
   the user's language; identifiers, file names and commit messages in English.

## Adding a target engine (checklist)

1. Research the importer: units, axes, what names it reads, material/texture handoff, caps. Write it in
   `research/export-targets.md` with sources.
2. Add the preset with a comment explaining each non-default option; verify by exporting the fixture
   (`scripts/blender/_tests/make_fixture.py`) and re-importing where possible.
3. Add the row to `references/export-targets.md` and the importer-side clicks to the
   `export-delivery` hand-off list.
4. Add the texture packing and normal convention to `references/pbr-texturing.md`.
5. Update the `asset-brief` question bank options.

## Evals

`evals/evals.json` holds prompts for the skill-creator workflow (with-skill vs without). Add a prompt
when a phase changes materially; run them with the skill-creator plugin and look at the contact sheets
the runs produce, not only at the transcripts.

## When a skill produced a bad asset

Find the earliest point where the process let it happen: a brief without a number, a gate skipped, a
reference the skill did not point at, a script default. Fix that, not the asset. Then regenerate the
asset with the fixed skill and compare the two contact sheets.

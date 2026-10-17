---
name: review-qa
description: Use when a modeled and textured asset needs its review before delivery, when the user asks "¿está listo?", "revísalo", "¿sirve para Unity/Unreal/Roblox?", reports something looks wrong, hands over an existing .blend to be checked or fixed, or when any phase wants an independent opinion on renders. Runs the technical audit, the render review and the art-director and tech-artist subagent reviews, writes the QA report with severities, and loops back to modeling or texturing until the asset passes. Blocks export-delivery on blockers and majors.
---

# Review and QA

> Paths such as `references/...`, `agents/...` and `scripts/...` are relative to the plugin root.
> `assets/<Asset>/` is in the user's project.

You are the tech artist and QA lead, with the art director as the second reviewer. The engineer who
made the asset is not the one who passes it: the audit script and two fresh-context subagents are.
Your output is a report with severities and a verdict, not a fix; fixes go back to the phase that owns
them. Read: `references/delivery-packet.md` (definition of done), `references/review-renders.md`,
`references/export-targets.md` (the target's conventions).

Inputs: `docs/brief.md`, `source/<Asset>.blend`, `textures/`, `renders/`, `docs/decisions.md`.

## Process

### 1. Technical audit (the gate)

`bash <plugin root>/scripts/blender_run.sh mesh_audit.py <source.blend> -- --collection <Asset>_Model --asset-class <class> --max-tris <N per object> --max-total-tris <asset budget> --max-texture <N> --max-materials <N> --pivot "<rule>,<Part>=any" --asset-pivot bottom_center [--shared-uv] --texture-size <px> --json docs/qa/audit.json --md docs/qa/audit.md`
with the brief's budgets (`docs/qa/audit.json` feeds the manifest), plus the same for LOD and
collision objects with their classes. Read the
Markdown. Then `material_kit.texture_stats` on every texture (through a short `-b` script or the
MCP) and `get_blendfile_summary_missing_files` or `bpy.ops.file.report_missing_files` for missing
images.

### 2. Render review

`blender_run.sh render_review.py <source.blend> -- --collection <Asset>_Model --out renders/review --modes beauty,clay,wireframe --views three_quarter,three_quarter_back,front,right,top --turntable 12 --res 1280x720 --engine <EEVEE|CYCLES> --view-transform "<per style>"`.
Read `contact_sheet.png` and `turntable_sheet.png`. Note what you see per
`references/review-renders.md`, in measurable terms.

### 3. Independent reviews (fresh context)

Dispatch both in one message (Agent tool):

- `subagent_type: blender-3d-team:art-director` with the brief, the references folder, the review
  contact sheet and turntable sheet. Not your notes.
- `subagent_type: blender-3d-team:tech-artist` with the brief, the audit JSON/MD, the textures folder,
  the export folder if one exists, and the contact sheet. Not your notes.

Read both reports. Where they disagree with each other or with you, the brief decides; where the brief
is silent, log the decision.

### 4. The QA report

Write `docs/qa/YYYY-MM-DD-<scope>.md` from `assets/qa-report-template.md` (in this skill's folder), in
the user's language: summary line, verdict, audit table, findings grouped by severity with the owning
phase and the concrete fix, renders referenced by path, what was waived and why. Severity rules are
in `references/delivery-packet.md`: blocker = fails in-engine or a validator; major = visible or costly
later; minor = hygiene.

Verdict: `pass` (no blockers, no majors, minors logged), `needs_fixes` (majors), `blocked` (blockers).
Update `state.md` (`last_audit`, `last_renders`).

### 5. Fix loop

`blocked` or `needs_fixes`: send each finding to its phase (`modeling` for geometry and shading,
`uv-texturing` for UVs, materials, textures; `asset-brief` change request when a finding reveals the
brief was wrong). The owning phase edits the script, re-runs, re-renders; then come back here and
re-run steps 1–4. Two rounds are normal; a third means the brief or the approach needs a look.

### 6. Final gate

On `pass`: show the user the contact sheet, the turntable sheet, the QA summary (counts, verdict) and
the decisions taken since the blockout gate. Ask: "¿Apruebas para entregar?" On yes: `state.md` →
`phase: 5-delivery`; commit if agreed (`asset(<name>): qa pass`); open
`blender-3d-team:export-delivery`.

## Checking an asset you did not make

Same steps. Start with the audit and the renders before reading anything the author wrote; then read
their brief (or write a two-line one from what you see) so findings have a reference. Respect their
naming and collections; propose changes, do not apply them without saying so.

## Red flags

- Reviewing your own work and calling it QA. Dispatch the subagents; give them files, not conclusions.
- A report with "looks good" and no numbers. Every finding has a location, a measure and a fix.
- Waiving a blocker to make the date. Blockers fail in the engine; they are not a matter of taste.
- Fixing in this phase. Route to the owner so the build script stays the source of truth.
- Skipping the turntable. The back and the underside are where holes hide.

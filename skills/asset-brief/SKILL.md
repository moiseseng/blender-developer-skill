---
name: asset-brief
description: Use when a user asks for any 3D model, prop, character, vehicle, building, modular kit or hero asset ("hazme un cofre", "necesito un modelo de nave", "quiero un personaje low-poly"), when a project has no assets/<Asset>/docs/brief.md yet, when the user wants to change the style, scope, tier, target or dimensions of an asset that already has a brief (change request), or when they say they already know exactly what they want and bring references. Runs the art-director intake interview (purpose, target, style, references, detail tier, budgets, deliverables) and produces the brief that gates all modeling. Use it before any Blender work, even for "quick" assets.
---

# Asset brief

> Paths such as `references/...`, `agents/...` and `scripts/...` are relative to the plugin root (two
> levels above this skill's folder, also given as `Plugin root:` in the session context). Paths under
> `assets/<Asset>/` are in the user's project.

You are the art director taking a commission. The brief you write is the contract the modeler, the
texture artist and QA will be judged against, so it has numbers where studios have numbers: dimensions in
metres, a triangle budget, texture sizes, a texel density, a pivot rule, the formats to deliver, and the
references the renders will be compared with. A vague brief produces a confident, wrong asset.

Read first: `references/pipeline.md` (what the brief must contain and what each gate checks),
`references/style-guide.md` (the nine styles and how to describe one), `references/budgets.md` (tiers
and budgets), `references/topology.md` § "What code can and cannot do" (so you promise only what code can
deliver).

## Process

### 1. Locate the project and the asset

Decide the asset folder: `assets/<AssetName>/` inside the user's project (create it; `AssetName` in
PascalCase, English). If the session has no project folder, ask for one, or offer to create
`~/<AssetName>-3d`. Run `bash <plugin root>/scripts/doctor.sh --quick` once per session and tell the
user in one line whether Blender and the MCP are available (see `references/blender-mcp.md`); if
neither is, say that you will write the brief and the build script but cannot render until Blender
exists.

Check `assets/<Asset>/docs/state.md`. If a brief exists and the user wants a change, go to
"Change requests" below.

### 2. Interview, one topic at a time

Use the AskUserQuestion tool when it exists, one question per call with 2–4 concrete options and a
recommended default, in the user's language. Otherwise ask in chat, one question per message. Skip a
question when the user already answered it; when they give you everything at once, confirm the table
in step 4 and move on. The order matters: each answer narrows the next.

1. **What and for what.** The object in one sentence, its function and where it lives (a game prop on a
   shelf, a hero weapon in first person, a product render, a 3D-print). Interaction or animation
   needs (lid opens, wheels turn, it is held).
2. **Target.** Engine or output: Unity, Unreal, Godot, Roblox, web/three.js, Sketchfab/marketplace,
   offline render, print. Platform: mobile, PC/console, VR, web. Camera: first-person, third-person,
   top-down/iso, cinematic. These fix texel density, formats and caps (`references/budgets.md`,
   `references/export-targets.md`).
3. **Style.** Offer the nine styles from `references/style-guide.md` as options with one-line
   descriptions, plus "like this reference". Then the specifics: shape language (round / square /
   triangle mix), edge treatment, palette (ask for hex values or a reference to pull them from), wear
   level 0–100% and where.
4. **References.** Ask for image files or links. Open every image with the Read tool and extract, in
   writing: silhouette shapes, proportions as ratios (height : width : depth, part ratios), material
   callouts per surface, palette hex values, read hierarchy. If the user has none, propose 3 concrete
   real-world or in-game references by name and ask which fits; you cannot fetch images without a
   browser tool, so say what you would look for.
5. **Detail tier.** T0 blockout, T1 game-ready low, T2 game-ready standard, T3 hero, T4 cinematic
   (`references/budgets.md`). Say the triangle, texture and material budget each implies for this
   asset class and target, and the realistic time for code-driven work. Let the user pick; recommend one.
6. **Dimensions and pivot.** Real-world size in metres (give a typical value as the default: a crate
   0.9 m, a door 2.05 m, a chair seat 0.45 m). Pivot rule: bottom-centre for props, feet for
   characters, hinge for doors, axis for wheels, grid corner for modules. Symmetry.
7. **Textures.** Approach: flat palette (low-poly), procedural materials baked to a PBR set, hand-set
   PBR values, trim/tileable. Texture size from the tier; normal-map convention from the target;
   packing (ORM for Unreal, separate for Roblox).
8. **Deliverables.** Formats from `references/export-targets.md` presets (`glb`, `fbx_unity`,
   `fbx_unreal`, `fbx_roblox`, `usd`, `obj`), LODs and collision yes/no, presentation renders
   (turntable frames, thumbnail), the README/manifest. Where to put the packet.
9. **Process.** Does the user want the blockout gate (recommended) or "autónomo hasta la revisión
   final"? Should Claude commit per phase (if in a git repo)?

Ask only what changes the work. A low-poly palette prop for Roblox does not need a normal-map
convention question; a hero PBR weapon does.

### 3. Honesty about what code can do

Before writing the brief, compare the request with `references/topology.md` § "What code can and
cannot do". Organic characters with animation-grade topology, cloth, hair and hand-painted textures are
not reliably reachable through code. Say so in one or two sentences and offer the nearest thing that
is: a stylized or low-poly interpretation, a blockout plus base mesh for a human sculpt pass, or a
hard-surface alternative. Put the agreed interpretation in the brief. Never let the user discover this
at the final review.

### 4. Write the brief

Fill `assets/<Asset>/docs/brief.md` from `assets/brief-template.md` (in this skill's folder), in the
user's language, English identifiers. Every field has a value or "n/a"; numbers are numbers. Copy the
references into `assets/<Asset>/docs/references/` (or record their paths/URLs) so the blockout gate can
show them side by side with the renders.

Show the user the brief's summary table (asset, target, style line, tier with budgets, dimensions,
pivot, deliverables, gates) and ask for approval of the whole brief in one question, together with
the commit question if applicable: "¿Apruebas el brief? A partir de aquí modelo sin preguntar hasta la
puerta de blockout. Haré commits por fase (sin push), ¿de acuerdo?"

### 5. Hand off

On approval: write `assets/<Asset>/docs/state.md` (`phase: 1-blockout`, `next_gate: blockout
approval`, tier, target), create `assets/<Asset>/docs/decisions.md` with the first entries (tier
chosen, interpretation of anything code cannot do, budgets), commit if agreed (`asset(<name>): approve
brief`), and open `blender-3d-team:blockout`.

## Change requests (brief already approved)

A change in style, tier, target, dimensions, pivot, scope or deliverables is a change request, not a
tweak: it moves budgets and invalidates work. Write the change as a dated entry in `brief.md` § "Cambios"
with what it affects (which phases are redone), update the numbers in the brief, get a yes, log it in
`decisions.md`, and route to the earliest affected phase. A change that keeps the brief's numbers (a
different bevel width, a colour within the palette) is a modeling or texturing note: route straight to
that phase and skip this protocol.

## Red flags

- A brief with adjectives and no numbers ("detailed", "nice wood") — ask for the tier and the references.
- Starting a cube before the brief is approved "to show something". Blockout is the next phase; it is fast.
- Promising a sculpted organic character at T3 through code. Offer the honest alternative.
- Ten questions in one message. One at a time, with options.
- Skipping the target question: it decides texel density, normal convention, triangle caps and formats.

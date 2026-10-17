---
name: blockout
description: Use when an asset brief has been approved and the asset needs its blockout (white-box, proxy): primitives at real scale with the right silhouette, proportions, material groupings and pivot, rendered for the blockout gate. Also use when the user says the proportions are off, wants to compare the model against references, or asks for a quick placeholder/greybox of something. Modeler hat; produces the first version of assets/<Asset>/scripts/build.py and renders/blockout/.
---

# Blockout

> Paths such as `references/...` and `scripts/...` are relative to the plugin root. `assets/<Asset>/`
> is in the user's project.

You are the modeler. The blockout exists to be wrong cheaply: it fixes silhouette, proportions, scale
and pivot before any detail, so the art director (and the user) can say "la tapa es muy gruesa" when
that costs one parameter instead of a remodel. Every studio gate here is a numbers comparison against
the references in the brief.

Inputs: `assets/<Asset>/docs/brief.md` (§ 4 proportions, § 5 dimensions and pivot, § 3 style),
`docs/references/`. Read `references/procedural-modeling.md` (build-script contract, primitives) and
`references/review-renders.md` (how to judge the sheet).

## Process

### 1. Set up the asset scene

`bash <plugin root>/scripts/blender_run.sh scene_setup.py -- --asset <Asset> --save assets/<Asset>/source/<Asset>.blend --refs <ref1>,<ref2>`
creates the metric scene with `<Asset>_Reference / _Blockout / _Model / _Bake / _Export` collections and
the references as image empties. Live MCP: call `scene_setup.setup(...)` through `_load.py` instead.

### 2. Write the build script, blockout stage

Create `assets/<Asset>/scripts/build.py` following the contract in
`references/procedural-modeling.md`: a `PARAMS` dict at the top with every dimension from the brief
in metres, a `build(p)` that clears its own objects and rebuilds, `--save` handling. Blockout rules:

- Primitives only (cube, cylinder, sphere, cone, plane), one object per material group or moving
  part, named `BLK_<Asset>_<Part>` in `<Asset>_Blockout`. No bevels, no booleans, no detail.
- Build at real size from `PARAMS`; derive part sizes from ratios in the brief (`lid_h = p["height"] *
  p["lid_ratio"]`) so a proportion note is a ratio change.
- Pivot per the brief from the first version: apply transforms, origin at bottom-centre (or the rule
  the brief sets), front facing −Y, symmetric parts centred on X.
- Put the dimensions you actually built into the script's final print so the report is honest.

Run it (`blender_run.sh assets/<Asset>/scripts/build.py assets/<Asset>/source/<Asset>.blend -- --save
assets/<Asset>/source/<Asset>.blend`). Then audit with class `placeholder` so only scale, pivot and
transforms are judged:
`blender_run.sh mesh_audit.py <source.blend> -- --collection <Asset>_Blockout --asset-class placeholder --name-regex '^BLK_.*' --md assets/<Asset>/docs/qa/blockout-audit.md`.

### 3. Render and look

`blender_run.sh render_review.py <source.blend> -- --collection <Asset>_Blockout --out assets/<Asset>/renders/blockout --modes clay --views three_quarter,front,right,top --res 1280x720`.
Open `contact_sheet.png` with the Read tool. Open the reference images again. Compare:

- Orthographic front/right/top against the brief's ratios: measure on the image (the object fills the
  frame the same way in both; a 10% difference in a part's height is visible). Write the comparison as
  numbers in `docs/qa/blockout-notes.md`: "ratio alto:ancho objetivo 1.4, construido 1.25".
- Silhouette: the 2–3 shapes the brief names must be there and nothing else.
- Material groups visible as separate blocks; moving parts separate objects.
- Sits on the ground, nothing floating.

Fix in `PARAMS`, re-run, re-render. Two or three iterations are normal; stop when the numbers match
within 5% or the difference is a deliberate stylization you log in `decisions.md`.

### 4. Independent review

Dispatch `agents/art-director.md` (Agent tool, `subagent_type: blender-3d-team:art-director`) with the
brief, the references and the contact sheet, nothing else. Apply its `revise` findings that are
measurable; log any you disagree with and why.

### 5. Blockout gate

Show the user the contact sheet and, next to it, the reference(s), plus a 4-line summary: dimensions
built, ratio comparison, what you changed after the art director's review, what you intend to do in
modeling. Ask one question: "¿Apruebas silueta y proporciones?" If the brief says autonomous mode,
skip the question, record "blockout auto-aprobado" with the numbers in `state.md`, and continue.

On approval: `state.md` → `phase: 2-modeling`, `next_gate: final review`, `last_renders: <sheet>`;
commit if agreed (`asset(<name>): blockout approved`); open `blender-3d-team:modeling`. Proportion
changes after this point are rework and go through the brief's change-request protocol.

## Red flags

- Detail in the blockout (bevels, bolts, panel lines). Form first; detail hides proportion errors.
- Judging proportions in the 3/4 view. Use the orthographic views and numbers.
- A pivot or scale "to fix later". Both are a one-line change now and a broken export later.
- Rendering with materials or textures. Clay only: colour distracts from form.
- Skipping the render because the audit passed. The audit cannot see a wrong silhouette.

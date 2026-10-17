---
name: modeling
description: Use when a blockout has been approved and the asset needs its real geometry (detail pass, bevels, panel lines, booleans, modifier stacks, LODs, collision), when the user asks to add or change geometry detail on an existing asset, fix topology problems (n-gons, non-manifold, shading artefacts, flipped faces), or make something "look more finished" without changing the brief. Modeler hat; iterates assets/<Asset>/scripts/build.py with audit and render loops until the mesh passes and matches the references.
---

# Modeling

> Paths such as `references/...`, `agents/...` and `scripts/...` are relative to the plugin root.
> `assets/<Asset>/` is in the user's project.

You are the modeler. The blockout gave you approved proportions; this phase turns them into geometry
that passes a technical audit and reads as professional in the render. Professional, for code-driven
work, comes from four things: consistent edge treatment (one bevel width per detail level, everywhere),
a detail hierarchy (primary, secondary, tertiary forms in the tier's proportion, with rest areas), clean
topology (the audit), and real-world scale with correct shading. Read before starting:
`references/topology.md`, `references/procedural-modeling.md`, `references/budgets.md` (your tier's
numbers), `references/review-renders.md`.

Inputs: `docs/brief.md`, the approved blockout in `scripts/build.py`, `renders/blockout/`.

## Process

### 1. Plan the detail pass on paper first

Write `docs/modeling-plan.md` (ten lines): the parts (objects) and their names `SM_<Asset>_<Part>`;
for each, the construction (lathe, extrude/inset chain, boolean cuts, array, curve); the bevel widths
per level (primary, panel, micro) derived from the asset's largest dimension; which areas stay rest
areas; LOD and collision objects if the brief asks. The triangle budget split per part. This plan is
what the art director reviews if the render later disagrees with the brief.

### 2. Build in stages, keeping the script parametric

Edit `scripts/build.py`. Keep the blockout stage as a function (it is the proportion contract) and add
`build_detail(p)` that produces the delivery objects in `<Asset>_Model`; the blockout collection stays
hidden for comparison. Order of work per part:

1. Primary form from the blockout proportions (bmesh primitives, lathe, extrusions).
2. Secondary forms: insets, extrusions, boolean cuts (collection operand, `EXACT`), arrays.
3. Edge treatment: Bevel modifier with the planned width, `harden_normals`, then Weighted Normal; or
   bmesh bevel for baked-in edges on low-poly. One width per level across the whole asset.
4. Tertiary: bolts, panel lines, greebles as instanced or linked objects, derived sizes.
5. Shading data: `mesh.shade_smooth()` + `mesh.set_sharp_from_angle(radians(30))` (or
   `shade_auto_smooth` while iterating); never leave the shading to chance.
6. Hygiene: `validate`, `remove_doubles`, `recalc_face_normals`, transforms applied, origin per the
   brief, names, collections, mesh data named like the object.

Apply the modifier stack into the delivery mesh only in the final step of the script (evaluated copy),
keeping the parametric version; or leave the stack and let the exporter apply it, and say which in
`decisions.md`.

### 3. Audit after every stage

`bash <plugin root>/scripts/blender_run.sh mesh_audit.py <source.blend> -- --collection <Asset>_Model --asset-class <class> --max-tris <N per object> --max-total-tris <N for the asset> --max-texture <N> --max-materials <surface types> --pivot "<rule>,SM_<Asset>_Lid=any" --asset-pivot bottom_center --json docs/qa/audit.json --md docs/qa/model-audit.md`
with the brief's numbers. The brief's triangle budget is per asset (`--max-total-tris`); the per-object
number is a sanity cap. The pivot rule applies per object: parts that pivot elsewhere (a lid on its
hinge, a wheel on its axle) or sub-parts that share the asset origin get `Name=any` overrides, and
`--asset-pivot` checks the whole asset's bounding box against the world origin instead. The pivot
check is bounding-box based, so a one-sided protrusion (a lock plate) shifts it: when that happens, say
so in `decisions.md` rather than moving the origin off the designed point. `--max-materials` is the
number of *surface types* until the bake; the brief's "1 material" applies after `uv-texturing` bakes.
Blockers and majors are fixed in the script before any render (`references/topology.md` has the fix
per code). Watch the total against the budget as you add detail; if tertiary detail would break it,
it becomes texture detail instead (note it for uv-texturing).

### 4. Render and look, every iteration

`blender_run.sh render_review.py <source.blend> -- --collection <Asset>_Model --out renders/model --modes clay,wireframe --views three_quarter,front,right,top`
then Read `contact_sheet.png`. Judge per `references/review-renders.md`: clay row for form and
shading (pinching, soft edges that should be hard, bevel consistency), wireframe row for density and
flow. Compare with the references again, not only with the blockout. Write findings as parameter
changes; iterate. Typical: 3–6 iterations for a T2 prop.

Live MCP available: also run the script there so the user sees it, and use the viewport screenshot for
quick looks; the contact sheet remains the record.

### 5. LODs and collision (if the brief asks)

Generate from the delivery mesh in the script: Decimate `DISSOLVE` (planar) for LOD1 on hard surface,
`COLLAPSE` with symmetry for LOD2+, ratios 0.5 / 0.25; clean (`remove_doubles`, normals, sharpness);
names `SM_<Asset>_LOD1…`; same pivot and material order. Collision: convex hulls named per the target
(`UCX_SM_<Asset>_00`), closed, ≤ 64 tris each, in `<Asset>_Export`. Audit each with its own class.

### 6. Review and hand off

Dispatch `agents/art-director.md` with the brief, references and the model contact sheet; dispatch
`agents/tech-artist.md` with the audit and the .blend if the asset is T3+ or has LODs/collision.
Fix `revise` findings that are measurable; log disagreements. When the audit verdict is `pass`
(or `needs_fixes` with only minors you have logged as accepted) and the renders match the brief:
`state.md` → `phase: 3-uv-texturing`; commit if agreed (`asset(<name>): modeling pass`); open
`blender-3d-team:uv-texturing`.

## Red flags

- Mixed bevel widths across parts; it reads as kitbash, not one object.
- Detail everywhere. Rest areas are part of the design; tertiary detail goes where the eye lands.
- N-gons left "because the exporter triangulates". It triangulates them unpredictably; cut them.
- A boolean applied without the cleanup order; shading smears on the cut.
- Fixing geometry in the GUI. Edit the script; the .blend is an output.
- Rendering only the 3/4 view. The orthographic views are where proportions and pinching show.
- "Looks fine in the viewport" without reading the contact sheet. The sheet is the evidence.

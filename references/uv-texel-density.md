# UVs and texel density

Distilled from `research/uv-and-texel-density.md` (sources there). Operator signatures confirmed on
Blender 5.2; all angles are radians.

## Rules

1. **Seams follow hard edges and hide.** Put every seam on a hard (sharp) edge when you can: a seam
   plus a hard edge on the same edge costs no extra vertices on the GPU, and a bake needs the UV split
   there anyway. Then hide the rest: underside > back > inside corners > silhouette. Never across a big
   visible flat face.
2. **Unwrap method by surface.** `ANGLE_BASED` for curved or organic; `MINIMUM_STRETCH` (SLIM, 10 to 50
   iterations) when both angle and area matter or seams are sparse; `CONFORMAL` only for planar pieces.
   The API default is `CONFORMAL`, so always pass `method=`. `smart_project` is for hard-surface
   blockouts and bake-checker passes, then `seams_from_islands` makes the result reproducible.
3. **Equalise, then pack.** `average_islands_scale()` before `pack_islands()`; otherwise islands of
   the same world size get different densities.
4. **Margin is per island, not the gap.** With `margin_method='FRACTION'`, `margin = (gap_px / 2) /
   texture_px`. Gap rule A (minimum): 2 px at 512, 4 at 1K, 8 at 2K, 16 at 4K, i.e. `margin = 0.001953`
   at any size. Rule B (atlases, high-contrast neighbours, aggressive mips): double it, `0.003906`.
5. **Rotation.** `rotate_method='CARDINAL'` (90° steps) for anything with directional detail, trims,
   text, pixel-aligned bakes; `'ANY'` only for unique bakes where coverage wins.
6. **Texel density is a project constant.** Pick one standard and tier from it: hero / first-person
   2x, standard props 1x, background 0.5x. Standards found: mobile 256 px/m, third-person PC/console
   512 px/m, first-person 1024 px/m, VR close-up or cinematic 2048 to 4096 px/m, modular environments
   around 200 px/m (2K spans 10 m). Neighbouring assets within ±10%.
7. **Coverage is reported, not gated.** No industry number exists; 72% and 87% both ship. Warn below
   60% on a unique-bake prop; do not fail on it.
8. **Overlap only on purpose.** Mirrored or repeated parts may stack if the shells are identical; move
   duplicates +1.0 U during the bake and back after. Never on a lightmap channel, never on anything
   with per-side detail (AO, decals, text). The mirror seam goes on a hidden edge.
9. **Lightmap UVs (Unity/Unreal static lighting)** are a second UV layer: no overlap, inside 0–1,
   `CARDINAL` pack, ≥4 px gap at the lowest lightmap resolution (gap 2/64 for a 64 lightmap), charts
   split at crevices, texture UV stays `uv_layers[0]` with `active_render=True`.
10. **Bake dilation ≠ UV gap.** `scene.render.bake.margin` (default 16 px, `ADJACENT_FACES`) fills the
    gutter after baking; set it to at least half the UV gap.

## Recipes (Blender 5.2, Edit mode, all faces selected)

Hard-surface prop, unique bake at 2K:

```python
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.edges_select_sharp(sharpness=0.523599)      # 30°: hard edges
bpy.ops.mesh.mark_seam(clear=False)
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.001)
bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(rotate=True, rotate_method="CARDINAL", shape_method="CONCAVE",
                        margin_method="FRACTION", margin=(8 / 2) / 2048, scale=True)
bpy.ops.object.mode_set(mode="OBJECT")
```

Quick auto-UV for a blockout or checker test: `bpy.ops.uv.smart_project(angle_limit=1.15192,
island_margin=0.003, rotate_method="AXIS_ALIGNED_Y")` then `seams_from_islands(mark_seams=True)`.

Tileable material on a surface: `bpy.ops.uv.cube_project(cube_size=2.0)` (cube_size in metres sets
the repeat directly); UVs may leave 0–1, which the audit flags as `UV_OUT_OF_BOUNDS`: note it in
decisions.md as intentional.

Trim strips: unwrap one quad to a true rectangle, `follow_active_quads(mode="LENGTH_AVERAGE")`,
`align_rotation(method="AUTO")`.

Set a target density after packing (keeps island ratios): compute `current = mesh_audit` texel density
(px/m, world space), then scale every UV about the layout centre by `target / current`.

## Measuring (what `mesh_audit.py` reports)

`TD = texture_px × sqrt(uv_area / mesh_area_world)` in px/m. The audit gives mean, min, max and the
coefficient of variation (`texel_density_cv`): above 0.35 means stretch or inconsistent island scale.
`uv_coverage` is rasterised (stacked islands are not double-counted); `uv_overlap_fraction` is the share
of covered texels hit twice; `uv_flipped_faces` are faces with negative signed UV area (mirrored on
purpose or a flipped island). In Blender's UV editor the same things are the stretch overlay
(`show_stretch`, `display_stretch_type='ANGLE'|'AREA'`) and `uv.select_overlap()`.

A UV layout image for the QA report: `bpy.ops.uv.export_layout(filepath=..., mode='PNG',
size=(2048, 2048), opacity=0.25)` (needs Edit mode with faces selected).

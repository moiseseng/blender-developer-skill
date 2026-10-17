# UV mapping, texel density and texture atlasing standards (Blender 5.2, bpy)

Research notes for the blender-3d-team skill. Operator signatures below were confirmed against the
Blender 5.x Python API / manual RST bundled with the connected Blender (Blender MCP docs tools) on
2026-10-17; the fetched manual navigation identified itself as the 5.2 LTS manual.
Items marked `(verify)` could not be confirmed against a primary source. Polycount forum pages
returned HTTP 403 to both fetch and curl; numbers from them are cited "via search snippet".

## Contents
1. Seam placement rules
2. Unwrap methods in Blender 5.x and when to use each
3. Pack Islands: parameters, margin formula, packing efficiency
4. Texel density: definition, formula, standard values, consistency
5. Padding / margin rules by texture size and mipmapping
6. Overlapping and mirrored UVs
7. Second UV channel for lightmaps (Unity, Unreal)
8. Atlases vs trim sheets vs tileables vs UDIMs
9. UV QA checks
10. Computing texel density and coverage with bpy/bmesh

---

## 1. Seam placement rules

1. Think "scissors": cut so the surface flattens with as little tearing as possible; put the cut on the
   least visible edge (Blender manual example: the back-most edge of a cylinder) (Blender manual).
2. Hidden-edge priority order: underside > back face > inside corners/crevices > silhouette edges.
   Never run a seam across a large flat visible face.
3. Baking rule: split UVs wherever there is a hard edge (sharp/split normal); the converse is not
   required, a UV seam does not need a hard edge (Polycount normal-map baking thread, via snippet).
4. Cost rule: every seam or hard edge doubles vertices on the GPU; a seam and a hard edge on the same
   edge cost nothing extra, so align them (same thread, via snippet).
5. Seams need not form closed loops; they only need to resolve regions that would stretch. Check with
   Select Linked in face mode: if faces beyond the intended island get selected the seam is open (manual).
6. For lightmap UVs, split charts at deep recesses/crevices so shadowed and lit faces do not share
   texels; otherwise keep charts contiguous, because every split breaks lighting continuity (Epic).
7. Disconnected sub-meshes become their own islands automatically (manual).

Operators (confirmed 5.2):
- `bpy.ops.mesh.edges_select_sharp(sharpness=0.523599)`  -- radians; 0.5236 = 30 deg, range [0.0001745, pi].
- `bpy.ops.mesh.mark_seam(clear=False)`  -- `clear=True` removes seams.
- `bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)`  -- island borders -> seams (and
  optionally sharp edges), useful after Smart UV Project to make the layout reproducible.

Sources: https://docs.blender.org/manual/en/latest/modeling/meshes/uv/unwrapping/seams.html ,
https://polycount.com/discussion/comment/1689459 (403; via snippet),
https://dev.epicgames.com/documentation/en-us/unreal-engine/understanding-lightmapping-in-unreal-engine

## 2. Unwrap methods in Blender 5.x and when to use each

All angles in operator arguments are radians. Always pass `method=` explicitly: the API default for
`unwrap` is `'CONFORMAL'` even though its own docstring says Angle Based usually gives better results.

| Operator (5.2 signature) | What it does | Use for |
|---|---|---|
| `bpy.ops.uv.unwrap(method='CONFORMAL', fill_holes=False, correct_aspect=True, use_subsurf_data=False, margin_method='SCALED', margin=0.001, no_flip=False, iterations=10, use_weights=False, weight_group="uv_importance", weight_factor=1.0)` | Seam-based unwrap. `method` in `'ANGLE_BASED'` (ABF), `'CONFORMAL'` (LSCM), `'MINIMUM_STRETCH'` (SLIM, added in 4.3). `iterations`, `no_flip`, `use_weights`/`weight_group`/`weight_factor` apply to Minimum Stretch only. | Default for anything hand-seamed. ANGLE_BASED for organic; CONFORMAL only for simple/planar pieces (faster, less accurate); MINIMUM_STRETCH when area AND angle distortion matter or seams are sparse. |
| `bpy.ops.uv.smart_project(angle_limit=1.15192, margin_method='SCALED', rotate_method='AXIS_ALIGNED_Y', island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)` | Splits by normal angle (`angle_limit` default 1.15192 rad = 66 deg, max pi/2) then projects each group. Lower limit = more, flatter islands. | Hard-surface/mechanical/architecture blockouts, auto-UV for baking checkers, first pass before `seams_from_islands`. Not for characters. |
| `bpy.ops.uv.lightmap_pack(PREF_CONTEXT='SEL_FACES', PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False, PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.1)` | Packs EACH FACE separately; `PREF_PACK_IN_ONE` shares one UV space across selected objects; `PREF_BOX_DIV` 1-48 quality. Result is disconnected/distorted (manual). | Blender-internal light/AO bakes only. Not for engine lightmaps (per-face charts waste texels and break lighting continuity); see section 7. |
| `bpy.ops.uv.follow_active_quads(mode='LENGTH_AVERAGE')` | Grows UVs from the active quad along quad loops; `mode` in `'EVEN'`, `'LENGTH'`, `'LENGTH_AVERAGE'`. Ignores non-quads; may exit 0-1 (manual). | Straight strips for trim sheets, pipes, belts, roads. First unwrap the active quad to a true rectangle. |
| `bpy.ops.uv.project_from_view(orthographic=False, camera_bounds=True, correct_aspect=True, clip_to_bounds=False, scale_to_bounds=False)` | Projects from the current 3D view. | Decals, flat signage, camera-projected textures, matte-painting planes. |
| `bpy.ops.uv.cube_project(cube_size=1.0, correct_aspect=True, clip_to_bounds=False, scale_to_bounds=False)`; `bpy.ops.uv.cylinder_project(direction='VIEW_ON_EQUATOR', align='POLAR_ZX', pole='PINCH', seam=False, radius=1.0, ...)`; `bpy.ops.uv.sphere_project(direction=, align=, pole=, seam=False, ...)` | Box/cylinder/sphere projection; islands overlap until packed. `direction` in `'VIEW_ON_EQUATOR'`, `'VIEW_ON_POLES'`, `'ALIGN_TO_OBJECT'`; `pole` in `'PINCH'`, `'FAN'`; `seam=True` splits by existing seams. | Placeholder tileable-material mapping on blockouts; `cube_size`/`radius` in world units set density directly. |
| `bpy.ops.uv.minimize_stretch(fill_holes=True, blend=0.0, iterations=0)` | Relaxes angles. `iterations=0` is unlimited only interactively: in scripts pass a finite count (e.g. 50-200). | Post-relax of ABF/LSCM results. |
| `bpy.ops.uv.average_islands_scale(scale_uv=False, shear=False)` | Scales islands to equal texel density by 3D area. | Always after unwrapping and before packing. |
| `bpy.ops.uv.align_rotation(method='AUTO', axis='X', correct_aspect=False)` | Rotates islands to an axis (`'AUTO'`, `'EDGE'`, `'GEOMETRY'`). | Straightening trim strips and hard-surface islands before CARDINAL packing. |

Minimum Stretch notes: implemented by Lukasz Czyz (UVPackmaster) on Aurel Gruber's SLIM code, in
Blender 4.3; author's tests: 5 iterations already less stretched than ABF/LSCM, 10 iterations
comparable in time to the old methods, gains plateau by ~50 iterations (80.lv).
`fill_holes=True` on open meshes avoids overlaps and preserves symmetry (manual). `correct_aspect`
only works when the material has an Image Texture node selected in the Shader Editor (manual).

Sources: https://docs.blender.org/manual/en/latest/modeling/meshes/editing/uv.html ,
https://docs.blender.org/api/current/bpy.ops.uv.html ,
https://80.lv/articles/blender-received-new-uv-unwrapping-algorithm/

## 3. Pack Islands: parameters, margin formula, packing efficiency

Confirmed 5.2 signature:
`bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, rotate_method='ANY', scale=True, merge_overlap=False, margin_method='SCALED', margin=0.001, pin=False, pin_method='LOCKED', shape_method='CONCAVE')`

- `udim_source`: `'CLOSEST_UDIM'`, `'ACTIVE_UDIM'`, `'ORIGINAL_AABB'`, `'CUSTOM_REGION'`. Custom region is
  set with `bpy.ops.uv.custom_region_set(xmin, xmax, ymin, ymax)` and needs
  `ToolSettings.use_uv_custom_region = True`; intended for atlas regions and trim-sheet zones (manual).
  Version it first appeared `(verify)`; it is present in the 5.2 bundled docs.
- `rotate_method`: `'ANY'`, `'CARDINAL'` (90 deg only), `'AXIS_ALIGNED'`, `'AXIS_ALIGNED_X'`, `'AXIS_ALIGNED_Y'`.
  Use `'CARDINAL'` or axis-aligned for anything with directional texture detail, trims, text, or
  pixel-aligned bakes; `'ANY'` only for unique bakes where efficiency wins.
- `shape_method`: `'CONCAVE'` (exact), `'CONVEX'` (hull, never places islands in holes), `'AABB'`.
- `margin_method`: `'SCALED'`, `'ADD'`, `'FRACTION'`. Only FRACTION maps to pixels (next bullet).
- `pin=True` + `pin_method` (`'SCALE'`, `'ROTATION'`, `'ROTATION_SCALE'`, `'LOCKED'`) protects pre-placed islands.
- `merge_overlap=True` keeps stacked (mirrored) shells together during packing.

Margin is not the gap. Manual: with FRACTION, `margin = 1/1024` on a 1024 texture gives 1 px around
EACH island, so islands are no closer than 2 px. Therefore:

    margin_method='FRACTION', margin = (gap_px / 2) / texture_px

Performance (manual): `shape_method='AABB'` + `margin_method='ADD'` is fastest; FRACTION can be up to
10x slower; CONCAVE/CONVEX are much slower than AABB; `rotate=True` costs little and usually improves
the pack, keep it on. For production packs use CONCAVE + FRACTION + rotate; for quick checker
previews use AABB + ADD.

UV coverage targets: no hard industry number was found. Polycount practitioners: a shotgun at 87% is
not better than a rifle at 72%, and chasing the last 1% is diminishing returns (via snippet). A
UV-Packer demo counted 48% as a good result versus 35% (80.lv, via snippet). Working rule: report coverage, warn
below 60% for unique-bake props, do not hard-fail on it `(verify)`.

Sources: https://docs.blender.org/manual/en/latest/modeling/meshes/uv/editing.html ,
https://polycount.com/discussion/comment/2060007 (403; via snippet),
https://80.lv/articles/uv-packer-3-released-for-free/

## 4. Texel density: definition, formula, standard values, consistency

Definition: texels per unit of world length, px/cm or px/m (Foundry Modo docs: "texture pixels that
span a given real-world distance"). Example from Modo: 512 px/m needs 2 UV units of a 256 texture for
1 m, but only 0.5 UV units of a 1024 texture.

Formula (Texel Density Checker source, `tdcore.cpp` and `utils.py`):

    TD = scale * sqrt(uv_area) / sqrt(mesh_area)
    scale = (largest_side_px / sqrt(aspect_ratio)) / (100 * scene.unit_settings.scale_length)   # -> px/cm
    px/m = px/cm * 100 ; px/in = px/cm * 2.54 ; px/ft = px/cm * 30.48

For a square texture this is `TD = sqrt(uv_area * W * H / mesh_area)`; uv_area is the fraction of the
0-1 square, mesh_area in scene units. Equivalences: 1024 px/m = 10.24 px/cm; a 1 m x 1 m face filling
a 1024 texture is 10.24 px/cm; at 5.12 px/cm a 512 texture covers 100 x 100 cm and a 1024 covers
200 x 200 cm (Polycount via snippet).

Standard values found (choose ONE project standard and tier from it):

| Context | Density | Source |
|---|---|---|
| Mobile | 256 px/m (2.56 px/cm); mobile/VR range 256-512 px/m | add-on preset list (via snippet, attribution `(verify)`); Strayspark |
| Third-person PC/console | 512 px/m (5.12 px/cm) "most common"; range 512-1024 px/m | Polycount (via snippet); Strayspark |
| First-person (weapons, hands) | 1024 px/m (10.24 px/cm); range 1024-2048 px/m | Polycount (via snippet); Strayspark |
| VR close inspection / cinematic | 2048 px/m (20.48 px/cm); 2048-4096 px/m | snippet `(verify)`; Strayspark |
| Modular environment (Frozenbyte) | 200 px/m: 1K spans 5 m, 2K spans 10 m | Frozenbyte wiki |
| Leonardo Iezzi's TD tables (px/cm by texture size and importance) | PDF behind Gumroad; values `(verify)` | Gumroad link below |

Asset-importance tiers (common practice, `(verify)` as a published standard): hero/first-person at
2x the project standard, standard props at 1x, background/distant at 0.5x, skybox/terrain decoupled.
Texture size by asset class (Strayspark): 512 small props and debris; 1K medium props and
third-person weapons; 2K large environment surfaces, first-person weapons, character bodies; 4K
character faces, first-person hands, hero items. BC7 VRAM per map: 1K about 1.33 MB, 2K about
5.33 MB, 4K about 21.33 MB.

Consistency rules:
1. Scene in metres with `unit_settings.scale_length = 1.0` (or factor it as tdcore does); apply the
   object's world matrix before measuring.
2. Per object: `average_islands_scale()` before packing, then scale the layout to the target TD
   (TD Checker "Set TD / Average" keeps island ratios; "Each" normalises every island).
3. Per set: compare each object's TD to the project standard (TD Checker "TD from Active to
   Others"); tolerance +-10% between neighbouring assets `(verify)`.
4. `pack_islands(scale=True)` changes TD: set TD after packing, or pack with `scale=False`.

Sources: https://learn.foundry.com/modo/12.0/content/help/pages/uving/texel_density.html ,
https://github.com/mrven/Blender-Texel-Density-Checker (tdcore/tdcore.cpp, texel_density/utils.py, docs/texel_units.md),
https://www.strayspark.studio/blog/texture-resolution-guide-games-512-1k-2k-4k ,
https://wiki.frozenbyte.com/index.php/3D_Asset_Workflow:_Tile_Textures_and_Trimsheets ,
https://polycount.com/discussion/comment/2486725 (403; via snippet), https://leonano.gumroad.com/l/texeldensity

## 5. Padding / margin rules by texture size and mipmapping

Why: mipmapping halves the texture per level and blends neighbouring pixels, so colour from an
adjacent island bleeds across the gap; a gap of P px survives log2(P) mip levels before closing.
A 2048 texture mipped to 256 (3 levels) with 4 px padding has 0.5 px left (Polycount via snippet).

Two rules found:

| Texture | Rule A (KarlS, Blender Artists) | Rule B (Polycount, via snippet) |
|---|---|---|
| 512 | 2 px | 4 px |
| 1024 | 4 px | 8 px |
| 2048 | 8 px | 16 px |
| 4096 | 16 px | 32 px "will never be a bad thing" |
| 8192 | 32 px | - |

Recommendation: Rule A is the minimum gap between islands; use Rule B for high-contrast neighbours,
aggressive mip bias, or atlases shared by distant objects. Rule A is a constant fraction of the
texture (gap = texture/256), so in Blender it is simply:

    pack_islands(margin_method='FRACTION', margin=(gap_px/2)/texture_px)   # Rule A: margin = 0.001953 at every size
    # Rule B: margin = 0.003906

Bake dilation is separate from the UV gap: `scene.render.bake.margin` (pixels, default 16, range
0-32767) extends the baked result as a post filter with `margin_type` default `'ADJACENT_FACES'`
(confirmed 5.x API); set it to at least half the UV gap so dilation fills the gutter. Lightmaps:
Unity default Pack Margin 4 px assuming a 1024 lightmap; Unreal requires >= 4 texels between charts
because DXT compresses 4x4 blocks, and no border padding (Lightmass pads the atlas border).

Sources: https://blenderartists.org/t/what-value-for-the-pixel-margin/1623197 ,
https://polycount.com/discussion/comment/2584460/ (403; via snippet),
https://docs.blender.org/manual/en/latest/modeling/meshes/uv/editing.html ,
https://docs.unity3d.com/Manual/LightingGiUvs-Reference.html ,
https://dev.epicgames.com/documentation/en-us/unreal-engine/understanding-lightmapping-in-unreal-engine

## 6. Overlapping and mirrored UVs

Allowed: symmetric halves, repeated parts (bolts, tiles, tread links), trim-sheet and tileable
mapping. Stacked shells must be geometrically identical.

Baking procedure: keep one copy in 0-1 and move every duplicate exactly +1.0 in U (or V) so the baker
ignores it; bake; move them back. Otherwise two 3D positions compete for the same texel and produce
bake errors, and 3D-projected masks/decals in Substance Painter break (Polycount via snippet; an Adobe
Community thread, via snippet, states overlapping UVs are not a supported workflow). Marmoset Toolbag 3 displayed
mirrored bakes incorrectly in-app while the exported maps were fine (Polycount via snippet).

Forbidden: the lightmap UV channel (Unreal flags overlap in orange, wrapping outside 0-1 in green),
unique bakes with position-based masks, per-face data (AO/curvature that must differ per side),
decals and text. Mirrored normal maps show a seam on the mirror line: put that seam on a hidden
edge; MikkTSpace handles the flipped bitangent sign in engines `(verify per engine)`.

Blender: `bpy.ops.uv.select_overlap(extend=False)` finds overlaps; `pack_islands(merge_overlap=True)`
keeps stacks together; a mirrored (negative-area) island has a negative signed UV area (section 10).

Sources: https://polycount.com/discussion/227790/marmoset-toolbag-3-inaccurate-bake-display-with-mirrored-uvs (403; via snippet),
https://polycount.com/discussion/comment/2723523/ (403; via snippet),
https://community.adobe.com/t5/substance-3d-painter-bugs/when-baking-textures-even-on-a-flat-surface-the-curvature-map-detects-the-uv-seams-as-if-they-were/idi-p/15600444 ,
https://dev.epicgames.com/documentation/en-us/unreal-engine/understanding-lightmapping-in-unreal-engine

## 7. Second UV channel for lightmaps (Unity, Unreal)

Common requirements: charts inside [0,1]x[0,1], zero overlap, padding between charts, angles and
relative areas preserved (Unity), one chart per contiguous lit region, splits at crevices (Epic).

Unity: lightmap UVs live in `Mesh.uv2` (channel index 1, shown as "UV1"). Generate Lightmap UVs
defaults: Hard Angle 88 deg (0-180; 180 treats everything smooth, for organic meshes), Angle Error
8%, Area Error 15%, Pack Margin 4 px assuming the mesh fills a 1024 lightmap (range 1-64); Margin
Method `Manual` or `Calculate` (uses Min Lightmap Resolution in texels/unit and Min Object Scale).

Unreal: "Lightmap Coordinate Index" selects the channel (typically 1). Chart spacing >= 4 texels
(DXT 4x4 blocks). No border padding needed. Lightmass pads 1 px per side, so the snapping grid for a
target resolution is `1 / (res - 2)`; for 64 that is 1/62 = 0.016129. Auto-generation: Source
Lightmap Index 0, Destination Lightmap Index 1, Min Lightmap Resolution power of 2 (default 64
`(verify)`); padding is derived from that resolution. Texture UVs may overlap or wrap; lightmap UVs
may not. UE5 with Lumen does not use lightmaps; they matter for baked/static lighting `(verify)`.

Blender recipe:
1. `uv2 = mesh.uv_layers.new(name="Lightmap")`; index 0 stays the texture UV; `mesh.uv_layers.active_index = 1` makes the lightmap the edit target; keep `mesh.uv_layers[0].active_render = True` so renders/bakes do not switch to the lightmap channel.
2. Seams: hard edges (`edges_select_sharp` at the project's smoothing angle) plus crevices; `unwrap(method='ANGLE_BASED')`.
3. `average_islands_scale()`, then `pack_islands(rotate_method='CARDINAL', shape_method='CONCAVE', margin_method='FRACTION', margin=(gap/2)/lightmap_res, scale=True)` with gap >= 4 px at the lowest lightmap resolution the mesh will use (e.g. 2/64 for a 64 lightmap).
4. Verify: zero `select_overlap`, no UV outside 0-1 (section 9). `lightmap_pack` is acceptable only for Blender's own bakes.
5. Export keeps all UV maps in FBX/glTF; name channels consistently (UVMap, Lightmap).

Sources: https://docs.unity3d.com/Manual/LightingGiUvs-GeneratingLightmappingUVs.html ,
https://docs.unity3d.com/Manual/LightingGiUvs-Reference.html ,
https://dev.epicgames.com/documentation/en-us/unreal-engine/understanding-lightmapping-in-unreal-engine ,
https://dev.epicgames.com/documentation/en-us/unreal-engine/generating-lightmap-uvs-in-unreal-engine

## 8. Atlases vs trim sheets vs tileables vs UDIMs

| Technique | Use when | Blender setup |
|---|---|---|
| Tileable (0-1 repeats) | Large continuous surfaces: walls, floors, terrain, rope; mesh size irrelevant | `cube_project(cube_size=...)` or unwrap, then scale UVs so TD matches the standard (Frozenbyte: 200 px/m, 2K spans 10 m); UVs may exceed 0-1 |
| Trim sheet | Modular sets with mostly planar/extruded geometry; architecture kits | Strips laid on a grid divisible by 10; each strip tiles in >= 1 direction; keep strips rectangular; flat border zones with normal (128,128,255); `follow_active_quads` + `align_rotation` to straighten; overlap encouraged; non-square sheet: scale U by the aspect (50% U for 2:1) |
| Texture atlas | Many unique small objects or a character set sharing one material to cut draw calls | Normalise TD per object first, then pack all into one 0-1 space (multi-object edit mode) with Rule A/B margins; reserve zones with `pack_islands(udim_source='CUSTOM_REGION')`; overlap only for identical parts |
| UDIM | Hero/film assets needing >4K of unique texels; realtime only with virtual texturing `(verify engine support)` | Tiles start at 1001, 10 per row, 1011 sits above 1001; tile = `1001 + floor(u) + 10*floor(v)` (confirmed by `uv.export_layout(export_tiles='UDIM')` docstring); create a tiled image, manage in UDIM Tiles panel; manual suggests >= 3 tiles (4K/2K/1K by importance); glTF export splits tiles into separate images |

Trim sheet vs atlas is intent: unique detail of many objects = atlas; decorative repeating strips for
one building = trim (Polycount via snippet). Unique unwrap is reserved for complex non-planar one-offs
(Frozenbyte).

Sources: https://wiki.frozenbyte.com/index.php/3D_Asset_Workflow:_Tile_Textures_and_Trimsheets ,
https://docs.blender.org/manual/en/latest/modeling/meshes/uv/workflows/udims.html ,
https://docs.blender.org/manual/en/latest/modeling/meshes/uv/editing.html ,
https://polycount.com/discussion/comment/2667525 (403; via snippet)

## 9. UV QA checks

| Check | Blender UI | Script rule |
|---|---|---|
| Stretch | UV Editor overlay `SpaceUVEditor.show_stretch = True`, `display_stretch_type = 'ANGLE'` or `'AREA'`; blue low, red high (manual) | Area: per-face `(uv_area/total_uv)/(mesh_area/total_mesh)`; flag outside 0.8-1.25 `(verify threshold)`. Angle: sum of abs(uv corner angle - 3D corner angle); flag > 15 deg per corner `(verify)` |
| Flipped islands | No built-in "select flipped" operator found in the 5.2 API `(verify)` | Signed UV area (shoelace) < 0 on an island whose neighbours are positive = flipped; fix by scaling the island by -1 on U |
| Out of bounds | Visual against the 0-1 grid; UDIM grid overlay for tiles | Any loop uv.x or uv.y outside [0,1] (allow when UDIM or bake-offset is intended) |
| Overlap | `bpy.ops.uv.select_overlap()` then inspect | Count selected faces after `select_overlap`; must be 0 for lightmap and unique-bake channels |
| Density variance | TD Checker checker material / vertex-colour viz | TD per island vs median; flag > +-10% unless tiered on purpose `(verify)` |
| Coverage | - | Sum of island UV areas (overlaps double-count; see section 10) |
| Review image | `bpy.ops.uv.export_layout(filepath, mode='PNG', size=(2048, 2048), opacity=0.25, export_tiles='NONE' or 'UDIM')` | Attach to QA report |

Sources: https://docs.blender.org/manual/en/latest/editors/uv/overlays.html ,
https://docs.blender.org/api/current/bpy.ops.uv.html , https://github.com/mrven/Blender-Texel-Density-Checker

## 10. Computing texel density and coverage with bpy/bmesh

API points (confirmed 5.2): `bm.loops.layers.uv.verify()` returns the active UV layer or creates one;
`bm.loops.layers.uv.active`; `loop[uv_layer].uv` is a 2D `mathutils.Vector`; `loop[uv_layer].pin_uv`;
`face.calc_area()` is in the mesh's local space. In object mode use `mesh.uv_layers.active.uv[i].vector`
(`MeshUVLoopLayer.data` is deprecated in 5.x).

```python
import bpy, bmesh, math

def uv_report(obj, tex_w=2048, tex_h=2048):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)                       # world-space areas (object scale matters)
    unit = bpy.context.scene.unit_settings.scale_length  # 1.0 when the scene is in metres
    uv_layer = bm.loops.layers.uv.verify()
    faces, tot_uv, tot_geo = [], 0.0, 0.0
    for f in bm.faces:
        uvs = [l[uv_layer].uv for l in f.loops]
        n = len(uvs)
        signed = 0.5 * sum(uvs[i].x * uvs[(i+1) % n].y - uvs[(i+1) % n].x * uvs[i].y for i in range(n))
        uv_a, geo_a = abs(signed), f.calc_area() * unit * unit
        td = math.sqrt(uv_a * tex_w * tex_h / geo_a) if uv_a > 0 and geo_a > 0 else 0.0  # px per metre
        oob = any(not (0.0 <= c.x <= 1.0 and 0.0 <= c.y <= 1.0) for c in uvs)
        faces.append({"index": f.index, "td_px_m": td, "flipped": signed < 0, "oob": oob,
                      "uv_area": uv_a, "geo_area": geo_a})
        tot_uv += uv_a; tot_geo += geo_a
    bm.free()
    td_mean = math.sqrt(tot_uv * tex_w * tex_h / tot_geo) if tot_geo > 0 else 0.0
    return {"td_px_m": td_mean, "td_px_cm": td_mean / 100.0, "coverage": tot_uv, "faces": faces}
```

Notes:
- Run from Object Mode: `bm.from_mesh()` reads stored mesh data, which is stale in Edit Mode. In Edit
  Mode use `bm = bmesh.from_edit_mesh(obj.data)` instead and do not call `bm.free()`.
- `coverage` is the summed island area as a fraction of the 0-1 square; stacked shells count twice,
  so for a true value subtract overlaps or rasterise the layout `(verify method)`.
- Per-island values: group faces whose loops share UV coordinates across an edge (TD Checker does this
  in `utils.get_uv_islands()`), then apply the same formula per group.
- Set a target density: `s = target_td / current_td`; for every loop `uv = pivot + (uv - pivot) * s`
  with pivot = island centre, (0,0), or the 2D cursor (TD Checker "Scale Anchor" options), then
  `bm.to_mesh(obj.data)`.
- Non-square textures: `tex_w * tex_h` in the formula already equals `(largest_side / sqrt(aspect))**2`.

Sources: https://docs.blender.org/api/current/bmesh.types.html ,
https://docs.blender.org/api/current/bpy.types.MeshUVLoopLayer.html ,
https://github.com/mrven/Blender-Texel-Density-Checker/blob/master/texel_density/utils.py ,
https://github.com/mrven/Blender-Texel-Density-Checker/blob/master/tdcore/tdcore.cpp

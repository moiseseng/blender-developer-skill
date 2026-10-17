# Topology and Modeling Best Practices for Professional-Quality Meshes (Blender 5.2, bpy/bmesh)

Notes for the "Blender 3D team" skill. Operator names, defaults and enums were checked against the Blender 5.2 LTS manual
and Python API bundled with the Blender MCP server; other numbers come from each section's URLs. `(verify)` = unconfirmed.

## Contents
1. Topology fundamentals: quads, poles, edge flow, where tris/ngons are allowed
2. Subdivision-surface rules and the real-time bevel + weighted-normals alternative (incl. Smooth by Angle in 4.1+/5.x)
3. Boolean workflow cleanup
4. Common defects, how to detect them in Blender, how to fix them (plus the automated gate)
5. Polycount budgets by target platform and asset class
6. Scale, orientation, pivot and transform conventions
7. LOD generation and collision-mesh conventions
8. What code-driven modeling can and cannot realistically achieve

---

## 1. Topology fundamentals

Rules (quad-dominant, "every edge has a reason"):
- A regular interior vertex has valence 4. A **pole** is any vertex with valence != 4: N-pole = 3 edges, E-pole = 5 edges.
  Find them with `bpy.ops.mesh.select_by_pole_count(pole_count=4, type='NOTEQUAL', exclude_nonmanifold=True)`.
  Manual: "Poles can cause ugly pinching when using the Subdivision Surface modifier". Put poles on flat, non-deforming
  areas; keep them out of joints, cheeks and mouth corners (Polycount).
- Catmull-Clark turns every face into quads; an n-sided face produces a centre vertex of valence n, a triangle a 3-pole.
  So every tri/ngon under subdivision is a pole generator, not just a face-count issue.
- Polygon density: more loops where there is curvature, fewer on straight/flat runs (Polycount). Target roughly uniform
  quad size within a surface; avoid spans that differ by more than about 2x between neighbours (industry practice, `(verify)`).
- Deforming meshes need edge loops that follow the muscle/bend direction. Highest-priority areas (Polycount): crotch/hips,
  shoulders/armpits, mouth corners/cheeks, knees, elbows, hands/fingers. Minimum 3 loops across a bending joint
  (one at the pivot, one each side) is the common floor; 5+ for hero characters (industry practice, `(verify)`).
- Triangles are **acceptable** in final low-poly game meshes (GPU triangulates anyway), on flat or hidden areas, and to
  terminate loops on hard surfaces where no subdivision follows ("triangles are fine, but you want every edge to be
  there for a reason", Polycount). **Not acceptable** in deforming regions, in sculpt base meshes (pinching), or on
  curved surfaces that will be subdivided.
- Ngons are **acceptable only** when planar, non-deforming, and not under Subdivision Surface (e.g. the top of a flat
  panel). Never on curved surfaces: "the triangulation of a distorted n-gon is undefined" (Blender manual, Mesh Analysis),
  which produces random shading and different triangulation per exporter. Roblox: "Use quads whenever possible. Avoid faces
  with 5 or more sides".
- Avoid long thin (sliver) triangles: they cost fill-rate ("Long thin triangles can cause slower rendering", Polycount) and
  shade badly. Bevels on low-poly meshes are the usual source (Polycount FWN page).
- Vertex count, not triangle count, drives GPU cost. Every UV seam, sharp/smoothing split and material change duplicates
  the vertices along it (Polycount Polygon Count). Keep seams and sharp edges aligned with each other where possible.
- Control triangulation yourself before baking/export: a quad can become a "ridge" or a "valley" depending on the
  diagonal (Polycount). Use a Triangulate modifier (quad method Beauty for organic, Fixed for hard surface) or
  `bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY')`.

Sources: http://wiki.polycount.com/wiki/Topology , http://wiki.polycount.com/wiki/Polygon_Count ,
http://wiki.polycount.com/wiki/GameRenderingTerminology ; Blender 5.2 manual: modeling/meshes/selecting/all_by_trait
(Poles by Count), modeling/meshes/mesh_analysis (Distortion).

## 2. Subdivision-surface modeling and the real-time alternative

### 2a. Subdivision-surface (high-poly / render) rules
- Each subdivision level multiplies vertex count by ~4 (Polycount). Level 2 on a 10k cage = ~160k verts. Keep `levels`
  (viewport, default 1) <= `render_levels` (default 2); manual warns the reverse wastes quality and memory.
- Holding/support loops: one loop each side of an edge that must stay sharp. The distance between the two support loops
  sets the apparent bevel radius; the subdivided edge lands roughly halfway. Keep spacing proportional to the desired
  radius, not to the face size; large flat regions without support loops read as soft and blobby (Polycount forum, `(verify)`).
- Segment matching: where two curved pieces join (cylinder into a box), give both the same segment count so loops can run
  through without creating poles on the curved surface (Polycount forum, `(verify)`).
- On flat regions you may terminate loops early, use ngons and triangles; on curved regions stay all-quad.
- Crease weights (`Shift+E`, 0..1, stored per edge) are a quick alternative to support loops but **do not export**:
  "These crease weights typically only work within the original modeling software and are not exportable" (Polycount).
  FBX and glTF carry no Catmull-Clark creases. If a mesh leaves Blender subdivided, apply the modifier first.
- `SubsurfModifier` properties worth setting in code: `levels`, `render_levels`, `use_limit_surface` (default True),
  `uv_smooth='PRESERVE_BOUNDARIES'` (default; right for game UVs), `use_creases` (default True), `quality` (default 3),
  `use_custom_normals` only if you rely on them.
- Bevel + Subsurf shortcut for hard surface: `BevelModifier` (`segments=2`, `limit_method='ANGLE'` with `angle_limit`
  default 0.523599 = 30 deg, or `'WEIGHT'` with per-edge bevel weights) placed **before** Subdivision Surface gives
  support loops automatically. Keep `use_clamp_overlap=True` (default) and width below half the shortest adjacent edge.

### 2b. Real-time hard surface: bevel + weighted normals (FWN) / "mid-poly"
- Face-weighted normals: add a small bevel (1 segment for pure low-poly, 2-3 for mid-poly), then make vertex normals
  perpendicular to the large flat faces so shading gradients fall across the narrow bevel faces only (Polycount FWN).
- Blender stack that does it: Bevel (`harden_normals=True`, `face_strength_mode='FSTR_AFFECTED'`) -> Weighted Normal
  (`mode='FACE_AREA'`, `use_face_influence=True`, `keep_sharp=True`, `weight=50` = uniform). Harden Normals needs a
  `custom_normal` attribute; the modifier creates it (manual). Enum values: `FSTR_NONE/FSTR_NEW/FSTR_AFFECTED/FSTR_ALL`.
- Mid-poly (80.lv, UE5 production): no high-to-low bake, no normal map for edges, "more bevels for most visible parts or
  fewer bevels for really tiny geometry", UVs no longer need a split at every 90 deg edge, so fewer shells and more
  texel density. Trade-off: more triangles and more sliver geometry; it suits static props, not skinned meshes.
- Custom normals must survive export. FBX: `bpy.ops.export_scene.fbx(use_mesh_modifiers=True, mesh_smooth_type='OFF')`
  ("Normals Only"; the exporter itself says to prefer it when the importer understands custom normals). glTF exports
  normals by default. "Some game engines do not import edited vertex normals. Check your engine's documentation" (Polycount).

### 2c. Auto Smooth -> Smooth by Angle (Blender 4.1+, confirmed in the 5.2 manual/API)
- 4.1 removed the mesh "Auto Smooth" property. Meshes now behave as if auto smooth were on at 180 deg: face-corner
  normals are split wherever an edge is marked sharp or a face is flat; custom normals are used when present.
- `Object > Shade Auto Smooth` = `bpy.ops.object.shade_auto_smooth(use_auto_smooth=True, angle=0.523599)` (30 deg).
  It adds the **Smooth By Angle** modifier (a geometry-nodes asset from the bundled Essentials library) and pins it last
  (`Modifier.use_pin_to_last`). Options: `Angle`, `Ignore Sharpness`. Removed again by `shade_smooth` / `shade_flat`.
- Edit Mode equivalent with no modifier: `bpy.ops.mesh.set_sharpness_by_angle(angle=0.523599, extend=False)` writes the
  `sharp_edge` attribute directly. Prefer this for export-ready meshes so no modifier has to be applied.
- `shade_smooth(keep_sharp_edges=True)` keeps sharp marks (`False` clears them). Versus <= 4.0 the old property acted
  after the whole stack; the modifier acts at its stack position (pinned last), so re-pin after appending modifiers in code.

Sources: http://wiki.polycount.com/wiki/Subdivision_Surface_Modeling , http://wiki.polycount.com/wiki/Face_weighted_normals ,
http://wiki.polycount.com/wiki/VertexNormal , https://80.lv/articles/creating-assets-within-the-mid-poly-workflow-in-ue5/ ,
https://developer.blender.org/docs/release_notes/4.1/modeling/ ,
https://blenderartists.org/t/blender-4-1-auto-smooth-is-now-a-modifier-only/1488922 ;
Blender 5.2 manual: scene_layout/object/editing/shading, modeling/modifiers/normals/smooth_by_angle,
modeling/modifiers/normals/weighted_normal, modeling/modifiers/generate/bevel, modeling/modifiers/generate/subdivision_surface;
API: bpy.types.BevelModifier, bpy.types.SubsurfModifier, bpy.ops.export_scene.fbx.

## 3. Boolean workflow cleanup

- Inputs: "Only Manifold meshes are guaranteed to give proper results" (manual). Run the non-manifold check (section 4)
  on both operands first. Solvers (5.2): `EXACT` (default, handles coplanar/overlap, slow), `FLOAT` (fast, fails on
  overlapping faces; `double_threshold` default 1e-6), `MANIFOLD` (fastest, manifold inputs only). `use_self` and
  `use_hole_tolerant` only when Exact shows errors (both cost time).
- Iterate non-destructively: cutters in a Collection operand (`operand_type='COLLECTION'`), `display_type='WIRE'`,
  `hide_render=True`, excluded from export; apply only for delivery.
- What booleans leave behind, and the fix order that works (one Edit Mode session, all selected):
  1. Doubled verts along the seam: `bpy.ops.mesh.remove_doubles(threshold=0.0001)` (1e-4 m default; use 1e-3 for
     metre-scale props).
  2. Zero-area faces / zero-length edges: `bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)`.
  3. Fan triangles on flat cut faces: `bpy.ops.mesh.dissolve_limited(angle_limit=0.0872665)` (5 deg default) collapses
     them into one planar ngon; then re-cut that ngon into quads with Knife / `bpy.ops.mesh.vert_connect_path` if it sits
     on a curved surface or will deform.
  4. Flipped faces from inverted cutters: `bpy.ops.mesh.normals_make_consistent(inside=False)`; `Union` of open
     operands also leaves interior faces, so re-run the section 4 non-manifold and interior-face checks at the end.
  5. Remaining ngons: `bpy.ops.mesh.select_face_by_sides(number=4, type='GREATER')` -> check planarity with Mesh Analysis
     Distortion; `bpy.ops.mesh.face_make_planar()` or triangulate with Beauty.
  6. Slivers where a cutter ran almost parallel to a face: move the cutter >= 1 mm off the face and redo, or dissolve the
     sliver edge; a later Bevel modifier collapses on sliver edges (common field report, `(verify)`).
  7. Shading smears across cut smooth surfaces: Weighted Normal modifier or `set_sharpness_by_angle(30 deg)` after the
     boolean. New-face materials: `material_mode='TRANSFER'` or `'INDEX'`.
- Never ship boolean topology on deforming meshes (retopo over it); for static hard-surface props boolean + cleanup is
  standard (Blender Studio lists Booleans as a core blocking modifier).

Sources: Blender 5.2 manual: modeling/modifiers/generate/booleans, modeling/meshes/editing/mesh/cleanup,
modeling/meshes/editing/mesh/delete; API: bpy.types.BooleanModifier, bpy.ops.mesh (remove_doubles, dissolve_degenerate,
dissolve_limited, normals_make_consistent, select_face_by_sides);
https://studio.blender.org/tools/artist-guide/asset-creation/modeling .

## 4. Common defects: detection and repair in Blender

| Defect | Detect (Edit Mode unless noted) | Fix |
|---|---|---|
| Non-manifold (holes, wire edges, edges with 3+ faces, inconsistent winding) | `mesh.select_non_manifold(extend=False, use_wire, use_boundary, use_multi_face, use_non_contiguous, use_verts)` (vertex/edge mode only) | `mesh.fill_holes(sides=0)` for holes; delete wire edges; `normals_make_consistent`; Roblox and 3D print require watertight |
| Loose verts / edges / faces | `mesh.select_loose(extend=False)` (respects select mode) | `mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)` |
| Duplicate vertices | `remove_doubles` reports count removed; or `bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)` | same |
| Interior faces | `mesh.select_interior_faces()` ("faces where all edges have more than 2 face users") | delete; re-run after Union booleans |
| Flipped normals | Overlay > Face Orientation (blue out / red in); Object Mode negative `obj.scale` is the usual cause | `normals_make_consistent(inside=False)`; `object.transform_apply(..., corrective_flip_normals=True)` |
| Zero-area / degenerate faces, zero-length edges | `dissolve_degenerate` count; 3D-Print Toolbox "Degenerate" | `mesh.dissolve_degenerate(threshold=1e-4)` |
| Non-planar / concave ngons | Mesh Analysis overlay `Distortion` (Solid shading, Edit Mode); `select_face_by_sides(4, 'GREATER')` | `face_make_planar`, split non-planar faces, or triangulate |
| Poles on curved/deforming areas | `select_by_pole_count(4, 'NOTEQUAL')` | move to flat areas, redirect loops |
| Unapplied scale/rotation | Object Mode: `obj.scale != (1,1,1)`, `obj.rotation_euler != (0,0,0)`; non-uniform scale breaks Solidify/Bevel thickness (manual) | `bpy.ops.object.transform_apply(location=False, rotation=True, scale=True, isolate_users=True)` for multi-user data |
| Off-origin / wrong pivot | compare `obj.location` and bbox min z with section 6 rules | `bpy.ops.object.origin_set(type='ORIGIN_CURSOR')` after placing cursor at bbox bottom centre; `ORIGIN_GEOMETRY` with `center='BOUNDS'` |
| Self-intersections | Mesh Analysis `Intersections` (binary); 3D-Print Toolbox "Intersections" | reposition parts, boolean Union, or accept for render-only |
| Thin walls / sharp slivers (print, Nanite, shadows) | Mesh Analysis `Thickness` (ray cast, min/max, samples) and `Sharp Edges` | thicken with Solidify, dissolve slivers |
| Corrupt indices after bmesh/foreach_set builds | `mesh.validate(verbose=True)` returns `True` when it had to fix something (invalid loops/edges, bad indices); `mesh.validate_material_indices()` | rebuild; always call `validate()` after procedural construction, it is not a topology linter |

Notes:
- Mesh Analysis overlay (`MeshStatVis`): Overhang, Thickness, Intersections, Distortion, Sharp Edges; red high / blue low /
  grey out of range. Edit Mode + Solid shading only, "currently only displayed with Deform Modifiers", slow on high-poly.
- 3D-Print Toolbox is **no longer bundled**: since 4.2 it is an Extension (v1.4.1, "Blender 4.2 LTS and newer") from
  extensions.blender.org. Guard scripts with `hasattr(bpy.ops.mesh, "print3d_check_all")` and fall back to the native
  operators above. Its operators (`print3d_check_solid/_intersect/_degenerate/_distort/_thick/_sharp`, `print3d_check_all`,
  `print3d_clean_non_manifold`) and thresholds (thickness 1 mm, distort 45, sharp 160, overhang 45 deg) are from memory `(verify)`.
- Automated gate (run before every export): `mesh.validate(verbose=True)` is False; `select_non_manifold`,
  `select_loose`, `select_interior_faces`, `select_face_by_sides(4,'GREATER')` on curved/deforming areas and
  `select_by_pole_count(4,'NOTEQUAL')` on deforming areas all select 0; a second `remove_doubles(1e-4)` and
  `dissolve_degenerate(1e-4)` remove 0; `normals_make_consistent` changes nothing; then sections 5-7 budgets and naming.
  Blender Studio's delivery list adds: clean UVs after topology changes, delete unused attributes, apply static modifiers.

Sources: Blender 5.2 manual: modeling/meshes/selecting/all_by_trait, modeling/meshes/mesh_analysis,
modeling/meshes/editing/mesh/cleanup, modeling/modifiers/generate/solidify; API: bpy.types.Mesh.validate,
bpy.ops.mesh.*, bpy.ops.object.transform_apply, bpy.ops.object.origin_set;
https://extensions.blender.org/add-ons/print3d-toolbox/ , https://projects.blender.org/blender/blender-manual/issues/104925 ,
https://studio.blender.org/tools/artist-guide/asset-creation/modeling .

## 5. Polycount budgets

Hard limits and official per-frame budgets (primary sources):

| Target | Limit / budget | Source |
|---|---|---|
| Roblox, any MeshPart | <= 20,000 triangles per mesh; solid-modeling results clamped to 20,000; watertight, quads, no zero-thickness | create.roblox.com general specs |
| Roblox avatar body (15 parts) | 10,742 tris total: head 4,000; torso 1,750; each arm 1,248; each leg 1,248 | character body specs |
| Roblox accessories (rigid or layered) | <= 4,000 tris; one mesh; textures <= 2048 | accessory specs |
| Roblox in-experience textures | 512x512 for most, 256 for minor images | performance docs |
| Meta Quest 2 | < 750k tris/frame, < 100 draw calls, 13.8 ms at 72 Hz | Meta device comparison |
| Meta Quest 3 | < 1.5M tris/frame, < 200 draw calls | Meta device comparison |
| Web / mobile AR catalogue (Khronos 3DC) | 150k tris, 3 MB, < 20 draw calls, 2K textures | 3DC Publishing Targets |
| Web banner ad | 30k tris, 500 KB, < 5 draw calls, 512 textures | 3DC Publishing Targets |
| Web planning tool | 40k tris, 1 MB, < 5 draw calls, 1K textures | 3DC Publishing Targets |
| Desktop 3D web viewer (three.js class) | 250k tris, 3 MB, < 100 draw calls, 2K textures; generic guidance <= 100k tris, < 5 MB | 3DC / Khronos blog |
| Unreal mobile | 65,535 vertices per mesh (16-bit index buffer) | UE 4.27 content standards |
| Unreal/Fortnite | any static mesh >= 500 verts must have LODs | Fortnite LOD best practices |
| Unity characters (legacy manual, 2017-era) | 300-1,500 polys/mesh mobile; 1,500-4,000 desktop; <= 30 bones mobile; 2-3 materials | Unity manual 5.5 |

Working budgets per asset class (synthesis of the above plus industry guides; CGAxis 2026 cites no sources, treat its
ranges as `(verify)`), in **triangles** for the LOD0 mesh:

| Asset class | Mobile / Roblox | PC / console | Web (three.js) | VR standalone | Offline render |
|---|---|---|---|---|---|
| Small prop (mug, tool) | 100-500 (Roblox 2-4k if unique) | 500-3,000 | 500-3,000 | 300-1,500 | 5k-50k (subdiv) |
| Large prop (furniture, crate, machine) | 500-2,000 | 2,000-10,000 | 2,000-10,000 | 1,000-5,000 | 10k-100k |
| Character (NPC / player) | 1,500-5,000 (Roblox body <= 10,742) | 15,000-50,000 | 10,000-40,000 | 5,000-20,000 | 100k-1M+ |
| Vehicle | 2,000-8,000 | 20,000-100,000 (racing hero up to 150k) | 20,000-60,000 | 10,000-40,000 | 300k-1.2M |
| Building / modular kit piece | 200-2,000 per module | 1,000-10,000 per module | 1,000-10,000 | 500-5,000 | 10k-200k+ |
| Hero asset (first-person weapon, showcase) | 3,000-10,000 | 50,000-150,000 | 50,000-100,000 (<= 150k cap) | 20,000-60,000 | unbounded |

Rules of thumb: instanced props cost count x instances, keep them at the low end; draw calls and vertex splits matter more
than triangles on mobile/VR; cylinder sides 8 (< 10 px), 16 (prop), 24-32 (hero close-up), 48+ render only (`(verify)`).

Sources: https://create.roblox.com/docs/art/modeling/specifications , https://create.roblox.com/docs/avatar/character-bodies/specifications ,
https://create.roblox.com/docs/art/accessories/specifications , https://create.roblox.com/docs/performance-optimization/improve ,
https://developers.meta.com/vr/resources/device-optimization-comparison/ ,
https://github.com/mlimper/3DC-Asset-Creation/blob/main/asset-creation-guidelines/full-version/sec99_PublishingTargets/PublishingTargets.md ,
https://www.khronos.org/blog/3d-commerce-working-group-releases-real-time-asset-creation-guidelines-to-assist-artists-create-efficient-reliable-models-for-retail-and-e-commerce ,
https://dev.epicgames.com/documentation/en-us/unreal-engine/external-content-development-standards?application_version=4.27 ,
https://dev.epicgames.com/documentation/fortnite/level-of-detail-lod-best-practices-in-fortnite ,
https://docs.unity3d.com/550/Documentation/Manual/ModelingOptimizedCharacters.html , http://wiki.polycount.com/wiki/Polygon_Count ,
https://cgaxis.com/polygon-count-guide-how-many-polys-do-you-really-need-in-2026/ (vendor, uncited).

## 6. Scale, orientation, pivot and transform conventions

- Model at real-world scale with Blender's default Metric, `unit_scale = 1.0`, 1 BU = 1 m. Door 2.0-2.1 m, chair seat
  0.45 m, human 1.75 m. glTF stores metres, +Y up, right-handed; Blender's glTF exporter converts from Z-up.
- Unreal: 1 Unreal Unit = 1 cm; forward = +X; static-mesh pivot "typically the center bottom", skeletal pivot "between
  the feet". Export FBX with `apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL'` (enum confirmed in the 5.2 API;
  default is `'FBX_SCALE_NONE'`), or set scene unit scale 0.01 and model in cm. The wrong combination imports at the
  right size but with (100,100,100) on the root, which breaks collision, sockets and physics (community reports, `(verify)`).
- Unity: 1 unit = 1 m; FBX import `Scale Factor` 0.01 for .fbx (file in cm), 1.0 for .blend. Model correctly scaled
  rather than fixing it in the importer ("important ... for correct physical behaviour").
- Roblox: 1 stud ~= 0.28 m (staff statement relayed on DevForum; `(verify)` against current docs). Avatar bodies must
  "face positive Z and stand up in positive Y" with all transforms frozen and pivots at 0,0,0; general specs require
  scale 1,1,1 and rotation 0,0,0 on export. Normal-scale body envelope: width 1.35-8.6 studs, height 3.6-9.5, depth 0.7-2.25.
- Pivot rules by asset type (industry convention, consistent with Epic's standard):
  props and furniture: bottom centre (sits on the floor when dropped at z=0); characters: between the feet at ground;
  wall/floor modules: bottom back-left corner or bottom centre on a fixed grid (1, 2, 4 m; UE commonly 100/200/400 cm);
  doors: hinge axis; wheels, turrets, levers: axis of rotation; attachments/weapons: grip or socket point;
  symmetric objects: centred on X=0 so Mirror modifiers and engine mirroring work.
- Code pattern: compute world bbox (`obj.bound_box` x `obj.matrix_world`), set `scene.cursor.location` to
  (cx, cy, min_z), `origin_set(type='ORIGIN_CURSOR')`, then `transform_apply(rotation=True, scale=True)` and finally
  `obj.location = (0,0,0)` before export.
- Apply before export: scale and rotation always; location only if the engine will place the asset. Apply or disable
  Mirror/Array/Boolean/Bevel/Solidify that define the final shape (Blender Studio: "apply most modifiers that should be
  static in final model"). Keep Smooth by Angle or bake it with `set_sharpness_by_angle`.
- Negative scale = inverted normals in most engines; `transform_apply(corrective_flip_normals=True)` repairs it.

Sources: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.pdf ,
https://dev.epicgames.com/documentation/en-us/unreal-engine/units-of-measurement-in-unreal-engine ,
https://dev.epicgames.com/documentation/en-us/unreal-engine/external-content-development-standards?application_version=4.27 ,
https://docs.unity3d.com/Manual/FBXImporter-Model.html , https://docs.unity3d.com/6000.0/Documentation/Manual/models-preparing.html ,
https://create.roblox.com/docs/avatar/character-bodies/specifications , https://create.roblox.com/docs/art/modeling/specifications ,
https://devforum.roblox.com/t/how-to-convert-studs-to-real-world-units/1863780 ,
https://studio.blender.org/tools/artist-guide/asset-creation/modeling ; API: bpy.ops.export_scene.fbx, bpy.ops.object.origin_set, transform_apply.

## 7. LOD generation and collision meshes

LOD rules:
- Fortnite/UE standard: 3 LODs for props; LOD1 = 50 % triangles, LOD2 = 25 %; LODs mandatory from 500 vertices.
  Screen-size switch points: architecture 1.0 / 0.4 / 0.1 / 0.03; props 1.0 / 0.2 / 0.08 / 0.02.
- UE auto-LOD groups (BaseEngine.ini): LevelArchitecture, SmallProp, LargeProp, Deco = 4 LODs at 50 % each step;
  HighDetail = 6 LODs; Vista and Foliage = 1 LOD. Default pattern therefore 100 / 50 / 25 / 12.5 %.
- Simplygon: fixed ratios fail on already-low meshes (a 12-tri crate at 30 % becomes 4 tris); under ~500 tris skip LODs or
  hand-build LOD1; automated chains should use screen-size/deviation targets (first switch ~1000 px height, 500-750 if dense).
- Unity LOD Group switches on % of screen height; defaults for a 3-level group roughly 60 / 30 / 10 % then culled `(verify)`.
- Count by asset class (synthesis): small prop 2 (LOD0 + LOD1) or none under 500 tris; large prop 3; building module 3-4;
  vehicle 3-4; character 3-4 (LOD3 often shares one material); hero first-person item 1-2; foliage/vista 1 + impostor.
- Blender code: duplicate the LOD0 object, add Decimate (`decimate_type='COLLAPSE'`, `ratio=0.5/0.25/0.125`,
  `use_symmetry=True, symmetry_axis='X'` for symmetric assets, `use_collapse_triangulate=True`), apply, then
  `remove_doubles`, `normals_make_consistent`, re-run `set_sharpness_by_angle`. For hard surface prefer
  `decimate_type='DISSOLVE'` (Planar, `angle_limit` 5 deg default) for LOD1 and Collapse for LOD2+. Name `Asset_LOD0 ..
  Asset_LODn`. UE's FBX LOD import expects a DCC "LOD Group" node, which Blender's exporter does not write `(verify)`;
  import LODs separately in UE ("Import LODs" option) or let UE/Unity generate them. Keep UV seams and silhouette edges
  out of the collapse by weighting a vertex group. LODs never change pivot, scale or material slot order.

Collision conventions:
- Unreal FBX: name collision meshes `UBX_<RenderMesh>` (box, undeformed), `UCP_<RenderMesh>` (capsule), `USP_<RenderMesh>`
  (sphere, "8 is a good number" of segments), `UCX_<RenderMesh>_00..` (convex, "completely closed"); hulls should not
  intersect each other. Export in the same FBX as the render mesh.
- Unity: convex MeshCollider <= 255 triangles; non-convex mesh colliders cannot collide with each other; primitives
  preferred for dynamic objects.
- Roblox: `CollisionFidelity` Box or Hull for small / non-interactive parts, Default for mid complexity,
  PreciseConvexDecomposition only when gameplay needs it (highest cost); large complex meshes get invisible primitive
  parts as custom collision. Box/Hull also save memory even when `CanCollide=false`.
- Web/three.js has no convention: ship a separate `<Name>_COL` convex/box mesh for Rapier/Ammo/cannon-es. Rule of thumb for
  all targets: collision <= 10 % of LOD0 tris, each convex piece <= 32-64 tris, <= 8-16 pieces per prop (`(verify)`).

Sources: https://dev.epicgames.com/documentation/fortnite/level-of-detail-lod-best-practices-in-fortnite ,
https://dev.epicgames.com/documentation/unreal-engine/static-mesh-automatic-lod-generation-in-unreal-engine ,
https://dev.epicgames.com/documentation/unreal-engine/importing-static-mesh-lods-using-fbx-in-unreal-engine ,
https://simplygon.com/posts/b83478b7-a2a1-46a9-a0e1-cba3da7da307 , https://docs.unity3d.com/Manual/class-LODGroup.html ,
https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine ,
https://docs.unity3d.com/6000.3/Documentation/Manual/class-MeshCollider.html ,
https://create.roblox.com/docs/reference/engine/enums/CollisionFidelity , https://create.roblox.com/docs/performance-optimization/improve ;
API: bpy.types.DecimateModifier.

## 8. What code-driven modeling can and cannot do

Realistic with bpy/bmesh + modifiers (clean quads, predictable results):
- Primitives, lathe/revolve (Screw modifier or bmesh spin), extrude/inset/bevel chains, profile sweeps along curves
  (Curve + Array), lattices and Simple Deform for bends/tapers, Mirror/Array for symmetry and repetition, Solidify for
  shells, Boolean for cut-outs on hard surfaces, Bevel + Weighted Normal for real-time shading, Decimate for LODs,
  Geometry Nodes for scattering, modular kit instancing, fences, pipes, procedural buildings and parametric variants.
- Asset classes that reach professional quality this way: furniture, containers, machines and sci-fi panels, weapons
  and vehicles at blockout-to-mid-poly level, architecture and modular kits, stylized low-poly props and environments,
  text and signage (Text -> mesh + Limited Dissolve or Remesh, per the manual), terrain from displacement.
- Quality gates that are easy to automate: all of section 4, polycount vs section 5, pivot/scale vs section 6.

Not realistic without manual sculpting/retopo (be explicit in the skill):
- Organic characters and creatures with animation-grade edge flow: face loops around eyes/mouth, shoulder/hip flow,
  hands. Blender Studio's own pipeline is sculpt first, then retopology into "relatively evenly distributed quads";
  no modifier or node produces deformation-aware loops. Voxel/Quadriflow Remesh gives even quads but random flow and
  poles in the wrong places; Skin + Subsurf gives a base mesh only.
- Cloth folds, wrinkles, fur/hair cards, pose-specific detail: cloth simulation gives a draped shape at simulation
  resolution, not production retopo; folds need sculpt passes. Micro detail (pores, weave, wear) belongs in textures.
- Boolean-heavy hard surface still needs the section 3 cleanup and often a manual re-cut of ngons on curved areas, and
  bevels pinch where three or more bevelled edges meet (Miter/Intersection options help, not cure). Expect code to hit
  budgets, defect checks, silhouettes and proportions from reference measurements reliably; expect a human pass for
  appeal, asymmetry and storytelling wear.

Sources: https://studio.blender.org/tools/artist-guide/asset-creation/modeling , http://wiki.polycount.com/wiki/Topology ;
Blender 5.2 manual: modeling/modifiers (generate: bevel, booleans, decimate, solidify, subdivision_surface),
modeling/texts/editing (convert to mesh), modeling/geometry_nodes.

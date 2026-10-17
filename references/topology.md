# Topology and modeling rules

Distilled from `research/topology-and-modeling.md` (sources there). Operators confirmed on Blender 5.2.

## What clean geometry means here

1. **Quad-dominant, every edge with a reason.** Regular vertices have 4 edges; a 3-edge (N) or 5-edge
   (E) pole is fine on flat, non-deforming areas and wrong on curved or bending ones (pinching under
   subdivision, shading artefacts). Loops where there is curvature, not on straight runs.
2. **Triangles** are acceptable in final game meshes on flat or hidden areas and to end loops on hard
   surfaces. Not in deforming regions, not on curved surfaces that get subdivided.
3. **N-gons** only when planar, non-deforming and never subdivided (the top of a flat panel). On a curved
   surface their triangulation is undefined and every exporter will cut them differently. Roblox rejects
   them outright. `mesh_audit` flags them (`GEO_NGONS`) for every class but placeholder/cinematic.
4. **Vertex splits cost, not triangles.** Each UV seam, sharp edge and material change duplicates the
   vertices on it. Put seams on sharp edges so one split pays for both.
5. **Control your own triangulation** before baking or exporting (a quad can fold as a ridge or a valley):
   Triangulate modifier, `quad_method='BEAUTY'` for organic, `'FIXED'` for hard surface, or
   `mesh.quads_convert_to_tris` in a copy. Keep quads in the source file.
6. **Shading is data, not a property.** Since 4.1 there is no Auto Smooth. For export-ready meshes write
   sharp edges directly: Edit mode, all selected, `bpy.ops.mesh.set_sharpness_by_angle(angle=0.523599)`
   (30°), then `bpy.ops.object.shade_smooth(keep_sharp_edges=True)`. `object.shade_auto_smooth` adds
   the Smooth By Angle modifier instead (pinned last; fine while iterating, one more thing to apply).

## Hard surface for real time: bevel + weighted normals

The look of a professional hard-surface asset comes from edges that catch light. Stack, in this order:

```python
bev = obj.modifiers.new("Bevel", "BEVEL")
bev.width = 0.004          # metres; 0.3–1% of the asset's largest dimension, same on every part
bev.segments = 2           # 1 for strict low-poly, 2–3 for mid-poly
bev.limit_method = "ANGLE"; bev.angle_limit = 0.523599
bev.harden_normals = True; bev.face_strength_mode = "FSTR_AFFECTED"
wn = obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
wn.mode = "FACE_AREA"; wn.use_face_influence = True; wn.keep_sharp = True
```

Consistent bevel width across all parts of an asset is what makes it read as one object; mixed widths
read as kitbash. Bevels create sliver triangles; keep `width` below half the shortest adjacent edge and
`use_clamp_overlap=True`. Export FBX with `mesh_smooth_type='OFF'` so custom normals ship; glTF carries
them by default.

For subdivision (render) assets: Bevel (`segments=2`, angle limit) **before** Subdivision Surface gives
support loops automatically; crease weights do not export, so apply Subsurf before delivery.

## Boolean cleanup, in this order (Edit mode, all selected)

1. `mesh.remove_doubles(threshold=0.0001)` (1e-3 for metre-scale props)
2. `mesh.dissolve_degenerate(threshold=0.0001)`
3. `mesh.dissolve_limited(angle_limit=0.0872665)` (5°) to collapse fan triangles on flat cuts
4. Re-cut any n-gon that lands on a curved surface (`vert_connect_path`) or triangulate it
5. `mesh.normals_make_consistent(inside=False)`; re-check interior faces after a Union of open meshes
6. `mesh.select_face_by_sides(number=4, type='GREATER')` must select nothing on curved areas
7. Shading: `set_sharpness_by_angle` or the Weighted Normal modifier

Keep cutters in a collection operand (`operand_type='COLLECTION'`, wire display, `hide_render`) until
delivery, solver `EXACT`; `use_self` / `use_hole_tolerant` only when Exact misbehaves. Never ship boolean
topology on a deforming mesh.

## Defects and their fix

| Defect (audit code) | Fix |
|---|---|
| Edges with 3+ faces, wire edges (`GEO_NONMANIFOLD`, `GEO_WIRE_EDGES`) | `select_non_manifold` → delete wire edges, `fill_holes(sides=0)`, remove interior faces |
| Loose vertices (`GEO_LOOSE_VERTS`) | `mesh.delete_loose()` |
| Duplicate vertices (`GEO_DUPLICATE_VERTS`) | `remove_doubles` |
| Inconsistent winding, inward normals (`GEO_FLIPPED_FACES`, `GEO_NORMALS_INWARD`) | `normals_make_consistent(inside=False)`; negative object scale is the usual cause: `transform_apply(scale=True)` with `corrective_flip_normals=True` |
| Zero-area faces, zero-length edges (`GEO_ZERO_AREA`, `GEO_ZERO_LENGTH`) | `dissolve_degenerate` |
| N-gons (`GEO_NGONS`) | re-cut into quads or triangulate; planar-only exceptions noted in decisions.md |
| 6+-edge poles (`GEO_POLES`) | move to flat areas, redirect loops; cylinder caps: use an n-gon cap or a grid cap |
| Rotation/scale not applied (`XFORM_*`) | `bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)` |
| Pivot off (`PIVOT_*`) | move vertices so the bbox bottom-centre sits at the object origin, then `obj.location = (0,0,0)` |
| `mesh.validate(verbose=True)` returned True | the mesh had corrupt indices; rebuild it (validate repairs, it is not a linter) |

The 3D-Print Toolbox is an extension, not bundled, since 4.2: `mesh_audit.py` uses bmesh and does not
depend on it.

## Scale, orientation, pivot

- Model at real-world size, metres, scene unit scale 1.0. Door 2.0–2.1 m, chair seat 0.45 m, adult
  1.75 m, crate 0.6–1.2 m.
- Pivot by type: props and furniture at bottom-centre (drops onto the floor at z=0); characters between the
  feet; wall and floor modules at a bottom corner or bottom-centre on the grid the brief sets (1/2/4 m);
  doors on the hinge axis; wheels, turrets, levers on their rotation axis; attachments at the grip or
  socket. Symmetric objects centred on X=0 so mirroring works.
- Forward: -Y in Blender (face the default front view). Exporters handle the rest (see
  `references/export-targets.md`).
- Apply rotation and scale always; location becomes zero at delivery. Apply the modifiers that define the
  final shape (Mirror, Array, Boolean, Bevel, Solidify); keep the build script as the editable source.

## LODs and collision

- LOD chain from 500 vertices up: LOD1 = 50% of LOD0 triangles, LOD2 = 25%, LOD3 = 12.5% (Epic defaults).
  Small props: LOD0 + LOD1 or none below 500 tris. Decimate `COLLAPSE` with `use_symmetry` for symmetric
  assets, `DISSOLVE` (planar) for the first hard-surface LOD; then `remove_doubles`,
  `normals_make_consistent`, `set_sharpness_by_angle`. Names `SM_Asset_LOD0…LODn`; same pivot, scale and
  material order on every level.
- Collision: Unreal reads `UCX_<Mesh>_00` (convex, closed), `UBX_` (box), `USP_` (sphere), `UCP_`
  (capsule) in the same FBX; Unity convex mesh colliders ≤ 255 tris; Roblox `CollisionFidelity` Box or
  Hull for small props; web engines take a separate `<Name>_COL` mesh. Rule of thumb: collision ≤ 10% of
  LOD0 triangles, each hull ≤ 64 tris, ≤ 16 hulls per prop.

## What code can and cannot do (say it in the brief)

Reliable through bpy, bmesh, modifiers and geometry nodes: furniture, containers, machines, sci-fi
panels and kitbash, weapons and vehicles to mid-poly, architecture and modular kits, stylized low-poly
props and environments, signage, terrain, LOD chains, and every gate in this file.

Not reliable without a human sculpt and retopo pass: animation-grade organic edge flow (faces,
shoulders, hands), cloth folds, hair, pose-specific detail. Remesh gives even quads with the wrong flow.
For those, the brief offers a base mesh plus a human pass, or a stylized/low-poly interpretation that
code can do well, and says so before work starts.

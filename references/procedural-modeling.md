# Procedural modeling in Blender 5.2 with bpy and bmesh

Distilled from `research/procedural-modeling-bpy.md`, where every snippet ran headless on 5.2.2 and
has its measured result; the test scripts are in `research/_tests/procedural/`. This is how the
modeler builds: a parametric build script, not clicks.

## The build script contract

`assets/<Asset>/scripts/build.py` is idempotent and parametric:

```python
# build.py - SM_Crate_A  (all sizes in metres)
PARAMS = dict(width=0.9, depth=0.9, height=0.9, plank=0.12, bevel=0.006, bevel_segments=2, bolts=True)

import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, "<plugin root>/scripts/blender"); from _load import load_module
kit = load_module("<plugin root>/scripts/blender", "material_kit")

def clear_asset(prefix="SM_Crate_A"):
    for ob in [o for o in bpy.data.objects if o.name.startswith(prefix)]:
        me = ob.data; bpy.data.objects.remove(ob, do_unlink=True)
        if me and me.users == 0: bpy.data.meshes.remove(me)

def build(p):
    clear_asset()
    coll = bpy.data.collections.get("Crate_A_Model") or bpy.context.scene.collection
    bm = bmesh.new()
    ... bmesh.ops here ...
    me = bpy.data.meshes.new("SM_Crate_A"); bm.to_mesh(me); bm.free(); me.update()
    me.validate(verbose=True); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(30))
    ob = bpy.data.objects.new("SM_Crate_A", me); coll.objects.link(ob)
    return [ob]

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    objs = build(PARAMS)
    if "--save" in argv:
        path = argv[argv.index("--save") + 1]; os.makedirs(os.path.dirname(path), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=path)
    print("BUILD_OK", [o.name for o in objs])
```

Run it with `scripts/blender_run.sh build.py [existing.blend] -- --save <source.blend>` (or through the
MCP in live mode). A review note becomes a `PARAMS` change or a new operation; nothing is done by hand.

## Building blocks (bmesh.ops, measured on 5.2)

- Primitives: `create_cube(size=1.0)` is 1 m; `create_grid(size=1.0)` is a **half**-extent (2 m);
  `create_cone(segments, radius1, radius2, depth, cap_ends=True)` is a cylinder when the radii match
  (`cap_tris=True` avoids the n-gon caps); `create_uvsphere`, `create_icosphere`, `create_circle`. Pass
  `matrix=Matrix.Translation(...) @ Matrix.Diagonal((sx, sy, sz, 1))` to place and scale at creation.
- `inset_region(faces, thickness, depth, use_even_offset=True)` returns the rim faces; the input faces
  stay as the inner panel. `inset_individual(faces, thickness=0, depth=-d)` is a straight recess.
- `extrude_face_region(geom=[f] + list(f.edges) + list(f.verts))`: pass all three element types, or
  the original face stays and the mesh is non-manifold. Then `translate` the returned verts.
- `bevel(geom=edges, offset, segments=N, profile=0.5, affect='EDGES', clamp_overlap=True)`: **always
  pass `affect='EDGES'` and `segments`**; the defaults bevel vertices with one segment.
- `bisect_plane(..., clear_outer=True)` + `contextual_create(geom=cut_edges)` cuts and caps with one
  n-gon; `spin` and `create_cone` caps are n-gons too. The audit flags n-gons for every class but
  placeholder/cinematic, so cap flat areas with a grid (`inset_region` + `subdivide_edges` with
  `use_grid_fill`) or `triangulate(faces=[cap])` before the audit; for domes prefer a quad-capped
  profile (`create_uvsphere` half, or a lathe whose profile ends slightly off-axis then `remove_doubles`)
  over fan caps that show as spokes in the wireframe.
- `spin(geom, cent, axis, angle=math.tau, steps=32, use_merge=True)` for lathes (bottles, wheels,
  vases); then `remove_doubles(dist=1e-5)` and **`recalc_face_normals`** (spin produces inward faces).
- `bridge_loops(edges)` between two rings; `symmetrize(direction='X')` keeps +X (delete the on-plane
  cap face first or you get non-manifold edges); `mirror(axis='X', merge_dist=1e-4)` is equivalent.
- `scale(vec, verts, space=Matrix.Translation(-pivot))` scales about a pivot (exaggerated proportions).
- Cleanup trio: `remove_doubles(dist=1e-4)` → `dissolve_limit(angle_limit=radians(1))` →
  `recalc_face_normals`. `triangulate(quad_method='BEAUTY')` only for export copies.
- Call `bm.verts.ensure_lookup_table()` (and faces/edges) again after any `new()` or delete before
  indexing.

## Modifier recipes (order top to bottom)

Mirror → Array → (Boolean) → Bevel (`limit_method='ANGLE'`, `harden_normals=True`,
`use_clamp_overlap=True`) → Weighted Normal (`keep_sharp=True`, `mode='FACE_AREA'`) → Subdivision (render
assets) → Smooth by Angle last. Apply the stack into a mesh without operators:

```python
dg = bpy.context.evaluated_depsgraph_get()
me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
```

| Recipe | Settings | Measured |
|---|---|---|
| Holding edges for subdivision | Bevel width 0.02, segments 2, then Subsurf levels 2, `shade_smooth()` | 0.5 m cube → 864 faces, clean |
| Shell | Solidify thickness 0.02, offset −1, even offset, rim | grid → 240 faces, manifold |
| Lathe (vase) | Screw angle τ, steps 32, axis Z, merge vertices, normal calculate | 192 faces, manifold |
| Thread | 3-vertex V profile, Screw `screw_offset` = pitch, iterations 10, steps 16 | open strip; close the profile for a solid |
| Pipe along a curve | cylinder segment along +X; Array `fit_type='FIT_CURVE'` + merge; Curve modifier `deform_axis='POS_X'` | 228 faces along 1.6 m |
| Taper | Simple Deform `TAPER`, factor −0.6, axis Z on a cube with 4 cuts | top 1.0 → 0.4 |
| Surface noise | Displace with a `CLOUDS` texture, strength 0.08, local coords | |
| Planar cleanup | Decimate `DISSOLVE`, angle 5° | 12 tris → 6 quads |
| Export triangles | Triangulate `BEAUTY`, `min_vertices=4` | quads → tris |

Booleans: `solver='EXACT'` by default; `use_self=True` when cutters overlap each other;
`'MANIFOLD'` (fastest) only with watertight cutters, it silently no-ops otherwise; `'FLOAT'` for speed
when nothing is coplanar. Cutters cut even when hidden or unlinked. Collection operand for many cutters.
Clean up after applying as in `references/topology.md`.

Curves for cables, pipes, ropes: `bpy.data.curves.new(name, 'CURVE')`, bezier points with `AUTO`
handles, `bevel_mode='ROUND'`, `bevel_depth`, `bevel_resolution=4`, `use_fill_caps=True`; convert
through the depsgraph; caps arrive as detached fans, so `remove_doubles(1e-5)` and `recalc_face_normals`.

## Geometry nodes from Python (5.2)

```python
ng = bpy.data.node_groups.new("GN_BoltRow", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
cnt = ng.interface.new_socket("Count", in_out="INPUT", socket_type="NodeSocketInt"); cnt.default_value = 6
# ... Mesh Line (OFFSET) -> Instance on Points (hex cylinder) -> Realize Instances -> Set Material -> Join with input
mod = ob.modifiers.new("Bolts", "NODES"); mod.node_group = ng
ident = next(i.identifier for i in ng.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT" and i.name == "Count")
getattr(mod.properties.inputs, ident).value = 8          # 5.2: mod["Socket_2"] raises TypeError
```

Always pass a concrete `socket_type` (`NodeSocketFloat`, `NodeSocketInt`, `NodeSocketMaterial`...).
**Realize Instances** before the output or the evaluated mesh drops every instance. Scattering:
Distribute Points on Faces (`POISSON`, distance min) → Instance on Points with its Rotation output →
Realize → Join.

## Kitbash and greebles (reads as professional when sizes are derived)

Derive detail sizes from the asset's longest dimension `L`: chamfer 0.5% of L, panel border 2%,
recess depth 0.4%, bolt radius 0.6%; one bevel width per asset; 1 segment for flat-shaded, 2–3 with
hardened normals for smooth. Panel lines = `inset_individual` on the large faces then a second inset
with `depth=-recess`; bolts = `create_cone(segments=6)` oriented with
`f.normal.to_track_quat('Z', 'Y')` at corners, as a separate `SM_<Asset>_Bolts` object or linked
duplicates (`bpy.data.objects.new(name, proto.data)` costs no geometry); slots = one cutter mesh of
boxes, EXACT boolean. Keep rest areas: not every face gets a panel.

## Organic-ish shapes and stylized shortcuts

- Rocks, boulders: icosphere subdivisions 3–4, layered `mathutils.noise.noise` along normals, scale
  non-uniformly, `smooth_vert` twice; faceted version: Decimate `COLLAPSE` ratio 0.1 + `shade_flat()`.
- Trunks and limbs: edge skeleton + Skin modifier (per-vertex radii, `use_root`) + Subsurf 2.
- Blobs: metaballs converted through the depsgraph, then `dissolve_limit`.
- Bends and leans: lattice (`points_u/v/w`, `co_deform`) or Simple Deform.
- Chunky toy look: bevel offset at 15% of the block size, 1 segment; rounded: 4 segments + smooth.
- Exaggeration: scale a vertex group about a pivot.

Honest limit: these give blobs, rocks, trunks and blockouts. Faces, hands, folds and hair need a sculpt;
the brief says so before modeling starts (`references/topology.md`).

## Material slots

`mesh.materials.clear()` resets every face's `material_index` to 0. Record the per-face indices (or the
face sets per surface) before clearing and reassign them after appending the slots, or assign slots
once and never clear. The baked material replaces all slots on purpose (one texture, one slot).

## Hygiene inside the script (order that worked)

Build in metres at identity → apply transforms (`me.transform(ob.matrix_world); ob.matrix_world =
Matrix.Identity(4)`) → origin to bottom-centre (translate vertices by `-(cx, cy, zmin)`, keep the
world position by moving `matrix_world` the other way) → place with `location` only → name
`SM_<Asset>_<Part>` in collection `<Asset>_Model` → `scene.unit_settings` metric, scale 1.0 → run
`mesh_audit` → `render_review`. Child parts: `lid.parent = body; lid.matrix_parent_inverse =
body.matrix_world.inverted()`.

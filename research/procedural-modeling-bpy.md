# Procedural & parametric modeling in Blender 5.2.2 LTS with `bpy` / `bmesh`

Research notes for the "3D modeling team" skill. Every snippet below ran in `Blender -b --python` on
5.2.2 LTS (macOS, 2026-09-15 build). The **measured** line after each snippet is copied from the
test log (`RESULT|label|verts|faces|tris|ngons|dims|nonmanifold|loose|flipped`). Test scripts and logs:
`research/_tests/procedural/t01…t10_*.py`, renders in `research/_tests/procedural/_out/r_*.png`.
Anything not run is marked `(verify)`.

**Contents**
1. [5.2 API surprises (read first)](#1-52-api-surprises)
2. [Boilerplate + self-check helper](#2-boilerplate--self-check-helper)
3. [Building blocks with `bmesh.ops`](#3-building-blocks-with-bmeshops)
4. [Spin (lathe), bridge, symmetrize](#4-spin-lathe-bridge-symmetrize)
5. [Booleans](#5-booleans)
6. [Modifier recipes and applying the stack in `-b`](#6-modifier-recipes-and-applying-the-stack)
7. [Curves: cables, pipes, ropes](#7-curves-cables-pipes-ropes)
8. [Geometry Nodes from Python](#8-geometry-nodes-from-python)
9. [Kitbash and greebling](#9-kitbash-and-greebling)
10. [Organic-ish shapes by code](#10-organic-ish-shapes-by-code)
11. [Stylized shortcuts](#11-stylized-shortcuts)
12. [Scale / pivot / naming hygiene](#12-scale--pivot--naming-hygiene)
13. [Self-check helpers](#13-self-check-helpers)
14. [Sources](#14-sources)

---

## 1. 5.2 API surprises

| Area | 5.2 behaviour (measured) | Old habit that now breaks |
|---|---|---|
| Boolean solver | `BooleanModifier.solver` enum is `'FLOAT' \| 'EXACT' \| 'MANIFOLD'` (default `EXACT`) | `'FAST'` raises; renamed in 5.0, `MANIFOLD` added in 4.5 |
| GN modifier inputs | `mod.properties.inputs.Socket_2.value = 8` (or `getattr(mod.properties.inputs, ident).value`); `.type = 'ATTRIBUTE'`, `.attribute_name` | `mod["Socket_2"] = 8` → `TypeError: this type doesn't support IDProperties` (changed in 5.2) |
| Auto Smooth | No mesh property. `bpy.ops.object.shade_auto_smooth(angle=…)` adds a **linked** GN asset modifier "Smooth by Angle" (`type == 'NODES'`, `use_pin_to_last=True`); works in `-b`. `bpy.ops.object.shade_smooth_by_angle(angle=…)` bakes the `sharp_edge` bool attribute instead (no modifier) | `mesh.use_auto_smooth` does not exist; `'SMOOTH_BY_ANGLE'` is not a modifier type |
| `bmesh.ops.bevel` defaults | Measured (`t11_defaults_probe.py`): with no `affect` a cube gets 14 faces = **vertex** bevel, even when `geom` is edges only; `affect='EDGES'` with no `segments` gives 26 faces = 1 segment (the RST's `segments=0` is a doc artifact) → **always pass** `affect='EDGES', segments=N, profile=0.5` | Modifier default is `EDGES`; the op default is the opposite |
| `bmesh.ops.create_grid(size=s)` | `size` is the **half**-extent: `size=1.0` → 2 m × 2 m grid | `create_cube(size=1.0)` is a full 1 m edge |
| `extrude_face_region(geom=[face])` | Faces-only input keeps the original face → interior face, 4 non-manifold edges. Pass `[f] + list(f.edges) + list(f.verts)` | Edit-mode extrude passes all three element types |
| `bmesh.ops.symmetrize(direction='X')` | Keeps the **+X** side and copies it to −X. `'-X'` deleted everything when the half lived on +X | Operator UI says "−X to +X" for the opposite case |
| `bmesh.ops.scale/translate/rotate(space=M)` | Vertices are transformed by `M⁻¹·S·M`, so `space=Matrix.Translation(-pivot)` scales **about pivot** (2.0 → 3.0 with pivot 1, scale 2); `+pivot` gave 5.0 | — |
| Curve → mesh caps | `use_fill_caps=True` caps arrive as **disconnected** triangle fans (48 boundary edges); weld with `remove_doubles(dist=1e-5)` → manifold | — |
| GN Transform node | `GeometryNodeTransform` inputs are `['Geometry','Mode','Translation','Rotation','Scale','Transform']` | — |
| Random Value / Compare | Input identifiers now equal their names (`'Min','Max','ID','Seed'` / `'A','B'`) | 4.x used `Min_001`… (5.2 release notes) |
| `Mesh` lookups | `bm.verts[i]` / `bm.faces[i]` need `ensure_lookup_table()` **again** after any `.new()` | — |

## 2. Boilerplate + self-check helper

All tests import `research/_tests/procedural/_check.py`. The load-bearing parts:

```python
import bpy, bmesh, math
from mathutils import Vector, Matrix
bpy.ops.wm.read_factory_settings(use_empty=True)          # clean scene in -b
def obj_from_bmesh(bm, name, collection=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.update()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob); return ob
def evaluated_mesh(ob, name=None):                          # whole modifier stack → new Mesh
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    me.name = name or ob.data.name + "_applied"; return me
def apply_stack(ob):                                        # in place
    me = evaluated_mesh(ob, ob.data.name); old = ob.data; ob.modifiers.clear(); ob.data = me
    if old.users == 0: bpy.data.meshes.remove(old)
```
`report(ob, label, evaluated=False, world=True)` prints the `RESULT|…` line (see §13). Measured: with and
without `preserve_all_data_layers`, `new_from_object` kept `UVMap`, a custom `panel_id` face attribute
and `custom_normal` (both `has_custom_normals=True`), so the flag made no difference in 5.2 for these layers.

## 3. Building blocks with `bmesh.ops`

Primitives (`t01_building_blocks.py`), measured:

| call | verts/faces/tris | dims (m) | note |
|---|---|---|---|
| `create_cube(bm, size=1.0)` | 8/6/12 | 1×1×1 | centred on origin |
| `create_cone(bm, segments=32, radius1=.5, radius2=.5, depth=2, cap_ends=True)` | 64/34/124, 2 ngons | 1×1×2 | = cylinder; `cap_tris=True` → 96 faces, 0 ngons |
| `create_cone(…, radius2=0.0, depth=1)` | 33/33/62 | 1×1×1 | cone |
| `create_circle(bm, segments=16, radius=.5, cap_ends=True)` | 16/1/14 | 1×1×0 | 16 boundary edges (open disc) |
| `create_uvsphere(bm, u_segments=32, v_segments=16, radius=.5)` | 482/512/960 | 1×1×1 | |
| `create_icosphere(bm, subdivisions=2, radius=.5)` | 42/80/80 | 0.95×1×1 | all tris |
| `create_grid(bm, x_segments=10, y_segments=10, size=1.0)` | 121/100/200 | **2×2**×0 | `size` = half extent |
| `create_cube(bm, size=1, matrix=Matrix.Translation((0,0,.5)) @ Matrix.Diagonal((2,1,1,1)))` | 8/6/12 | 2×1×1, zmin 0 | place/scale at creation |

Panel build — inset → extrude inward → bevel → bisect → cap → cleanup (one live `bm`):

```python
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.translate(bm, verts=bm.verts[:], vec=(0, 0, 0.5))                   # sit on ground
top = max(bm.faces, key=lambda f: f.calc_center_median().z)
r = bmesh.ops.inset_region(bm, faces=[top], thickness=0.08, use_even_offset=True)
# r['faces'] = the 4 NEW rim faces; `top` is still the (shrunk) inner face, area 1.0 -> 0.706
r = bmesh.ops.extrude_face_region(bm, geom=[top] + list(top.edges) + list(top.verts))
bmesh.ops.translate(bm, verts=[g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)], vec=(0, 0, -0.03))
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.01, offset_type='OFFSET', segments=2, profile=0.5,
                affect='EDGES', clamp_overlap=True)
r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=(0, 0, 0.6), plane_no=(0, 0, 1), clear_outer=True)
cut = [g for g in r['geom_cut'] if isinstance(g, bmesh.types.BMEdge)]
bmesh.ops.contextual_create(bm, geom=cut)                                      # cap with one n-gon
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts[:], edges=bm.edges[:])
```
Measured per stage: inset 12/10 → extrude 16/14 (manifold; faces-only input gave 15 faces, 4 non-manifold)
→ bevel 128/126 → bisect open 40/33 (12 boundary) → capped 40/34, 1 ngon, manifold → triangulate 76 tris
→ dissolve_limit 46 faces, 1 ngon (planar tris merged back).

`inset_individual` for recessed panels in one go — `thickness=0, depth=-d` is a straight push-in:
```python
r = bmesh.ops.inset_individual(bm, faces=bm.faces[:], thickness=0.08, depth=0.0, use_even_offset=True)
inner = [f for f in bm.faces if f not in set(r['faces'])]      # input faces stay = the inner panels
bmesh.ops.inset_individual(bm, faces=inner, thickness=0.0, depth=-0.02)
```
Measured: cube → 56/54/108, manifold, 6 recessed panels.

Cleanup trio, measured on two touching cubes: `remove_doubles(dist=1e-4)` 16 → 12 verts; delete the
coincident interior faces (`context='FACES'`); after deliberately `reverse_faces` on 3 faces the check
reported `flipped=3`; `recalc_face_normals(bm, faces=bm.faces[:])` → `flipped=0`.

## 4. Spin (lathe), bridge, symmetrize

Bottle lathe (`t02_spin_bridge_sym.py`): profile `(radius, z)` in the XZ plane, spun around Z.
```python
profile = [(0,0),(.035,0),(.04,.01),(.04,.18),(.03,.22),(.015,.24),(.015,.29),(.018,.30),(0,.30)]
vs = [bm.verts.new((x, 0, z)) for x, z in profile]
for a, b in zip(vs, vs[1:]): bm.edges.new((a, b))
bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0,0,0), axis=(0,0,1), dvec=(0,0,0),
               angle=math.tau, steps=32, use_merge=True)
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)      # collapse the on-axis duplicates
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])             # spin produced ALL faces inward
```
Measured: raw 288 verts, 64 boundary edges, `flipped=256`; clean **226 verts = 32×7 off-axis + 2**,
256 faces, 0.08×0.08×0.30 m, manifold. Caps become triangle fans automatically.
Tire: `create_circle(12, r=0.08, matrix=T(0.3,0,0)@Rot(90°,X))` spun 48 steps → 576/576, 0.76×0.76×0.16 m.
Elbow: 90° spin, 8 steps, `use_merge=False` → 144 verts, open ends (32 boundary).
Bridge: two `create_circle`s (r 0.5 at z0, r 0.3 at z1), `bridge_loops(bm, edges=bm.edges[:])` → 24 quads.
Symmetrize: a +X half **with the on-plane face deleted first** (`delete(context='FACES_ONLY')`), then
`symmetrize(bm, input=verts+edges+faces, direction='X', dist=1e-4)` → 28/22, 2.0 m wide, manifold.
With the cap face left on the plane the result had 4 non-manifold edges (same for the Mirror modifier).
`bmesh.ops.mirror(bm, geom=…, axis='X', merge_dist=1e-4)` gives the identical 28/22 result.

## 5. Booleans

```python
m = base.modifiers.new("Bool", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cutter
m.solver = 'EXACT'            # 'FLOAT' | 'EXACT' | 'MANIFOLD'
m.use_self = True             # EXACT only: cutter mesh intersects itself
m.use_hole_tolerant = True    # EXACT only: non-manifold operands
m.operand_type = 'COLLECTION'; m.collection = cutters_col     # many cutters at once
```
Measured, 1 m cube minus r 0.2 cylinder (`t03_boolean.py`):

| case | result |
|---|---|
| FLOAT / EXACT / MANIFOLD, closed cutter | all 72/40/144, 4 ngons, manifold |
| FLOAT / EXACT, **open** (uncapped) cutter | still cut, 72/40 |
| MANIFOLD, open cutter | **no-op** (8/6) + warning "object(s) … have non-manifold geometry" |
| EXACT, self-intersecting cutter, `use_self=False` | garbage: 14 faces, 10 ngons, 204 tris |
| same, `use_self=True` | 76/40/152 correct |
| cutter `hide_viewport=True`, or `hide_set(True)+hide_render`, or even unlinked from the scene | all still cut (72/40) in `-b` |
| collection operand, 2 overlapping cutters | 120/64/240, manifold |

Rules: MANIFOLD only for watertight cutters (fastest); EXACT when cutters overlap each other
(`use_self`); FLOAT when you need speed and nothing is coplanar. Hide cutters with
`display_type='WIRE'; hide_render=True; hide_set(True)`.
Cleanup after applying: `remove_doubles(1e-4)` → `dissolve_limit(1°)` → `recalc_face_normals`; then
`triangulate` only n-gons for export: measured 40 faces/4 ngons → 108 faces/0 ngons, 144 tris unchanged.
Operator route also works in `-b`:
```python
with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
    bpy.ops.object.modifier_apply(modifier=m.name)       # {'FINISHED'}, modifiers left: 0
```

## 6. Modifier recipes and applying the stack

Hard-surface stack (`t04_modifier_stack.py`), order top→bottom: **Mirror → Array → Bevel → Weighted Normal
→ (Subdivision) → Smooth by Angle last** (the Smooth-by-Angle asset pins itself last).
```python
mir = ob.modifiers.new("Mirror", 'MIRROR'); mir.use_axis[0] = True; mir.use_clip = True
mir.use_mirror_merge = True; mir.merge_threshold = 1e-4
arr = ob.modifiers.new("Array", 'ARRAY'); arr.count = 3; arr.use_relative_offset = True
arr.relative_offset_displace = (0, 1.5, 0)
bev = ob.modifiers.new("Bevel", 'BEVEL'); bev.limit_method = 'ANGLE'; bev.angle_limit = math.radians(30)
bev.width = 0.003; bev.segments = 3; bev.profile = 0.5; bev.harden_normals = True; bev.use_clamp_overlap = True
wn = ob.modifiers.new("WeightedNormal", 'WEIGHTED_NORMAL'); wn.keep_sharp = True; wn.mode = 'FACE_AREA'
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.shade_auto_smooth(angle=math.radians(30))   # appends linked "Smooth by Angle" (NODES)
apply_stack(ob)                                             # §2 helper; keeps custom normals + sharp_edge
```
Measured: L-bracket half (12 verts, seam face on x=0 deleted) → evaluated **624/630/1236**, 0.4×0.4×0.1 m,
manifold; applied mesh `has_custom_normals=True`, `sharp_edge` attribute present.
Modifier-free alternative for export: `bpy.ops.object.shade_smooth_by_angle(angle=…)` wrote 360 sharp edges.

| recipe | key settings | measured |
|---|---|---|
| Bevel → Subsurf (holding edges) | `BEVEL width .02 segments 2` then `SUBSURF levels 2`, `me.shade_smooth()` | 0.5 m cube → 866/864/1728 |
| Solidify shell | `thickness .02, offset -1, use_even_offset, use_rim` | 1 m grid → 242/240, 0.02 thick, manifold |
| Screw lathe (vase) | profile edges; `angle=τ, steps=32, axis='Z', use_merge_vertices, use_normal_calculate, use_smooth_shade` | 162/192/320, 0.16×0.16×0.25, manifold |
| Screw thread | 3-vert V profile; `screw_offset=0.004 (pitch), iterations=10, steps=16` | 483/320, height 0.044; open strip (close the profile for a solid) |
| Pipe along curve | segment cylinder oriented along +X; `ARRAY fit_type='FIT_CURVE', curve=path, use_merge_vertices` then `CURVE object=path, deform_axis='POS_X'` | 240/228, spans 1.61 m |
| Taper | `SIMPLE_DEFORM deform_method='TAPER', factor=-0.6, deform_axis='Z'` on a cube with 4 cuts | top width 1.0 → 0.4 |
| Surface detail | `DISPLACE texture=bpy.data.textures.new('T','CLOUDS') (noise_scale .3), strength .08, texture_coords='LOCAL'` | sphere 1.0 → 1.015×0.997×1.019 |
| Planar cleanup | `DECIMATE decimate_type='DISSOLVE', angle_limit=5°` | 12 tris → 6 quads |
| Export tris | `TRIANGULATE quad_method='BEAUTY', ngon_method='BEAUTY', min_vertices=4` | 6 quads → 12 tris |

Stack order source: manual *Modifiers › Introduction* ("calculated top to bottom"); Smooth by Angle
"should be last, or at least after Subdivision" (manual *Smooth By Angle Modifier*).

## 7. Curves: cables, pipes, ropes

```python
cu = bpy.data.curves.new("CU_Cable", 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('BEZIER'); sp.bezier_points.add(3)
for p, co in zip(sp.bezier_points, [(0,0,1), (.4,.1,.6), (.8,-.1,.55), (1.2,0,1)]):
    p.co = co; p.handle_left_type = p.handle_right_type = 'AUTO'     # or 'FREE' + set p.handle_left/right
cu.bevel_mode = 'ROUND'; cu.bevel_depth = 0.01; cu.bevel_resolution = 4   # ring = 12 verts at res 4
cu.resolution_u = 12; cu.fill_mode = 'FULL'; cu.use_fill_caps = True
ob = bpy.data.objects.new("CU_Cable", cu); bpy.context.scene.collection.objects.link(ob)
me = evaluated_mesh(ob, "SM_Cable")                     # curve → mesh, no operator needed
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
```
Measured (`t05_curves.py`): raw 468/452/884 with **48 boundary edges** (caps are detached fans);
after `remove_doubles` 444 verts, manifold. Without caps: 444/432, 24 boundary. Pipe r 0.04, res 8:
700/676/1316. POLY rope (12 points, `(x,y,z,w)` coords, `spline.use_smooth=True` — `use_smooth` is per
spline, not on the Curve): 120/110. Custom profile: `cu.bevel_mode='OBJECT'; cu.bevel_object=profile_curve`
(2D POLY square, `use_cyclic_u=True`) → square duct 100/100; raw normals were all inward (`flipped=96`),
fixed by `recalc_face_normals`. `bpy.ops.object.convert(target='MESH')` under `temp_override` also works.

## 8. Geometry Nodes from Python

```python
ng = bpy.data.node_groups.new("GN_BoltRow", 'GeometryNodeTree')
ng.interface.new_socket("Geometry", in_out='INPUT',  socket_type='NodeSocketGeometry')
ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
s = ng.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt'); s.default_value = 6; s.min_value = 1
s = ng.interface.new_socket("Spacing", in_out='INPUT', socket_type='NodeSocketFloat'); s.subtype = 'DISTANCE'
ng.interface.new_socket("Material", in_out='INPUT', socket_type='NodeSocketMaterial')
n, L = ng.nodes, ng.links.new
gi, go = n.new('NodeGroupInput'), n.new('NodeGroupOutput')
line = n.new('GeometryNodeMeshLine'); line.mode = 'OFFSET'          # inputs: Count, Resolution, Start Location, Offset
xyz = n.new('ShaderNodeCombineXYZ')
cyl = n.new('GeometryNodeMeshCylinder'); cyl.inputs['Vertices'].default_value = 6; cyl.inputs['Depth'].default_value = .008
iop = n.new('GeometryNodeInstanceOnPoints')                          # Points, Selection, Instance, Pick Instance, Instance Index, Rotation, Scale
real = n.new('GeometryNodeRealizeInstances'); setm = n.new('GeometryNodeSetMaterial')
xf = n.new('GeometryNodeTransform'); xf.inputs['Translation'].default_value = (0, 0, .5)
join = n.new('GeometryNodeJoinGeometry')
L(gi.outputs['Count'], line.inputs['Count']); L(gi.outputs['Spacing'], xyz.inputs['X']); L(xyz.outputs['Vector'], line.inputs['Offset'])
L(line.outputs['Mesh'], iop.inputs['Points']); L(cyl.outputs['Mesh'], iop.inputs['Instance'])
L(iop.outputs['Instances'], real.inputs['Geometry']); L(real.outputs['Geometry'], setm.inputs['Geometry'])
L(gi.outputs['Material'], setm.inputs['Material']); L(setm.outputs['Geometry'], xf.inputs['Geometry'])
L(gi.outputs['Geometry'], join.inputs['Geometry']); L(xf.outputs['Geometry'], join.inputs['Geometry'])
L(join.outputs['Geometry'], go.inputs['Geometry'])

mod = ob.modifiers.new("Bolts", 'NODES'); mod.node_group = ng
def set_input(mod, name, value):                               # 5.2: properties.inputs.<identifier>.value
    ident = next(i.identifier for i in mod.node_group.interface.items_tree
                 if i.item_type == 'SOCKET' and i.in_out == 'INPUT' and i.name == name)
    getattr(mod.properties.inputs, ident).value = value
set_input(mod, "Count", 8); set_input(mod, "Spacing", 0.1); set_input(mod, "Material", bpy.data.materials.new("M_Bolt"))
applied = bpy.data.objects.new("SM_Hull_Applied", evaluated_mesh(ob))
```
Measured (`t06_geonodes.py`): cube + 8 hex bolts → **104/70/172**, 1.21×1.0×1.0 m, manifold; applied mesh
got material slots `[None, 'M_Bolt']`. Identifiers are `Socket_0, Socket_2…` (Geometry out is `Socket_1`);
item props: `name, value, type ('VALUE'|'ATTRIBUTE'), attribute_name`. **Without Realize Instances the
evaluated/applied mesh is just the input cube (8 verts)** — instances are dropped by `new_from_object`.
Scatter: `GeometryNodeDistributePointsOnFaces` (`distribute_method='RANDOM'|'POISSON'`; inputs Mesh,
Selection, Distance Min, Density Max, Density, Density Factor, Seed; outputs Points, Normal, Rotation)
→ Instance on Points with `dist.outputs['Rotation']` → Realize → Join: density 30 on a 6 m² cube gave
180 rivets, 2168/3606 verts/faces. `socket_type` must be a concrete `NodeSocket*` name: measured,
`socket_type='DEFAULT'` raises (enum not found; valid: Float, Int, Bool, Vector, Color, Rotation, Matrix,
String, Menu, Geometry, Object, Collection, Image, Material, Font, Sound, Bundle, Closure) and omitting it
silently creates a `NodeSocketFloat`.

## 9. Kitbash and greebling

Derive every detail size from the asset's longest dimension (`t07_greeble.py`, 2 m hull):
chamfer 0.5 % (1 cm), panel border 2 % (4 cm), recess depth 0.4 % (8 mm), bolt radius 0.6 %. One bevel
width per asset, 1 segment for flat-shaded/low-poly, 2–3 with `harden_normals` for smooth shading.
These ratios are a working convention, not a published rule `(verify)`.
```python
big = [f for f in bm.faces if f.calc_area() > 0.3]
bmesh.ops.inset_individual(bm, faces=big, thickness=BORDER, use_even_offset=True)   # panel lines
bmesh.ops.inset_individual(bm, faces=big, thickness=0.0, depth=-DEPTH)              # recess (inputs = inner faces)
sharp = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0.0) > math.radians(30) and <outer-hull test>]
bmesh.ops.bevel(bm, geom=sharp, offset=CHAMFER, segments=1, profile=0.5, affect='EDGES', clamp_overlap=True)
# bolts: one bmesh, a cone per corner, oriented to the face normal
rot = f.normal.to_track_quat('Z', 'Y').to_matrix().to_4x4()
bmesh.ops.create_cone(bm_bolts, segments=6, radius1=r, radius2=r*.85, depth=h, cap_ends=True,
                      matrix=Matrix.Translation(pos) @ rot)
```
Measured: hull 8/6 → panels 56/54 → chamfer (52 edges) 152/146 → 24 hex bolts 288/192 (separate
`SM_Hull_Bolts` object) → 5 boolean slots (one cutter mesh of 5 boxes, EXACT) evaluated 184/168 → applied +
cleanup 160/120/316, manifold. Render `_out/r_t07b.png` shows crisp panel lines, chamfers, corner bolts, slots.
Linked duplicates for repeated greebles cost no geometry: `bpy.data.objects.new(name, proto.data)` → `mesh.users == 7`.

## 10. Organic-ish shapes by code

```python
from mathutils import noise
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=4, radius=0.5); bm.normal_update()
for v in bm.verts:                                              # layered noise along normals
    v.co += v.normal * (0.12 * noise.noise(v.co * 1.5) + 0.04 * noise.noise(v.co * 6.0 + Vector((7, 3, 1))))
bmesh.ops.scale(bm, vec=(1.0, 0.8, 0.6), verts=bm.verts[:])
for _ in range(2):
    bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
```
Measured (`t08_organic.py`): boulder 642/1280 tris, 1.0×0.78×0.59 m (smoothing shrank 2–3 %).
Quad version: cube `subdivide_edges(cuts=6, use_grid_fill=True)` + noise + `SUBSURF 1` → 1178/1176 quads.
Metaballs: `mb = bpy.data.metaballs.new(); mb.resolution = 0.05; el = mb.elements.new(); el.co, el.radius`
→ `evaluated_mesh(mb_ob)` → 764/902 (0.96×0.64×0.64 m); `dissolve_limit(3°)` → 838 faces.
Skin tree from an edge skeleton:
```python
sk = tree.modifiers.new("Skin", 'SKIN'); sk.use_smooth_shade = True; sk.branch_smoothing = 0.5
for sv, r in zip(tree.data.skin_vertices[0].data, radii): sv.radius = (r, r)   # layer exists after modifiers.new
tree.data.skin_vertices[0].data[root_index].use_root = True
ss = tree.modifiers.new("Subsurf", 'SUBSURF'); ss.levels = 2; apply_stack(tree)
```
Measured: 8-vert / 7-edge skeleton → Skin 230/229 quads → +Subsurf 2 → 3644/3640, 1.41×0.83×3.28 m, manifold.
Lattice: `lat = bpy.data.lattices.new(); lat.points_u = lat.points_v = 2; lat.points_w = 3`; lattice object
scaled to cover the mesh (spans −0.5..0.5); edit `lat.points[i].co_deform` (index = u + v·U + w·U·V);
`ob.modifiers.new("Lattice", 'LATTICE').object = lat_ob`. Measured: can 0.6×0.6×1.0 → 0.647×0.596×1.0 (lean + taper).
Honest limit: these give blobs, rocks, trunks and blockouts; no code path here produces sculpted
anatomy, folds or wrinkles — plan a sculpt/scan or stylize instead.

## 11. Stylized shortcuts

- Faceted rock: noisy icosphere (sub 3) → `DECIMATE decimate_type='COLLAPSE', ratio=0.12,
  use_collapse_triangulate=True` → `apply_stack` → `me.shade_flat()`. Measured 320 → **38 tris**, all flat.
- Chunky bevel: `bevel(offset=0.075 (15 % of a 0.5 m block), segments=1)` → 24/26 chamfered "toy";
  `segments=4` + `shade_smooth()` → 152/150 rounded. Both manifold.
- Exaggerated proportions: pick a vertex group and scale about a pivot — explicit and convention-free:
  `for v in head: v.co = pivot + (v.co - pivot) * 1.6` (figure 0.5×0.5×1.32 → 0.70×0.70×1.51 m), or
  `bmesh.ops.scale(bm, vec=(1.6,)*3, space=Matrix.Translation(-pivot), verts=head)` (verified: vert at 2 → 3 with pivot 1, ×2).
- Low-poly gem: `create_uvsphere(u_segments=10, v_segments=6)` + `shade_flat()` → 52/60/100.

## 12. Scale / pivot / naming hygiene

Order that worked (`t10_hygiene.py`): build in metres at identity → **apply transforms first** → origin to
bottom-centre → place with `location` only → name `SM_<Asset>_<Part>` in collection `SM_<Asset>`.
```python
def apply_transforms(ob):               # Ctrl+A All Transforms
    ob.data.transform(ob.matrix_world); ob.matrix_world = Matrix.Identity(4); ob.data.update()
def origin_to_bottom_center(ob):        # pivot moves, mesh stays put in world space
    me = ob.data; xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    off = Vector(((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, min(zs)))
    me.transform(Matrix.Translation(-off)); ob.matrix_world = ob.matrix_world @ Matrix.Translation(off)
```
Measured: 0.8 m crate with stray `scale=(1,1,1.25)` → after apply local dims 0.8×0.8×1.0, `matrix_world`
identity → after origin move local zmin 0.0, origin at the old bbox bottom (3, 2, −0.5) → `location=(0,0,0)`.
Child part: `lid.parent = body; lid.matrix_parent_inverse = body.matrix_world.inverted()`.
`scene.unit_settings.system='METRIC'; scale_length=1.0`. Export sanity in `-b`: `bpy.ops.export_scene.gltf(
filepath, export_format='GLB', use_selection=True, export_apply=True)` → 6.8 KB; `bpy.ops.export_scene.fbx(
filepath, use_selection=True, apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True)` → 13.5 KB.

## 13. Self-check helpers

```python
def mesh_stats(me, matrix=None):
    me.calc_loop_triangles()
    st = dict(verts=len(me.vertices), faces=len(me.polygons), tris=len(me.loop_triangles),
              ngons=sum(1 for p in me.polygons if len(p.vertices) > 4))
    cs = [(matrix or Matrix.Identity(4)) @ v.co for v in me.vertices]          # bbox dims
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    st['nonmanifold'] = sum(1 for e in bm.edges if not e.is_manifold)         # includes boundary edges
    st['boundary'] = sum(1 for e in bm.edges if e.is_boundary)
    st['loose'] = sum(1 for v in bm.verts if not v.link_edges)
    before = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])                        # on a throwaway copy
    st['flipped'] = sum(1 for f, n in zip(bm.faces, before) if f.normal.dot(n) < 0)
    bm.free(); return st
```
Use `evaluated=True` (read `ob.evaluated_get(dg).data`) to check a modifier stack without applying it.
Interpretation: `nonmanifold == boundary` ⇒ merely open (pipes, grids); `nonmanifold > boundary` ⇒ interior
faces or wire edges; `flipped == faces` on an open sheet is just orientation ambiguity. Measured on a cube
with a loose vert, a wire edge and one reversed face: `nonmanifold=1 loose=1 flipped=1`; fix with
`bmesh.ops.delete(geom=[v for v in bm.verts if not v.link_edges], context='VERTS')`,
`delete(geom=[e for e in bm.edges if not e.link_faces], context='EDGES')`, `recalc_face_normals` → all zero.
`mesh.validate()` returned False (did not catch any of these — it only fixes invalid indices/data).

## 14. Sources

- Blender 5.2 Python API release notes — GN modifier `properties.inputs` API, Random Value/Compare identifiers: https://developer.blender.org/docs/release_notes/5.2/python_api/
- Blender 5.0 Python API release notes — `FAST`→`FLOAT`, bpy.props no longer dict-accessible: https://developer.blender.org/docs/release_notes/5.0/python_api/
- Blender 4.5 release coverage of the Manifold solver: https://www.cgchannel.com/2025/07/blender-4-5-lts-is-out-check-out-its-5-key-features
- Bundled 5.2 API RST (via MCP `get_python_api_docs`): `bmesh.ops.bevel/spin/inset_region/bisect_plane/symmetrize/bridge_loops/dissolve_limit/smooth_vert`, `bpy.types.BooleanModifier`, `BevelModifier`, `NodeTreeInterface`, `NodesModifier`.
- Bundled manual: `manual/modeling/modifiers/generate/booleans.rst` (solver options), `bevel.rst` (Harden Normals, Face Strength), `normals/weighted_normal.rst`, `generate/screw.rst`, `generate/skin.rst` (root, branch smoothing), `generate/decimate.rst` (Planar), `deform/lattice.rst`, `modeling/metas/properties.rst`, `geometry_nodes/point/distribute_points_on_faces.rst`, `geometry_nodes/curve/operations/curve_to_mesh.rst` (Fill Caps).
- Smooth By Angle modifier manual page (4.1+ replacement for Auto Smooth, keep last in stack): https://docs.blender.org/manual/en/4.2/modeling/modifiers/normals/smooth_by_angle.html
- Depsgraph / `evaluated_get` → `new_from_object` pattern: https://docs.blender.org/api/5.1/bpy.types.Depsgraph.html
- Modifier order write-up (Mirror → Array → Solidify → Boolean → Bevel → Weighted Normal → Subdivision): https://steveyang.readthedocs.io/Modeling/Non-destructive/ND-Beginning/Modifier_Stack_Order/

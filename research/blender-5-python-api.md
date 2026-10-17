# Blender 5.2 LTS Python API — patterns, pitfalls, breaking changes vs 3.x/4.x

Target: **Blender 5.2.2 LTS** (`bpy.app.version == (5, 2, 2)`, Python 3.13.13), driven headless with
`/Applications/Blender.app/Contents/MacOS/Blender -b --python script.py`.

**Verification legend** — every snippet carries one of:
`[-b tNN]` ran in background mode, script `research/_tests/tNN_*.py` ·
`[docs]` checked against the bundled 5.2 API RST (MCP `get_python_api_docs`) ·
`[notes]` release notes only, not executed · `(verify)` unconfirmed.

Release notes (Python API pages): [4.0](https://developer.blender.org/docs/release_notes/4.0/python_api/) ·
[4.1](https://developer.blender.org/docs/release_notes/4.1/python_api/) · [4.2](https://developer.blender.org/docs/release_notes/4.2/python_api/) ·
[4.3](https://developer.blender.org/docs/release_notes/4.3/python_api/) · [4.4](https://developer.blender.org/docs/release_notes/4.4/python_api/) ·
[4.5](https://developer.blender.org/docs/release_notes/4.5/python_api/) · [5.0](https://developer.blender.org/docs/release_notes/5.0/python_api/) ·
[5.1](https://developer.blender.org/docs/release_notes/5.1/python_api/) · [5.2](https://developer.blender.org/docs/release_notes/5.2/python_api/).
Pipeline/I-O pages use the slug `pipeline_io/`: [5.0](https://developer.blender.org/docs/release_notes/5.0/pipeline_io/),
[5.1](https://developer.blender.org/docs/release_notes/5.1/pipeline_io/), [5.2](https://developer.blender.org/docs/release_notes/5.2/pipeline_io/).

## Contents
1. [Breaking changes table (3.x → 5.2)](#1-breaking-changes-table)
2. [Background mode (`-b`) and context](#2-background-mode-and-context)
3. [Mesh creation, attributes, normals](#3-mesh-creation-attributes-normals)
4. [bmesh modelling chain](#4-bmesh-modelling-chain)
5. [Modifiers, transforms, origin, collections, naming](#5-modifiers-transforms-origin-collections-naming)
6. [Materials, image textures, image I/O](#6-materials-image-textures-image-io)
7. [Headless rendering, camera, world, turntable](#7-headless-rendering-camera-world-turntable)
8. [Export / import](#8-export--import)
9. [Measuring and QA](#9-measuring-and-qa)
10. [Extensions / add-on packaging](#10-extensions--add-on-packaging)

---

## 1. Breaking changes table

| Area | 3.x / early 4.x | 5.2 | Since | Proof |
|---|---|---|---|---|
| Auto smooth | `mesh.use_auto_smooth`, `mesh.auto_smooth_angle` | **gone**. Use `bpy.ops.object.shade_auto_smooth(angle=)` (adds a "Smooth by Angle" NODES modifier) or data-level `mesh.set_sharp_from_angle(angle=)` + `mesh.shade_smooth()` | 4.1 | `[-b t01]` hasattr False; `[docs]` |
| Split normals | `mesh.calc_normals_split()`, `free_normals_split()`, `calc_normals()`, `create_normals_split()` | **gone**. Read `mesh.corner_normals[i].vector`, `vertex_normals`, `polygon_normals` (auto-computed); write with `normals_split_custom_set(_from_vertices)` | 4.0/4.1 | `[-b t01]` |
| Smooth flag | `poly.use_smooth` | still works, but is a view on the `sharp_face` FACE/BOOLEAN attribute (`shade_smooth()` *removes* the attribute) | 4.1 | `[-b t01,t04]` |
| Crease / bevel weight | `edge.crease`, `edge.bevel_weight`, `vertex_layers_float` … | **gone** → `mesh.attributes["crease_edge"]`, `bevel_weight_edge`, generic `mesh.attributes.new(name, type, domain)` | 4.0 | `[notes 4.0]`, `[docs Mesh]` |
| Vertex colors | `mesh.vertex_colors` | still present but documented "Legacy… deprecated"; use `mesh.color_attributes.new(name, 'BYTE_COLOR'|'FLOAT_COLOR', 'CORNER'|'POINT')` | 3.2+ | `[docs]`, `[-b t02]` |
| Attribute group type | `bpy.types.AttributeGroup` | split: `AttributeGroupMesh`, `…PointCloud`, `…Curves`, `…GreasePencil` | 4.3 | `[notes 4.3]`, `[-b t02]` |
| Principled BSDF sockets | `Specular`, `Emission`, `Subsurface`, `Transmission`, `Coat`, `Sheen`, `Subsurface Color` | `Specular IOR Level`, `Emission Color` (+`Emission Strength`, default **0.0**), `Subsurface Weight`, `Transmission Weight`, `Coat Weight`, `Sheen Weight`; old names raise `KeyError` | 4.0 | `[-b t01,t03]` |
| Material blend | `mat.blend_method`, `mat.shadow_method` | `mat.surface_render_method` ∈ `{'DITHERED','BLENDED'}`; `shadow_method` gone, `blend_method` still exists (legacy) | 4.2 | `[-b t03]` |
| `Material.use_nodes` | required `mat.use_nodes = True` | **DeprecationWarning, removed in 6.0**. New materials/worlds already have a node tree (Principled BSDF + Output). Just don't set it. Same for `World.use_nodes` | 5.0 | `[-b t01,t02]` |
| EEVEE id | `'BLENDER_EEVEE'` (legacy) → 4.2 `'BLENDER_EEVEE_NEXT'` | back to **`'BLENDER_EEVEE'`**; `'BLENDER_EEVEE_NEXT'` raises TypeError. Engines: `BLENDER_EEVEE`, `BLENDER_WORKBENCH`, `CYCLES` | 5.0 | `[-b t02]` |
| EEVEE settings | `scene.eevee.use_gtao`, `gtao_distance`, `use_bloom`, `use_ssr`, `taa_render_samples` | `use_gtao/gtao_*/bloom/ssr` **gone** (`view_layer.eevee.ambient_occlusion_distance`); `taa_render_samples`, `use_raytracing`, `use_shadows`, `shadow_ray_count`, `use_fast_gi` exist | 4.2–5.0 | `[-b t01]` property list |
| Motion blur / shadows | `scene.eevee.use_motion_blur`, `light.cycles.cast_shadow` | `scene.render.use_motion_blur`, `light.use_shadow` | 4.2 | `[notes 4.2]`, `[-b t04]` |
| Output format | `image_settings.file_format = 'FFMPEG'` | must set **`image_settings.media_type = 'VIDEO'` first** (`'IMAGE'`, `'MULTI_LAYER_IMAGE'`, `'VIDEO'`); otherwise TypeError | 5.0 | `[-b t02]` |
| Colorspaces | `'Linear'`, `'Raw'`, `'sRGB'` | `'Linear'`/`'Raw'` **gone** → `'Linear Rec.709'`, `'Non-Color'`; `'sRGB'`, `'ACEScg'`, `'scene_linear'` exist. Default view transform is **AgX** | 4.0 | `[-b t01,t03]` |
| Context override | `bpy.ops.x.y(override_dict)` | removed → `with bpy.context.temp_override(window=, area=, region=, **members):` | 4.0 | `[notes 4.0]`, `[docs Context]`, `[-b t07]` |
| Actions | `action.fcurves`, `action.groups`, `action.id_root` | **removed** (slotted actions). Use `anim_utils.action_get_channelbag_for_slot(action, slot).fcurves`; `ActionSlot` has `identifier`/`name_display`, **no `.name`** | 4.4 depr → 5.0 removed | `[-b t03,t04]` |
| GN modifier inputs | `mod["Socket_1"] = v`, `mod["Socket_1_use_attribute"]` | **removed** ("this type doesn't support IDProperties") → `mod.properties.inputs.Socket_1.value`, `.type` (`'VALUE'`/`'ATTRIBUTE'`), `.attribute_name`; outputs: `mod.properties.outputs.<id>.attribute_name` | 5.2 | `[-b t03,t04]` |
| Node groups | `tree.inputs.new()` / `tree.outputs.new()` | `tree.interface.new_socket(name, in_out='INPUT', socket_type='NodeSocketFloat')`; identifiers are `Socket_N` | 4.0 | `[-b t02]` |
| Compositor | `scene.use_nodes`, `scene.node_tree` | `scene.node_tree` **gone** → `scene.compositing_node_group`; `use_nodes` deprecated (always True) | 5.0 | `[-b t04]` |
| Boolean solver | `'FAST'` | `'FLOAT'`; enum `FLOAT, EXACT, MANIFOLD` (default EXACT) | 5.0 | `[-b t02]` |
| mathutils buffers | float64 | **float32** buffer protocol: `np.asarray(Vector)` is float32; `foreach_get` into float64 still works | 5.0 | `[-b t02,t04]` |
| OBJ/PLY/STL | `bpy.ops.export_scene.obj`, `import_scene.obj` (Python) | `bpy.ops.wm.obj_export/obj_import`, `wm.ply_export`, `wm.stl_export` (C++). `export_scene` has only `fbx`, `gltf` | 4.0 | `[-b t02]` |
| FBX import | `bpy.ops.import_scene.fbx` | default is **`bpy.ops.wm.fbx_import`** (ufbx, C++); legacy still exists. Exporter unchanged (`export_scene.fbx`) | 5.0 | `[-b t06]`, `[notes 5.0 io]` |
| Collada | `wm.collada_export` | removed (attribute exists but no RNA type) | 5.0 | `[-b t02]` |
| glTF format | `export_format='GLTF_EMBEDDED'` | removed; only `'GLB'`, `'GLTF_SEPARATE'`; enum is dynamic (`enum_items` empty) — **always pass `export_format` explicitly** | 4.2 | `[-b t03]` |
| USD export | `export_textures=True`, `visible_objects_only` | `export_textures_mode ∈ {'KEEP','PRESERVE','NEW'}`; `export_textures` → TypeError; `selected_objects_only`, `convert_orientation`, `export_global_forward_selection='NEGATIVE_Z'` | 5.0 | `[-b t02,t03]` |
| Add-ons | `bl_info` dict | `blender_manifest.toml` extension (legacy `bl_info` still loads `(verify)`) | 4.2 | `[notes 4.2]`, manual |
| UV pin / select | `uv_layer.pin[i]` auto-created; `MeshUVLoopLayer.vertex_selection` | `pin` empty until `uv_layer.pin_ensure()`; UV selection now shared attributes `.uv_select_vert/edge/face` | 5.0 | `[-b t03]` |
| GPU in `-b` | — | `gpu.init()` required before any `gpu.*` call in background (`SystemError` otherwise) | 5.2 | `[-b t04,t05]` |
| GPU backend | OpenGL | prefs `system.gpu_backend ∈ {OPENGL, METAL, VULKAN}`; macOS = `METAL`. 5.0 kept OpenGL default on Win/Linux; 5.1 targeted Vulkan default `(verify for 5.2)` | 5.x | `[-b t03]`, press |
| ID renaming | `id.name = x` (auto `.001`) | also `id.rename(name, mode='ALWAYS'|'NEVER'|'SAME_ROOT')` returning a status; `.name =` still auto-suffixes | 4.3 | `[-b t04]` |
| `bpy.app` | `version_char` | removed; `version_string == '5.2.2 LTS'`, `bpy.app.background`, `bpy.app.cachedir` (5.1) | 4.0 | `[-b t01,t02]` |

Also `[notes]` only: 5.0 removed dict access `scene['cycles']`; render pass names standardised (`"Z"`→`"Depth"`); `Image.bindcode`/BGL removed; 5.2 changed socket identifiers of Compare / Random Value nodes; VSE `Sequence`→`Strip` (4.4).

---

## 2. Background mode and context

Facts measured in `-b` `[-b t02,t03,t07]`: `bpy.app.background is True`; the factory startup file provides a `Window`
and a `Screen("Layout")` with areas `PROPERTIES, OUTLINER, DOPESHEET_EDITOR, VIEW_3D`; `bpy.context.area`/`region` are `None`;
`bpy.context.mode == 'OBJECT'`; the default scene already contains `Camera`, `Cube`, `Light`.

**What works with no override at all** (executed bare, `{'FINISHED'}` `[-b t03,t04,t05,t10]`): `object.select_all`, `object.delete`,
`object.mode_set`, `mesh.select_all`, `mesh.mark_seam`, `uv.smart_project`, `uv.unwrap`, `uv.pack_islands`, `object.shade_smooth`,
`object.shade_auto_smooth`, `object.modifier_apply`, `object.origin_set(type='ORIGIN_GEOMETRY')`, `object.transform_apply`,
`mesh.primitive_cube_add`, `view3d.camera_to_view_selected`, `object.bake`, `render.render`, every exporter. Do **not** wrap these blindly.

**What needs a VIEW_3D override**: `view3d.view_selected`, `view3d.snap_cursor_to_selected` poll False bare, True inside the
override `[-b t07]`. Pattern (window/area/region must nest consistently — `[docs Context.temp_override]`):

```python
import bpy
win = bpy.context.window                      # exists in -b
area = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
with bpy.context.temp_override(window=win, area=area, region=region):
    bpy.ops.view3d.view_selected()            # [-b t07]
# debugging a failing op: `with bpy.context.temp_override(...) as ov: ov.logging_set(True)` prints members read [docs]
```

Selection/active object — set both explicitly, operators mutate them `[-b t03]`:

```python
def select_only(obj, view_layer=None):
    vl = view_layer or bpy.context.view_layer
    for ob in bpy.data.objects: ob.select_set(False)
    obj.select_set(True); vl.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')   # bmesh.from_edit_mesh(obj.data) while in EDIT
bpy.ops.object.mode_set(mode='OBJECT') # always return before reading obj.data
```

Depsgraph: `obj.matrix_world` is stale after `obj.location = …` until `bpy.context.view_layer.update()` (measured
`(0,0,0)` → `(5,0,0)` `[-b t04]`). Evaluated data: `dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg)`.

---

## 3. Mesh creation, attributes, normals

```python
me = bpy.data.meshes.new("Part")
me.from_pydata(verts, [], faces)          # edges inferred from faces [docs]
if me.validate(verbose=True): print("fixed invalid geometry")  # drops bad faces, returns True [-b t06]
me.update(calc_edges=True)
me.shade_smooth()                          # removes 'sharp_face' attr; shade_flat() sets it for every face [docs, -b t01]
me.set_sharp_from_angle(angle=math.radians(30))   # fills 'sharp_edge' EDGE/BOOLEAN attr — modifier-free auto smooth [-b t01]
ob = bpy.data.objects.new("Part", me); bpy.context.scene.collection.objects.link(ob)
```

Attribute API (all measured `[-b t04]`): built-ins visible in `me.attributes` include `position` (POINT/FLOAT_VECTOR),
`sharp_face`, `sharp_edge`, `UVMap` (CORNER/FLOAT2), plus internal `.select_*`, `.uv_select_*`, `.pn.<uvmap>` (pins).
Types: `FLOAT, INT, BOOLEAN, FLOAT_VECTOR, FLOAT_COLOR, QUATERNION, FLOAT4X4, STRING, INT8, INT16_2D, INT32_2D, FLOAT2, FLOAT4, BYTE_COLOR`;
domains for meshes `POINT, EDGE, FACE, CORNER`.

```python
import numpy as np
a = me.attributes.new("my_weight", 'FLOAT', 'POINT')
a.data.foreach_set("value", np.linspace(0, 1, len(me.vertices), dtype=np.float32))
pos = np.empty(len(me.vertices) * 3, dtype=np.float32)      # float32 is native since 5.0
me.attributes["position"].data.foreach_get("vector", pos)    # same as me.vertices.foreach_get("co", ...)
uv = me.uv_layers.active                                      # me.uv_layers.new(name="UVMap") to create
uv.data[i].uv  ==  uv.uv[i].vector                            # both forms work [-b t03]
me.calc_loop_triangles(); tris = len(me.loop_triangles)       # == sum(len(p.vertices)-2 for p in me.polygons)
```

Custom normals: `me.normals_split_custom_set(list_of_corner_vectors)` / `normals_split_custom_set_from_vertices(...)`;
read-only `me.corner_normals`, `me.has_custom_normals`, `me.normals_domain` (`'FACE'` on a flat cube) `[docs, -b t04]`.

---

## 4. bmesh modelling chain

Signatures below are `[docs bmesh.ops.*]`; the chain ran manifold at every step (`validate() False`, 124 tris) `[-b t09]`.

```python
import bmesh, math
from bmesh.types import BMVert
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.1, segments=2, affect='EDGES', profile=0.5, clamp_overlap=True)
top = [f for f in bm.faces if f.normal.z > 0.99]            # 0.9 also catches 22.5° bevel faces (cos=0.92) → non-manifold later
bmesh.ops.inset_region(bm, faces=top, thickness=0.2, depth=0.0, use_even_offset=True)
inner = [f for f in bm.faces if f.normal.z > 0.99 and f.calc_area() > 1.0]
r = bmesh.ops.extrude_face_region(bm, geom=inner)           # does NOT remove originals when geom is faces only
bmesh.ops.translate(bm, verts=[g for g in r["geom"] if isinstance(g, BMVert)], vec=(0, 0, -0.3))
bmesh.ops.delete(bm, geom=inner, context='FACES')           # <- required, else 4 non-manifold edges per face [-b t08,t09]
bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if all(v.co.z < -0.99 for v in e.verts)], cuts=1, use_grid_fill=True)
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts[:], edges=bm.edges[:], delimit={'NORMAL'})
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
bm.to_mesh(me); bm.free(); me.update()
```

Notes: `extrude_discrete_faces(bm, faces=)` extrudes per-face and *does* replace originals (manifold) `[-b t09]`.
`bevel(..., affect='VERTICES'|'EDGES')` — the old `vertex_only=` is gone `[docs]`. Return dicts: bevel → `faces/edges/verts`,
inset_region → `faces`, extrude_face_region → `geom`, subdivide_edges → `geom_inner/geom_split/geom`,
triangulate → `edges/faces/face_map/face_map_double` `[-b t03]`. After deletions call `bm.verts.ensure_lookup_table()`
before indexing. Edit-mode variant: `bm = bmesh.from_edit_mesh(me)` … `bmesh.update_edit_mesh(me)`.

---

## 5. Modifiers, transforms, origin, collections, naming

```python
mod = ob.modifiers.new("Bevel", 'BEVEL'); mod.width = 0.05; mod.segments = 2
select_only(ob); bpy.ops.object.modifier_apply(modifier="Bevel")   # works in -b [-b t03]; params: modifier, report, merge_customdata, single_user [docs]
# Non-operator alternative: evaluated copy (keeps the original object untouched)
dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
baked = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)   # or ev.to_mesh() + ev.to_mesh_clear()
```

Smooth-by-angle for export: `bpy.ops.object.shade_auto_smooth(angle=)` adds **one** NODES modifier named "Smooth by Angle"
(idempotent; a 2nd call only updates `mod.properties.inputs.Input_1.value`) `[-b t05]`. Normals therefore only reach
exporters with `export_apply=True` (glTF) / `use_mesh_modifiers=True` (FBX) / `apply_modifiers=True` (OBJ), or after
`modifier_apply`, which bakes it into the `sharp_edge` attribute `[-b t04]`. For asset pipelines prefer the data-level
`me.set_sharp_from_angle(angle); me.shade_smooth()` — no modifier, exports everywhere `[-b t01]`.

Geometry Nodes modifier values (5.2 API): `mod.properties.inputs.<identifier>.value / .type / .attribute_name`,
`mod.properties.outputs.<identifier>.attribute_name`; `getattr(mod.properties.inputs, ident)` for dynamic names.
Dict-style `mod["Socket_1"]` raises TypeError `[-b t04]`. Interface sockets: `ng.interface.new_socket("Scale", in_out='INPUT', socket_type='NodeSocketFloat').identifier` → `Socket_2` `[-b t02]`.

```python
from mathutils import Matrix, Vector
bpy.context.view_layer.update()
me.transform(ob.matrix_world); ob.matrix_world = Matrix.Identity(4)          # "apply all transforms" without ops [-b t03]
c = sum((v.co for v in me.vertices), Vector()) / len(me.vertices)           # origin to geometry centre
me.transform(Matrix.Translation(-c)); ob.location = ob.matrix_world @ c     # [-b t03]
col = bpy.data.collections.new("Assets"); bpy.context.scene.collection.children.link(col); col.objects.link(ob)
bpy.data.objects.remove(other, do_unlink=True)                               # also unlinks from all collections
ob.rename("Part", mode='ALWAYS')   # returns 'RENAMED_COLLISION_FORCED' and bumps the other ID to .001; mode='NEVER' → 'UNCHANGED_COLLISION' [-b t04]
```

Modifier type ids `[-b t02]`: `BEVEL, BOOLEAN, ARRAY, MIRROR, SOLIDIFY, SUBSURF, TRIANGULATE, WELD, DECIMATE, EDGE_SPLIT, WEIGHTED_NORMAL, NODES, DISPLACE, SHRINKWRAP, REMESH, UV_PROJECT, …`. Boolean: `mod.solver ∈ {'FLOAT','EXACT','MANIFOLD'}`.

---

## 6. Materials, image textures, image I/O

```python
mat = bpy.data.materials.new("PBR")              # node tree already present; do NOT touch mat.use_nodes (deprecated) [-b t02]
nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]; out = nt.nodes["Material Output"]
bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1.0)
bsdf.inputs["Roughness"].default_value = 0.5; bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Emission Strength"].default_value = 0.0          # 5.x default is 0.0, colour white [-b t03]
tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = albedo_img          # sRGB default
nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
rough = nt.nodes.new("ShaderNodeTexImage"); rough.image = rough_img
rough.image.colorspace_settings.name = 'Non-Color'            # data maps; 'Linear'/'Raw' no longer exist [-b t03]
nt.links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
nrm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(nrm.outputs["Normal"], bsdf.inputs["Normal"])
me.materials.append(mat)                                      # poly.material_index selects the slot
```

Full 5.2 Principled input list `[-b t01]`: Base Color, Metallic, Roughness, IOR, Alpha, Thin Wall, Normal, Weight, Diffuse Roughness,
Subsurface Weight/Radius/Scale/IOR/Anisotropy, Specular IOR Level, Specular Tint, Anisotropic, Anisotropic Rotation, Tangent,
Transmission Weight, Coat Weight/Roughness/IOR/Tint/Normal, Sheen Weight/Roughness/Tint, Emission Color, Emission Strength,
Thin Film Thickness, Thin Film IOR. Alpha blending: `mat.surface_render_method = 'BLENDED'`.

Images `[-b t03,t05]` — `Image.save(filepath='', quality=0, save_copy=False)` and `Image.save_render(filepath, scene=None, quality=0)` `[docs/RNA]`:

```python
import numpy as np, os
img = bpy.data.images.new("albedo", 1024, 1024, alpha=True, float_buffer=False)            # 8-bit sRGB
data = bpy.data.images.new("height", 1024, 1024, float_buffer=True, is_data=True)          # 32-bit float, colorspace 'Non-Color'
px = np.zeros(1024 * 1024 * 4, dtype=np.float32); px[3::4] = 1.0
img.pixels.foreach_set(px)      # BYTE buffer: pixels are the stored codes in colorspace_settings.name (sRGB-encoded for colour maps)
data.pixels.foreach_set(px)     # FLOAT buffer: pixels are scene-linear; save() encodes to the image colorspace [-b t10]
img.filepath_raw = os.path.join(out_dir, "albedo.png"); img.file_format = 'PNG'; img.save()        # 8-bit PNG
data.filepath_raw = os.path.join(out_dir, "height.exr"); data.file_format = 'OPEN_EXR'; data.save() # float EXR
data.file_format = 'PNG'; data.save(filepath=os.path.join(out_dir, "height16.png"))        # float buffer → 16-bit PNG automatically
# explicit depth via scene settings: scene.render.image_settings.file_format='PNG'; .color_depth='16'; data.save_render(path, scene=scene)
```

**Pixel encoding `[-b t10]`** — writing 0.2 everywhere: byte sRGB image → file code 0.2 (pixels *are* sRGB codes, no
conversion); float sRGB image → file code 0.485 (linear in, sRGB-encoded on save); byte `is_data` image → 0.2. So for
colour maps computed in linear space create them with `float_buffer=True` and write linear values; `save()` then writes an
encoded 16-bit PNG, or use `save_render(path, scene=sc)` with `color_depth='8'` for an 8-bit encoded PNG (code 0.486 measured).
Byte images are right only when you already hold display-encoded 8-bit data (e.g. loaded textures).

Measured facts: `Image.save()` on a float buffer writes **16-bit** PNG, on a byte buffer 8-bit; `save_render` follows
`scene.render.image_settings` (`color_depth ∈ '8','10','12','16','32'`, `color_mode`). **`save(filepath=)` obeys
`image.file_format`, not the extension** — `file_format='OPEN_EXR'` + `save(filepath="x.png")` wrote EXR bytes into `x.png`
`[-b t10]`. A Non-Color image saved under the AgX view transform (`save()` or `save_render()`) round-tripped at exactly
0.502 — no view transform was applied. **PNG does not store the colorspace**: reloaded data maps come back `'sRGB'` and
need `colorspace_settings.name = 'Non-Color'` again `[-b t05]`.
`image.file_format` enum: `AVIF, JPEG, OPEN_EXR, PNG, WEBP, BMP, CINEON, DPX, IRIS, JPEG2000, HDR, TARGA, TARGA_RAW, TIFF, OPEN_EXR_MULTILAYER, FFMPEG`.

Baking `[-b t05]` — Cycles only; the image node must be **active** in the material's node tree:

```python
scene.render.engine = 'CYCLES'; scene.cycles.samples = 16; scene.cycles.device = 'CPU'
tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bake_img; nt.nodes.active = tex
select_only(ob)
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=4, use_clear=True,
                    target='IMAGE_TEXTURES', save_mode='INTERNAL')   # then bake_img.save(); byte image → pixels are sRGB-encoded: (0.2,0.6,0.1) read back (0.475,0.784,0.341)
# other params [docs]: type='NORMAL'|'EMIT'|'AO'|'COMBINED'…, normal_space='TANGENT', use_selected_to_active, cage_extrusion, uv_layer
```

---

## 7. Headless rendering, camera, world, turntable

All three engines rendered a PNG in `-b` on macOS (Metal) `[-b t03]`:

```python
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'        # or 'CYCLES' / 'BLENDER_WORKBENCH'; 'BLENDER_EEVEE_NEXT' → TypeError
sc.eevee.taa_render_samples = 64          # EEVEE quality; sc.eevee.use_raytracing, use_shadows, use_fast_gi also exist
sc.cycles.samples = 128; sc.cycles.device = 'CPU'   # 'GPU' needs prefs.addons['cycles'].preferences devices (verify in -b)
sc.render.resolution_x = 1024; sc.render.resolution_y = 1024; sc.render.resolution_percentage = 100
sc.render.image_settings.media_type = 'IMAGE'; sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'; sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'   # default 'AgX'; also 'Filmic', 'Khronos PBR Neutral', 'Raw', 'False Color' [-b t02]
sc.render.filepath = "/abs/path/beauty.png"
bpy.ops.render.render(write_still=True)        # params: animation, write_still, use_viewport, layer, scene, frame_start, frame_end [docs]
```

Camera framing (`Object.camera_fit_coords(depsgraph, flat_xyz_list) -> (location, ortho_scale)` fits along the camera's
current view direction, so aim first) `[-b t03,t04]`:

```python
from mathutils import Vector
cam = bpy.data.objects["Camera"]; cam.location = (6, -6, 4)
cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()   # look-at origin
bpy.context.view_layer.update()
pts = [c for v in (ob.matrix_world @ Vector(b) for b in ob.bound_box) for c in v]
loc, scale = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), pts)
cam.location = loc                      # for ortho cameras also cam.data.ortho_scale = scale
sc.camera = cam
```

World / HDRI `[-b t03]`: `w = bpy.data.worlds.new("Studio"); sc.world = w` — tree already has `Background` + `World Output`;
`env = w.node_tree.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdr_path)`;
`w.node_tree.links.new(env.outputs["Color"], w.node_tree.nodes["Background"].inputs["Color"])`; strength on `inputs["Strength"]`.

Turntable (slotted actions — `action.fcurves` is gone; the `keyframe_new_interpolation_type` preference is **ignored** by
`keyframe_insert`, keys came out BEZIER) `[-b t04,t05]`:

```python
from bpy_extras import anim_utils
ob.rotation_euler = (0, 0, 0);            ob.keyframe_insert("rotation_euler", index=2, frame=1)
ob.rotation_euler = (0, 0, math.tau);     ob.keyframe_insert("rotation_euler", index=2, frame=97)
ad = ob.animation_data                    # ad.action_slot.identifier == 'OBCube', .name_display == 'Cube'
cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)   # or ad.action.layers[0].strips[0].channelbag(slot)
for fc in cb.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
sc.frame_start, sc.frame_end = 1, 96; sc.render.filepath = "/abs/path/turn_"   # frame number appended
bpy.ops.render.render(animation=True)
```

---

## 8. Export / import

All parameter names below are `[docs]` for glTF/FBX (full signatures in bundled RST) and RNA-introspected + executed for
USD/OBJ/STL (not in the bundled `bpy.ops.wm` page) `[-b t02,t03]`. Every call wrote a file in `-b`.

```python
select_only(ob)   # use_selection / export_selected_objects / selected_objects_only all read the selection
bpy.ops.export_scene.gltf(filepath=p + ".glb", export_format='GLB',        # or 'GLTF_SEPARATE' (writes .gltf/.bin/textures/)
    use_selection=True, export_apply=True, export_yup=True, export_texcoords=True, export_normals=True,
    export_tangents=False, export_materials='EXPORT',                     # 'PLACEHOLDER' | 'VIEWPORT' | 'NONE'
    export_image_format='AUTO',                                           # 'JPEG' | 'WEBP' | 'NONE'
    export_draco_mesh_compression_enable=False, export_animations=False, export_skins=False, export_morph=False)
bpy.ops.export_scene.fbx(filepath=p + ".fbx", use_selection=True, object_types={'MESH', 'ARMATURE', 'EMPTY'},
    apply_scale_options='FBX_SCALE_ALL',                                  # FBX_SCALE_NONE | FBX_SCALE_UNITS | FBX_SCALE_CUSTOM | FBX_SCALE_ALL
    axis_forward='-Z', axis_up='Y', bake_space_transform=True,            # FBX uses '-Z' spelling
    use_mesh_modifiers=True, mesh_smooth_type='FACE',                     # 'OFF' (normals only) | 'FACE' | 'EDGE' | 'SMOOTH_GROUP'
    use_tspace=False, use_triangles=False, path_mode='COPY', embed_textures=True, add_leaf_bones=False, bake_anim=False)
bpy.ops.wm.obj_export(filepath=p + ".obj", export_selected_objects=True, apply_modifiers=True, export_uv=True,
    export_normals=True, export_materials=True, export_pbr_extensions=False, export_triangulated_mesh=False,
    forward_axis='NEGATIVE_Z', up_axis='Y', global_scale=1.0, path_mode='COPY', apply_transform=True)   # OBJ uses 'NEGATIVE_Z'
bpy.ops.wm.usd_export(filepath=p + ".usdc", selected_objects_only=True, export_materials=True,
    export_textures_mode='NEW',                                           # 'KEEP' | 'PRESERVE' | 'NEW'; old export_textures= → TypeError
    generate_preview_surface=True, export_uvmaps=True, export_normals=True, evaluation_mode='RENDER',
    convert_orientation=False, export_global_forward_selection='NEGATIVE_Z', export_global_up_selection='Y',
    meters_per_unit=1.0, triangulate_meshes=False, relative_paths=True)   # .usdz also supported
bpy.ops.wm.stl_export(filepath=p + ".stl", export_selected_objects=True, apply_modifiers=True)
```

Axis spelling differs per exporter: FBX `'-Z'`, OBJ/USD `'NEGATIVE_Z'` `[-b t03]`. FBX `embed_textures` only works with
`path_mode='COPY'` `[docs]`. glTF `export_apply` prevents shape-key export `[docs]`. Importers: `bpy.ops.wm.fbx_import` (default,
ufbx), `bpy.ops.import_scene.fbx` (legacy), `bpy.ops.import_scene.gltf` and `bpy.ops.wm.gltf_import` both exist, `wm.obj_import`,
`wm.usd_import` (`import_subdivision`, `property_import_mode` renamed in 5.0) `[-b t06,t02]`. 5.2 glTF adds point-cloud,
meshopt (`EXT/KHR_meshopt_compression`), iridescence/dispersion `[notes 5.2 io]`. `bpy.ops.wm.save_as_mainfile(filepath=, compress=True)` saves the .blend.

---

## 9. Measuring and QA

```python
import bmesh
from mathutils import Vector
def measure(ob):
    me = ob.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)       # == len(me.loop_triangles) after calc_loop_triangles() [-b t03]
    dims = tuple(ob.dimensions)                                 # world-scale AABB size; ob.bound_box = 8 local corners
    world_bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    bm = bmesh.new(); bm.from_mesh(me)
    non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
    non_manifold_verts = [v for v in bm.verts if not v.is_manifold]
    loose_verts = [v for v in bm.verts if not v.link_edges]
    loose_edges = [e for e in bm.edges if not e.link_faces]
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    bm.free()
    return dict(tris=tris, dims=dims, nm_edges=len(non_manifold_edges), nm_verts=len(non_manifold_verts),
                loose_v=len(loose_verts), loose_e=len(loose_edges), ngons=ngons,
                uv_layers=[u.name for u in me.uv_layers], materials=[m.name for m in me.materials if m])
```

Verified on the default cube: `tris=12`, `dims=(2,2,2)`, zero non-manifold/loose `[-b t03]`. UV bounds: iterate
`me.uv_layers.active.uv[i].vector` and check `0 <= u,v <= 1`. `me.validate(verbose=True)` returns True **only if it fixed
something** (dropped an out-of-range face in `[-b t06]`) — call it after any `from_pydata` with untrusted indices.

---

## 10. Extensions / add-on packaging

Since 4.2 add-ons are *extensions*: a folder with `blender_manifest.toml` (`id`, `version`, `name`, `tagline`, `maintainer`,
`type = "add-on"`, `blender_version_min`, `license`, optional `wheels`) built with `blender --command extension build`
(manual: *Advanced › Extensions › Getting Started*) `[docs manual]`. Legacy `bl_info` modules still load per 4.2 notes
`(verify on 5.2)`. Ops: `bpy.ops.extensions.package_install_files`, `bpy.ops.preferences.addon_enable(module=)` still exists
`[-b t04]`. For a `-b --python` skill none of this is needed: plain scripts + `bpy.utils.register_class` suffice.

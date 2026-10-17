# Blender 5.x Python: the patterns that work and the changes that bite

Distilled from `research/blender-5-python-api.md`, where every snippet is tagged with the test script
that ran it on Blender 5.2.2 LTS in background mode. When unsure about an argument, ask the bundled
docs through the MCP (`get_python_api_docs("bpy.ops.uv.pack_islands")`) instead of recalling 3.x.

## Breaking changes you will hit (3.x / 4.x habits)

| You remember | In 5.2 |
|---|---|
| `mesh.use_auto_smooth`, `auto_smooth_angle` | Gone (4.1). Data level: `mesh.set_sharp_from_angle(angle=rad)` then `mesh.shade_smooth()`. Or `bpy.ops.object.shade_auto_smooth(angle=)` which adds a "Smooth by Angle" nodes modifier (pinned last). |
| `mesh.calc_normals_split()` | Gone. Read `mesh.corner_normals[i].vector`; write `normals_split_custom_set(...)`. |
| `edge.crease`, `edge.bevel_weight` | Attributes: `mesh.attributes["crease_edge"]`, `"bevel_weight_edge"`, `"sharp_edge"`, `"sharp_face"`. |
| Principled `Specular`, `Emission`, `Subsurface`, `Transmission` | `Specular IOR Level`, `Emission Color` + `Emission Strength` (default 0.0), `Subsurface Weight`, `Transmission Weight`, `Coat Weight`, `Sheen Weight`. |
| `mat.use_nodes = True` | Deprecated (gone in 6.0); new materials and worlds already have a node tree. |
| `mat.blend_method`, `shadow_method` | `mat.surface_render_method = 'DITHERED' \| 'BLENDED'`. |
| `'BLENDER_EEVEE_NEXT'` | Engines are `BLENDER_EEVEE`, `BLENDER_WORKBENCH`, `CYCLES`. `scene.eevee.use_gtao/bloom/ssr` gone. |
| Colorspaces `'Linear'`, `'Raw'` | `'Linear Rec.709'`, `'Non-Color'`. Default view transform is AgX. |
| `bpy.ops.x(override_dict)` | `with bpy.context.temp_override(window=, area=, region=): ...` |
| `action.fcurves` | Slotted actions (5.0): `bpy_extras.anim_utils.action_get_channelbag_for_slot(action, slot).fcurves`. |
| `mod["Socket_1"] = v` on a nodes modifier | `mod.properties.inputs.Socket_1.value` (5.2). |
| `tree.inputs.new()` | `tree.interface.new_socket(name, in_out='INPUT', socket_type='NodeSocketFloat')`. |
| `scene.node_tree` | `scene.compositing_node_group`. |
| Boolean solver `'FAST'` | `'FLOAT'`; also `'EXACT'` (default), `'MANIFOLD'`. |
| `bpy.ops.export_scene.obj` | `bpy.ops.wm.obj_export` (also `wm.ply_export`, `wm.stl_export`, `wm.usd_export`); axes spelled `'NEGATIVE_Z'` there, `'-Z'` in FBX. |
| glTF `'GLTF_EMBEDDED'` | Only `'GLB'` and `'GLTF_SEPARATE'`; always pass `export_format` explicitly. |
| USD `export_textures=True` | `export_textures_mode='NEW'`. |
| `image_settings.file_format = 'FFMPEG'` | Set `image_settings.media_type = 'VIDEO'` first. |
| `gpu.*` in background | Call `gpu.init()` first (5.2). |
| `bmesh.ops.bevel(vertex_only=)` | `affect='EDGES' \| 'VERTICES'`. |

## Background mode (`blender -b`)

- There is a window and a VIEW_3D area in the factory startup, so UV operators, `modifier_apply`,
  `origin_set`, `transform_apply`, `object.bake`, `render.render` and every exporter run with **no**
  override. Only view-centric operators (`view3d.view_selected`, `snap_cursor_to_selected`) need
  `temp_override(window=win, area=view3d_area, region=window_region)`.
- Selection and active object are explicit state; set both before an operator and set the mode:

```python
def select_only(obj):
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
```

- `obj.matrix_world` is stale after you set `obj.location` until `bpy.context.view_layer.update()`.
- Evaluated (modifiers applied) data without operators:
  `dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)`.
- All three engines render headless on macOS and Linux; Cycles uses the CPU unless GPU devices are
  configured in preferences.

## Building meshes

```python
me = bpy.data.meshes.new("SM_Part"); me.from_pydata(verts, [], faces)
if me.validate(verbose=True): print("validate fixed something: check the generator")
me.update(calc_edges=True)
me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(30))
ob = bpy.data.objects.new("SM_Part", me); collection.objects.link(ob)
```

bmesh chain gotchas: `extrude_face_region` leaves the original faces behind when given faces only
(delete them with `bmesh.ops.delete(bm, geom=faces, context='FACES')` or use
`extrude_discrete_faces`); call `ensure_lookup_table()` after deletions before indexing; face
selection by normal needs a tight threshold (`> 0.99`) or bevel faces sneak in; finish with
`remove_doubles`, `recalc_face_normals`, `to_mesh`, `free`.

Apply transforms without operators: `me.transform(ob.matrix_world); ob.matrix_world = Matrix.Identity(4)`.
Origin to bottom-centre: translate vertices by `-(cx, cy, zmin)` and set `ob.location = (0,0,0)`.

## Materials and images

- `mesh.materials.clear()` resets every face's `material_index` to 0; reassign indices after re-appending slots.
- Colour sockets are scene-linear. A hex or sRGB colour must be converted before
  `default_value`: `linear = ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92`.
- Data images: `bpy.data.images.new(name, w, h, float_buffer=True, is_data=True)` for normal and
  height (saves 16-bit PNG), `is_data=True` byte images for roughness, metallic, AO. PNG does not
  store the colourspace: set `colorspace_settings.name = 'Non-Color'` again after loading.
- `Image.save()` never applies the view transform; `save_render()` does for colour images. Set
  `filepath_raw` and `file_format` first; `save(filepath=)` obeys `file_format`, not the extension.
- Byte image `pixels` are the stored codes (sRGB for colour), float image `pixels` are linear.
- Baking (Cycles only): the target Image Texture node must be `select = True` and `nodes.active` in
  every material of the baked object; defaults of `bpy.ops.object.bake` differ from the scene's
  (`margin_type='EXTEND'`, `use_clear=False`), so pass arguments explicitly. Metallic, alpha and
  height have no bake pass: route them into Emission and bake `EMIT` (what `bake_textures.py` does).

## Rendering and cameras

```python
sc.render.engine = "BLENDER_EEVEE"; sc.eevee.taa_render_samples = 64
sc.view_settings.view_transform = "Khronos PBR Neutral"   # or "Standard", "AgX"
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
loc, ortho_scale = cam.camera_fit_coords(dg, flat_list_of_world_points)   # fits along the current view direction
bpy.ops.render.render(write_still=True)
```

Turntable keyframes come out BEZIER regardless of preferences; set `kp.interpolation = 'LINEAR'` on
the channelbag's fcurves. `render_review.py` sidesteps animation by rendering camera positions.

## Export (parameter names confirmed)

FBX: `apply_scale_options`, `axis_forward='-Z'`, `axis_up='Y'`, `bake_space_transform`,
`use_mesh_modifiers`, `mesh_smooth_type='OFF'`, `use_tspace`, `path_mode='COPY'`, `embed_textures`
(COPY only), `add_leaf_bones=False`, `bake_anim=False`.
glTF: `export_format`, `use_selection`, `export_apply`, `export_yup`, `export_texcoords`,
`export_normals`, `export_tangents`, `export_materials`, `export_image_format`,
`export_draco_mesh_compression_enable`, `export_animations=False`.
OBJ: `export_selected_objects`, `apply_modifiers`, `export_uv`, `export_normals`, `export_materials`,
`export_pbr_extensions`, `forward_axis='NEGATIVE_Z'`, `up_axis='Y'`, `path_mode`.
USD: `selected_objects_only`, `export_materials`, `export_textures_mode`, `evaluation_mode='RENDER'`,
`convert_orientation`, `meters_per_unit`.
`scripts/blender/export_asset.py` wraps these as presets; `references/export-targets.md` explains the
per-engine choices.

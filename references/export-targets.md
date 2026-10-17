# Export targets: what each engine expects and how the presets deliver it

Distilled from `research/export-targets.md` (Unity, Epic, Godot, Roblox, Khronos, three.js and Blender
5.2 docs; sources there). `scripts/blender/export_asset.py` encodes the settings as presets and verifies
the result (GLB header parse, FBX re-import with the 5.x importer).

## Blender 5.2 baseline

- FBX export is still the Python add-on (`bpy.ops.export_scene.fbx`, binary FBX 7400); FBX import is
  the C++ `bpy.ops.wm.fbx_import`. Collada is gone. glTF 5.2 adds meshopt compression.
- glTF defaults that bite: `export_apply=False` (modifiers not applied), `export_tangents=False`,
  `export_extras=False`. The presets set `export_apply=True`, extras on, tangents when a normal map
  exists.
- Source files stay quads; exporters triangulate (`use_triangles`, glTF always, USD `triangulate_meshes`,
  OBJ `export_triangulated_mesh`).

## Per target

| Target | Preset | Units / axes | Settings that matter | Importer side |
|---|---|---|---|---|
| **Godot 4, three.js, Babylon, viewers** | `glb` | metres, Y-up, front +Z = Blender −Y | `export_yup=True`, `export_apply=True`, extras on | Zero rotation needed. Godot reads name suffixes `-col`, `-convcol`, `-colonly`, `-navmesh`, `-occ`, `-rigid`, `-noimp`; animations named `*loop*` loop. Godot and three.js expect OpenGL normals. |
| **Unity 6** | `fbx_unity` | 1 unit = 1 m, Y-up, +Z forward | `FBX_SCALE_NONE` (importer shows 0.01 + convert units, size is 1:1), `mesh_smooth_type='OFF'`, no tangents (Unity computes MikkTSpace), `bake_space_transform=True` for static meshes (off automatically with armatures) | Or leave the −89.98° X fix to the importer's "Bake Axis Conversion". `_LOD0…_LOD7` suffixes build a LOD Group. FBX materials carry diffuse/emissive/bump only: assign metallic/roughness textures in Unity, or ship the GLB for glTFast. OpenGL normals. |
| **Unreal 5** | `fbx_unreal` | 1 UU = 1 cm, Z-up, +X forward | `FBX_SCALE_NONE` (1 m → 100 cm), `mesh_smooth_type='FACE'`, triangles, tangents, no space-transform bake (Convert Scene handles Y-up) | One FBX per prop: collision `UCX_<Mesh>_00` (`UBX_`, `USP_`, `UCP_`) and `SOCKET_<Mesh>_00` import only for the first mesh in a file. Pivot at world origin. Model facing −Y lands on −Y: tick "Force Front XAxis" or build facing +X. LODs: import per level in the Static Mesh editor (Blender cannot write an FBX LodGroup). Normal maps DirectX: "Flip Green Channel" or bake with `normal_g='NEG_Y'`. Only Color and Normal auto-connect in materials. |
| **Roblox Studio** | `fbx_roblox` (or `glb`) | studs, 1 stud = 0.28 m | `FBX_SCALE_UNITS`, textures copied and embedded, no leaf bones, no animation | Importer "Scale unit" re-interprets; "Merge Meshes" off to keep parts; "Use Imported Pivot" on. 20 000 tris per mesh, one UV set in 0–1, one material per MeshPart, OpenGL normals, separate 8-bit roughness/metalness maps, textures 1024 for a 20x20-stud object. glTF needs no scale configuration. |
| **Web delivery, Sketchfab, Fab** | `glb` (+ source) | metres, Y-up | Draco (`--draco`) or meshopt for size; textures PNG/JPEG/WebP | Khronos 3D Commerce targets: web catalogue 3 MB / 150k tris / 2K textures; banner 500 KB / 30k / 512. Post-process with `gltf-transform optimize` or `gltfpack` when installed. |
| **Offline render, other DCC** | `usd` / `usdz` | `metersPerUnit=1`, Y-up with Convert Orientation | `export_textures_mode='NEW'`, Preview Surface from Principled | USDZ cannot hold UDIMs; opacity needs a threshold node; OpenGL normals. |
| **Generic** | `fbx`, `obj`, `stl` | Blender defaults | | OBJ carries only basic materials (+PBR extensions when `export_pbr_extensions`). |

## Cross-cutting rules

- Apply rotation and scale, origin where the target expects the pivot (bottom-centre for props; Unreal
  wants the object at world origin), front facing −Y in Blender for Unity, Godot, web and Roblox.
- Hierarchy: empties export as FBX nulls / glTF nodes; Unity keeps them, Unreal ignores them except
  `SOCKET_`, Godot keeps `Node3D` placeholders, Roblox makes a Model with children.
- Textures: inside the GLB; next to the FBX for Unity and Unreal (`path_mode='COPY'`); embedded for
  Roblox. Normal green channel: OpenGL everywhere except Unreal.
- Per-asset batch: `use_selection` with the asset's objects (what the script does); FBX
  `batch_mode='COLLECTION'` writes one file per collection if ever needed.

## Verification (what `export_asset.export(verify=True)` does and what to add by hand)

1. GLB: parse the header, compare the POSITION accessor bounds (converted back to Z-up) with the
   scene's bounding box, count primitives, materials, images, triangles.
2. FBX: re-import with the 5.x importer into a throwaway scene; dimensions in metres must match the
   source, root rotation `(0, 0, 0)`, root scale 1.
3. By hand when available: `npx @gltf-transform/cli validate out.glb` and `inspect` (materials, texture
   packing); the Khronos web validator; a test import in the real engine project with a clean log.
4. Record the numbers in the README (counts, dimensions, formats, normal convention).

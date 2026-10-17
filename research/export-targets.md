# Export conventions and settings per target (Blender 5.2 → engines/web/USD)

Researched 2026-10-17 against primary docs. Numbers and option names are quoted from the sources listed at the end of each section; anything not confirmed by a primary source is marked `(verify)`.

## Contents
1. Blender 5.2 exporter baseline (what the add-ons actually do)
2. Unity (6.x)
3. Unreal Engine 5
4. Godot 4
5. Roblox Studio
6. three.js / web (glTF)
7. Sketchfab / Fab
8. USD for offline render / other DCC
9. Cross-target comparison
10. Verification after export

---

## 1. Blender 5.2 exporter baseline

| Fact | Detail |
|---|---|
| FBX **import** | New C++ importer `bpy.ops.wm.fbx_import` (`WM_OT_fbx_import`), default since 5.0 ("added in 4.5 as experimental"); legacy Python importer remains as `bpy.ops.import_scene.fbx`. Manual page `files/import_export/fbx.html` documents import only and says "To export FBX files use the FBX Add-on". |
| FBX **export** | Still the Python add-on `bpy.ops.export_scene.fbx` (`scripts/addons_core/io_scene_fbx`). Writes binary FBX `FBX_VERSION = 7400` (FBX 2014/2015 file version); no ASCII. Manual page is now `files/import_export/fbx_legacy.html`. |
| Collada | `.dae` import and export removed in 5.0. |
| glTF | `bpy.ops.export_scene.gltf`, add-on version 5.2.41. 5.2 adds `export_meshopt_compression_enable` (default False) + `export_meshopt_extension` ∈ {`EXT_meshopt_compression`, `KHR_meshopt_compression`}, point-cloud I/O, `KHR_materials_iridescence`/`_dispersion` export. |
| USD | `bpy.ops.wm.usd_export` (C++). 5.2: colour-space aware, new export option controlling save frequency (lower peak memory), NURBS surfaces exported as mesh. |
| OBJ | `bpy.ops.wm.obj_export` (C++). 5.0 added export "Apply Transform" and importer "Material Name Collision". |

**FBX exporter defaults (API):** `global_scale=1.0`, `apply_unit_scale=True`, `apply_scale_options='FBX_SCALE_NONE'` (UI "All Local"), `use_space_transform=True`, `bake_space_transform=False` (UI "Apply Transform" — API text: "WARNING! experimental option, use at own risk, known to be broken with armatures/animations"), `axis_forward='-Z'`, `axis_up='Y'`, `use_mesh_modifiers=True` ("prevents exporting shape keys"), `mesh_smooth_type='OFF'` (= "Normals Only"; others `'FACE'`, `'EDGE'`, `'SMOOTH_GROUP'`), `colors_type='SRGB'`, `use_tspace=False` ("will only work correctly with tris/quads only meshes!"), `use_triangles=False`, `use_custom_props=False`, `add_leaf_bones=True`, `primary_bone_axis='Y'`, `secondary_bone_axis='X'`, `use_armature_deform_only=False`, `armature_nodetype='NULL'`, `bake_anim=True`, `bake_anim_use_all_bones=True` ("needed with some target applications, like UE4"), `bake_anim_use_nla_strips=True`, `bake_anim_use_all_actions=True`, `bake_anim_force_startend_keying=True`, `bake_anim_step=1.0`, `bake_anim_simplify_factor=1.0`, `path_mode='AUTO'`, `embed_textures=False` ("only for Copy path mode!").
`apply_scale_options`: `FBX_SCALE_NONE` = scale baked into each object transform, FBX scale stays 1.0; `FBX_SCALE_UNITS` = units scaling written to the FBX scale (importers that read FBX units get it right); `FBX_SCALE_CUSTOM`; `FBX_SCALE_ALL`. Manual mismatch to know about: the 5.2 "FBX (Legacy)" page still says "Scale … 10 is the default" and describes Apply Transform with the OBJ wording; the API text above is authoritative.

**glTF exporter defaults (API/source):** `export_format='GLB'`, `export_yup=True`, `export_apply=False` (Apply Modifiers OFF by default — turn it on), `export_image_format='AUTO'` (PNG stays PNG, JPEG stays JPEG, WebP stays WebP, others → PNG; alternatives `'JPEG'`, `'WEBP'`, `'NONE'`), `export_jpeg_quality=75`, `export_image_quality=75`, `export_texcoords=True`, `export_normals=True`, `export_tangents=False`, `export_materials='EXPORT'` (`'PLACEHOLDER'` keeps slots without textures, `'VIEWPORT'`, `'NONE'` merges primitives), `export_vertex_color='MATERIAL'`, `export_extras=False` (custom properties → glTF `extras`), `export_cameras=False`, `export_lights=False` (`KHR_lights_punctual`), `export_animations=True`, `export_animation_mode='ACTIONS'`, `export_frame_step=1`, `export_force_sampling=True`, `export_skins=True`, `export_influence_nb=4`, `export_def_bones=False`, `export_morph=True`, `export_import_convert_lighting_mode='SPEC'`, Draco: `export_draco_mesh_compression_enable=False`, `_level=6`, `_position_quantization=14`, `_normal_quantization=10`, `_texcoord_quantization=12`, `_color_quantization=10`, `_generic_quantization=12`. gltfpack bridge: `export_use_gltfpack=False`, `export_gltfpack_tc=True` (KTX2/BasisU), `_tq=8`, `_si=1.0`, `_sa=False`, `_slb=False`, `_vp=14`, `_vt=12`, `_vn=8`, `_vc=8`, `_noq=True`, `_kn=False`.
Material handoff rules the exporter reads: Base Color / Metallic / Roughness / Normal (via a **Normal Map** node, Tangent Space only) / Emission / Alpha from **Principled BSDF**; an ORM-style texture is copied verbatim only if wired through **Separate RGB** with G→Roughness, B→Metallic; occlusion only via the `glTF Material Output` node group's `Occlusion` input (occlusion lives in R). Images must be PNG/JPEG (others converted). Bake normals with "space: Tangent, R:+X, G:+Y, B:+Z". Mapping node → `KHR_texture_transform`; emissive > 1 → `KHR_materials_emissive_strength`. UDIM is split automatically. Export-supported extensions: `KHR_draco_mesh_compression`, `KHR_lights_punctual`, `KHR_materials_{clearcoat,transmission,unlit,emissive_strength,volume,sheen,specular,anisotropy,dispersion,ior,variants}`, `KHR_texture_transform`, `EXT_mesh_gpu_instancing`, `EXT_meshopt_compression`, `KHR_meshopt_compression`.

Sources: https://developer.blender.org/docs/release_notes/5.0/pipeline_io/ · https://developer.blender.org/docs/release_notes/5.1/pipeline_io/ · https://developer.blender.org/docs/release_notes/5.2/pipeline_io/ · https://docs.blender.org/manual/en/5.2/files/import_export/fbx.html · https://docs.blender.org/manual/en/5.2/files/import_export/fbx_legacy.html · https://docs.blender.org/manual/en/5.2/addons/scene_gltf2.html · https://projects.blender.org/blender/blender/src/branch/blender-v5.2-release/scripts/addons_core/io_scene_fbx/fbx_utils.py · https://projects.blender.org/blender/blender/src/branch/blender-v5.2-release/scripts/addons_core/io_scene_gltf2/__init__.py · Blender Python API `bpy.ops.export_scene.fbx` / `bpy.ops.export_scene.gltf` (bundled 5.2 docs)

---

## 2. Unity (6.x)

| Setting | Value |
|---|---|
| Format | FBX ("Unity uses the .fbx file format as its internal importing chain… use .fbx wherever possible"). `.blend` works only with Blender installed: Unity "launches Blender in the background" and runs the FBX exporter. glTF needs the `com.unity.cloud.gltfast` package. |
| Units / axes | 1 unit = 1 m ("Unity's physics expects 1 meter = 1 unit"), Y-up, left-handed, +Z forward. Importer: **Convert Units** (file units → Unity), **Scale Factor**. |
| Blender FBX export | `axis_forward='-Z'`, `axis_up='Y'` (defaults), `apply_unit_scale=True`, `apply_scale_options='FBX_SCALE_NONE'` (or `'FBX_SCALE_ALL'` to get importer Scale Factor 1 instead of 0.01 `(verify)`), `use_space_transform=True`, `bake_space_transform=False`, `mesh_smooth_type='OFF'` with importer Normals=Import (or `'FACE'` if you let Unity calculate), `use_tspace=False` (importer Tangents = Calculate Mikktspace), `use_triangles=False` (Unity triangulates; Keep Quads option exists), `add_leaf_bones=False`, `path_mode='COPY'` + `embed_textures=False` (ship textures next to the FBX; Unity does not auto-assign Blender textures). |
| Rotation gotcha | Blender FBX roots import with X rotation −89.98°. Fix on the Unity side: Model tab → **Bake Axis Conversion** (2020.1+; "embeds axis conversion directly into asset data rather than compensating… via the root GameObject's Transform"). Blender-side alternative `bake_space_transform=True` is experimental and breaks armatures/animations. A Blender model facing −Y imports facing Unity +Z `(verify empirically with one test cube)`. |
| Naming read by importer | `<MeshName>_LOD0`, `_LOD1` … (up to 8 levels) → auto **LOD Group** component on import. No texture-suffix detection; Unity assigns texture type by Texture Importer settings. |
| Materials | FBX gives Unity diffuse colour/texture, emissive, bump factor, transparency only — no roughness/metallic. Material Creation Mode: None / Standard (Legacy) / **Import via MaterialDescription**; Location: **Use Embedded Materials** (default since 2017.2) or extract. Normal maps: +Y (OpenGL) convention `(community consensus)`. |
| glTF via glTFast | Imports `KHR_draco_mesh_compression`, `KHR_texture_basisu` (KTX2), `KHR_texture_transform`, `KHR_lights_punctual`, `KHR_mesh_quantization`, `EXT_meshopt_compression`, `EXT_mesh_gpu_instancing`; images PNG/JPEG/KTX2 (no WebP). |
| Other importer defaults | Weld Vertices on, Index Format 16-bit, Optimize Mesh Everything, Normals Mode area-and-angle weighted, Strict Vertex Data Checks on. |

Sources: https://docs.unity3d.com/Manual/3D-formats.html · https://docs.unity3d.com/2017.4/Documentation/Manual/HOWTO-ImportObjectBlender.html · https://docs.unity3d.com/Manual/FBXImporter-Model.html · https://docs.unity3d.com/Manual/FBXImporter-Materials.html · https://docs.unity3d.com/Manual/lod-group-configure.html · https://discussions.unity.com/t/bake-axis-conversion-import-setting/792937 · https://docs.unity3d.com/Packages/com.unity.cloud.gltfast@6.20/manual/features.html · https://www.strayspark.studio/blog/directx-vs-opengl-normal-maps-explained

---

## 3. Unreal Engine 5

| Setting | Value |
|---|---|
| Format | FBX ("import pipeline uses FBX 2020.2… Using a different version during export may result in incompatibilities"); Blender writes file version 7400, which UE imports in practice `(verify per UE build)`. glTF/USD also import (Interchange). Whether Interchange is the default FBX path in your UE 5.x build `(verify)`. |
| Units / axes | 1 UU = 1 cm ("Convert Scene Unit… UE's unit of measure, centimeters"), Z-up, left-handed, +X forward. Import options **Convert Scene**, **Force Front XAxis** ("front X axis instead of -Y axis"), **Convert Scene Unit**, Import Uniform Scale; defaults `(verify: typically Convert Scene on, others off)`. |
| Blender FBX export | `axis_forward='-Z'`, `axis_up='Y'`, `apply_unit_scale=True`, `apply_scale_options='FBX_SCALE_NONE'` (1 m → 100 cm), `mesh_smooth_type='FACE'` or `'SMOOTH_GROUP'` (UE expects smoothing groups when it computes normals) or `'OFF'` + UE Normal Import Method = Import Normals (and Tangents, with `use_tspace=True`, triangles/quads only), `use_triangles=True` ("Meshes in Unreal Engine must be triangulated"), `add_leaf_bones=False`, `primary_bone_axis='Y'`, `secondary_bone_axis='X'`, `bake_anim_use_all_bones=True`, `use_armature_deform_only=True`, `path_mode='COPY'`, `embed_textures=False` (import textures separately with Import Textures). Put the render mesh pivot at world origin ("pivot point… always located at the origin (0,0,0) when exporting"). |
| Rotation gotcha | Two primary facts: UE forward is +X; `Force Front XAxis` maps the FBX front to +X instead of −Y. Resulting mapping of a Blender −Y-facing model (default export, Convert Scene) `(verify with a test mesh)`: faces UE −Y; tick Force Front XAxis or model facing +X in Blender to land on +X. |
| Naming read by importer | Collision: `UBX_<RenderMeshName>_##` box (regular box, no moved verts), `UCP_` capsule, `USP_` sphere ("8 segments is a good number"), `UCX_` convex ("any completely closed convex 3D shape"). "When importing multiple meshes with custom collision in a single file, only the first mesh's collision will be imported" → one FBX per static mesh. Sockets: `SOCKET_<RenderMeshName>_##`, single-mesh FBX only. LODs: FBX **LodGroup** node + **Import Mesh LODs** (Mesh ▸ Advanced); Blender cannot author a LodGroup, so either import LOD1+ via Static Mesh Editor LOD Settings, or use Epic's Send to Unreal add-on, which strips `_LOD\d` suffixes by regex (`pCube1_LOD0` → `pCube1`) and imports per-LOD. `SM_`, `SK_`, `M_`, `MI_`, `T_`, `PHYS_`, `AS_`, `BP_`, `SKEL_`, `LS_`, `FXE_`, `FXS_` are Epic's *recommended* prefixes (`[AssetTypePrefix]_[AssetName]_[Descriptor]_[Variant]`); the engine does not read them. Allar's community guide uses `S_` for static mesh and texture suffixes `_D _N _R _A _O _B _E _M _S`, packed = combined letters (e.g. `_ERO`); it has no `_ORM` entry. |
| Materials/textures | FBX import: "only Color and Normal will automatically be connected; Specular maps will be imported but not connected". Material Import Method: Create New Materials / Create New Instanced Materials / Do Not Create Material; Base Material Name; Reorder Material To FBX Order. Texture pipeline: `detect_normal_map_texture` (content-based test, sets sRGB off + Normalmap compression) and `flip_normal_map_green_channel`; UE expects −Y (DirectX) normals `(community consensus)` → flip G of Blender bakes (or bake with −Y). Texture suffixes are not read by the importer. |
| Mesh options | Generate Lightmap UVs, One Convex Hull per UCX, Combine Meshes, Transform Vertex to Absolute, Bake Pivot in Vertex (experimental), Build Nanite, Remove Degenerates, Normal Generation Method Built In/MikkTSpace, Compute Weighted Normals, Vertex Color Import Option (no special setup), multiple UV sets supported. |

Sources: https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine · https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-import-options-reference-in-unreal-engine · https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-static-mesh-lods-using-fbx-in-unreal-engine · https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxAssetImportData · https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData · https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeGenericTexturePipeline · https://dev.epicgames.com/documentation/en-us/unreal-engine/recommended-asset-naming-conventions-in-unreal-engine-projects · https://epicgames.github.io/BlenderTools/send2ue/asset-types/static-mesh.html · https://github.com/Allar/ue5-style-guide

---

## 4. Godot 4

| Setting | Value |
|---|---|
| Format | glTF 2.0 "(recommended)": `.glb` (embedded textures, smaller) or `.gltf` (text, VCS-friendly). `.blend` direct import: Godot calls Blender's glTF exporter (Blender 3.0+, 3.5+ recommended; Editor Settings ▸ Filesystem ▸ Import ▸ Blender ▸ Blender Path; everyone on the team needs Blender; not on Android/web editors). FBX via built-in `ufbx` (4.3+; earlier FBX2glTF). OBJ: no skinning/animation/UV2/PBR. |
| Units / axes | "1 unit being equal to 1 meter", right-handed, Y-up, camera forward −Z; **asset front is +Z** ("In Blender, this means that +Y is rear and -Y is front") — so a Blender model facing −Y with `export_yup=True` imports correctly with **zero rotation**. Use `look_at(..., use_model_front=true)` / `Vector3.MODEL_*` in code. |
| Blender glTF export | `export_format='GLB'`, `export_yup=True`, `export_apply=True`, `export_extras=True` (for import hints via custom properties), `export_tangents=False` (Godot "Ensure Tangents" generates Mikktspace), `export_animation_mode='ACTIONS'`, `export_influence_nb=4` (viewers expect 4 or 8), `export_def_bones=True`. Godot docs: triangulate before export (Triangulate modifier + Apply Modifiers), apply object transforms, export in rest pose, design lighting in Godot. |
| Naming read by importer (suffixes; separators `-`, `$`, `_`; case-insensitive) | `-noimp` remove node/animation · `-col` static trimesh collision child (Mesh only) · `-convcol` ConvexPolygonShape3D · `-colonly` remove mesh, keep StaticBody3D · `-convcolonly` convex decomposition · `-navmesh` NavigationMesh · `-occ` / `-occonly` Occluder3D · `-rigid` RigidBody3D · `-vehicle` / `-wheel` VehicleBody3D / VehicleWheel3D · animations whose name **starts or ends** with `loop` or `cycle` → loop flag (Blender: name the Action, e.g. `Walk-loop`, use NLA) · `-alpha`, `-vcol` material hints `(verify)`. Pitfall: Blender's `.001` de-dup produces `Wall-col.001` and the suffix no longer terminates the name `(verify)`. |
| extras | Custom Properties exported as glTF `extras` land in node/mesh/material metadata: `node.get_meta("extras")` (Godot version that introduced it `(verify)`). |
| Import config | Root Type/Root Name, Apply Root Scale, Meshes: Ensure Tangents, Generate LODs, Create Shadow Meshes, Light Baking + Lightmap Texel Size; Animation: FPS (30 typical), Trimming, Remove Immutable Tracks; Advanced Import Settings per mesh/material/animation (physics shape, loop mode, save to file); `EditorScenePostImport._post_import(scene)` scripts. |
| Materials/textures | glTF PBR imports 1:1 (BaseColor sRGB, MetallicRoughness G/B, Occlusion R, Normal, Emissive). "Godot expects the normal map to use X+, Y+, and Z+ coordinates" (OpenGL). No filename-suffix detection; textures come from the glTF. |

Sources: https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/available_formats.html · https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/model_export_considerations.html · https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/node_type_customization.html · https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/import_configuration.html · https://docs.godotengine.org/en/stable/tutorials/3d/introduction_to_3d.html · https://docs.godotengine.org/en/stable/classes/class_basematerial3d.html · https://forum.godotengine.org/t/gltf-import-how-does-one-get-metadata-extras/105711

---

## 5. Roblox Studio

| Setting | Value |
|---|---|
| Format | 3D Importer: "You can import meshes in the .fbx, .obj, or .gltf format". `.glb` accepted by Open Cloud Assets API (`model/gltf-binary`, 20 MB per call); Studio `.glb` drag-in `(verify)`. Roblox: "GLTF (.gltf) formats… do not require these additional scaling configurations." |
| Units | Studs. "1 stud = 28 cm". Blender config page: Scene ▸ Units ▸ Unit System **None**, Rotation Degrees. Three FBX scale routes: (1) recommended `apply_scale_options='FBX_SCALE_UNITS'` ("FBX Unit Scale") with all other scales 1.0; (2) export Scale 0.01; (3) scene Unit Scale 0.01 ("can cause unexpected Blender issues"). Importer **Scale Unit** (default Studs; Inches/Feet/Meters/Centimeters/Millimeters) can re-interpret. |
| Blender FBX export (Roblox docs) | Forward "Z Forward", Up "Y Up" as written on Roblox's page `(verify vs Blender default -Z)`, Apply Scalings = FBX Unit Scale, `path_mode='COPY'` + `embed_textures=True`, `add_leaf_bones=False`, `bake_anim=False` unless exporting animation; Studio's **World Forward** (default Front) / **World Up** (default Top) override orientation at import. |
| Importer defaults | Import Only As Model on · Upload to Roblox on · Add to Workspace on · Insert Using Scene Position off · **Set Pivot to Scene Origin on** · **Use Imported Pivot on** · Anchored off · **Merge Meshes off** ("merges all MeshParts… into a single MeshPart") · Invert Negative Faces off · Make Double Sided off · Ignore Vertex Colors off · Rig Type auto (R15/Custom/No Rig) · Keep Zero Influence Bones off. |
| Per-mesh limits | "Individual meshes can not exceed 20,000 triangles"; watertight, "quads where possible" (no n-gons), non-zero volume; ≤4 bone influences per vertex; bones frozen (scale 1,1,1, rot 0,0,0), root at 0,0,0; one animation track per file. Marketplace: rigid accessories ≤4k tris, single mesh, textures ≤2048²; R15 body 10,742 tris total (Head 4000, Torso 1750, each arm/leg 1248). Cage meshes `<Name>_InnerCage` / `_OuterCage`, attachments `_Att`, body parts `_Geo`. Studio file-size cap `(verify; undocumented)`. |
| Textures | "Roblox supports up to 4096×4096 pixel texture resolutions (4K)" and "up to 1024×1024 pixel spaces for texture maps" — which applies to MeshPart/SurfaceAppearance `(verify)`; guidance 256² for 5×5-stud, 512² for 10×10, 1024² for 20×20 objects. Formats .png/.jpg/.tga/.bmp. PBR: Albedo RGB 24-bit, Normal RGB 24-bit, Roughness/Metalness/Emissive 8-bit grayscale. "Roblox only supports OpenGL format – Tangent Space normal maps". Single UV set, UVs inside 0–1. SurfaceAppearance: ColorMap, NormalMap, RoughnessMap, MetalnessMap, EmissiveMaskContent, AlphaMode. Importer builds SurfaceAppearance from Principled BSDF textures when embedded `(verify)`. |

Sources: https://create.roblox.com/docs/art/modeling/3d-importer · https://create.roblox.com/docs/art/modeling/specifications · https://create.roblox.com/docs/art/modeling/texture-specifications · https://create.roblox.com/docs/art/modeling/export-requirements · https://create.roblox.com/docs/art/blender · https://create.roblox.com/docs/physics/units · https://create.roblox.com/docs/art/modeling/surface-appearance · https://create.roblox.com/docs/art/accessories/specifications · https://create.roblox.com/docs/art/characters/specifications · https://create.roblox.com/docs/cloud/guides/usage-assets

---

## 6. three.js / web (glTF)

| Setting | Value |
|---|---|
| Format | `.glb` ("we recommend using glTF… both .GLB and .GLTF… well supported"). glTF spec: meters, right-handed, +Y up, **front faces +Z**. |
| Blender glTF export | `export_format='GLB'`, `export_yup=True`, `export_apply=True`, `export_image_format='AUTO'` or `'JPEG'`/`'WEBP'` (+`export_image_add_webp`, `export_image_webp_fallback`), Draco on (`export_draco_mesh_compression_enable=True`, 14/10/12/10/12 bits) **or** `export_meshopt_compression_enable=True` (5.2) **or** gltfpack bridge with `export_gltfpack_tc=True` (KTX2). Keep object names stable (`scene.getObjectByName`) and "never scale anything… apply that scale to the vertices" (three.js manual). |
| Loader | `GLTFLoader` + `setDRACOLoader()`, `setKTX2Loader()`, `setMeshoptDecoder()`; textures `flipY=false`, sRGB for colour, linear for data. Supports `KHR_draco_mesh_compression`, `KHR_lights_punctual`, `KHR_materials_{anisotropy,clearcoat,diffuse_roughness,dispersion,emissive_strength,ior,specular,transmission,iridescence,unlit,volume}`, `KHR_mesh_quantization`, `KHR_meshopt_compression`, `KHR_texture_basisu`, `KHR_texture_transform`, `EXT_meshopt_compression`, `EXT_mesh_gpu_instancing`, `EXT_texture_webp`, `EXT_texture_avif`. |
| Normal map | glTF: "+X is right and +Y is up. +Z points toward the viewer" (OpenGL). Metallic-roughness: roughness G, metalness B; occlusion R; baseColor sRGB. |
| Budgets (Khronos 3D Commerce v1.0 publishing targets) | Web catalogue / single-item mobile AR: **3 MB, 150k tris, <20 draws (500 max), 2K textures**; desktop web: 3 MB, 250k tris, <100 (800), 2K; banner ad: 500 KB, 30k tris, <5 (100), 512²; web planner (one of many items): 1 MB, 40k tris, <5 (50), 1K. Rationale: load < 3 s at 10 Mb/s. Drop order for low-end: emissive, then ORM, then normals. |
| Post-export tools | `gltf-transform optimize in.glb out.glb --compress draco|meshopt --texture-compress webp|ktx2 --texture-size N --simplify --simplify-error …` (also `dedup instance palette flatten join weld simplify resample prune sparse`); `gltf-transform draco` quantize defaults position 14 / normal 10 / texcoord 12 / color 8 / generic 12; `simplify --ratio R --error 0.0001 --lock-border`; `resize --width --height`; `inspect`; `validate`. `gltfpack -c|-cc` (EXT_meshopt_compression), `-tc` KTX2+BasisU, `-tu` UASTC, `-tq`, `-tw` WebP, `-tp` power-of-two, `-tr`, `-si R`, `-sa`, `-kn`, `-ke`, `-km`, `-noq`, `-vpf`, `-mi`. |
| Troubleshooting (three.js) | check console + `onError`; test in another viewer; "scaling the model up or down by a factor of 1000"; add a light; fix absolute texture paths like `C:\…`. |

Sources: https://threejs.org/manual/#loading-3d-models · https://threejs.org/manual/#load-gltf · https://github.com/mrdoob/three.js/blob/dev/examples/jsm/loaders/GLTFLoader.js · https://raw.githubusercontent.com/KhronosGroup/glTF/main/specification/2.0/schema/material.schema.json · https://raw.githubusercontent.com/KhronosGroup/glTF/main/specification/2.0/schema/material.pbrMetallicRoughness.schema.json · https://github.com/KhronosGroup/3DC-Asset-Creation/blob/main/asset-creation-guidelines-1.0/full-version/sec99_PublishingTargets/PublishingTargets.md · https://github.com/KhronosGroup/3DC-Asset-Creation/blob/main/asset-creation-guidelines-1.0/full-version/sec02_CoordinateSystemAndScaleUnit/CoordinateSystemAndScaleUnit.md · https://github.com/donmccurdy/glTF-Transform/blob/main/packages/cli/README.md · https://meshoptimizer.org/gltf/

---

## 7. Sketchfab / Fab

| Setting | Sketchfab | Fab |
|---|---|---|
| Formats | Processing priority "FBX, GLTF/GLB, BLEND, OBJ, STL, PLY, USD, ABC, 3DS, ASC, DAE"; textures in zip root or subfolder (zip/rar/7z). | 3D exchange: FBX, GLB, GLTF, OBJ, USD, USDZ; DCC: 3ds Max, Blender, Cinema 4D, Maya; engines: UEFN, Unreal Engine, Unity. |
| Size limits | Plans page: Basic 100 MB / 10 uploads per month; Pro 200 MB / 50; Enterprise 500 MB / custom (help article still names a "Premium… up to 500MB" tier). | UE format ≤15 GB (larger needs review); Unity = Asset Store limit; "Additional Files" 6 GB each, max 3 (18 GB); other file types 6 GB, one per type `(verify; page scraped as "6B")`. |
| Rules | Upload credits: Basic 10, Pro 50, Premium 200 per month. Polygon/texture caps per tier not published `(verify)`. | Textures embedded or relative paths next to the model; English alphanumeric names; no nested zips (`.mhpkg`). |
| Delivery | `.glb` with PBR, Y-up, meters; one material per surface type. Sketchfab ↔ Fab transition status `(verify; nothing on the live pages)`. | Ship a `.glb` for the viewer plus source FBX/Blender; declare polycount/LODs in listing `(verify)`. |

Sources: https://help.sketchfab.com/en/articles/16152560-uploading-3d-models · https://sketchfab.com/plans · https://help.sketchfab.com/en/articles/16152176-is-paid-membership-required-to-upload-one-large-file · https://help.sketchfab.com/en/articles/16152582 · https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab

---

## 8. USD for offline render / other DCC

| Setting | Value |
|---|---|
| Format | `.usd` / `.usda` (ASCII) / `.usdc` (binary) / `.usdz` (archive; UDIM textures cannot be included). |
| Axes / units | Blender writes its native Z-up unless **Convert Orientation** is on with Forward/Up chosen (e.g. −Z forward, Y up for Y-up apps); USD stage `upAxis` may be Y or Z, USDZ expects +Y up, +Z front, meters. **Units** sets `metersPerUnit` (Meters Per Unit for Custom). Khronos: glTF and USDZ both "+Y world up, +Z world front, right-hand… meter-based". |
| Key export options (UI names; python names `(verify)`) | Root Prim path; Selection Only; Visible Only; Animation (full frame range); Custom Properties (+ Namespace, default `userProperties`); Blender Names; Allow Unicode (USD 24.03+); Relative Paths; Xform Ops: Translate/Rotate/Scale, Translate/Orient/Scale, Matrix; Use Settings for Viewport/Render; Object Types (Meshes, Lights, World Dome Light, Cameras [perspective only], Curves, Point Clouds, Volumes, Hair); UV Maps, Rename UV Maps (→ `st`), Normals (incl. custom), Merge parent Xform, **Triangulate** (+ quad/n-gon method); Rigging: Shape Keys (→ blend shapes), Armatures (→ UsdSkel), Only Deform Bones; Materials: **USD Preview Surface Network** (approximates Principled BSDF; only Diffuse BSDF, Principled BSDF, Image Texture, UVMap, Separate RGB nodes), **MaterialX Network**; Export Textures: Keep / Preserve / New Path (`textures/` folder), Overwrite Textures; USDZ Texture Downsampling Keep/256/512/1024/2048/4096/Custom; Instancing (experimental). |
| Material caveats | Multiple materials → GeomSubsets (first material also bound to the whole mesh); double-sidedness taken from first material; `opacityThreshold` needs a Round or `1 - (value < threshold)` math node on Alpha; displacement object-space only. |
| Normal map | USDZ uses OpenGL convention (+X right, +Y up, +Z toward viewer). |

Sources: https://docs.blender.org/manual/en/5.2/files/import_export/usd.html · https://developer.blender.org/docs/release_notes/5.2/pipeline_io/ · https://github.com/KhronosGroup/3DC-Asset-Creation/blob/main/asset-creation-guidelines-1.0/full-version/sec02_CoordinateSystemAndScaleUnit/CoordinateSystemAndScaleUnit.md

---

## 9. Cross-target comparison

| | Unity | Unreal 5 | Godot 4 | Roblox | three.js/web | Sketchfab/Fab | USD/offline |
|---|---|---|---|---|---|---|---|
| Preferred file | FBX (glTF via glTFast) | FBX 2020.2-compatible | `.glb` | FBX (Copy+Embed) or `.gltf` | `.glb` | `.glb` (+ source FBX) | `.usdc`/`.usdz` |
| Unit | 1 u = 1 m | 1 UU = 1 cm | 1 u = 1 m | 1 stud = 28 cm | 1 u = 1 m | m | `metersPerUnit` |
| Up / forward | Y / +Z | Z / +X | Y / asset front +Z (camera −Z) | Top / Front (importer) | Y / +Z | Y / +Z | Y or Z |
| Handedness | left | left | right | left `(verify)` | right | right | right |
| Blender axis opts | `-Z`/`Y` (default) | `-Z`/`Y` + UE Convert Scene | `export_yup=True` | FBX "Z Forward"/"Y Up" per Roblox doc | `export_yup=True` | `export_yup=True` | Convert Orientation `-Z`/`Y` for Y-up targets |
| Scale option | `FBX_SCALE_NONE` + Convert Units | `FBX_SCALE_NONE` (1 m → 100 cm) | n/a (meters) | `FBX_SCALE_UNITS` | n/a | n/a | Units = Meters |
| Zero-rotation fix | Bake Axis Conversion (importer) | Force Front XAxis / model facing +X `(verify)` | none needed (model faces −Y) | World Forward/Up overrides | none | none | Convert Orientation |
| Names the importer reads | `_LOD0…_LOD7` | `UBX_/UCP_/USP_/UCX_<Mesh>_##`, `SOCKET_<Mesh>_##`, LodGroup | `-col -convcol -colonly -convcolonly -navmesh -occ -rigid -vehicle -wheel -noimp`, `loop/cycle` | `_InnerCage/_OuterCage/_Att/_Geo` (avatars) | `extras`, node names | – | prim names, `userProperties:` |
| Material survives? | diffuse/emissive/bump only | Color + Normal auto-wired | full glTF PBR | PBR → SurfaceAppearance | full glTF PBR | PBR | PreviewSurface approximation |
| Normal-map green | +Y (OpenGL) | −Y (DirectX; Flip Green Channel) | +Y | +Y (OpenGL only) | +Y (spec) | +Y | +Y |
| Textures | ship beside FBX | import separately | inside `.glb` | embed (FBX) / inside glTF | inside `.glb` | zip or `.glb` | `textures/` or inside `.usdz` |
| Per-mesh cap | none hard (16-bit index default) | none hard (Nanite optional) | none hard | **20,000 tris**; Marketplace 4k acc. / 10,742 body | 150k tris / 3 MB (3DC web target) | 100–500 MB per upload | none |
| Triangulate on export | optional (Keep Quads) | required (`use_triangles=True`) | recommended (modifier) | quads allowed | glTF always triangles | glTF triangles | optional |

### 9b. Multi-object vs single-object, pivots, hierarchy, empties, modifiers (cross-cutting)

- **Source stays quads; export triangulates.** FBX `use_triangles`, glTF (always triangles; "automatically converted to triangles when exporting"), USD **Triangulate**, OBJ **Triangulated Mesh**. Modifiers: FBX `use_mesh_modifiers=True` by default but glTF `export_apply=False` by default — set it to `True`; both block shape-key export when on (API warning).
- **Empties / hierarchy.** FBX `object_types` includes `'EMPTY'` (written as FBX Null nodes); glTF writes Empties as nodes (`export_hierarchy_flatten_objs` flattens; `export_hierarchy_full_collections` adds collection empties). Unity imports "all nodes with position, rotation and scale; pivot points and names" and offers **Preserve Hierarchy** (explicit prefab root even for single-root files) and **Sort Hierarchy By Name**. Unreal static-mesh import ignores empties except `SOCKET_` children; **Combine Meshes** merges everything in the file into one asset, otherwise one Static Mesh per mesh node; **Transform Vertex to Absolute** bakes node transform/offset/pivot into vertices, **Bake Pivot in Vertex** (experimental) applies pivot rotation. Godot keeps Empties as `Node3D` placeholders (`-colonly` on Empties was Collada-only). Roblox **Import Only As Model** (one asset with children) vs **Merge Meshes** (single MeshPart); **Use Imported Pivot** (on) keeps each child's pivot, **Set Pivot to Scene Origin** (on) sets the model pivot to scene origin.
- **One asset per file for Unreal props** (custom collision imports only for the first mesh in a file; sockets need a single-mesh FBX). Unity/Godot/web tolerate multi-object scenes; Roblox imports multi-mesh files as a Model.
- **Pivot/origin before export:** `Object > Apply > All Transforms`; put the origin where the target expects it (Unreal: object at world origin, pivot = origin; Godot/Unity/web: base-centre or as designed). Three.js manual: "never scale anything… apply that scale to the vertices". Use Blender `use_selection` / `use_active_collection` / glTF `collection` + `at_collection_center` for per-asset batch exports; FBX `batch_mode='COLLECTION'` writes one file per collection.

---

## 10. Verification after export

1. **Re-import glTF into Blender headless** and print size + root rotation (Blender is at `/Applications/Blender.app`):
   `/Applications/Blender.app/Contents/MacOS/Blender -b --python-expr "import bpy; bpy.ops.import_scene.gltf(filepath='out.glb'); [print(o.name, [round(d,3) for d in o.dimensions], [round(r,3) for r in o.rotation_euler]) for o in bpy.context.scene.objects]"` — dimensions must match the source in metres; root `rotation_euler` must be `(0,0,0)`. For FBX use the default C++ importer `bpy.ops.wm.fbx_import(filepath=…)` (idname `WM_OT_fbx_import` in 5.2 source; `bpy.ops.import_scene.fbx` is the legacy Python add-on) and confirm cm → m scaling.
2. **Khronos glTF-Validator**: web drag-and-drop https://github.khronos.org/glTF-Validator/ ; CLI `gltf_validator -o -a out.glb` (Dart binary from GitHub releases); npm `gltf-validator`. Also `npx @gltf-transform/cli validate out.glb` and `npx @gltf-transform/cli inspect out.glb` (node/npx are installed here; `gltf-transform` and `gltfpack` are not — install with `npm i -g @gltf-transform/cli gltfpack`).
3. **Bounding-box / orientation check** inside Blender before export: `Object > Apply > All Transforms`, origin where the engine expects the pivot (Unreal: world origin; Godot/Unity/web: base-centre), front facing −Y (Godot/web/Unity) or +X (Unreal).
4. **FBX**: open the file in Blender's C++ importer or the target engine; confirm scale factor 1.0/0.01 as intended, no −89.98° root rotation (Unity), smoothing present (Unreal warns when missing).
5. **Texture conventions**: flip green for Unreal; confirm ORM packing (R=AO, G=roughness, B=metal) survives by inspecting `gltf-transform inspect` materials output; confirm all images are PNG/JPEG/WebP/KTX2 as targeted.

Sources: https://github.com/KhronosGroup/glTF-Validator · https://github.com/donmccurdy/glTF-Transform/blob/main/packages/cli/README.md · Blender 5.2 manual FBX/glTF pages (section 1)

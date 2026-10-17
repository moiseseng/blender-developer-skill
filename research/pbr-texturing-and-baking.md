# PBR texturing, procedural materials and baking in Blender 5.x

Research notes for the Blender 3D-team skill (Blender 5.2 LTS, Python-driven, no Substance). Verified 2026-10-17 against the Blender 5.2 manual/API, Blender source (`main`), the glTF 2.0 spec and engine docs. Items marked `(verify)` were not confirmed from a primary source.

1. [Metal/roughness workflow: value rules](#1-metalroughness-workflow-value-rules)
2. [Texture sets and channel packing per target](#2-texture-sets-and-channel-packing-per-target)
3. [Color management in Blender 5.x](#3-color-management-in-blender-5x)
4. [Baking in Blender (UI + Python)](#4-baking-in-blender-ui--python)
5. [Procedural material recipes](#5-procedural-material-recipes)
6. [Resolution, formats, naming](#6-resolution-formats-naming)
7. [Trim sheets and tileables](#7-trim-sheets-and-tileables)
8. [QA checklist for textures](#8-qa-checklist-for-textures)

---

## 1. Metal/roughness workflow: value rules

1. **Base Color of dielectrics (sRGB 8-bit):** darkest 30–50, brightest 240. Charcoal-like blacks sit at ~50; fresh snow is the 240 ceiling (Adobe PBR Guide pt. 2).
2. **Base Color of raw metals:** 180–255 sRGB (70–100 % linear reflectance; iron sits near the 180 floor). A "metal" pixel darker than that is oxidised/dirty/painted: treat it as a dielectric, lower Metallic and lower the base color (Adobe).
3. **Dielectric F0 is fixed by the shader:** 2–5 % (0.02–0.05 linear, 40–75 sRGB); default 4 % = IOR 1.5 (Adobe; Marmoset: "0.04 linear, 0.22 sRGB" per channel, `#383838`). Do not paint specular for dielectrics in metal/rough.
4. **Metallic is binary:** 0 or 1; grey only on transitions (dirt, dust, rust). Painted/rusted metal = 0 (Marmoset, Adobe). QA: histogram must be bimodal.
5. **Roughness is the artistic map:** 0 = mirror, 1 = fully diffuse (Blender Principled). Blender/glTF/Unreal/Godot/Roblox use *roughness*; Unity and Marmoset-gloss use *smoothness = 1 − roughness*.
6. **No lighting in Base Color:** no directional light, no AO, no cavity. AO goes to its own map/slot (Marmoset). Micro-occlusion is tolerated if it respects rule 1 (Adobe).
7. **Python writes scene-linear.** `node.inputs['Base Color'].default_value`, Color Ramp stops, Mix colors are linear (Blender 5.0 moved brush/palette colors to scene-linear "to match shader nodes"). Convert sRGB references: `c = s/255; lin = c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4`. 30 sRGB → 0.0130, 50 → 0.0319, 180 → 0.4564, 240 → 0.8714.
8. **Principled BSDF socket names (5.2):** `Base Color`, `Metallic`, `Roughness`, `IOR` (default 1.5), `Alpha`, `Normal`, `Weight`, `Thin Wall` (new 5.2), `Subsurface Weight/Radius/Scale/IOR/Anisotropy`, `Specular IOR Level`, `Specular Tint`, `Anisotropic`, `Anisotropic Rotation`, `Tangent`, `Transmission Weight`, `Coat Weight/Roughness/IOR/Tint/Normal`, `Sheen Weight/Roughness/Tint`, `Emission Color`, `Emission Strength`, `Thin Film Thickness/IOR` (5.0+). Node type `ShaderNodeBsdfPrincipled`.
9. **Specular/gloss workflow (note only):** diffuse + specular color + gloss; not supported by glTF core, Roblox or Godot standard materials. Convert: metal → specular = base color, diffuse = black; dielectric → specular `#383838`, gloss = 1 − roughness (Marmoset).

Sources: https://www.adobe.com/learn/substance-3d-designer/web/the-pbr-guide-part-2 · https://marmoset.co/posts/physically-based-rendering-and-you-can-too/ · https://marmoset.co/posts/pbr-texture-conversion/ · https://docs.blender.org/manual/en/5.2/render/shader_nodes/shader/principled.html · https://developer.blender.org/docs/release_notes/5.0/color_management/

## 2. Texture sets and channel packing per target

| Target | Color map | Rough/metal/AO packing | Normal Y | Emissive | Notes |
|---|---|---|---|---|---|
| glTF 2.0 (web, Godot/Three.js import) | `baseColorTexture` sRGB (A = alpha) | `metallicRoughnessTexture`: **G = roughness, B = metalness**, R/A unused, linear; `occlusionTexture`: **R**, linear, may share the same image → "ORM" | +Y up (OpenGL), linear, Z in B must be > 0.5 | sRGB RGB | 8-bit allowed, ">8 bits MAY" |
| Unreal Engine 5 | BaseColor sRGB | Community "ORM" **R = AO, G = Rough, B = Metal**, sRGB **off**, compression Masks/BC7 `(verify: not an Epic requirement)` | **−Y (DirectX)**: tick *Flip Green Channel* on import of OpenGL maps | sRGB | Textures `T_*`, suffix per map |
| Unity URP Lit | Base Map sRGB | Metallic map **R = Metallic, G = Occlusion, B unused, A = Smoothness**; "Metallic Alpha" source | **+Y (OpenGL)** ("Unity uses Y+ normal maps") | sRGB | Smoothness = 1 − roughness |
| Unity HDRP Lit | Base Map sRGB | Mask Map **R = Metallic, G = AO, B = Detail mask, A = Smoothness**; import with sRGB off | +Y | sRGB | Detail map R albedo, G normal Y, B smoothness, A normal X |
| Godot 4 ORMMaterial3D | Albedo sRGB | Single ORM texture, same format as the Substance "Unreal Engine" preset → **R = AO, G = Rough, B = Metal** | **+Y** ("X+, Y+, Z+"); only R,G read; DirectX maps need Y flipped | Emission sRGB | StandardMaterial3D reads rough/metal/AO from a chosen channel (default R) |
| Roblox SurfaceAppearance | `ColorMap` RGB(A) 24-bit, `AlphaMode` Opaque/Overlay/Transparency/TintMask | **Separate** grayscale 8-bit `RoughnessMap`, `MetalnessMap` (no packing, no AO slot) | `NormalMap` RGB, **OpenGL only**, flat = (127,127,255) | `EmissiveMaskContent` grayscale | 1 material per MeshPart, UVs in 0–1 |

Normal-map green channel rules:
1. OpenGL (+Y up): Blender bake/render default, glTF, Unity, Godot, Roblox. DirectX (−Y): Unreal; Substance/Marmoset are configurable (blog source, `(verify)` for Marmoset default).
2. Visual test: on an OpenGL map the *top* edge of a raised bump is bright green; DirectX is the opposite.
3. Flip in Blender, three routes: (a) **at bake time** `bpy.ops.object.bake(type='NORMAL', normal_g='NEG_Y')` (swizzle items `POS_X/POS_Y/POS_Z/NEG_X/NEG_Y/NEG_Z`); (b) **reading a DirectX map** (5.1+): Normal Map node `convention='DIRECTX'` (`ShaderNodeNormalMap.convention`, default `'OPENGL'`); (c) **node conversion**: `Separate Color(RGB)` → `Math(SUBTRACT, 1 − G)` → `Combine Color(RGB)`.
4. For glTF export keep the bake panel at Tangent, R=+X, G=+Y, B=+Z and connect Image Texture (Non-Color) → Normal Map (Tangent) → Principled `Normal` (Blender glTF manual).
5. Blender glTF exporter picks up occlusion only from a node group named **`glTF Material Output`** with an `Occlusion` input (Add ▸ Output ▸ glTF Material Output); roughness/metal must come through `Separate Color` G→Roughness, B→Metallic with the image set to Non-Color, or the exporter re-encodes the image. The manual still says "Separate RGB": that node was removed in 5.0, use `ShaderNodeSeparateColor` (`mode='RGB'`).

Sources: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html (§3.9.2, §5.19.5–5.19.6) · https://docs.blender.org/manual/en/5.2/addons/import_export/scene_gltf2.html · https://dev.epicgames.com/documentation/en-us/unreal-engine/texture-asset-editor-in-unreal-engine · https://andrewdowell.artstation.com/blog/0vAm4/unreal-engine-advanced-channel-packing · https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@12.1/manual/lit-shader.html · https://docs.unity3d.com/Packages/com.unity.render-pipelines.high-definition@17.0/manual/Mask-Map-and-Detail-Map.html · https://docs.unity3d.com/Manual/StandardShaderMaterialParameterNormalMap.html · https://docs.godotengine.org/en/stable/tutorials/3d/standard_material_3d.html · https://docs.godotengine.org/en/stable/classes/class_basematerial3d.html · https://create.roblox.com/docs/en-us/art/modeling/surface-appearance · https://create.roblox.com/docs/en-us/art/modeling/texture-specifications · https://www.strayspark.studio/blog/directx-vs-opengl-normal-maps-explained · https://docs.blender.org/manual/en/5.2/render/shader_nodes/displacement/normal_map.html

## 3. Color management in Blender 5.x

1. **Image color space:** `sRGB` for Base Color and Emissive; **`Non-Color`** for Normal, Roughness, Metallic, AO, Height/Displacement, masks, ORM packs (manual: "Such maps do not actually store colors … should be marked as Non-Color Data"). Set at creation: `bpy.data.images.new(name, w, h, alpha=False, float_buffer=True, is_data=True)` or later `img.colorspace_settings.name = 'Non-Color'`.
2. **Working space (5.0+):** file-level setting, default `Linear Rec.709`; keep it for game textures. `Linear Rec.2020`/`ACEScg` change every stored color and are meant for wide-gamut/ACES delivery.
3. **View transforms available in 5.2:** `Standard`, `ACES 1.3`, `ACES 2.0`, `Khronos PBR Neutral`, `AgX` (default; 16.5 stops), `Filmic` (deprecated), `Filmic Log`, `False Color`, `Raw`, plus HDR variants. For texture work: preview with **Khronos PBR Neutral** (built to make output sRGB match input base color under grey lighting) or **Standard**; never judge albedo values under AgX/Filmic.
4. **What the view transform does to saved textures (from `image_save.cc` / `colormanagement.cc`):**
   - `Image.save()` → `save_as_render=False`: no view transform; float buffer is encoded into the image's own color space (sRGB images get the sRGB curve, Non-Color stays raw). Needs `img.filepath_raw` and `img.file_format` set first (or pass `filepath=`).
   - `Image.save_render(path, scene=)` → `save_as_render=True`: for byte formats (PNG/JPG/TGA) the **scene view transform + look + exposure are baked in** for sRGB images → under AgX your Base Color is tone-mapped. Non-Color images are exempt ("data buffers never get color space conversions"). OpenEXR output is always linear float and exempt.
   - Rule: export textures with `img.save()`; if you need `save_render` (to force 8-bit or a scene format), first set `scene.view_settings.view_transform='Standard'`, `look='None'`, `exposure=0`, `gamma=1`, `display_settings.display_device='sRGB'`.
5. **Bit depth on save:** `img.save()` on a `float_buffer=True` image picks the best depth the format allows → PNG **16-bit**, EXR **32-bit**; byte images save 8-bit. `save_render` uses `scene.render.image_settings` (`file_format`, `color_depth` in {'8','16'} for PNG, {'16','32'} for EXR, `color_mode` BW/RGB/RGBA, `compression` 0–100 default 15). 5.0 added `ImageFormatSettings.media_type` (`'IMAGE'`, `'MULTI_LAYER_IMAGE'`, `'VIDEO'`).
6. `bpy.ops.image.save_as(save_as_render=False, copy=True, filepath=...)` mirrors the UI; "Save As Render … for PNG apply view and display transform".

Sources: https://docs.blender.org/manual/en/5.2/render/color_management/color_spaces.html · https://docs.blender.org/manual/en/5.2/render/color_management/displays_views.html · https://developer.blender.org/docs/release_notes/5.0/color_management/ · https://docs.blender.org/api/5.2/bpy.types.Image.html · https://docs.blender.org/api/5.2/bpy.types.ImageFormatSettings.html · https://docs.blender.org/api/5.2/bpy.types.BlendDataImages.html · https://docs.blender.org/api/5.2/bpy.ops.image.html · https://projects.blender.org/blender/blender/src/branch/main/source/blender/blenkernel/intern/image_save.cc · https://projects.blender.org/blender/blender/src/branch/main/source/blender/imbuf/intern/colormanagement.cc

## 4. Baking in Blender (UI + Python)

**Facts (5.2 manual/API):**
1. Baking is **Cycles only** (`scene.render.engine='CYCLES'`); it uses the render samples/bounces. 1–16 samples suffice for Diffuse-Color, Normal, Roughness, Emit, UV, Position; AO/Combined/Shadow need 64–256 (community practice, `(verify)`).
2. Target = the Image Texture node that is **selected *and* active** in each material (5.0 change, PR#137389: "Bake only to selected (and active) images"; a material without one bakes nothing). Mesh needs a UV map; `uv_layer=` overrides the active UV.
3. **Bake types** (`type=`): `COMBINED, AO, SHADOW, POSITION, NORMAL, UV, ROUGHNESS, EMIT, ENVIRONMENT, DIFFUSE, GLOSSY, TRANSMISSION`. `pass_filter` items: `NONE, EMIT, DIRECT, INDIRECT, COLOR, DIFFUSE, GLOSSY, TRANSMISSION`.
   - Base Color = `type='DIFFUSE', pass_filter={'COLOR'}` ("if only Color is selected you get the pass color … independent of sampling").
   - Roughness = `type='ROUGHNESS'`. Normal = `type='NORMAL'` (`normal_space='TANGENT'|'OBJECT'`, swizzle). AO = `type='AO'` (world AO distance; ignores lights). Emissive = `type='EMIT'`.
   - **Metallic, Alpha, Height, masks have no bake type:** temporarily wire the socket/value into an `ShaderNodeEmission` → Material Output and bake `EMIT` (Emit bakes exactly what is plugged in; set Strength 1).
   - `COMBINED` = lighting + color (light-map/stylized "baked lighting" only; never for PBR albedo).
4. **Selected to Active** (high→low): select high-poly objects, make low-poly active, `use_selected_to_active=True`. Rays cast from the low inward. `cage_extrusion` (used with `use_cage=True`; cage built from the active with Edge Split disabled, or `cage_object` with identical face count/order) **or** `max_ray_distance` (only without cage; 0 = unlimited). Start at extrusion ≈ 1–2 % of object size and grow until skews/misses vanish. Join many high-poly parts first (fixed CPU memory per source object).
5. **Margin:** `margin` px, `margin_type='ADJACENT_FACES'` (default in scene settings, better across seams) or `'EXTEND'` (operator default!). Minimums (Polycount): 256 → 2 px, 512 → 4 px, 1024 → 8 px, 2048 → 16 px; UV gutters ≥ 2× padding.
6. **Precision:** create normal/height/position targets with `float_buffer=True` (32-bit float internally) to avoid banding from skewed cages; save PNG 16-bit (automatic via `img.save()`) or EXR half/float. 8-bit is fine for Base Color, Roughness, Metallic, AO.
7. **Procedural → image:** keep the procedural node tree, add the target Image Texture node (unlinked is fine), bake each channel with the types above, then build a second "export" material that reads the images. Bake Base Color with lights irrelevant (`DIFFUSE`+`COLOR`), so no lighting leaks in.
8. **Atlas of many objects to one image:** give every object a non-overlapping island in a shared bake UV map (second UV layer), add the same image to a selected+active Image Texture node in every material, select all objects, `use_selected_to_active=False`, bake once per map. `use_clear=True` is safe when all objects bake in one `bpy.ops.object.bake` call; if objects bake in separate calls, pass it only on the first (clear wipes the whole image). Joining the objects first avoids margin overwrites.
9. **Operator defaults differ from scene defaults:** `bpy.ops.object.bake` → `margin=16, margin_type='EXTEND', use_clear=False, save_mode='INTERNAL'`; `scene.render.bake` → `margin=16, margin_type='ADJACENT_FACES', use_clear=True`. Pass arguments explicitly. `scene.cycles.bake_type` holds the UI pass; `scene.render.bake.type` is for multires (`NORMALS/DISPLACEMENT/VECTOR_DISPLACEMENT`).
10. **4.x → 5.x changes:** 5.0 bakes only to selected+active images; 5.0 removed `ShaderNodeSeparateRGB/CombineRGB` (use `ShaderNodeSeparateColor/CombineColor`, `mode='RGB'`; `ShaderNodeMixRGB` still exists but prefer `ShaderNodeMix`, `data_type='RGBA'`); 5.0 render passes renamed (`DiffCol` → `Diffuse Color`); 5.1 Normal Map node `convention` OpenGL/DirectX and `base` Original/Displaced; 5.2 Principled `Thin Wall`, Cycles texture cache (`.tx` files in `blender_tx/`), `image.pixels[a:b:step]` slicing. **Multires-bake properties moved** off `RenderSettings`: 4.5 `scene.render.bake_type / use_bake_multires / use_bake_lores_mesh / bake_margin / bake_margin_type / use_bake_clear / use_bake_selected_to_active / bake_samples / bake_bias / bake_user_scale` no longer exist in 5.2; use `scene.render.bake.type` (`NORMALS/DISPLACEMENT/VECTOR_DISPLACEMENT`), `.use_multires`, `.use_lores_mesh`, `.displacement_space` (new), `.margin`, `.margin_type`, `.use_clear`, `.use_selected_to_active`. The `bpy.ops.object.bake` signature is identical in 4.5 and 5.2 (checked).

**End-to-end Python (5.2):**
```python
import bpy, os
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.samples = 16
vs = scene.view_settings; vs.view_transform, vs.look, vs.exposure, vs.gamma = 'Standard', 'None', 0.0, 1.0
obj = bpy.data.objects['SM_Prop']; nt = obj.active_material.node_tree
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
OUT = bpy.path.abspath('//textures') if bpy.data.filepath else '/tmp/textures'   # '//' needs a saved .blend
os.makedirs(OUT, exist_ok=True)                                                     # img.save() fails on a missing folder

def bake_target(name, size, is_data, float_buffer):
    img = bpy.data.images.new(name, size, size, alpha=False, float_buffer=float_buffer, is_data=is_data)
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
    for n in nt.nodes: n.select = False
    tex.select = True; nt.nodes.active = tex          # 5.0+: selected AND active
    return img, tex

def save_png(img, name):
    img.filepath_raw = os.path.join(OUT, name + '.png'); img.file_format = 'PNG'; img.save()

BAKE = dict(margin=8, margin_type='ADJACENT_FACES', use_clear=True, target='IMAGE_TEXTURES', use_selected_to_active=False)
img, tex = bake_target('SM_Prop_BaseColor', 2048, is_data=False, float_buffer=False)
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, **BAKE)
save_png(img, 'SM_Prop_BaseColor')                      # 8-bit sRGB, no view transform
img, tex = bake_target('SM_Prop_Roughness', 2048, is_data=True, float_buffer=False)
bpy.ops.object.bake(type='ROUGHNESS', **BAKE)
save_png(img, 'SM_Prop_Roughness')                      # 8-bit linear (Non-Color)
img, tex = bake_target('SM_Prop_Normal', 2048, is_data=True, float_buffer=True)
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z', **BAKE)
save_png(img, 'SM_Prop_Normal')                         # float buffer -> 16-bit PNG automatically
# Metallic: route Principled 'Metallic' source into an Emission shader, bake type='EMIT', restore links afterwards.
# High->low: select high-poly objects + active low, use bpy.ops.object.bake(type='NORMAL', use_selected_to_active=True,
#            use_cage=True, cage_extrusion=0.02, max_ray_distance=0.0, **{k:v for k,v in BAKE.items() if k!='use_selected_to_active'})
# Pack ORM with numpy: px = np.asarray(img.pixels).reshape(-1,4); orm[:,0]=ao[:,0]; orm[:,1]=rough[:,0]; orm[:,2]=metal[:,0]; orm_img.pixels.foreach_set(orm.ravel())
```

Sources: https://docs.blender.org/manual/en/5.2/render/cycles/baking.html · https://docs.blender.org/api/5.2/bpy.ops.object.html#bpy.ops.object.bake · https://docs.blender.org/api/5.2/bpy.types.BakeSettings.html · https://docs.blender.org/api/5.2/bpy_types_enum_items/bake_pass_type_items.html · https://developer.blender.org/docs/release_notes/5.0/rendering/ · https://developer.blender.org/docs/release_notes/5.0/python_api/ · https://developer.blender.org/docs/release_notes/5.1/rendering/ · https://developer.blender.org/docs/release_notes/5.2/python_api/ · https://developer.blender.org/docs/release_notes/5.2/cycles/ · https://www.katsbits.com/codex/?p=9730 · http://wiki.polycount.com/wiki/Edge_padding · https://cgcookie.com/articles/bit-depth-how-compression-affects-normal-maps

## 5. Procedural material recipes

Node names are Blender 5.2 (`bpy` type in brackets). Keys: `Noise Texture` [ShaderNodeTexNoise] inputs `Vector, Scale, Detail, Roughness, Lacunarity, Distortion`, outputs `Fac, Color`; `Voronoi Texture` [ShaderNodeTexVoronoi] features `F1/F2/Smooth F1/Distance to Edge/N-Sphere Radius`, inputs `Scale, Randomness`, outputs `Distance, Color, Position`; `Bevel` [ShaderNodeBevel] `Radius, Normal`, property `samples` (default 4, Cycles only, ~20 % slower); `Ambient Occlusion` [ShaderNodeAmbientOcclusion] `Color, Distance, Normal`, props `samples, inside, only_local`, outputs `Color, AO`; `Geometry` [ShaderNodeNewGeometry] outputs `Pointiness` (Cycles only, per-vertex, needs dense geometry), `Random Per Island`; `Object Info` [ShaderNodeObjectInfo] `Random, Object Index, Color`; `Map Range`, `Color Ramp` [ShaderNodeValToRGB], `Mix` [ShaderNodeMix, data_type RGBA, inputs Factor/A/B], `Bump` [ShaderNodeBump] `Strength, Distance, Height, Normal`.

1. **Edge wear (paint chipped to bare metal), bake-friendly:**
   `Bevel(Radius 0.01–0.03 m, samples 8) → Vector Math(DOT_PRODUCT, with Geometry.Normal) → Map Range(From 0.90–1.00 → 1–0)` = edge mask; `× Noise(Scale 25, Detail 6, Roughness 0.6).Fac` thresholded with `Color Ramp(0.45–0.55)`; `Mix(Factor=mask, A=paint color, B=metal color 180–255 sRGB) → Base Color`; `mask → Metallic`; `Mix(mask, paint rough 0.5, metal rough 0.3) → Roughness`. Alternative mask: `Geometry.Pointiness → Map Range(0.5–0.6 → 0–1)` (needs subdivided mesh) or `AO(inside=True, Distance 0.02).AO` inverted.
2. **Dirt in cavities:** `AO(Distance 0.1–0.3, samples 8, inside=False).AO → Invert → × Noise(Scale 8).Fac → Color Ramp(0.3–0.8)` = dirt mask; `Mix(dirt, base, dirt color 40–70 sRGB) → Base Color`; `Map Range(dirt, 0–1 → base rough–0.9) → Roughness`; dirt forces `Metallic` toward 0.
3. **Layered wear/grunge for roughness:** `Noise(Scale 4, Detail 8, Roughness 0.7).Fac` (large blotches) `+ 0.3 × Voronoi(F1, Scale 60).Distance` (speckle) `+ 0.15 × Noise(Scale 200)` (micro) → `Map Range(0–1 → ±0.15 around base roughness)`; keep final roughness inside 0.2–0.9 so highlights never clip to mirror or disappear.
4. **Imperfection maps (fingerprints/smudges/scratches):** tile a 1K grayscale imperfection image with `Texture Coordinate(UV) → Mapping(Scale 2–4)` → `Image Texture (Non-Color)` → `Math(MULTIPLY 0.1–0.25) → Math(ADD, roughness)`; same mask × 0.02 as `Bump.Height`.
5. **Color variation per instance:** `Object Info.Random → Color Ramp(3–5 stops of the palette) → Base Color`, or `Random → Map Range(0–1 → ±0.05) → Hue/Saturation/Value(Value) `. Note: Object Info is per object instance; bake collapses it, so bake per object or use `Random Per Island` for one mesh.
6. **Stylized flat palette (low-poly):** one 16×16 to 64×64 PNG, each cell a flat color; set every face's UVs to a point at a cell centre (`uv = ((cx+0.5)/W, (cy+0.5)/H)`), Image Texture `interpolation='Closest'`, `Roughness` 0.6–0.9 constant, `Metallic` 0. One material per scene → one draw call. Gradient atlas: horizontal strips 4–8 px tall, UV island stretched vertically across a strip for fake shading; keep `Closest`/`Linear` and 2–4 px padding between strips.
7. **Bake order for the above:** Base Color (`DIFFUSE`+`COLOR`), Roughness (`ROUGHNESS`), Metallic (`EMIT` trick), Normal (`NORMAL`, with Bump/Bevel contributing), AO (`AO`, world distance 0.2–1 m).

Sources: https://docs.blender.org/manual/en/5.2/render/shader_nodes/input/bevel.html · https://docs.blender.org/manual/en/5.2/render/shader_nodes/input/ao.html · https://docs.blender.org/manual/en/5.2/render/shader_nodes/input/geometry.html · https://docs.blender.org/manual/en/5.2/render/shader_nodes/input/object_info.html · https://docs.blender.org/manual/en/5.2/render/shader_nodes/textures/noise.html · https://docs.blender.org/manual/en/5.2/render/shader_nodes/textures/voronoi.html · https://docs.blender.org/manual/en/5.2/render/shader_nodes/converter/separate_color.html · https://www.blendernation.com/2019/02/10/better-edge-and-cavity-masking-with-cycles/ · https://superhivemarket.com/products/palettegrid/docs

## 6. Resolution, formats, naming

1. **Texel density targets:** mobile/VR 256–512 px/m; third-person 512–1024 px/m; first-person 1024–2048 px/m; cinematic 2048–4096 px/m (StraySpark). Environment trim/tiles: 200 px/m is a common studio standard → 1K spans 5 m, 2K spans 10 m (Frozenbyte). Keep density uniform per scene (±25 %); mismatches read worse than low absolute resolution.
2. **Resolution by asset class:** 256 — tiny props, decals, palette/gradient atlases, LOD2+; 512 — small props never approached, particles, distant set dressing; 1K — medium props, furniture, weapons at gameplay distance, modular pieces, trims; 2K — walls/floors, FP weapons, character bodies, vehicles; 4K — hero faces, FP hands/weapons, close-inspection hero assets. Power-of-two only (128–8192); non-square allowed (e.g. 2048×1024 trims).
3. **Platform caps:** Roblox uploads max 4096² but per-object budget 5×5 studs → 256, 10×10 → 512, 20×20 → 1024; formats .png/.jpg/.tga/.bmp; roughness/metalness single-channel 8-bit. Unreal/Unity/Godot accept 8K; glTF images must be PNG or JPEG (Blender exporter converts others). VRAM (BC7): 1K ≈ 1.33 MB, 2K ≈ 5.33 MB, 4K ≈ 21.33 MB; a BaseColor+Normal+ORM set ≈ 4 / 16 / 64 MB.
4. **Formats:** PNG 8-bit for Base Color, Roughness, Metallic, AO, Emissive, packed masks; PNG 16-bit (or EXR half) for Normal and Height/Displacement masters, downsample to 8-bit with dithering for engines; EXR 32-bit float only for HDR emissive, position, vector displacement; never JPEG for normals/masks. Keep 16-bit masters next to 8-bit deliveries.
5. **Naming (Unreal community standard, Allar guide):** `T_<Asset>_<Suffix>`: `_D` BaseColor/Diffuse (alt `_BaseColor`, `_BC`), `_N` Normal, `_R` Roughness, `_M` Metallic (Allar also uses `_M` for mask — pick one and document), `_O`/`_AO` Occlusion, `_E` Emissive, `_A` Alpha/Opacity, `_H` Height, `_B` Bump, `_S` Specular; packed = concatenate letters in channel order (`_ORM` = R AO, G Rough, B Metal; `_ERO` etc.). Blender glTF exporter emits `<Material>_baseColor`, `_normal`, `_metallicRoughness`, `_occlusion`, `_emissive` `(verify exact casing)`. Textures ≤ 8192, multiples of powers of two, uniform density.

Sources: https://www.strayspark.studio/blog/texture-resolution-guide-games-512-1k-2k-4k · https://wiki.frozenbyte.com/index.php/3D_Asset_Workflow:_Tile_Textures_and_Trimsheets · https://create.roblox.com/docs/en-us/art/modeling/texture-specifications · https://github.com/Allar/ue5-style-guide · https://cgcookie.com/articles/bit-depth-how-compression-affects-normal-maps · https://docs.blender.org/manual/en/5.2/addons/import_export/scene_gltf2.html

## 7. Trim sheets and tileables

1. A **tileable** repeats on both axes; a **trim sheet** is an atlas of horizontal strips that each tile along **one** axis (U); a **decal/atlas** packs non-tiling sub-textures. Many tiles on one sheet = fewer materials/draw calls.
2. Plan the sheet on a grid whose divisions are multiples of 10 (Frozenbyte) or powers of two; strip heights like 1/16, 1/8, 1/4 of V so UVs snap to exact fractions (e.g. U 0–1, V 0.40–0.50). Typical 2K trim: 2–3 large panels (256–512 px), 4–6 mid trims (64–128 px), 6–10 thin trims (16–32 px), one flat-color/gradient row.
3. Keep **2–4 px of padding** between strips at 1K, 4–8 px at 2K, and bevel/edge highlights inside the strip; mipmaps bleed across strips otherwise (Polycount edge padding).
4. Geometry must be cut where a tile changes: an atlas sub-tile can only repeat if the face edges coincide with UV 0–1 of that tile, or the shader does the wrap. Trims suit planar/extruded geometry; use a separate unique-UV bake for organic hero parts.
5. Build trims in Blender as a flat high-poly strip set (bevels, insets, bolts) baked **selected-to-active** onto a plane with `use_cage=True`, then tile-test with `Image Texture` extension `Repeat` and a 2× UV scale; fix visible seams with `Mapping` offsets or by cloning across the wrap.
6. Vertex-color or second-UV blends add location-specific dirt/wear on top of trims without new textures (Polycount threads).

Sources: http://wiki.polycount.com/wiki/Texture_atlas · http://wiki.polycount.com/wiki/Edge_padding · https://wiki.frozenbyte.com/index.php/3D_Asset_Workflow:_Tile_Textures_and_Trimsheets · https://polycount.com/discussion/comment/2737786

## 8. QA checklist for textures

1. **Albedo range:** per-channel sRGB min ≥ 30 (dielectrics; allow ≥ 20 for ≤ 1 % of pixels), max ≤ 240 for dielectrics; metal pixels 180–255. In Python read `img.pixels` (scene-linear floats for sRGB images), convert to sRGB and histogram; flag pure black (0,0,0) and pure white. Lighting/AO in albedo shows as directional gradients across flat UV islands.
2. **Metallic:** ≥ 95 % of pixels at < 0.1 or > 0.9; grey zones only at rust/dirt transitions. **Roughness:** no large regions at exactly 0 or 1; mean between 0.25 and 0.85.
3. **Normal map:** colour space Non-Color; flat areas ≈ (128,128,255); blue channel > 0.5 everywhere (glTF: "SHOULD NOT contain blue values ≤ 0.5"; check `pixels[2::4]`); orientation test — top edge of a raised detail bright green = OpenGL; confirm in a 5.1+ Normal Map node by toggling `convention` and viewing a lit sphere; length of decoded vector 0.95–1.05.
4. **Seams:** render a Cycles preview with a 50 % grey, roughness 0.5 override and inspect UV borders; margin ≥ Polycount minimum (1K → 8 px); `margin_type='ADJACENT_FACES'`; islands ≥ 2× margin apart; no overlapping islands on a bake UV (overlaps are fine only on palette/trim UVs).
5. **Texel density:** `density = sqrt(uv_area / world_area) × resolution` per face; all faces within ±25 % of the asset target; compare against neighbouring assets in the scene.
6. **Color-space audit:** every Image Texture feeding `Normal`, `Roughness`, `Metallic`, AO, Height, Alpha → `img.colorspace_settings.name == 'Non-Color'`; Base Color / Emission Color → `'sRGB'`. Normal Map node `space='TANGENT'` and `uv_map` equals the texture's UV map.
7. **Missing/unsaved textures:** `img.has_data is False`, `img.filepath` empty, or `not os.path.exists(bpy.path.abspath(img.filepath))`; generated images never saved (`img.source == 'GENERATED'`); `img.is_dirty`. Use `bpy.ops.file.report_missing_files()` before export.
8. **Export sanity:** resolution is power-of-two and within the platform cap (Roblox 1024 budget tiers); bit depth 8 for colour/masks, 16 for normal masters; file names follow §6; the glTF `metallicRoughness` image is linear with G/B populated; Unreal normal maps have Flip Green Channel ticked or were baked with `normal_g='NEG_Y'`; Unity packed map has smoothness in A, not roughness.

Sources: https://www.adobe.com/learn/substance-3d-designer/web/the-pbr-guide-part-2 · https://marmoset.co/posts/physically-based-rendering-and-you-can-too/ · https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html · http://wiki.polycount.com/wiki/Edge_padding · https://docs.blender.org/api/5.2/bpy.types.Image.html · https://www.strayspark.studio/blog/directx-vs-opengl-normal-maps-explained · https://create.roblox.com/docs/en-us/art/modeling/texture-specifications

# PBR texturing, procedural materials and baking

Distilled from `research/pbr-texturing-and-baking.md` (Adobe PBR guide, Marmoset, glTF 2.0 spec,
Blender 5.2 manual and source, engine docs). `scripts/blender/material_kit.py` implements the recipes;
`scripts/blender/bake_textures.py` implements the bake.

## Value rules (metal / roughness)

- **Base colour of dielectrics**: sRGB 30–50 darkest, 240 brightest. No lighting, no AO baked in.
- **Raw metals**: sRGB 180–255. A "metal" darker than that is paint, rust or dirt: metallic 0.
- **Metallic is binary**: 0 or 1, grey only on transitions. QA: histogram bimodal.
- **Roughness is the artistic map**: never flat; keep inside 0.2–0.9; metals never 0. Unity and gloss
  workflows use smoothness = 1 − roughness.
- **Dielectric specular** is fixed (IOR 1.5, 4%); do not touch `Specular IOR Level` for dielectrics.
- Python colour sockets are **scene-linear**: convert hex/sRGB before `default_value`
  (`material_kit.hex_to_linear`). 180 sRGB → 0.456 linear; writing 0.7 "because it looks right in sRGB"
  gives a 2x too bright albedo.
- Judge albedo under **Khronos PBR Neutral** or **Standard**, never AgX or Filmic.

## Texture set per target

| Target | Colour | Rough / metal / AO | Normal green | Notes |
|---|---|---|---|---|
| glTF (Godot, three.js, Roblox glTF, Blender) | baseColor sRGB | metallicRoughness: **G = roughness, B = metallic**; occlusion R; may be one ORM image | **+Y (OpenGL)** | The exporter builds this from the Principled links; occlusion only through a `glTF Material Output` node group with an `Occlusion` input |
| Unreal | BaseColor sRGB | ORM **R = AO, G = rough, B = metal**, sRGB off | **−Y (DirectX)**: tick *Flip Green Channel* on import, or bake with `normal_g='NEG_Y'` | `T_<Asset>_<Suffix>` |
| Unity URP | Base Map sRGB | Metallic map **R = metal, A = smoothness**, G = AO | +Y | smoothness = 1 − roughness |
| Unity HDRP | Base Map sRGB | Mask map R metal, G AO, B detail, A smoothness | +Y | |
| Roblox SurfaceAppearance | ColorMap | **separate** 8-bit RoughnessMap and MetalnessMap, no AO slot | +Y only, flat = (127,127,255) | one material per MeshPart, UVs in 0–1, 1024 max for a 20x20 stud object |

Colourspace in Blender: `sRGB` for base colour and emissive; `Non-Color` for normal, roughness,
metallic, AO, height, masks, ORM. PNG does not store it: set it again after loading.

## Baking (Cycles only)

- Target: an Image Texture node that is **selected and active** in every material of the baked object
  (5.0 rule; a material without one bakes nothing).
- Base colour = `type='DIFFUSE', pass_filter={'COLOR'}` (lighting-independent). Roughness =
  `ROUGHNESS`. Normal = `NORMAL`, tangent, +X +Y +Z (captures Bump and Normal Map nodes in the shader).
  AO = `AO`. Emissive = `EMIT`. **Metallic, alpha, height have no pass**: route the socket's source
  into Emission and bake `EMIT`.
- High to low: select the high objects, make the low active, `use_selected_to_active=True`, either a
  cage (`use_cage`, `cage_extrusion` ≈ 1–2% of the object size) or `max_ray_distance`, not both.
- Samples: 8–16 for colour, roughness, normal, emit; 64–256 for AO. Margin ≥ 2 px at 256, 4 at 512,
  8 at 1K, 16 at 2K, `margin_type='ADJACENT_FACES'`.
- Precision: normal and height targets `float_buffer=True` (16-bit PNG on save), everything else
  8-bit. Save with `Image.save()`, never `save_render` for data maps.
- After baking, build the export material that reads the images (`bake_textures.py --rewire`) so glTF
  and FBX carry textures; keep the procedural material in the .blend for re-bakes.

## Procedural recipes that read as professional

1. **Edge wear** (paint chipped to metal): `Bevel(radius 0.01–0.03 m, samples 8)` · dot ·
   `Geometry.Normal` → `Map Range(0.90–1.00 → 1–0)` = edge mask; multiply by
   `Noise(scale 25, detail 6).Fac` through a `Color Ramp(0.45–0.55)`; mask drives `Mix(paint, metal)`
   → Base Color, mask → Metallic, mask → `Mix(rough 0.5, rough 0.3)` → Roughness.
2. **Dirt in cavities**: `AO(distance 0.1–0.3, inside off).AO` inverted × `Noise(scale 8)` →
   `Color Ramp(0.3–0.8)`; mixes a dark colour (sRGB 40–70) into Base Color, pushes Roughness toward
   0.9, forces Metallic to 0.
3. **Roughness breakup**: `Noise(scale 4, detail 8)` large blotches + 0.3 × `Voronoi F1(scale 60)`
   speckle + 0.15 × `Noise(scale 200)` micro → `Map Range` to ±0.15 around the base roughness.
4. **Imperfections**: a tiled 1K grayscale imperfection image (Non-Color) × 0.1–0.25 added to
   roughness, the same mask × 0.02 as `Bump.Height`.
5. **Per-instance variation**: `Object Info.Random → Color Ramp` of the palette (bakes per object), or
   `Geometry.Random Per Island` within one mesh.
6. **Flat palette (low-poly)**: a 16x16 to 64x64 PNG of colour cells, every face's UVs collapsed to its
   cell centre, Image Texture interpolation `Closest`, constant roughness 0.6–0.9, metallic 0. One
   material for the whole scene. Gradient atlas variant: horizontal strips with islands stretched
   vertically for fake shading, 2–4 px padding.
7. **Bake order**: base colour, roughness, metallic, normal, AO; then ORM pack if the target wants it.

## Sizes, formats, names

- Resolution by class: 256 tiny props, decals, palettes; 512 small props; 1K medium props, weapons at
  gameplay distance, trims; 2K walls, floors, first-person weapons, character bodies; 4K hero faces,
  first-person hands. Square power of two; non-square only for trims (2048x1024).
- Formats: PNG 8-bit for colour, roughness, metallic, AO, emissive, masks; PNG 16-bit for normal and
  height masters (ship 8-bit copies when the engine does not need more); EXR only for HDR data. Never
  JPEG for normals or masks.
- Names: `T_<Asset>_BaseColor`, `_Normal` (OpenGL unless `_Normal_DX`), `_Roughness`, `_Metallic`,
  `_AO`, `_Emissive`, `_Height`, `_ORM`. Say the normal convention and packing order in the README.

## Texture QA (what the tech artist checks)

Albedo min ≥ 30 sRGB and max ≤ 240 for dielectrics, metals 180–255; metallic ≥ 95% of pixels under
0.1 or over 0.9; roughness mean 0.25–0.85 and no large flat regions at 0 or 1; normal blue channel
> 0.5 everywhere and flat areas ≈ (128,128,255); no seams on a grey-override render; texel density
within ±25% across the asset; every data image Non-Color; nothing missing (`img.has_data`,
`os.path.exists`). `material_kit.texture_stats(path)` prints these numbers.

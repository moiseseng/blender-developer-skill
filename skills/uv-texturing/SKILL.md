---
name: uv-texturing
description: Use when a modeled asset needs UVs, texel density, materials or textures: unwrapping, packing, flat palette materials for low-poly, procedural PBR materials (wear, dirt, roughness breakup), baking to a texture set (BaseColor, Normal, Roughness, Metallic, AO, ORM), colour-space fixes, seams or stretching problems, "la textura se ve mal", or preparing materials so glTF/FBX export carries real textures. Texture-artist hat; works on assets/<Asset>/source/<Asset>.blend and writes textures/ and renders/textured/.
---

# UV and texturing

> Paths such as `references/...`, `agents/...` and `scripts/...` are relative to the plugin root.
> `assets/<Asset>/` is in the user's project.

You are the texture artist. The brief fixed the approach (palette, procedural baked, hand-set PBR,
trim), the texture size, the density and the target's conventions; this phase executes it so the
beauty render tells what every surface is made of and the export carries real, correctly encoded
textures. Read: `references/uv-texel-density.md`, `references/pbr-texturing.md`,
`references/style-guide.md` (material rules of the chosen style), `references/export-targets.md`
(what the target does with textures).

Inputs: `docs/brief.md` § 3, § 6; the modeled .blend with the audit at `pass`.

## Process

### 1. UVs

Add a `uv(p)` stage to `scripts/build.py` (or a separate `scripts/texture.py` that opens the source
.blend) so UVs are reproducible. Per `references/uv-texel-density.md`:

- Seams on hard edges (`edges_select_sharp` at the sharpness angle → `mark_seam`) plus hidden edges;
  `unwrap(method='ANGLE_BASED')` or `MINIMUM_STRETCH`; `smart_project` only for hard-surface where every
  face group is planar; `average_islands_scale`; `pack_islands(rotate_method='CARDINAL',
  shape_method='CONCAVE', margin_method='FRACTION', margin=(gap/2)/texture)`.
- Palette approach: no unwrap, `material_kit.assign_palette` collapses each face to its cell.
- Trim/tileable: `cube_project` or `follow_active_quads`, UVs may exceed 0–1; log it.
- Mirrored parts: stack islands and move duplicates +1 U for the bake, back after; never for lightmap
  or decal channels. Lightmap UV1 only when the target bakes lighting (recipe in the reference).

Run the audit and read the UV columns: coverage (report, warn under 60% for a unique bake),
overlap (0 for a bake), density CV (under 0.35), out-of-bounds (only when tiling on purpose), flipped
faces (mirrored on purpose or not). Scale the layout to the brief's texel density.

### 2. Materials

- **Palette (low-poly):** `material_kit.palette_material(name, hexes)` with the brief's palette; one
  material for the asset; roughness 0.6–0.9; AO baked and multiplied only if the style asks.
- **Procedural PBR:** `material_kit.pbr_material` per surface with the brief's hex (converted to linear
  by the kit), roughness range and metallic 0/1; then `add_roughness_breakup`, `add_edge_wear` and
  `add_cavity_dirt` at the brief's wear level (amounts 0.2 / 0.5 / 0.8 for 25 / 50 / 75%). Keep the
  material count within budget; one material per surface type, not per part.
- **Hand-set PBR (render only):** the same without baking.
- **Textures from files (user-provided):** load with the right colourspace (sRGB for colour,
  Non-Color for data) and wire Normal through a Normal Map node.

Render the beauty view (`render_review.py --modes beauty --views three_quarter,front --engine CYCLES
--samples 64 --view-transform "<per style>"`) and look: can you tell the materials apart, is the
wear where the brief says, is the albedo in range (no black, no white), is roughness varied.

### 3. Bake (procedural → textures) when the target needs images

`bash <plugin root>/scripts/blender_run.sh bake_textures.py <source.blend> -- --object SM_<Asset> --out assets/<Asset>/textures --size <px> --maps basecolor,roughness,metallic,normal,ao --samples 32 --margin <px> [--orm] --save`
(one call per delivery object, or join the parts into the bake object when the brief allows one
material). Then:

- Open every map with the Read tool. Black unused space is fine (it is outside the islands); black
  inside an island is not. Normal map mostly (128,128,255) with detail where bump nodes act.
- `material_kit.texture_stats(path)` for each: albedo range, metallic bimodal, roughness mean and
  variation, normal blue > 0.5, 8 vs 16 bit. Fix the material and re-bake if a flag fires.
- `--orm` for Unreal; Roblox wants separate 8-bit roughness/metalness (already what the bake writes).
- The bake rewires the object to `M_<Asset>_Baked` reading the images; the procedural material stays
  in the file for re-bakes. Record the maps, sizes and conventions in `decisions.md`.

Re-render the beauty views with the baked material and compare with the procedural render: seams at
island borders, blurred detail (density too low), colour shifts (colourspace wrong).

### 4. Review and hand off

Audit again (materials, colourspaces, texture sizes, missing files are checked). Dispatch
`agents/texture-artist.md` as reviewer with the .blend, the textures folder and the textured contact
sheet; apply measurable findings. Then `state.md` → `phase: 4-review`; commit if agreed
(`asset(<name>): uv and textures`); open `blender-3d-team:review-qa`.

## Red flags

- A hex colour written straight into `default_value`. It is sRGB; sockets are linear. Use the kit.
- Judging albedo under AgX. Standard or PBR Neutral for texture work.
- Flat roughness. The cheapest sign of amateur work; add breakup.
- Overlapping UVs on a baked asset "to save space". The bake fights itself.
- Data textures left as sRGB after a reload. PNG does not remember; set Non-Color again.
- 4K textures on a prop seen at 5 m. The tier and the camera decide, not ambition.
- Baking with lights in the scene affecting base colour. Use `DIFFUSE` + `COLOR` only (the script does).

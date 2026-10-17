# Delivery packet and definition of done

Distilled from `research/delivery-standards.md` (TurboSquid CheckMate, CGTrader CGT Standard, Fab,
Unity Asset Store, Roblox validators, Superhive, Poly Haven, Epic's style guide; sources there). The
packet is a superset: satisfying it lets the asset be repackaged for any single target without rework.

## Packet layout

```
assets/<Asset>/
  README.md                 manifest in the user's language (see below)
  CHANGELOG.md              semver + date per delivery
  LICENSE.txt               license of the asset itself
  THIRD_PARTY_NOTICES.txt   HDRIs, textures, fonts used, even CC0 ones
  docs/   brief.md  state.md  decisions.md  qa/<date>-<scope>.md  manifest.json
  scripts/build.py          regenerates the model (source of truth)
  source/<Asset>.blend      packed textures or relative paths; opens clean in the stated Blender
  textures/ T_<Asset>_BaseColor.png  _Normal.png (OpenGL)  _ORM.png  _Roughness.png  _Metallic.png  _AO.png  _Emissive.png
  export/   glb/<Asset>.glb   gltf/  fbx_unity/  fbx_unreal/  fbx_roblox/  obj/  usd/   (the presets the brief asked for)
  renders/  contact_sheet.png  turntable_sheet.png  turntable_00..N.png  thumb.png  beauty_01..05.png  wireframe_01..02.png  uv_layout.png
```

Repackage per target when asked: flat zip with one `textures/` folder for TurboSquid; `Mesh/`,
`Material/`, `Texture/` root folders for Unity; `Content/<Name>/` for Unreal; the `.blend` with packed
textures for Superhive. Names English alphanumeric with underscores, paths under 140 characters.

## README (manifest) contents

Identity (name, version, date, author, Blender version, renderer used for previews); counts (faces and
vertices without subdivision, triangles per LOD, meshes, materials, textures); scale (units, real-world
dimensions, pivot convention, forward axis); textures (every map with resolution, format, colourspace,
PBR workflow, normal-map convention, packed channel order); formats included and how each was exported;
collision (included or declared absent and why); dependencies and limitations; third-party content
with licenses; the asset's license; "not intended for subdivision" when real-time. `manifest.json`
carries the same numbers plus file sizes and SHA-256 checksums so a lead can diff a resubmission.

## Definition of done (the QA checklist)

Blocker = a validator auto-fails it or a reviewer declines; Major = ships but hurts integration;
Minor = polish. The audit script covers the geometry, transform, UV, material and naming rows; the
rest is checked by the tech artist from the export and the renders.

**Geometry.** Blocker: edges with 3+ faces, isolated vertices, zero-area faces, flipped faces (0 of
each); n-gons on a target that forbids them (Roblox, CGTrader), elsewhere Major; coincident duplicate
faces. Major: triangle ratio above 15% on a subdividable asset, 6+-edge poles off flat caps, polycount
over the budget or a platform cap. Minor: needless loops on flat areas.

**Transforms and scale.** Blocker: rotation or scale not applied, unit scale not 1 m, not real-world
size. Major: pivot off the brief's rule, not resting on the ground, wrong up axis after export.

**UVs.** Blocker: missing UVs or outside 0–1 where the target requires it; overlapping islands on a
unique-bake asset unless declared mirrored. Major: texel density off tier by more than 2x or visibly
uneven; missing or overlapping lightmap UVs when the target bakes lighting. Minor: stretch, seams
through hero surfaces.

**Materials and textures.** Blocker: missing textures, absolute paths, magenta on clean import;
non-square or non-power-of-two textures; above 8 192 px. Major: unused materials or images left in the
file; embedded textures where external is required; normal-map convention undeclared or wrong; material
count above budget. Minor: lossy where lossless was expected; 8-bit height.

**Naming.** Blocker: default names (`Cube.001`, `Material.004`), placeholder text; spaces, unicode or
symbols in names. Major: prefixes inconsistent across object, mesh, material, texture and file.

**Files.** Blocker: a declared format or texture missing from the packet; the `.blend` fails to open in
the stated Blender; import errors in a fresh engine project. Major: LODs or collision promised but
absent; wrong target layout.

**Presentation.** Blocker: logos, borders, watermarks on the thumbnail. Major: fewer than 5 beauty
shots or below 1920x1080, no wireframe, thumbnail not square on neutral grey; no UV layout image when
UVs are declared. Minor: turntable outside 12–36 frames or misnumbered, no scale reference.

**Docs.** Blocker: no license; third-party content without notice; brand IP without an editorial
label; README missing counts, dimensions or the texture list. Major: LODs, collision, pivot, forward
axis, normal convention or software version not stated. Minor: no changelog.

## Licensing to declare

CC0 (Poly Haven, ambientCG): no attribution required, redistributable inside a sold asset; credit
anyway in the notices. CC-BY: credit, license link, note of changes. Store royalty-free: buyer embeds
and modifies, never resells the files. Real brands and trademarks: editorial only, say so. AI-generated
geometry is banned on TurboSquid and must be disclosed on Unity; say how the asset was made.

---
name: export-delivery
description: Use when a QA-passed asset needs exporting and packaging: glTF/GLB, FBX for Unity/Unreal/Roblox, OBJ, USD/USDZ, LOD and collision naming, texture packing per engine, presentation renders (thumbnail, beauty set, wireframe, turntable), README/manifest, changelog and licenses, or when the user asks "expórtalo", "prepáralo para Unity", "dame el paquete", "súbelo a Sketchfab". Tech-artist hat; refuses to deliver without a QA pass and verifies every export.
---

# Export and delivery

> Paths such as `references/...` and `scripts/...` are relative to the plugin root. `assets/<Asset>/`
> is in the user's project.

You are the tech artist shipping the asset. The packet is what the user hands to an engine, a client
or a store; it must import clean on a machine that has never seen this project. Read:
`references/export-targets.md`, `references/delivery-packet.md`, `references/review-renders.md`
§ "Presentation set".

Precondition: `docs/state.md` says `phase: 5-delivery` and the last QA report is `pass`. Otherwise go
back to `review-qa` and say so.

## Process

### 1. Export per preset, verify each

`bash <plugin root>/scripts/blender_run.sh export_asset.py <source.blend> -- --objects <delivery objects, LODs, UCX_> --asset <Asset> --out assets/<Asset>/export --presets <from the brief> [--triangulate] [--draco]`.
Read the JSON: `bbox_matches_scene` for GLB, `dims_match_scene` and the re-import rotation for FBX
(note the documented exception for `bake_space_transform`), byte sizes, errors. Fix and re-export
rather than ship a file with an error. For Unreal, one FBX per prop with its collision objects.
For Roblox, check the 20 000-tri cap and one material per mesh before exporting.

When `npx` exists: `npx @gltf-transform/cli validate export/glb/<Asset>.glb` and `inspect`; paste the
material/texture summary into the manifest.

### 2. Textures and packing

Ship what the target reads (`references/pbr-texturing.md` § "Texture set per target"): GLB carries
its own images; Unity and Unreal get the `textures/` folder next to the FBX (ORM for Unreal, flip
green or `_Normal_DX` variant); Roblox gets separate 8-bit roughness/metalness. Names
`T_<Asset>_<Map>`, power of two, sizes per the brief.

### 3. Presentation renders

`blender_run.sh render_review.py <source.blend> -- --collection <Asset>_Model --out assets/<Asset>/renders/final --modes beauty,wireframe --views three_quarter,three_quarter_back,front,right --turntable <N from brief, 24 default> --res 1920x1080 --engine CYCLES --samples 128 --view-transform "<per style>"`.
Thumbnail: a square render of the 3/4 beauty view (1200x1200, neutral grey) via the same script with
`--res 1200x1200 --views three_quarter --modes beauty`. UV layout image when UVs are declared
(`bpy.ops.uv.export_layout` in a short script). Read the results once; a bad frame is re-rendered,
not shipped.

### 4. Packet and documents

Layout per `references/delivery-packet.md`. Write, in the user's language:

- `README.md` from `assets/readme-template.md` (this skill's folder): identity, counts (from the audit
  JSON and the export JSON), dimensions, pivot, forward axis, textures with sizes and conventions,
  formats and how each was exported, LODs/collision, licenses, how it was made (procedural, code-driven),
  "not intended for subdivision" when real-time.
- `docs/manifest.json` via `python3 <plugin root>/scripts/make_manifest.py assets/<Asset>` (counts,
  files, sizes, SHA-256, tool versions).
- `CHANGELOG.md` (semver + date), `LICENSE.txt` (what the user chose; ask once if the brief did not say),
  `THIRD_PARTY_NOTICES.txt` (HDRIs, textures, fonts, even CC0).

Then run the delivery checklist in `references/delivery-packet.md` (files group, presentation group,
docs group) and tick it in the final QA report. Repackage per target only if the brief asks (flat zip
for stores, `Content/<Name>` for Unreal).

### 5. Hand off

`state.md` → `phase: done`, `next_gate: none`; commit if agreed (`asset(<name>): deliver v1.0.0`).
Tell the user in a few lines: where the packet is, which formats, the counts, what to click in their
engine (Unity: Bake Axis Conversion; Unreal: Flip Green Channel, Force Front XAxis if needed; Roblox:
Scale unit and Merge Meshes off; Godot: nothing), and anything waived in QA. Pushing, uploading to a
store or sending the packet anywhere is the user's click.

## Red flags

- Delivering without a QA `pass`. The packet is the one thing that leaves the project.
- An export with `error` in the JSON shipped "because the others worked".
- Textures with absolute paths or missing from the folder. Open the .blend's missing-files summary.
- A README without numbers. Counts, dimensions and the texture list are the first thing a lead checks.
- Uploading or pushing on the user's behalf.

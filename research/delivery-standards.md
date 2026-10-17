# Professional 3D Asset Delivery Standards (marketplace + studio QA)

Researched 2026-10-17 from primary marketplace pages. Items marked `(verify)` come from secondary sources, search snippets, or pages that would not load (403/JS-only). Numbers are quoted as published; marketplaces change them.

## Contents
1. [Marketplace technical requirements](#1-marketplace-technical-requirements) — TurboSquid, Fab, Unity, CGTrader, Roblox, Superhive, Sketchfab
2. [Reference conventions from asset libraries](#2-reference-conventions-from-asset-libraries) — Poly Haven, KitBash3D, UE style guide, Blender bundles
3. [Preview / presentation requirements](#3-preview--presentation-requirements)
4. [Documentation requirements](#4-documentation-requirements)
5. [Folder structure conventions](#5-folder-structure-conventions)
6. [Licensing basics](#6-licensing-basics)
7. [Common rejection reasons and the implied definition of done](#7-common-rejection-reasons-and-the-implied-definition-of-done)
8. [Studio-side acceptance](#8-studio-side-acceptance)
9. [Consolidated delivery packet spec](#9-consolidated-delivery-packet-spec)
10. [QA checklist with severities](#10-qa-checklist-with-severities)

---

## 1. Marketplace technical requirements

### 1.1 TurboSquid (CheckMate Pro/Lite + product imagery)
The CheckMate spec pages themselves now 404; requirements below come from the CheckMate Pro v2 checklist, the 2012 spec-update post (section numbers), the CheckMate category pages, and TurboSquid training pages.

| Area | Requirement | Source |
|---|---|---|
| Topology | Pro: "Polygonal Quads/Tris" or "Quads only" (§3.5.3); Lite also allows "Tris only" (§3.3.3). No isolated vertices. Pro v2: poles with 6+ edges only on flat pie-shaped caps; no unnecessary edge detail; no crease values > 0. | checklist, spec-updates, ?p=5284 |
| Quad ratio | Training: quad-based, max 10–15% triangles for subdividable models `(verify as spec clause)` | ?p=13833 |
| Clean geometry | No coincident (coplanar) faces, no coincident vertices, no isolated vertices, normals facing outward. Intersecting faces that cut through each other are fine. | clean-geometry |
| Scale | Real-world scale, any unit system; metric cm/m recommended; never "generic units"; set System Unit Scale, not just display units. | checklist, real-world-scale |
| Origin / pivot | Pivot at world 0,0,0; model sits on or slightly above the ground plane; pivot centered in X/Z at base of bounding box; up-axis = world up. Multi-part models grouped so one selection moves everything. | centering-at-the-origin |
| Transforms | Reset: position/rotation 0, scale 100% / 1.0 before delivery. | resetting-transforms |
| Scene hygiene | Objects in a named layer; remove extraneous splines, helpers, hidden objects; unused materials removed from the file. | checklist, texture-references |
| Textures | §2.1.4: no texture paths referenced by the model; paths stripped. Meaningful names on bitmaps and materials. All textures included; non-native files must "open without errors and include all textures" (Lite). | spec-updates, texture-references, ?p=6038 |
| Archive | §3.2.4.2: each archive flat, no folders; or textures in a single subfolder beneath the main file; or one named textures ZIP as a supporting item. | spec-updates, texture-references |
| Declared data | Poly and vertex counts recorded without subdivision; geometry type; native format + version + renderer. | checklist |
| Description | Must state third-party renderer, all texture resolutions, unit scale and model dimensions; realtime models add "This model is not intended for subdivision". | checklist |
| Naming (product) | Noun or adjective-noun, spelled correctly, first letter capitalized. | checklist |

Sources: https://blog.turbosquid.com/2013/09/11/checkmate-pro-v2-checklist/ · https://blog.turbosquid.com/2012/07/23/checkmate-specification-updates · https://blog.turbosquid.com/?p=5284 · https://blog.turbosquid.com/?p=6038 · https://resources.turbosquid.com/training/modeling/clean-geometry/ · https://resources.turbosquid.com/training/modeling/real-world-scale/ · https://resources.turbosquid.com/training/training-scene-organization/resetting-transforms/ · https://resources.turbosquid.com/training/training-scene-organization/centering-at-the-origin/ · https://resources.turbosquid.com/checkmate/checkmate-product-presentation/checkmate-texture-references/ · https://resources.turbosquid.com/?p=13833

### 1.2 Fab (Epic)
`www.fab.com/technical-requirements` returned 403; data is from the Epic developer-docs mirror and the publishing guide.

| Area | Requirement |
|---|---|
| Formats | Engines: UEFN, Unreal, Unity. Exchange: FBX, GLB, GLTF, OBJ, USD, USDZ. DCC: 3ds Max, Blender, Cinema 4D, Maya. |
| Size limits | UE project 15 GB; up to 3 additional files at 6 GB each (18 GB total); other file types 6 GB per file; gallery images < 25 MB combined; 3D previews < 500 MB. |
| Gallery media | Images min 1920×1080, JPEG/PNG, < 3 MB each. Video 1920×1080, MP4/MOV/WEBM, ≤ 300 MB. Thumbnail required; exact thumbnail pixel size `(verify)`. |
| 3D models | No visual defects; no material defects or visible seams; proper collision where applicable; proper LODs and state which are included; modular kits: pivots placed so meshes assemble smoothly; no Z-fighting/overlapping polygons; "products must be complete" and "function as you describe". |
| Textures (UEFN) | Power-of-2 dimensions; max 8192 px (≤ 4096 recommended); asset paths ≤ 140 characters. |
| Structure | UE: `Content/` must contain exactly one subdirectory named after the product; English alphanumeric names; no vague names ("Assets", "NewFolder"); all redirectors cleaned; unused plugins disabled; one `.uefnproject` per zip, no `.py`. |
| Minimum content | Props (realistic): 1 unique model; simple stylized props ~25; materials/textures: 1 unique material; characters: 1 full model. |
| Listing fields | Title (ideally < 30 chars), description, category, tags, thumbnail, media gallery, license + price, technical details (auto-filled from files when possible, editable). Statuses: Draft → Pending Approval → Changes Needed / Approved → Live; Declined = resubmit as new listing. |
| Licenses | Standard (Personal: buyer < $100k revenue/12 mo; Professional: > $100k) or CC-BY (free only). Standard forbids standalone resale/redistribution. |

Sources: https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab · https://dev.epicgames.com/documentation/en-us/fab/publishing-assets-for-sale-or-free-download-in-fab · https://dev.epicgames.com/documentation/en-us/fab/licenses-and-pricing-in-fab · https://www.fab.com/technical-requirements (403)

### 1.3 Unity Asset Store (guidelines last updated 2026-05-20)
| Area | Requirement |
|---|---|
| Mesh (§2.4) | Formats .fbx/.dae/.abc/.obj. Position/rotation 0, scale 1. +Z forward. 1 unit = 1 m. Pivot at bottom-center or logical rotation point. Photoscanned/AI meshes retopologized; no "unreasonably excessive" density. |
| Materials/textures | Every visible mesh has material + prefab. PBR sets: albedo, normal, metallic/specular, smoothness/roughness. Lossless formats (.png/.tga/.psd/.psb). Tileables seamless. Normal maps flagged as Normal Map. Power-of-2 where appropriate. |
| LOD / collision | LOD meshes wired into a LOD Group with all levels configured. Static models have colliders fitting the model. |
| Organization | Root folder with Mesh/Material/Texture subfolders; paths < 150 chars; no duplicate files. Large environments split into separate .fbx containers. |
| Package | ≤ 6 GB (UPM 700 MB); zero errors/warnings after setup; demo scene required for 3D; docs (.txt/.md/.pdf/.html/.rtf) if code/config; Third-Party Notices file; avoid GPL/LGPL/attribution-required dependencies; AI use disclosed. |
| Listing tech details | Number of unique assets, polygon count, texture dimensions, render pipelines, texture map types, dependencies/limitations. Min Unity 2022.3; Unity 6.5+ needs URP/HDRP. |
| Key images | Icon 160×160 (no text); Card 420×280; Cover 1950×1300; Social 1200×630 (no text); screenshots ≥ 1200 px wide; video MP4 ≤ 500 MB. No Unity logos, sale banners, default skybox, watermarks. |

Sources: https://assetstore.unity.com/publishing/submission-guidelines · https://support.unity.com/hc/en-us/articles/210122403-What-makes-a-great-key-image-and-are-there-any-size-restrictions-

### 1.4 CGTrader (CGT Standard, automated validator)
Enforced by the validator (badge only if all pass): binary FBX only; no unsupported objects (cameras, lights, dummies); geometry has no n-gons, no faceted surfaces where smoothing is expected, manifold (no edge shared by > 2 faces, no disconnected vertices); PBR workflow; textures external (not embedded), square, power-of-2 in {512, 1024, 2048, 4096}; all materials assigned; UVs fully unwrapped with no overlapping islands; names use allowed characters only. The blog *recommends* ≥ 2048 px textures `(verify)`. The open-source checker `cgtcheck-open` (Blender 2.93+) emits JSON with expected/found per check (e.g., triangle count, fully faceted objects).
Sources: https://www.cgtrader.com/blog/cgt-standard-what-it-means-for-3d-model-buyers · https://www.cgtrader.com/blog/mastering-cgtraders-quality-standard-geometry-requirements · https://github.com/CGTrader/cgtcheck-open · https://help.cgtrader.com/hc/en-us/articles/12602200107281-About-model-standard (403)

### 1.5 Roblox (Creator Store / Marketplace / UGC)
| Area | Requirement |
|---|---|
| General mesh | ≤ 20,000 triangles per mesh; quads where possible, no n-gons; watertight, no holes or backfaces; no zero-thickness geometry; one material per MeshPart; single UV set; UVs inside 0–1 (overlap permitted for general meshes). |
| Textures | Up to 4096×4096 (general); Marketplace accessories ≤ 2048×2048; PBR maps 1024 cited by a secondary source `(verify)`. Formats .png/.jpg/.tga/.bmp. Albedo RGB 24-bit; normal RGB OpenGL tangent space; roughness/metalness/emissive 8-bit grayscale. Guidance: 256 px for 5-stud, 512 for 10-stud, 1024 for 20-stud objects. |
| Rigid accessories | Single mesh, ≤ 4,000 tris, watertight; ≥ 1 correctly named attachment (HatAttachment, HairAttachment, BodyBackAttachment…); bounding limits per body scale (e.g., Normal Hat 1.87×2.5×1.87 studs); Material Plastic, Transparency 0, VertexColor 1,1,1; no scripts/extra parts. |
| Rigs | Bones frozen (scale 1, rot 0), root at 0,0,0; ≤ 4 bone influences per vertex; one animation track per export; cages suffixed `_InnerCage` / `_OuterCage`. |
| Validator | Rejects: UVs outside [0,1], zero-area UV or mesh triangles, vertex colors, n-gons, zero dimensions on any axis, rig attachments rotated (must be 0,0,0), custom attributes/scripts/tags, wrong CollisionFidelity. |
| Blender export | Unit System None or FBX "Apply Scalings: FBX Unit Scale" (or scale 0.01); exporter Forward = Z, Up = Y; Path Mode Copy + Embed Textures; disable Add Leaf Bones; glTF needs no scale fix; import with Scale Unit = Stud. 1 m = 25/7 studs (1 stud = 0.28 m) `(verify)`. |

Sources: https://create.roblox.com/docs/en-us/art/modeling/specifications · https://create.roblox.com/docs/en-us/art/modeling/texture-specifications · https://create.roblox.com/docs/en-us/avatar/rigid-accessories/specifications · https://create.roblox.com/docs/art/validation-errors · https://create.roblox.com/docs/en-us/art/blender · https://create.roblox.com/docs/en-us/art/modeling/export-requirements · https://robloxapi.github.io/ref/enum/MeshScaleUnit.html

### 1.6 Superhive (formerly Blender Market; blendermarket.com redirects)
.blend must open and work in the current official Blender; logical English names for meshes, materials, textures, armatures, bones, scenes (no `Cube.001` / `Material.004`); textures packed or in a textures folder with relative links; orphan data removed; render-ready (download → open → F12 matches product images); ≤ 5 GB per file (1 GB chunks preferred); ≥ 5 images, 2:1 aspect, ≥ 1200 px wide (1200×600), PNG/JPG; English description; written docs + FAQ; support within 72 h; no Blender logos in images (immediate rejection).
Sources: https://support.superhivemarket.com/article/253-general-product-guidelines-for-uploading-products · https://support.superhivemarket.com/article/186-why-products-get-rejected

### 1.7 Sketchfab (viewer/hosting limits; Store sales moved to Fab `(verify)`)
Zip = model + .mtl (OBJ) + textures (root or subfolder); format priority FBX > glTF/GLB > BLEND > OBJ…; textures ≤ 75 MB each, ≤ 8192×8192, JPG/PNG/TIFF/TGA/DDS/GIF/BMP/VTF (converted to PNG); ≤ 100 materials per model; no special characters in material/texture names; join meshes sharing a material; RGB/linear color only. Upload size: Premium 500 MB confirmed; Basic 100 MB / Pro 200 MB `(verify)`.
Sources: https://help.sketchfab.com/en/articles/16152560-uploading-3d-models · https://help.sketchfab.com/en/articles/16152646 · https://help.sketchfab.com/en/articles/16152181-premium-membership

## 2. Reference conventions from asset libraries
- **Poly Haven model standard** (page is JS-only; from indexed text `(verify)`): texture files `slug_map.format` (e.g., `marble_bust_01_diff.png`), both GL and DX normals, 16-bit PNG, alpha as separate map and in diffuse alpha; Blender collection named exactly the slug, no cameras/lights; single mesh/material named as slug, multiples prefixed `slug_part`. https://docs.polyhaven.com/en/technical-standards/models
- **KitBash3D**: kit = 3D file + textures folder; PBR set Base Color, Roughness, Metalness, Opacity, Emission, Normal, Height (+ MADS/ARM packed for UE/Unity); 2K and 4K PNG for DCCs; UE packages at 1K/2K/4K; UE folders Blueprints / Levels / Materials / Static Meshes / Textures `(verify)`. https://help.kitbash3d.com/en/articles/6449589-what-comes-with-a-kit · https://help.kitbash3d.com/en/articles/11698511-structural-updates-to-kits-for-unreal-engine
- **UE community style guide (Allar)**: `Prefix_BaseAssetName_Variant_Suffix`; `SM_`/`S_` static mesh, `SK_` skeletal, `M_` material, `MI_` instance, `T_` texture with `_D _N _R _M _O _E _A`, packed `_ORM`; PascalCase, no spaces/unicode/symbols; all content under `Content/<ProjectName>/`; no type folders ("Meshes", "Textures"). Content checks: no missing UVs, non-overlapping lightmap UVs, collision on every mesh, power-of-2 textures ≤ 8192, zero errors/warnings. https://github.com/Allar/ue5-style-guide
- **Blender official asset bundles**: CC0 only; every asset carries tags, description, license metadata; engine-tagged materials; dragging in must not alter scene settings; must work offline; lightweight textures. https://developer.blender.org/docs/features/asset_system/asset_bundles/guidelines/
Sources: https://docs.polyhaven.com/en/technical-standards/models · https://help.kitbash3d.com/en/articles/6449589-what-comes-with-a-kit · https://help.kitbash3d.com/en/articles/11698511-structural-updates-to-kits-for-unreal-engine · https://github.com/Allar/ue5-style-guide · https://developer.blender.org/docs/features/asset_system/asset_bundles/guidelines/

## 3. Preview / presentation requirements
| Item | TurboSquid | Unity | Fab | Superhive |
|---|---|---|---|---|
| Thumbnail / search image | Square ≥ 1200×1200, background RGB 247,247,247, whole model, no borders/QR/logos/overlays | Icon 160×160, Card 420×280, Cover 1950×1300, Social 1200×630 | Thumbnail required `(verify size)` | 2:1 featured image ≥ 1200 px wide |
| Beauty shots | ≥ 5, ≥ 1920×1080; multiple angles, close-ups, context, scale reference, studio lighting | Screenshots ≥ 1200 px wide | Gallery ≥ 1920×1080, < 3 MB each | ≥ 5 images total |
| Wireframe | ≥ 1 (Pro v2: ≥ 2), ≥ 1920×1080; contrasting wires on untextured colored shading `(verify)`; extra for each subdivision level | — | — | — |
| Turntable | 12–36 frames, ≥ 1920×1080, files numbered `_00`/`_01` with leading zero, JPG/PNG/GIF, or Marmoset .mview | Video MP4 ≤ 500 MB (optional) | Video 1920×1080 ≤ 300 MB (optional) | GIF allowed on page |
| UV layout | Required for Pro if UVs declared (§3.1.5): UV cage over diffuse texture | — | — | — |
| Overlays/text | Text < 25% of image, black/white/subdued; no marketing overlays; viewport screenshots never as signature image | Minimal text, no watermarks/sale banners/default skybox/Unity logo | — | No Blender logos |

Lighting convention: TurboSquid StemCell uses a calibrated neutral HDRI with "zero color information" so material values read true; studio scenes in cm, HDRI intensity 1, linear/gamma 1.0 `(verify)`. Default to a neutral HDRI (Poly Haven CC0 studio HDRI) or 3-point rig on a 247-gray backdrop; put a human/1 m scale reference in at least one shot (TurboSquid lists "scale references" among recommended product shots). Turntable at 24 or 36 frames = 15° or 10° steps is the common convention inside the 12–36 window `(convention)`.

Sources: https://resources.turbosquid.com/turbosquid/product-page/product-imagery-checklist/ · https://resources.turbosquid.com/turbosquid/product-page/product-imagery · https://resources.turbosquid.com/?p=16828 · https://support.unity.com/hc/en-us/articles/210122403-What-makes-a-great-key-image-and-are-there-any-size-restrictions- · https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab · https://support.superhivemarket.com/article/253-general-product-guidelines-for-uploading-products

## 4. Documentation requirements
What marketplaces make you declare (union, so the README covers every store):
- Identity: product name (noun/adjective-noun, capitalized), version, date, author/contact, software + version it was authored in (TurboSquid requires native format + version + renderer; Superhive requires current-Blender compatibility; Unity requires min Unity version).
- Counts: polygon (face) and vertex counts at base level, without subdivision (TurboSquid); triangle count per LOD (Fab: "state which LODs are included"); number of unique meshes/materials/textures (Unity technical details).
- Scale: unit system and real-world dimensions (TurboSquid description requirement); pivot convention (bottom-center) and forward axis (+Z Unity, -Y Blender).
- Textures: list every map with resolution and format; PBR workflow (metal/rough vs spec/gloss); normal-map convention (OpenGL/DirectX); packed channel order (e.g., ORM/ARM).
- Formats included and how each was exported (FBX/OBJ/glTF/USD); whether textures are embedded or external; "not intended for subdivision" when realtime.
- Collision: included or not, type (convex hulls / UCX_ meshes / engine-generated).
- Dependencies and limitations; renderer used for previews; third-party content with licenses (Unity Third-Party Notices file; Superhive "credit any open-source material").
- License of the asset itself (see §6). AI disclosure where required (Unity field; TurboSquid prohibits AI-made models).
- Changelog: Fab/Unity show per-version listings; keep `CHANGELOG.md` with semver and date `(convention; not a published requirement)`.
Sources: https://blog.turbosquid.com/2013/09/11/checkmate-pro-v2-checklist/ · https://assetstore.unity.com/publishing/submission-guidelines · https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab · https://support.superhivemarket.com/article/253-general-product-guidelines-for-uploading-products

## 5. Folder structure conventions
Published targets disagree, so keep one master packet and repackage per target:
- TurboSquid: flat ZIP (model + textures) or one `textures/` subfolder; paths stripped.
- Unity: `<Root>/Mesh`, `Material`, `Texture` (+ `Prefabs`, `Scenes`, `Documentation`); paths < 150 chars.
- Unreal/Fab: `Content/<ProductName>/…` single top-level folder; style guide forbids type folders; names English alphanumeric, ≤ 140-char paths (UEFN).
- Superhive: `.blend` with packed textures or relative `textures/` folder.
- KitBash3D/Poly Haven: one scene file + one textures folder; textures named `slug_map`.
Master packet (delivery layout, then export per target):
```
AssetName_v1.2.0/
  README.md  CHANGELOG.md  LICENSE.txt  THIRD_PARTY_NOTICES.txt
  source/      AssetName.blend (relative paths or packed), AssetName.spp (optional)
  export/      fbx/ AssetName.fbx (LOD0..LODn, UCX_ collision)   gltf/ AssetName.glb
               obj/ AssetName.obj + .mtl                          usd/ AssetName.usdz (optional)
  textures/    T_AssetName_BaseColor_2K.png  _Normal_GL  _ORM  _Emissive  (16-bit PNG where lossless matters)
  renders/     thumb_1200x1200.png  beauty_01..05_1920x1080.png  wireframe_01.png  uv_layout.png
               scale_ref.png  turntable/turntable_00..35.png (or .mp4)
  docs/        manifest.json  qa-report.md
```
Sources: https://resources.turbosquid.com/checkmate/checkmate-product-presentation/checkmate-texture-references/ · https://assetstore.unity.com/publishing/submission-guidelines · https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab · https://github.com/Allar/ue5-style-guide · https://help.kitbash3d.com/en/articles/6449589-what-comes-with-a-kit

## 6. Licensing basics
| License | Meaning for a delivery | Declare |
|---|---|---|
| CC0 1.0 | Public-domain dedication; no attribution; commercial OK; patents/trademarks untouched; no warranty. Poly Haven and ambientCG assets are CC0 (redistribution allowed; don't claim authorship; logos excluded). Blender bundles accept CC0 only. | "CC0 — no attribution required" |
| CC BY 4.0 | Share/adapt commercially, but must credit creator, link license, indicate changes. Fab offers CC-BY only for free listings. Unity advises avoiding attribution-required dependencies and listing them in Third-Party Notices. | credit text + license link in THIRD_PARTY_NOTICES |
| Royalty-free (store) | Buyer may embed in games/films/renders, modify, share within one corporate entity; may not redistribute files, resell as stock, or use as a logo (TurboSquid). Fab Standard: Personal (< $100k rev) / Professional tiers, same rights, no standalone resale. | "Royalty-free, Standard license" |
| Editorial | Real brands/trademarks/designs: news, teaching, non-commercial only; no modification/printing (TurboSquid); CGTrader similar. Branded models get suspended without it. | "Editorial use only" + brand note |

Rules of thumb: HDRIs/textures from Poly Haven or ambientCG may ship inside a sellable asset with no credit (credit anyway in docs); never ship CC-BY/GPL content without notices; never depict real brands unless labelled editorial; AI-generated geometry is banned on TurboSquid and must be disclosed on Unity.
Sources: https://creativecommons.org/publicdomain/zero/1.0/ · https://creativecommons.org/licenses/by/4.0/ · https://polyhaven.com/license · https://ambientcg.com/ · https://docs.ambientcg.com/license/ · https://www.turbosquid.com/help/en/articles/9937423-royalty-free-license-faq · https://www.turbosquid.com/help/en/articles/14829413-what-are-the-limitations-and-upgrade-policies-for-3d-model-licenses-on-turbosquid · https://help.cgtrader.com/hc/en-us/articles/360015193398-Editorial-License · https://dev.epicgames.com/documentation/en-us/fab/licenses-and-pricing-in-fab · https://developer.blender.org/docs/features/asset_system/asset_bundles/guidelines/

## 7. Common rejection reasons and the implied definition of done
| Rejection (source) | Definition-of-done item |
|---|---|
| Missing/unpacked textures; shaders not linked (Superhive); textures absent or path errors (TurboSquid Lite) | Open on a clean machine: zero missing files, zero pink/magenta materials |
| Absolute texture paths (TurboSquid §2.1.4) | All paths relative or packed; paths stripped before export |
| Incorrect pivot, rotation or scale (Unity); unreset transforms (TurboSquid) | Loc 0 / Rot 0 / Scale 1, pivot bottom-center at origin, 1 unit = 1 m |
| Missing colliders on static models (Unity); no collision (Fab) | Collision mesh or declared "none" with reason |
| LODs not configured / not stated (Unity LOD Group, Fab) | LOD chain exported and listed with tri counts |
| N-gons, non-manifold, faceted, overlapping UV islands (CGT validator); n-gons, zero-area tris, UVs outside 0–1 (Roblox validator) | Validator-clean mesh; UVs in 0–1 when target requires |
| Default names `Cube.001` (Superhive); vague folders (Fab); special characters (CGTrader/Sketchfab) | Every datablock, file and folder named per convention |
| Errors/warnings after import (Unity, Fab) | Import log clean in a fresh project |
| Inadequate docs, placeholder text, poor description (Superhive, Unity) | README complete; no "Lorem ipsum"; counts and dimensions stated |
| Image problems: wrong aspect/size, too few, logos, borders, watermarks (all) | Render set meets §3 table for the target |
| Brands/trademarks, printable weapons, AI-made (TurboSquid suspension) | IP clearance noted; no AI geometry where banned |
Sources: https://support.superhivemarket.com/article/186-why-products-get-rejected · https://assetstore.unity.com/publishing/submission-guidelines · https://www.turbosquid.com/help/en/articles/12098178-why-can-models-or-products-be-suspended-on-turbosquid · https://www.cgtrader.com/blog/cgt-standard-what-it-means-for-3d-model-buyers · https://create.roblox.com/docs/art/validation-errors · https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab

## 8. Studio-side acceptance (what a lead checks before "integrated")
- **Clean-project import**: copy the submission to an empty location, compare to the manifest, scan for missing textures/absolute paths/duplicates/caches, import into a fresh target-engine project with the approved preset; zero unknown warnings. Evidence: versioned manifest (files, sizes, checksums, tool versions), automated geometry/naming report, import log, wireframe + UV-checker + turntable + LOD-transition + collision-view renders, profiler capture (memory, draw calls, frame cost), signed pass/waiver list.
- **In-engine look**: materials resolve in the project's shading model; normal-map convention correct (OpenGL vs DirectX flip); no seams (Fab); texture power-of-2 ≤ 8192 (Allar/Fab).
- **Collision**: present on all meshes (Allar), fits the model (Unity), correct fidelity (Roblox Default).
- **LOD transitions**: UE auto thresholds 2 LODs → switch at 50% screen size; 3 LODs → 66.7% / 33.3%; set per-LOD screen size manually, use dithered LOD transition (~0.25–0.5 s blend) and avoid huge single drops (e.g., 100k→30k→8k→1.5k rather than 100k→1k) `(convention)`.
- **Texel density consistent with neighbors**: asset matches the project's declared tier; common tiers 512 px/m third-person, 1024 px/m first-person, 2048 px/m VR/hero, with hero/FPS weapons 2–4× `(blog convention)`. Check with a UV-checker render next to a neighboring asset.
- **Draw calls / material count**: engines batch by shared material; fewer material slots and atlased textures = fewer draw calls (Unity); Roblox allows one material per MeshPart; Sketchfab caps 100 materials. Record material-slot count in the manifest.
- **Budgets**: polycount per LOD, texture memory, bone count/influences (Roblox ≤ 4), file size — defined per project class (background prop vs hero), not inherited from a single number.
Sources: https://www.seeles.ai/features/tools/dcc-delivery-limits-acceptance-checklist · https://dev.epicgames.com/documentation/en-us/unreal-engine/creating-and-using-lods-in-unreal-engine · https://bugnet.io/blog/fix-unreal-static-mesh-lod-screen-size-popping · https://www.strayspark.studio/blog/texture-resolution-guide-games-512-1k-2k-4k · https://docs.unity3d.com/cn/2022.3/Manual/DrawCallBatching.html · https://github.com/Allar/ue5-style-guide · https://create.roblox.com/docs/en-us/art/modeling/specifications

## 9. Consolidated delivery packet spec
Superset of every marketplace above; satisfying it lets the packet be repackaged for any one target without rework.
1. **Geometry**: real-world scale, 1 BU = 1 m; loc/rot 0, scale 1 applied; pivot bottom-center at world origin, model resting on Z=0 (Blender) / Y=0 (engine); quad-dominant, ≤ 10–15% tris for subdividable, tri-optimized for realtime; no n-gons, no isolated/coincident verts, no coplanar faces, manifold, normals outward, no zero-area faces; hierarchy grouped under one root (empty or collection) named as the asset.
2. **UVs**: fully unwrapped, inside 0–1, non-overlapping for baked/unique sets (mirrored overlap only if declared); texel density matches declared tier; second non-overlapping UV channel for lightmaps when targeting UE/Unity baked lighting.
3. **Materials/textures**: PBR metal/rough as primary; square power-of-2 (512–4096; 8192 max); lossless PNG/TGA (16-bit PNG where precision matters); normal map GL by default with DX variant or stated convention; packed ORM/ARM declared; textures external with relative paths and also a packed-source `.blend`; no unused materials/images/orphans; one material slot per logical surface, count recorded.
4. **LODs & collision**: LOD0..n exported and listed with tri counts (or "LOD0 only" stated); collision as UCX_/convex meshes or declared as engine-generated.
5. **Naming**: `AssetName` PascalCase or `asset_name_01` slug, consistent across object, mesh, material, texture, file; type prefixes/suffixes (`SM_`, `T_…_BaseColor`, `_Normal_GL`, `_ORM`); no default names, spaces, unicode or symbols; paths < 140 chars.
6. **Files**: `source/*.blend` (Blender 5.2, packed); `export/fbx` (binary, -Y forward/Z up applied per target preset), `export/gltf/*.glb`, `export/obj + .mtl`; optional USDZ; one zip per target layout (flat for TurboSquid, Unity root folders, UE `Content/<Name>`).
7. **Presentation**: thumbnail 1200×1200 on RGB 247 gray; ≥ 5 beauty shots 1920×1080 (angles, close-up, context, scale reference); ≥ 2 wireframes 1920×1080 contrasting wires; UV layout over base color; turntable 24–36 frames 1920×1080 numbered `_00`…; neutral HDRI or 3-point lighting; no logos/borders/text > 25%.
8. **Docs**: `README.md` with every §4 item; `manifest.json` (counts, dims, textures, LODs, formats, checksums, tool versions); `CHANGELOG.md`; `LICENSE.txt`; `THIRD_PARTY_NOTICES.txt` (even for CC0 sources); `qa-report.md` with the checklist below filled.
Sources: synthesized from §1–§8 above.

## 10. QA checklist with severities
Blocker = validator auto-fail or reviewer decline; Major = passes upload but hurts usability/integration; Minor = polish.

**Geometry**
- [ ] Blocker — non-manifold edges, isolated vertices, zero-area faces, flipped normals: 0
- [ ] Blocker — n-gons: 0 (CGTrader, Roblox); Major on marketplaces that allow them
- [ ] Blocker — coincident/coplanar duplicate faces: 0 (TurboSquid; causes Z-fighting, Fab)
- [ ] Major — tri ratio > 15% on a subdividable asset; poles > 5 edges off flat caps
- [ ] Major — polycount exceeds declared budget or target cap (Roblox 20k/mesh, 4k accessory)
- [ ] Minor — unnecessary edge loops / density on flat areas

**Transforms / scale**
- [ ] Blocker — rotation or scale not applied (≠ 0 / ≠ 1); unit scale not 1 m
- [ ] Blocker — model not at real-world size (check bounding dims vs README)
- [ ] Major — pivot not bottom-center at origin (or not at logical hinge for modular/animated parts)
- [ ] Major — not resting on ground plane / wrong up axis after export

**UVs**
- [ ] Blocker — UVs missing or outside 0–1 where target requires (Roblox, baked maps)
- [ ] Blocker — overlapping islands on a unique-texture asset (CGT Standard) unless declared mirrored
- [ ] Major — texel density off project tier by > 2× or visibly inconsistent across the asset
- [ ] Major — no second UV for lightmaps when target bakes lighting; lightmap UVs overlap
- [ ] Minor — stretching > checker tolerance, seams through hero surfaces

**Materials / textures**
- [ ] Blocker — missing textures, absolute paths, pink materials on clean import
- [ ] Blocker — non-square or non-power-of-2 textures (CGT); > 8192 px (Fab/UE)
- [ ] Major — unused materials/images/orphan data left in file; embedded textures where external required
- [ ] Major — normal-map convention undeclared or wrong for target; normal not flagged as normal map (Unity)
- [ ] Major — material slot count above budget; same surface split across slots
- [ ] Minor — lossy textures where lossless expected; no 16-bit for height/displacement

**Naming**
- [ ] Blocker — default names (`Cube.001`, `Material.004`), placeholder text
- [ ] Blocker — spaces/unicode/special characters in file, material or texture names
- [ ] Major — prefixes/suffixes inconsistent between object, material, texture, file
- [ ] Minor — paths > 140 chars; vague folder names

**Files / packaging**
- [ ] Blocker — archive missing a declared format or texture; .blend not opening in current Blender
- [ ] Blocker — import errors/warnings in fresh Unity/UE/Roblox project
- [ ] Major — LODs/collision promised but not present; wrong target layout (flat vs Content/<Name>)
- [ ] Major — file size over target limit (Unity 6 GB; Fab 6 GB/file; Superhive 5 GB)
- [ ] Minor — no USD/glTF variant when requested; no checksums in manifest

**Presentation**
- [ ] Blocker — thumbnail with logos/borders/QR/watermark, Unity/Blender/TurboSquid branding, AI imagery where banned
- [ ] Major — fewer than 5 beauty shots or below 1920×1080; no wireframe; thumbnail not 1200×1200 square on 247 gray
- [ ] Major — missing UV layout image when UVs declared (CheckMate Pro)
- [ ] Minor — turntable outside 12–36 frames or misnumbered; no scale reference; text > 25% of frame

**Docs**
- [ ] Blocker — no license declared; third-party content without notice; brand IP without editorial label
- [ ] Blocker — README missing poly/vert counts, dimensions/units, texture list with resolutions
- [ ] Major — LODs, collision, pivot, forward axis, normal convention, software version not stated
- [ ] Minor — no changelog; renderer used for previews not stated; "not intended for subdivision" missing on realtime assets

Sources: synthesized from §1–§8 above; severities are this document's suggestion, not a marketplace scale.

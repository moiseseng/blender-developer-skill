# Art styles, detail tiers, reference use, and presentation rendering (Blender 5.x)

Research notes for the Blender 3D-team skill (intake interview + presentation conventions). Researched 2026-10-17 against Blender 5.0–5.2 LTS docs/release notes.
Caveats: Blender was not reachable over MCP during research, so engine *defaults* are marked `(verify in 5.2)`; the Polycount wiki and the Dota 2 Steam KB were unreachable (JS/offline), so claims from them come from search snippets and are marked `(verify)`. Numbers without a citation are labelled **convention** or **estimate**.

## Contents
1. [Style taxonomy with production rules](#1-style-taxonomy)
2. [Detail tiers for intake](#2-detail-tiers)
3. [Reference workflow](#3-reference-workflow)
4. [Color and palette rules](#4-color-and-palette-rules)
5. [Presentation rendering in Blender 5.x](#5-presentation-rendering-in-blender-5x)
6. [Readability rules for game assets](#6-readability-rules)
7. [Code-driven modeling: achievable vs. needs sculpting](#7-code-driven-modeling)
8. [Suggested intake fields](#8-suggested-intake-fields)

---

## 1. Style taxonomy

| Style | Topology / shading | Texture approach | Texel density | Lighting that flatters it | Top pitfalls |
|---|---|---|---|---|---|
| **Low-poly flat-shaded** | Visible triangles; Shade Flat / split normals (smoothing angle 0); <1,000 tris per prop; ~300 verts per model if batching matters (Unity figure) | Palette texture: one small image of color squares (256×256 cited), all faces of one color UV'd into one swatch; or vertex colors (all 3 corners same color); bake AO and multiply | n/a (palette) | One strong directional key + colored ambient; faceting *is* the shading, so light angle matters more than texture | Skinny triangles cause shading spikes; mixing smooth + flat; too many colors; multiple materials kill batching |
| **Low-poly smooth / stylized** (Monument Valley, Alto's) | Smooth shading, simple quads, silhouette-driven; often orthographic camera (MV) | No textures: flat materials or vertex colors + world-space Y gradient; fog/atmosphere for depth; limited hues per area | n/a | Unlit or soft directional + rim; foreground colors purer, background tinted toward the sky | Over-detailing; perspective camera breaking the "diorama" feel; gradients fighting flat color |
| **Hand-painted stylized** (WoW, Dota 2) | Medium poly: Dota 2 slot budgets 1,500–4,000 tris LoD0, LoD1 = 40%; chunky, scaled-up forms (WoW camera is far) | Diffuse-only with light painted in: top light, baked AO, curvature edge highlights; value gradient dark at feet → light at head; large crisp graphic patterns; clamp shadows/highlights | Dota 2 slots: 256–512 px textures per item | Subtle/flat in-engine light; presentation: warm key + faint cool fill + skylight | Double lighting (painted + strong dynamic); small noisy detail; inconsistent material "gold" tones |
| **Toon / cel** | Clean quads, deliberate creases (crease angle drives lines); hard edges where lines should appear | Flat colors + 2–3 tone ramp (Shader to RGB → ColorRamp in EEVEE); 5.1 Raycast node enables NPR effects in EEVEE | Low; often untextured | Single key + hard terminator; view transform **Standard** so flat colors stay flat | AgX desaturating/flattening colors; inverted hull breaking on concave corners; Line Art slow with many modifiers/instances |
| **PBR stylized** (Overwatch, Fortnite) | Silhouette-first, large interesting shapes, no micro bumps; bevels on everything or big baked bevels, avoid raw 90° edges; density where seen (hands, face, weapons) | Metal/roughness PBR; lighten base color along convex edges; clean material contrast (painted metal vs worn wood); metals never perfectly clean; rectangular 1024×2048 maps when islands are long | Standard game TD (512–1024 px/m) | Bright optimistic key, strong fill; view transform **Khronos PBR Neutral** keeps swatches faithful | Areas of visual noise that don't read at distance; over-shiny metals; missing value hierarchy |
| **PBR realistic** | Dense support loops / subdiv or baked high→low; real-world scale mandatory | Scan-like albedo, roughness variation via imperfection maps (fingerprints, smudges, dust, scratches); wear story placed by rules | Hero 2,048–4,096 px/m; archviz ~5,120 px/m | HDRI (Poly Haven CC0) + soft key; view transform **AgX** | Single flat roughness value; uniform wear; wrong scale; textures >4K without need |
| **Hard-surface sci-fi / mech** | Primary → secondary → tertiary forms; panel breaks by boolean cuts; Bevel modifier + Weighted Normal; greebles instanced (kitbash) | Trim sheets / tiling + decals; edge wear from curvature; panel-line AO | 512–1,024 px/m, trims higher | Studio HDRI with strong speculars so bevels catch highlights | Inconsistent bevel widths; boolean n-gon shading; pinching; greeble soup with no rest areas |
| **Voxel** | Cubes on a grid; MagicaVoxel-style models up to 256³ `(verify)`; 32³ characters often read better than 64³ | Palette-indexed color (.vox stores exactly 256 RGBA entries); palette decided first | n/a | Soft sun + AO; cavity shading | Thin 1-voxel edges alias; too many colors; detail invisible at game camera distance |
| **Isometric / diorama** | Orthographic camera; 2:1 dimetric = camera rot X 60°, Z 45°; true iso ≈ X 54.736°, Z 45° | Any of the above (usually low-poly smooth or hand-painted); scene composed to the frame | per base style | One fixed key matching the camera angle; shadows must fall on-grid | Accidental perspective camera; mismatched tile scale (e.g. 64×32 px tiles for 2:1) |

Notes on the strongest primary sources:
- **TF2 (Valve, NPAR 2007 / GDC 2008):** silhouettes first; interior details (clothing folds) echo silhouette shapes; high-frequency detail omitted; rim highlights instead of dark outlines; read hierarchy team → class → weapon; value gradient dark feet → light chest, highest contrast at chest where the weapon is held; restricted palette (skin, team primary, secondary, tertiary, metal).
- **Overwatch (GDC 2017 + 80.lv studies):** everything recognizable by silhouette alone; big shapes near the top of characters; general → specific detail passes; lighten base color along convex edges; large baked bevels and corner pieces instead of 90° angles; small details live mostly in the specular layer; minor intersections allowed between same-material pieces to speed kitbashing.
- **Dota 2 texture guide (snippet, `verify`):** default hero gradient darkest at feet → lightest at head; shadows/highlights clamped per character; sculpt detail is lost in normal maps so light is painted into color; large crisp patterns aid legibility. Per-slot budgets (Juggernaut): Head 3,000/1,200 tris, 512²; Arms 1,500/600, 256²; Weapon 2,500/1,000, 256²; Legs 2,000/800, 512².
- **Flat-shaded (tutsplus):** smoothing angle 0 for hard edges; single palette texture for one material across the game; bake AO in Blender and multiply over color.
- **Toon outlines in Blender:** inverted hull (Solidify + flipped normals + backface-culled emission material, real-time), Freestyle (Render properties checkbox; works with EEVEE and Cycles; Workbench `(verify)`; memory heavy, no Z-depth in result, no face-intersection lines), Grease Pencil **Line Art** modifier (Scene/Collection/Object source; Contour, Crease, Intersections, Material Borders, Edge Marks, Loose, Light Contour, Cast Shadow; needs active camera; each modifier recomputes occlusion), shader-based (Shader to RGB / Raycast), Wireframe modifier for technical lines.

Sources: https://cdn.fastly.steamstatic.com/apps/valve/2008/GDC2008_StylizationWithAPurpose_TF2.pdf · https://www.cs.princeton.edu/courses/archive/fall07/cos597B/papers/mitchell-team-fortress.pdf · https://gdcvault.com/play/1024268/The-Art-of-Overwatch-Evolving · https://www.cookandbecker.com/en/article/378/designing-overwatch.html · https://80.lv/articles/studying-overwatch-style · https://80.lv/articles/overwatch-technical-overview · https://80.lv/articles/comparing-team-fortress-2-and-overwatch-art-direction · https://help.steampowered.com/faqs/view/0688-7692-4D5A-1935 · https://www.dota2.com/workshop/requirements/juggernaut · https://80.lv/articles/002mrs-crafting-a-wow-diorama-textures-painting-lighting · https://code.tutsplus.com/go-beyond-retro-pixel-art-with-flat-shaded-3d-in-unity--gamedev-12259a · https://polycount.com/discussion/comment/1261416/ · https://80.lv/articles/altos-adventure-a-game-with-style · https://www.gamedeveloper.com/art/get-art-tips-from-ustwo-naughty-dog-and-the-remakers-of-i-halo-i-at-gdc · https://meliorgames.com/game-art-design/what-is-stylized-game-art-techniques-and-examples/ · https://www.poliigon.com/textures/surface-imperfections · https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox.txt · https://gamefromscratch.com/creating-isometric-tiles-in-blender/ · https://www.blendernation.com/2023/12/21/7-ways-to-make-lineart-in-blender-4-0/ · https://docs.blender.org/manual/en/5.0/render/freestyle/introduction.html · https://docs.blender.org/manual/en/5.0/grease_pencil/modifiers/generate/line_art.html · https://developer.blender.org/docs/release_notes/5.1/eevee/

---

## 2. Detail tiers

Proposed 5-tier ladder for the intake interview. Columns anchored to sources where possible; time is an **estimate** for code-driven Blender work on a single prop/character (no source defines this).

| Tier | Use | Tris (prop / character) | Textures | Materials | LODs | Render for review | Time (estimate) |
|---|---|---|---|---|---|---|---|
| **T0 Blockout / placeholder** | scale, silhouette, layout | 50–2,000 / ≤5,000 primitives | none; viewport/object colors or MatCap | 1 (flat) | none | Workbench clay | 5–20 min |
| **T1 Game-ready low** (mobile, VR, background) | mobile props <500–1,500; mobile characters 1,500–5,000 | 300–1,500 / 1,500–5,000 | 256–512 px, atlas; TD 256–512 px/m | 1 (atlas) | LOD1 at 40–50% | EEVEE 16 spp | 20–60 min |
| **T2 Game-ready standard** (PC/console prop, NPC) | typical shipped asset | 1,000–10,000 / 10,000–20,000 | 1,024–2,048 px; TD 512–1,024 px/m (5.12 px/cm "third-person" standard) | 1–2 | 3 levels: 100/50/25% (or 100/40% Dota-style) | EEVEE 64 spp | 1–3 h |
| **T3 Hero / high** (first-person weapon, main character, marketplace "hero") | close-up readable | 10,000–50,000 / 15,000–50,000 | 2,048–4,096 px; TD 1,024–2,048 px/m (10.24 px/cm "first-person") | 2–4 | 3–4 levels | Cycles 128–256 spp + denoise | 3–8 h |
| **T4 Offline / cinematic** | renders, archviz, film | subdivision surface, no cap | 4,096–8,192 px (Fab/UEFN max 8,192), UDIM; TD 2,048–5,120 px/m | unlimited | none | Cycles noise-threshold 0.01 or lower | 8 h+ |

Industry anchors behind the numbers:
- Platform polycount guides (2024–2026): mobile assets 1,500–5,000 tris, mobile props <500; PC/console props 1,000–10,000; hero characters 15,000–50,000; vehicles up to 80,000–150,000.
- Dota 2 budgets: LoD1 is 40% of LoD0 for the four wearable slots (3,000→1,200; 2,500→1,000; 2,000→800; 1,500→600); the ability ward is 50% (4,000→2,000).
- LOD convention: LOD1 = 50% tris, LOD2 = 25% (Simplygon notes this is the "traditional art guideline" and recommends screen-size targets instead). Unity switches LOD1 at <50% screen height and LOD2 at <25%.
- Texel density: 5.12 px/cm (=512 px/m) for third-person, 10.24 px/cm (=1,024 px/m) for first-person; a 1,024² at 512 px/m covers 2×2 m. Texelmaster presets: Mobile 256, PC Low 512, PC Standard 1,024, PC High 2,048, Hero 4,096, Archviz 5,120 px/m.
- Marketplace rules: Fab/UEFN textures power-of-two, max 8,192; one material per surface; "lowest poly count that preserves silhouette". TurboSquid CheckMate: real-world scale, quads/tris only, non-overlapping UVs, texture resolutions listed; "realtime" vs "subdividable" model classes. Unity Asset Store gives no numeric caps (quality reviewed).

Sources: https://cgaxis.com/polygon-count-guide-how-many-polys-do-you-really-need-in-2026/ · https://blog.neural4d.com/user-guide/polygon-count-for-3d-game-assets/ · https://www.dota2.com/workshop/requirements/juggernaut · https://simplygon.com/posts/b83478b7-a2a1-46a9-a0e1-cba3da7da307 · https://docs.unity3d.com/ru/2019.3/Manual/LevelOfDetail.html · https://polycount.com/discussion/comment/2760149 · https://polycount.com/discussion/comment/2304751 · https://superhivemarket.com/products/texelmaster-texel-density-manager/docs · https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab · https://blog.turbosquid.com/2013/09/11/checkmate-pro-v2-checklist/ · https://assetstore.unity.com/publishing/submission-guidelines

---

## 3. Reference workflow

**Board (PureRef).** Blender Studio's stylized-character course groups references into four buckets and keeps PureRef on a second monitor rather than inside the viewport: *Style* (films, other games, sculpts), *Design* (concept art, photos, clothing/hair), *Technical* (topology, polycount, material setup, e.g. Polycount), *Real-life* (anatomy, fabric, expressions). Proposed board layout (convention): 1 hero image at 2× size, 3–6 style images, 1 row of material swatches/callouts, 1 row of "do not" images.

**What to extract (checklist for the interview):**
1. Silhouette: fill the reference black; name the 2–3 shapes that survive (TF2: identifiable at first read; Overwatch: readable from silhouette alone).
2. Proportions: heads-tall (realistic 7–8; stylized 1/6–1/7 head-to-height; chibi 2–4 heads), width:height ratio, biggest-mass location (Overwatch puts big shapes near the top).
3. Shape language: circle = friendly/safe, square = stable/strong, triangle = dynamic/danger (Pixar/Disney examples: Carl square, Muntz/Syndrome triangular).
4. Material callouts: per surface — material name, base-color hex, roughness range (e.g. painted metal 0.35–0.55), metallic 0/1, edge treatment (bevel/baked/lightened).
5. Palette: 3–5 hexes with 60-30-10 roles; note hue of shadows (cool) and lights (warm).
6. Wear story: intensity 0/25/50/75/100% (factory-new → abandoned) and *where*: convex edges polished, crevices dark (AO), rust on horizontals/bottoms, contact wear where hands/feet touch.
7. Read hierarchy: what must be seen first at distance (team → class → weapon in TF2); where the highest contrast sits.

**Using reference inside Blender (5.x):**
- `Add ▸ Image ▸ Reference` / `Background` creates an **Image Empty**; set Depth = Front with low Opacity for modeling, Side = Front/Back to show a front/back sheet only from its side, disable *Show in Perspective* to hide it when orbiting; Offset X/Y 0.5/0.5 centers the origin. Python: `bpy.ops.object.empty_image_add(filepath=..., background=False)` `(verify)`; properties `empty_display_size`, `empty_image_depth`, `empty_image_side`, `show_empty_image_perspective`, `use_empty_image_alpha` `(verify)`.
- `Add ▸ Image ▸ Mesh Plane` (Images-as-Planes, built in since 4.2): Shadeless/Principled/Emission material, Size Mode Absolute/Scale to Camera Frame/Pixels per Inch, Align to axis or Face Camera (optional Locked Track).
- Camera **Background Images** (camera data ▸ Viewport Display): Image/Movie Clip source, Opacity, Depth back/front, Frame Method Stretch/Fit/Crop, Offset in camera-bound fractions (0.1 = 10%), Rotation, Scale, Flip X/Y. Python: `cam.data.show_background_images = True; bg = cam.data.background_images.new(); bg.image = img` `(verify)`.

**Describing a style precisely to a collaborator (template):** "*{style name}*; silhouette language {round/square/triangle mix, e.g. 70% round / 30% square}; proportions {heads tall, head:body}; palette {3–5 hex} in 60/30/10; materials {base hex, roughness a–b, metallic} per surface; edges {bevel width mm or baked}; wear {0–100%} placed at {edges/crevices/contacts}; read order {1,2,3}; camera {persp 50 mm / ortho iso}; view transform {Standard / PBR Neutral / AgX}."

Sources: https://studio.blender.org/training/stylized-character-workflow/5d3a1b734bc3ff1bb9513d3a · https://www.creativebloq.com/how-to/pureref · https://docs.blender.org/manual/en/5.0/modeling/empties.html · https://docs.blender.org/manual/en/5.0/modeling/meshes/import_images_as_planes.html · https://docs.blender.org/manual/en/5.0/render/cameras.html · https://dreamfarmstudios.com/blog/shape-language-in-character-design/ · https://blog.cg-wire.com/character-shape-language/ · https://www.strayspark.studio/blog/visual-storytelling-through-surface-wear-game-design · https://cdn.fastly.steamstatic.com/apps/valve/2008/GDC2008_StylizationWithAPurpose_TF2.pdf

---

## 4. Color and palette rules

- **Value before hue.** Readability comes from value contrast; most readability failures are value failures. Build a 3-value notan (dark/mid/light) before picking hues (convention).
- **Hue-shift shading (TF2 / Gooch):** shading obeys a warm-to-cool shift; shadows go cool, never black; saturation rises at the terminator and the terminator is often reddened; extreme lights/darks reserved for edge lines and highlights.
- **Painted light (WoW):** top light; warm lights, cool shadows; keep material hues consistent across the asset (one "gold").
- **Character gradient (TF2, Dota 2):** darkest at feet → lightest at chest/head; highest contrast where the eye must land (weapon/face).
- **60-30-10:** 60% dominant, 30% secondary, 10% accent; spend the accent on gameplay-relevant parts (interactables, team, focal point).
- **Restricted palettes:** TF2 limited to skin + team primary + secondary + tertiary + metal; pixel/voxel art works in 8–32 colors per scene (voxel formats cap at 256); Alto's limits hues per biome and keeps foreground colors purer than tinted backgrounds.
- **Team / faction color must always contrast** (TF2 red vs blue; Overwatch criticized for HUD-dependent team color). Pair color with material/shape (red = warm, natural, angular; blue = cool, industrial, orthogonal in TF2 maps).
- **Saturation discipline for stylized PBR:** bright palette but clamp shadows/highlights (Dota 2); avoid blend modes that blow out hues; pick view transform so flat swatches survive (see §5).

Sources: https://www.cs.princeton.edu/courses/archive/fall07/cos597B/papers/mitchell-team-fortress.pdf · https://cdn.fastly.steamstatic.com/apps/valve/2008/GDC2008_StylizationWithAPurpose_TF2.pdf · https://80.lv/articles/002mrs-crafting-a-wow-diorama-textures-painting-lighting · https://help.steampowered.com/faqs/view/0688-7692-4D5A-1935 · https://uxcel.com/blog/mastering-the-60-30-10-rule-in-design-691 · https://www.wayline.io/learn/pixel-art/2 · https://80.lv/articles/altos-adventure-a-game-with-style · https://80.lv/articles/comparing-team-fortress-2-and-overwatch-art-direction · https://bugnet.io/blog/readable-game-art-why-clarity-beats-detail

---

## 5. Presentation rendering in Blender 5.x

**Neutral studio lighting**
- 3-point: key 45° off camera and ~45° up, fill on the opposite side, rim behind. Ratios: fill = key/2 (**2:1**, one stop) for soft commercial look; **4:1** (two stops) for drama; 1:1 for flat catalog shots. Raising fill visibly weakens the rim — rebalance.
- HDRI: Poly Haven is **CC0** (no attribution needed). Studio category (165 HDRIs) includes `studio_small_01…09`, `brown_photostudio_01…07`, `photo_studio_01`, `white_studio_01…06`, `monochrome_studio_01…04`, `cyclorama_hard_light`; max resolutions 16k–24k, use 2k–4k for lighting. Hide the HDRI from camera (Film ▸ Transparent, or Light Path *Is Camera Ray* mix to a backdrop color).
- Gradient backdrop: large plane with a bent back wall (cyclorama), mid-gray ≈ 0.18 linear (**convention**); or world gradient via Light Path camera-ray mix.

**Camera**
- Default lens 50 mm on a 36 mm sensor `(verify in 5.2)`; 50 mm for general asset shots, **85 mm** for hero/beauty (compression, isolation); never below 35 mm for products (distortion). Orthographic + Orthographic Scale for iso/tiles; Lens Shift keeps verticals vertical instead of tilting.
- Convention: ¾ view, camera height at ~⅓–½ of object height, object fills 60–75% of frame; pivot at base so the turntable stays centered.

**Turntable**
- TurboSquid still-turntable spec: 12–36 frames, even count, one extra keyframe (e.g. 25 keys for 24 frames) with the last frame excluded for a seamless loop, linear tangents, 360° around Z, model centered on XY, ≥1,920×1,080, same resolution for all frames.
- Proposal for video turntables: rotate an **Empty parent** (lights stay fixed) 0→360° with linear interpolation over **120–144 frames at 24 fps** (5–6 s), or 180 @ 30 fps; render frames 1…N-1.
- Fast path: `View ▸ Render Playblast` (Viewport Render animation) — Workbench/EEVEE only, not Cycles; disable overlays unless you want the wireframe.

**Wireframe-over-shaded** — three options: (a) **Wireframe modifier** on a duplicate (Thickness, Offset 0 centered, *Even Thickness*, *Material Offset* → dark emission material; skinny faces can spike), (b) Freestyle line set on edge marks / crease angle (EEVEE or Cycles), (c) Viewport Render with the Wireframe overlay enabled (Workbench/EEVEE).

**Clay / MatCap form review (Workbench)** — Lighting: Flat / Studio (key front + rim back, configurable, *World Space Lighting*) / MatCap (5.0 MatCaps gained specular layers); Color: Material / Object / Random / Attribute / Texture / Single; Options: Cavity (World = precise, Screen = fast, Both; Ridge/Valley sliders), Shadow (Darkness 0–1, Light Direction), Outline, Specular Highlights, X-Ray, Backface Culling; Anti-aliasing: None / Single Pass / Multisample 5, 8, 11, 16, 32.

**EEVEE vs Cycles**
- EEVEE (engine id `BLENDER_EEVEE` since 5.0): review renders, stylized/NPR (Shader to RGB, 5.1 Raycast node), turntables. Defaults 16 viewport / 64 render samples `(verify in 5.2)`; jittered shadows are always on in final renders; raise Shadows ▸ Rays/Steps for soft lights; Raytracing Screen-Trace for reflections (5.2 reworked screen-space GI, added *Backface* option; scenes may render darker than 5.1).
- Cycles: final PBR/realistic. Adaptive sampling noise threshold "typical 0.1–0.001" (manual); use **0.01** for final `(convention)`, 0.05 for review; max samples 1,024 viewport / 4,096 render `(verify in 5.2)`; denoise with OpenImageDenoise, passes Albedo+Normal, Prefilter Accurate, Quality High for final / Fast for viewport; Time Limit for budgets. 5.2 adds Texture Cache (.tx files) and Thin Wall in Principled BSDF.

**Color management (5.0+)** — Views: **Standard** (no tone mapping; "often used for non-photorealistic results"), **Khronos PBR Neutral** (output sRGB matches input base color under gray lighting; "aimed toward product photography"), **AgX** (16.5 stops, desaturates bright colors; Filmic deprecated), ACES 1.3/2.0, AgX HDR, False Color for exposure checks. Display: sRGB for universal viewing, Display P3 for wide gamut, Rec.2100-PQ/HLG for HDR video. Working space per file: default Linear Rec.709 (Rec.2020/ACEScg optional) — choose at project start. Rule of thumb: flat/toon/voxel → Standard; stylized PBR & product shots → PBR Neutral; realistic → AgX.

**Resolution / output** — Review: 1,280×720 or 1,920×1,080 at Percentage 50%; final stills 1,920×1,080 to 3,840×2,160; turntables ≥1,920×1,080; frame rate default 24 fps `(verify)`; PNG with Film ▸ Transparent for alpha. Filter Size default 1.5 px `(verify)`.

Sources: https://gvmled.com/?p=93866 · https://fstoppers.com/lighting/why-your-rim-light-looks-weaker-every-time-raise-fill-904930 · https://imaginated.com/blog/what-is-lighting-ratio · https://polyhaven.com/license · https://api.polyhaven.com/assets?type=hdris&category=studio · https://help.intangible.ai/compose/lenses · https://www.keh.com/expert-advice/camera-gear/35mm-vs-50mm-vs-85mm-for-portraits-which-should-you-choose/ · https://resources.turbosquid.com/turbosquid/product-page/creating-turntables/ · https://docs.blender.org/manual/en/5.0/editors/3dview/viewport_render.html · https://docs.blender.org/manual/en/5.0/modeling/modifiers/generate/wireframe.html · https://docs.blender.org/manual/en/5.0/render/workbench/introduction.html · https://docs.blender.org/manual/en/5.0/render/workbench/options.html · https://docs.blender.org/manual/en/5.0/render/eevee/render_settings/sampling.html · https://docs.blender.org/manual/en/5.0/render/eevee/render_settings/raytracing.html · https://docs.blender.org/manual/en/5.0/render/cycles/render_settings/sampling.html · https://docs.blender.org/manual/en/5.0/render/color_management/index.html · https://developer.blender.org/docs/release_notes/5.0/color_management/ · https://developer.blender.org/docs/release_notes/5.0/eevee/ · https://developer.blender.org/docs/release_notes/5.2/eevee/ · https://developer.blender.org/docs/release_notes/5.2/cycles/ · https://docs.blender.org/manual/en/5.0/render/cameras.html · https://docs.blender.org/manual/en/5.0/render/output/properties/format.html

---

## 6. Readability rules

1. **Silhouette test:** render the asset as a black fill at gameplay distance; it must be identifiable and distinct from every other asset of its class (TF2's Heavy reads even when mostly cut off). Two similar silhouettes → redesign one.
2. **Distance test:** judge at the size the player sees — Unity's LOD1/LOD2 switch at 50%/25% screen height is a good proxy; store capsules are ~231 px wide `(snippet)`.
3. **Squint test:** blur until only big shapes/values remain; the focal point must still be obvious.
4. **Value bands:** player, threats and interactables occupy a different brightness band than the background.
5. **Read hierarchy:** decide order (TF2: team → class → weapon) and give the first item the biggest shape/highest contrast; big shapes near the top of characters (Overwatch).
6. **Areas of rest:** leave 30–40% of the surface low-detail (**convention**); interior detail should echo the silhouette, not fight it.
7. **Density where seen:** faces, hands, weapons get the mesh/texture budget; backs and legs don't.
8. **Gameplay visual language:** consistent color = consistent function (accent 10% for interactables); faction colors always contrast; shape language signals intent (round = safe, square = sturdy, triangle = threat); emissive/high-saturation reserved for things the player must notice.

Sources: https://cdn.fastly.steamstatic.com/apps/valve/2008/GDC2008_StylizationWithAPurpose_TF2.pdf · https://80.lv/articles/comparing-team-fortress-2-and-overwatch-art-direction · https://www.cookandbecker.com/en/article/378/designing-overwatch.html · https://80.lv/articles/overwatch-technical-overview · https://bugnet.io/blog/readable-game-art-why-clarity-beats-detail · https://docs.unity3d.com/ru/2019.3/Manual/LevelOfDetail.html · https://dreamfarmstudios.com/blog/shape-language-in-character-design/

---

## 7. Code-driven modeling

**Realistically achievable through `bpy` (professional quality):**
- Hard-surface and props: primitives + Boolean (Exact/Fast) → Bevel modifier (Width/Offset/Percent, Segments, Limit Method Angle or Weight, Harden Normals) → Weighted Normal; Mirror/Array/Solidify/Screw/Simple Deform; Smooth-by-Angle; panel lines by inset+boolean; greebles as linked/instanced collections (kitbash). 5.2 Geometry Nodes adds the **Mesh Bevel node**, lists, geometry bundles, Collection Children, and GN modifiers on Empties (fully generated objects).
- Environments/dioramas: GN scattering, instancing, modular kits on a grid (pivots that snap — Fab guidance), trim-sheet UVs by code.
- Low-poly flat/smooth, voxel (Remesh ▸ Blocks or GN cube instancing), isometric scenes, toon setups (Solidify hull, Line Art, Shader-to-RGB ramps), procedural materials (noise/voronoi/wave + ColorRamp, curvature-based edge wear, AO-based dirt), vertex colors written as attributes, AO/curvature/normal baking.
- Presentation: cameras, 3-point rigs, HDRI worlds, turntables, Workbench clay passes, color management — all scriptable and deterministic.

**Needs a human sculptor/painter (be honest at intake):** organic faces/anatomy, cloth folds, hand-painted texture intent, creature design, "appealing" stylized characters. Code approximations: metaballs/Skin modifier + Subdivision for blobby organics, curves + Skin for limbs, procedural displacement for rock/terrain, GN hair curves. Offer T0–T1 placeholders for these and say so.

**Techniques that make code-driven work look professional**
1. Bevel every visible edge with widths consistent per tier (e.g. primary 5–20 mm, panel lines 1–3 mm, micro 0.5–1 mm at 1 m object scale — `(verify)` convention) and harden normals.
2. Real-world scale, pivot at base, applied transforms, named objects/materials (marketplace checklists).
3. Material definition before texture: correct roughness/metallic per surface; metals never roughness 0; add roughness breakup (imperfection textures) and edge lightening for stylized.
4. Consistent texel density per tier; power-of-two textures; one material per surface.
5. Light and color-manage deliberately (§5): PBR Neutral for stylized swatches, AgX for realism, Standard for flat.
6. Wear story by rule (edges/crevices/horizontals/contacts) at a stated 0–100% intensity; add one asymmetry.
7. Review in Workbench clay first (form), then wireframe (topology), then lit (materials) — each a scripted preset.

**5.x API facts that bite scripts:** engine identifier `BLENDER_EEVEE` (not `_NEXT`); `scene.eevee.gtao_distance` moved to the view layer as `ambient_occlusion_distance` (5.0); GN modifier inputs now `modifier.properties.inputs.<id>.value` instead of `modifier["id"]` (5.2, breaking); `gpu.init()` required for GPU work in `--background` (5.2); data-block names up to 255 bytes; Intel Mac builds dropped (5.0); Python 3.13 (5.1).

Sources: https://docs.blender.org/manual/en/5.0/modeling/modifiers/generate/bevel.html · https://docs.blender.org/manual/en/5.0/modeling/modifiers/modify/weighted_normal.html · https://developer.blender.org/docs/release_notes/5.2/geometry_nodes/ · https://developer.blender.org/docs/release_notes/5.2/python_api/ · https://developer.blender.org/docs/release_notes/5.0/ · https://developer.blender.org/docs/release_notes/5.0/eevee/ · https://80.lv/articles/overwatch-technical-overview · https://www.strayspark.studio/blog/procedural-damage-game-assets-complete-workflow · https://blog.turbosquid.com/2013/09/11/checkmate-pro-v2-checklist/ · https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab

---

## 8. Suggested intake fields

| Field | Options / format | Drives |
|---|---|---|
| Style | one of the 9 rows in §1 (+ 1–3 named references) | topology, texture, view transform, outline method |
| Tier | T0–T4 | tri budget, texture size, materials, LODs, render engine/samples |
| Target platform | mobile / PC-console / offline | texel density, texture max |
| Camera use | first-person / third-person / top-down / iso / cinematic | TD (10.24 vs 5.12 px/cm), lens, ortho angles |
| Shape language | % round / square / triangle | silhouette, bevel radius |
| Proportions | heads-tall or key ratios | blockout |
| Palette | 3–5 hex + 60/30/10 roles; shadow hue | materials, backdrop |
| Materials | per surface: hex, roughness range, metallic, edge treatment | shader setup |
| Wear | 0/25/50/75/100% + where | procedural wear masks |
| Read hierarchy | ordered list | contrast placement |
| Presentation | clay / wireframe / lit / turntable; resolution | render presets |

Sources: derived from §1–§7 above (no additional URLs).

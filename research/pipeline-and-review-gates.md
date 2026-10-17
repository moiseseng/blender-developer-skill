# How studios run the 3D asset production pipeline and its review gates

Research notes for the blender-3d-team skill, 2026-10-17. Primary sources (studio docs, engine docs, the Blender 5.2
manual/API RST bundled with the Blender MCP server, a real competition brief, GDC abstracts, Kitsu docs) are preferred;
vendor blogs (Lemonsky, Zatun, IRPR, Stray Spark, Rebusfarm) are labelled secondary. The Polycount wiki refused
connections all session and polycount.com returned 403; Riot/Blizzard/Ubisoft style guides are not public. Anything not
confirmed from a fetched page is marked `(verify)`. Sibling files hold the detail this file points to:
`topology-and-modeling.md`, `uv-and-texel-density.md`, `delivery-standards.md`.

## Contents
1. Game / real-time asset: stage sequence, outputs, gates
2. Render / offline asset: where it differs
3. The asset brief: fields, budgets, deliverables, acceptance criteria (+ a real brief)
4. Review gates: what is checked, by whom, status workflow, "approved blockout"
5. Review-render conventions (turntable, beauty, wireframe)
6. Roles and what each owns
7. Naming conventions (engine side, Blender Studio side, baking)
8. Reference numbers
9. Blender 5.2 settings the gates depend on (bake, FBX)
10. Definition of done (merged checklist)
11. Items still to verify

---

## 1. Game / real-time asset: stage sequence, outputs, gates

Three studio-side descriptions agree on the shape: Ratloop Games Canada (14 steps, 3 formal check-ins), Lemonsky
(5 stages, each a gate) and Zatun (5 milestone reviews); 80.lv (Daniel McGowan) adds the level-side framing and the
Callisto Protocol breakdown adds what is gathered before modeling.

| # | Stage | Output | Gate / check before next stage | Source |
|---|---|---|---|---|
| 1 | Level brief / kickoff | Story or objective, presented to concept, level design and env art together | none; starts concept work | 80.lv |
| 2 | Concept + reference | Concept sheet showing shape, material, story and function of the asset | Concept "finalized and approved" as reference (Ratloop step 2); Zatun review 1 before any 3D | Callisto, Ratloop, Zatun |
| 3 | Brief / spec | Reference, specs, scope, deadline; four documents exist first (style guide, tech spec, workflow map, definition of done) | Brief owner named | Lemonsky |
| 4 | Info gathering | Exact size of the prop, height of the area it sits in, viewing distance | asked of design before blockout | Callisto |
| 5 | Blockout / white-box / proxy | Primitive placeholders in engine; proxy carries silhouette, accurate proportions, clear material groupings | **Check-in #1** (Ratloop): standards + integration needs with Audio, Animation, Level Design, UI, Programming; "locks silhouette, proportion and read before detail work" (Lemonsky) | Ratloop, 80.lv, Lemonsky |
| 6 | High-poly | Sculpt or subdiv/bevel model used only for baking | Zatun review 3 "before retopology and texturing" | Ratloop, Zatun |
| 7 | Low-poly / retopo | Game mesh within budget | **Check-in #2** "geometric state before texture work" (Ratloop); Zatun review 4 = topology + UVs in-engine | Ratloop, Zatun |
| 8 | UV | UV0 (+ UV1 lightmap if the engine needs it) | UV islands split along all hard-edge borders (Marmoset); lightmap UVs may not overlap (Allar) | Marmoset, Allar |
| 9 | Bake | Normal + detail maps from high to low | Tangent space must match target engine (Mikk/xNormal for Unity and Unreal) | Marmoset |
| 10 | Texture | PBR set; variants (clean / rusty / destroyed) where context needs them | Zatun review 5 "complete with textures in the game environment" | Callisto, Zatun |
| 11 | LODs + collision | LOD chain; collision primitives | Every mesh needs collision; meshes seen at distance need LODs | Allar |
| 12 | Export + import | FBX/glTF per naming spec; materials assembled in engine | Import test, naming validation, folder-structure check | Ratloop 11-12, Lemonsky |
| 13 | Integration QA | Asset in the build on target hardware | **Check-in #3** final QA (Ratloop); "counts as delivered only when performing in the actual build" (Lemonsky) | Ratloop, Lemonsky |
| 14 | Submission | Released to main build | Supervisor sets Done (Kitsu) | Ratloop, Kitsu |

Ordering: Ratloop builds low-poly before high-poly (hard-surface, mid-poly first); Zatun, Kaedim and Blender Studio
(sculpt then retopo) put high-poly first for organic work; decide per asset in the brief. Tiers set priority and budget:
hero (interactive/destructible, fewest, most resources) > modular (trim sheets, tiling textures) > props > vista
("bottom of the list for poly-priority") (80.lv).

Sources: https://ratloopgamescanada.com/dev-blog/art-pipeline · https://www.lemonskystudios.com/insights/game-art-outsourcing-pipeline · https://zatun.com/a-step-by-step-guide-to-outsourcing-3d-game-art/ · https://80.lv/articles/the-stages-of-environment-art-in-gamedev · https://80.lv/articles/creating-props-for-the-callisto-protocol · https://marmoset.co/posts/toolbag-baking-tutorial/ · https://github.com/Allar/ue5-style-guide · https://docs.kaedim3d.com/creating-assets/game-ready-assets/stages-of-a-game-ready-asset

## 2. Render / offline asset: where it differs

1. Stages (Blender Studio): pre-production (storyboard, editorial, previz, R&D, concept design) → asset creation
   (modeling/sculpting, shading, rigging, animation testing, 2D assets) → shot production (assembly, layout, animation,
   lighting, FX, rendering, coloring) → publishing. No bake-to-low-poly stage is mandatory: detail stays as multires
   ("reproject sculpted details onto subdivided geometry"); shading bakes procedurals to textures only when needed.
2. Modeling input = **approved concept design** + sculpted T-pose, optional hero pose, deformation tests, a style
   guide "with creative limitations" (Blender Studio).
3. Modeling hand-off (Blender Studio): final topology, basic UVs, shape keys, textures baked from sculpt detail, pivot
   markers as empties, helper shapes (closed eyes, open mouth), applied transforms; consistent normals with smooth
   shading, merge-by-distance done, scale and most modifiers applied, UVs verified, logical names and collections,
   placeholder materials with viewport colours, unused attributes removed.
4. Shading inputs: "Base Models for tests / Final Topology for task"; first decisions PBR vs NPR, Cycles vs EEVEE,
   procedural vs data-driven; data layers = UV maps, color attributes, named generic attributes; main shader and
   utility node groups live in library files and are linked in (Blender Studio).
5. File model: one task file per department (`rex.rigging.blend`, `rex.shading.blend`) owning one Task Layer
   (Modeling, Rigging, Shading, Grooming); **pull** dependencies, then **push** into the versioned publish file that
   shots link. A new version (v001, v002) is cut only for breaking changes and "will always be in the 'Review' state
   and needs to be first approved by the team" (Blender Studio asset pipeline).
6. VFX variant (CAVE): files move WIP → version → published; model scale and world coordinates fixed per show;
   approval checkpoints are 360 shaded + wireframe turntables and reference-aligned lineups (section 5) before
   hand-off to texturing/lookdev and rigging.
7. Department hand-off control (Autodesk Maya docs): the TD authors the asset template with published attributes; the
   artist builds and publishes extra attributes; the TD "reviews the integrity of the template" and approves the asset
   to the next department.
8. Tracker statuses (Kitsu): TODO → WIP → Waiting For Approval (artist) → Retake or Done (supervisor only); every
   Retake increments a counter used as a quality metric.

Sources: https://studio.blender.org/tools/pipeline-overview/introduction · https://studio.blender.org/tools/pipeline-overview/asset-creation/modeling · https://studio.blender.org/tools/pipeline-overview/asset-creation/shading · https://studio.blender.org/blog/asset-pipeline-update-2022 · https://caveacademy.com/wiki/pipeline/vfx-pipeline/modelling-pipeline/ · https://mintlify.wiki/cgwire/kitsu/tasks/task-status · https://help.autodesk.com/cloudhelp/2017/ENU/Maya/files/GUID-4201475F-80EE-4931-8D8A-847BC3ADBFC0.htm

## 3. The asset brief: fields, budgets, deliverables, acceptance criteria

| Field | Content | Source |
|---|---|---|
| Identity | Asset name per naming convention; tier (hero / modular / prop / vista) | 80.lv, IRPR |
| Function + context | Story and function; where it lives; exact size; height of the area; viewing distance | Callisto |
| Target | Engine + version, platform, quality tier, verification method (= the definition-of-done doc) | Lemonsky |
| References | Concept art; reference boards with on-target **and off-target** examples; mood/material notes; in-engine screenshots; reference models; unacceptable examples with explanations | Lemonsky, Zatun |
| Geometry budget | Polygon/triangle budget per asset type; topology requirements | Zatun, IRPR, gamedeveloper.com |
| Texture budget | Resolution, required PBR map set, texel density, formats, colour space, atlas organisation | Zatun, IRPR, Lemonsky |
| Rules | Naming conventions, folder structure, pivot/scale rules, LOD requirements, rigging requirements | IRPR, Lemonsky, Zatun |
| Deliverables | File formats, folder structure, source files included or not, version numbering, who integrates | Lemonsky, Zatun |
| Review plan | Named owners for brief, feedback consolidation, sign-off, dispute resolution; revision budget per asset; escalation path + timeline | Lemonsky |
| Schedule | Deadline; milestones "blocking, first pass, final" | Lemonsky, IRPR |
| Acceptance | QC checklist: polygon counts, texture resolution, performance; style consistency, no visible errors | Zatun |

Stated rules: "Expect 2-3 rounds of revisions minimum" for complex assets (Zatun); notes must be location-specific,
drawn on the asset or tied to references (Lemonsky); the lead's spec document lists polygon budgets, texture dimensions,
animation frame counts and visual references (gamedeveloper.com).

**A real brief with numbers** (Skills Canada BC, 3D Game Art 2023 PDF): 6.5 h; still-life lunch + drink + lunchbox + a
"mystery hero prop" revealed on the day; "no more than 20,000 tris"; "no texture map should exceed 2048 x 2048"; "make
maximum use of the texture maps so pixel space is not wasted"; maps combined into materials; UVs "distribute pixels
evenly"; "texel density will be examined during judging"; deliverable = lit Sketchfab URL + zipped project with textures
and models; out-of-spec work "will not be judged". Marks /100: organisation 5, brief interpretation 10, modelling 20,
texture mapping 30, hero prop 25, export/presentation 10. Scoresheet lines (1-5 each): appropriate distribution of
polygons; organised naming of objects, materials, assets; similarity to concept; even and efficient use of texture
space; varied map types (colour, normal, specular, alpha); organised naming of maps; even UV distribution; cleanliness
(seamlines, ngons, normals, holes); illumination and camera set-up. Studio art tests use the same form, e.g. 50k tris,
max 6 textures 512-4096 plus one alpha ≤1024, scene 10x10 m to 300x300 m, 2 weeks `(verify: Polycount thread, snippet only)`.

Sources: https://skillscanada.bc.ca/wp-content/uploads/2023/01/3D-Game-Art-Provincials-2023.pdf · https://www.lemonskystudios.com/insights/game-art-outsourcing-pipeline · https://zatun.com/a-step-by-step-guide-to-outsourcing-3d-game-art/ · https://3d.irpr.agency/guides/game-art-outsourcing-guide/ · https://www.gamedeveloper.com/production/common-methodologies-for-lead-artists · https://polycount.com/discussion/189476/enrvironment-art-test · GDC abstracts on briefs/spec sheets: https://gdcvault.com/play/1023158/Art-Direction-Bootcamp-Guerrilla-Games · https://gdcvault.com/play/1015796/Uncharted

## 4. Review gates: what is checked, by whom, status workflow

| Gate | Checked | Decides | Source |
|---|---|---|---|
| G0 Concept / brief | Concept approved as reference; four pre-production docs exist; budgets filled in | Art director; brief owner | Ratloop, Lemonsky |
| G1 Blockout | List below | inferred: AD + lead on read; tech artist on scale/pivot; design/animation on function | Ratloop, 80.lv, Lemonsky |
| G2 High-poly | Form and detail density against style guide, before retopo | AD / lead | Zatun |
| G3 Low-poly + UV | Tri count vs budget; n-gons, normals, holes; seams on hard edges; texel density; padding; lightmap UVs non-overlapping; reviewed **in-engine** | Lead + tech artist | Ratloop, Zatun, Allar, Marmoset |
| G4 Bake | Seam/skew artifacts; tangent space = engine; padding set | Tech artist | Marmoset |
| G5 Texture / material | Style-guide match; PBR ranges (metallic black or white only); variants present | AD / lead | Zatun, Khronos |
| G6 Integration QA | Naming validation, folder structure, import test, in-engine pass on target hardware; collision and LODs present | Tech art / QA; cross-discipline check-in | Lemonsky, Ratloop, Allar, Epic |
| G7 Sign-off | Status set to Done (supervisor-only) | Supervisor / lead | Kitsu |

**"Approved blockout" means all of these hold:**
1. Silhouette reads at the intended viewing distance; proportions match concept (Lemonsky "locks silhouette,
   proportion, and read"; 80.lv "silhouette, accurate proportions").
2. Material groupings are visible as separate blocks (80.lv proxy phase).
3. Placed in the target scene/engine at real scale and checked for fit (Ratloop white-box; gamedeveloper.com: review
   "in the game environment", not in the modeling package).
4. Exact size, surrounding height and viewing distance confirmed with design (Callisto).
5. Pivot/origin and orientation decided and marked (Blender Studio pivot empties; Epic: pivot at 0,0,0).
6. Interaction/animation needs confirmed with the other disciplines (Ratloop check-in #1 attendees; Callisto keeps
   animation and lighting "in the loop").
7. Tri and texture budgets allocated per the brief; proportion changes after this point count as rework.

Status and feedback mechanics: Kitsu TODO → WIP → WFA (artist) → Retake (supervisor, counter +1) or Done (supervisor);
a Blender Studio asset version stays in Review until the team approves. One named review owner consolidates notes into
a single decision; each asset has a revision budget tracked per round; stalled reviews have an escalation path
(Lemonsky). Feedback is specific, with visual markup and annotated screenshots (Zatun); reviews are more frequent early
and never dropped near deadlines; assets need explicit approval before advancing (gamedeveloper.com). Automated gate:
Unreal Data Validation runs on asset save (default), on demand from the Content Browser, and from the command line in
CI; rules are added by subclassing `UEditorValidatorBase` (C++, Blueprint, Python) or overriding `IsDataValid`; result
is Pass or Fail per asset.

Sources: https://ratloopgamescanada.com/dev-blog/art-pipeline · https://www.lemonskystudios.com/insights/game-art-outsourcing-pipeline · https://80.lv/articles/the-stages-of-environment-art-in-gamedev · https://80.lv/articles/creating-props-for-the-callisto-protocol · https://www.gamedeveloper.com/production/common-methodologies-for-lead-artists · https://github.com/Allar/ue5-style-guide · https://marmoset.co/posts/toolbag-baking-tutorial/ · https://mintlify.wiki/cgwire/kitsu/tasks/task-status · https://dev.epicgames.com/documentation/en-us/unreal-engine/data-validation-in-unreal-engine

## 5. Review-render conventions (turntable, beauty, wireframe)

1. Turntable = one 360° rotation before a fixed camera; standard 240 frames at 24 fps = 10 s (The Rookies).
2. Passes: beauty (lit, textured), grey/clay (form), wireframe overlay (topology) (The Rookies). VFX modelling: shaded
   360 + wireframe 360, each "with reference and slate info"; scan-based work adds four reference-aligned lineups
   (shaded, shaded+wire, wire+backplate, backplate) (CAVE).
3. Cameras: 50-85 mm equivalent; front, three-quarter, side; locked (The Rookies). "Lock cameras down from v001 and
   use the same cameras" for every version; portrait framing for tall assets, landscape for wide (CAVE).
4. Background neutral mid-grey 18-50 %; never pure white or black (The Rookies).
5. Lighting: clean studio HDRI for beauty (The Rookies); lineups "do not modify the lighting", default shaded mode,
   consistent across iterations (CAVE).
6. Reference kit order: colour chart, grey card, grey ball, chrome ball, then asset; kit at the edge or rendered
   separately (CAVE).
7. Delivery: frames → mp4, reviewed in SyncSketch (CAVE) or as Kitsu previews with annotations; game assets are also
   reviewed inside the engine build (gamedeveloper.com).

Sources: https://www.therookies.co/blog/education/present-3d-props · https://caveacademy.com/wiki/post-production-assets/assets-general/framing-your-asset-for-turntables/ · https://caveacademy.com/wiki/pipeline/vfx-pipeline/modelling-pipeline/creating-360-model-lineup-viewport-renders/ · https://www.gamedeveloper.com/production/common-methodologies-for-lead-artists

## 6. Roles and what each owns

| Role | Owns | Gate authority | Source |
|---|---|---|---|
| Art director | Visual direction: palettes, detail levels, environment aesthetic, character design; works with the game designer; holds the vision across env, characters, VFX, UI, animation `(verify: ScreenSkills page returned 403)` | Approves concept (G0), look at G2/G5 | gamedeveloper.com, Callisto |
| Lead artist | "Art processes; tools; geometric budgets; texture budgets; task definitions; scheduling of tasks"; asset-spec document; weekly team meeting; flags production risk | Runs reviews; explicit approval before an asset advances | gamedeveloper.com |
| Technical artist / TD | Pipelines, tools, engine/platform constraints, shaders; asset templates and validators; supervises TAs; training | Checks template/asset integrity, approves hand-off to next department; owns automated validators | Maya docs, Lucid Games posting, Epic, Blender Studio |
| Modeler / environment artist | Blockout → high → low → UV → bake; names parts for hand-off; LODs/collision | Submits WFA with turntables | Callisto, Blender Studio, Kitsu |
| Texture / shading artist | PBR vs NPR, engine choice, procedural vs data-driven, layered materials, variants, utility node groups | Submits WFA | Blender Studio, Callisto |
| Supervisor (tracker role) | Reviews previews, writes annotations | Only role that sets Retake or Done | Kitsu |
| Review owner / producer | Workflow map naming owners for brief, feedback, sign-off, disputes; revision budget | "Delivered" = performs in build | Lemonsky |
| QA / integration | In-engine verification on target hardware, import and naming checks | G6 | Lemonsky, Ratloop; distinct art-QA job title `(verify)` |

Sources: https://www.gamedeveloper.com/production/common-methodologies-for-lead-artists · https://80.lv/articles/creating-props-for-the-callisto-protocol · https://help.autodesk.com/cloudhelp/2017/ENU/Maya/files/GUID-4201475F-80EE-4931-8D8A-847BC3ADBFC0.htm · https://hitmarker.net/jobs/lucid-games-technical-art-director-746291 · https://mintlify.wiki/cgwire/kitsu/tasks/task-status

## 7. Naming conventions

**7.1 Engine side (Unreal, Unity).** Epic's page gives `[AssetTypePrefix]_[AssetName]_[Descriptor]_[OptionalVariant]`
and prefixes `SM_` static mesh, `SK_` skeletal mesh, `T_` texture, `M_` material, `MI_` material instance, `PHYS_`,
`PM_`, `PPM_`, `HDR_`, `BP_`, `ABP_`, `AS_`, `AM_`, `BS_`, `SKEL_`, `Rig_`, `WBP_`, `DT_`, `E_`, `F_`, `FXS_/FXE_/FXF_`.
**Epic lists no texture suffixes**; the `_D/_N/...` set is community practice:
- Allar: `Prefix_BaseAssetName_Variant_Suffix`; generic variants two digits (`Rock_01`); chained variants allowed
  (`Flooring_Marble_01`). Suffixes `_D` base colour, `_N` normal, `_R` roughness, `_A` alpha, `_AO`, `_B` bump, `_E`
  emissive, `_S` specular, `_M` mask **and** `_M` metallic (ambiguous). Packed textures stack suffixes (`_ERO`); alpha in
  the `_D` alpha channel keeps `_D`; RGBA packing beyond that is discouraged.
- Looman: `_D _N _E _M(mask) _R _MT(metallic) _AO`; examples `T_Grass_D`, `T_Pipe_Long_N`, `SM_Pipe_01`. Resolution
  for this skill: `_MT` metallic, `_M` mask, `_ORM` packed AO/roughness/metallic (`_ORM` is common UE practice but on
  neither Epic's nor Allar's page `(verify)`).
- FBX collision (Epic): `UBX_` box, `UCP_` capsule, `USP_` sphere, `UCX_` convex, as `UCX_[RenderMeshName]_##`;
  RenderMeshName "must be identical to the name of the render mesh". Sockets `SOCKET_[RenderMeshName]_##`; one
  socketed mesh per FBX.
- LODs: Unity imports `Name_LOD0 ... _LOD7` automatically (max 8, LOD0 most detailed). Unreal uses no suffix: LODs go
  in an FBX LOD group with "Import LODs" enabled.
- Bake groups (Marmoset Quick Loader): `objectname_high`, `objectname_low`, `objectname_high_bolt`; case-insensitive.

**7.2 Blender Studio (film side).** "No caps, no gaps"; no `+=#^*&^$()?!`; `_` inside a token, `-` between tokens,
`.` for variants. Files `{show}-{type}-{name}.{variant}-{task}-v{version}_{info}.{ext}`; types `char|set|lib|props`;
tasks `reference|concept|design|sculpting|modeling|shading|rigging`; versions only on exports/renders. Examples
`char-gabby-concept.blend`, `char-gabby.red-shading-v006.png`, `140_0010-anim.blend` (shot `010_0030` = sequence×10,
shot×10). Datablocks: `lower_underscore_case` with ALL-CAPS prefix; root collections `CH-` character, `PR-` rigged prop,
`LI-` library/environment, `SE-` set, `LG-` light rig, `CA-` camera rig; sub-collections named after Task Layers;
objects `GEO-`, `RIG-`, `LGT-`, `GPL-`, `WGT-`, `HLP-`, `ENV-`, `TMP-`; `.L/.R` sides, `.variant` (`.burned`), `_001`
not `.001`; mesh and shape-key names match the object; node trees `GN-`, `SH-`, `CM-` + identifier; every datablock
carries the asset identifier. Textures lowercase with `_`, asset first, map type last (`col`, `bump`, `nor`, `disp`,
`spec`): `bark_oak_normal.png`, `bark_oak_albedo.png`.

**7.3 Portable files (Khronos).** Names from `a-z _ - 0-9`, first character a letter, words separated by `_` or `-`.

Sources: https://dev.epicgames.com/documentation/en-us/unreal-engine/recommended-asset-naming-conventions-in-unreal-engine-projects · https://github.com/Allar/ue5-style-guide · https://tomlooman.com/unreal-engine-naming-convention-guide/ · https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine · https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-static-mesh-lods-using-fbx-in-unreal-engine · https://docs.unity3d.com/Manual/lod-group-configure.html · https://marmoset.co/posts/toolbag-baking-tutorial/ · https://studio.blender.org/tools/naming-conventions/introduction · https://studio.blender.org/tools/naming-conventions/datablock-names · https://studio.blender.org/tools/naming-conventions/file-types · https://studio.blender.org/tools/naming-conventions/examples · https://raw.githubusercontent.com/mlimper/3DC-Asset-Creation/main/asset-creation-guidelines/RealtimeAssetCreationGuidelines.md

## 8. Reference numbers

| Item | Value | Source / status |
|---|---|---|
| Competition prop budget | ≤20,000 tris; maps ≤2048² | Skills Canada 2023 (primary) |
| Commerce/web real-time asset | ≤100,000 tris; file "ideally less than 5 MB"; 1K or 2K base colour/ORM/emissive, 2K normals; power-of-two, square not required; 1 unit = 1 m; bottom-centre at 0,0,0; metallic black or white only | Khronos v1.0 text (v2.0 pages are WIP stubs) |
| Texel density | hero ≈10.24 px/cm (1024 px/m); background ≈5.12 px/cm | Rebusfarm (secondary); per-perspective values first-person 10.24 / third-person 5.12 / top-down 2.56 px/cm `(verify, search snippet only)` |
| Tier budgets | hero prop 5-20k, env prop 0.5-5k, background 0.1-1k, character 15-80k, vehicle 10-50k tris; LOD1 50 %, LOD2 25 %, LOD3 ≤10 %; collision 8-32 tris; UV padding 2-4 px | Stray Spark blog, indicative `(verify)` |
| Review cadence / revisions | 3 formal check-ins (blockout, geometry, final); "2-3 rounds minimum" | Ratloop; Zatun (secondary) |
| Bake quality | AO 256 rays test, 512+ final; 8-bit with dithering; details ≥1 px | Marmoset |
| LOD count | Unity LOD Group max 8 levels | Unity manual |
| Turntable | 240 f @ 24 fps; 50-85 mm; 18-50 % grey | The Rookies (secondary) |
| Blender bake margin | default 16 px, type Adjacent Faces | Blender 5.2 API `BakeSettings` |

Sources: sections 3, 5, 9 plus https://ja.rebusfarm.net/blog/texel-density-basics-every-artist-should-know · https://www.strayspark.studio/blog/game-ready-asset-checklist-blender-2026 · https://docs.unity3d.com/Manual/lod-group-configure.html

## 9. Blender 5.2 settings the gates depend on

Confirmed against the RST bundled with the Blender MCP server (`render/cycles/baking.rst`, `bpy.types.BakeSettings.rst`,
`bpy.ops.export_scene.rst`):
1. Bake (G4): *Selected to Active* casts from selected (high) to active (low). *Cage* on → rays from a ballooned copy;
   a cage object must have identical topology (face count and order); *Cage Extrusion* is the inward distance with
   cage, *Max Ray Distance* without. Avoid Edge Split hard splits during the bake ("non-smooth normals around the
   edges"). Normal space default **Tangent**; margin default **16 px**, type **Adjacent Faces** (alt. Extend), present
   "to avoid discontinuities at UV seams, due to texture filtering and mip-mapping".
2. FBX export defaults (`bpy.ops.export_scene.fbx`): `global_scale=1.0`, `apply_unit_scale=True`,
   `apply_scale_options='FBX_SCALE_NONE'`, `axis_forward='-Z'`, `axis_up='Y'`, `use_space_transform=True`,
   `bake_space_transform=False` (experimental, "known to be broken with armatures/animations"), `mesh_smooth_type='OFF'`
   (doc: prefer Normals Only when the importer reads custom normals), `use_tspace=False` (tris/quads-only meshes),
   `use_triangles=False`, `use_mesh_modifiers=True` (prevents exporting shape keys), `path_mode='AUTO'`,
   `embed_textures=False`. The manual's "Scale ... 10 is the default" contradicts the API default 1.0 `(verify in UI)`.
3. Tangent basis: bake Mikk/xNormal for Unity and Unreal; Y+ = OpenGL (Blender), Y- = DirectX; flip only when the
   engine needs it (Marmoset). A vendor UE5 preset (`-Y Forward, Z Up, Apply Scalings = FBX All, Smoothing = Face`)
   conflicts with the manual's Normals Only advice `(verify per engine)`.

Sources: bundled Blender 5.2 manual/API RST (online mirror https://docs.blender.org/manual/en/latest/render/cycles/baking.html) · https://marmoset.co/posts/toolbag-baking-tutorial/ · https://www.strayspark.studio/blog/game-ready-asset-checklist-blender-2026

## 10. Definition of done (merged checklist)

1. Brief, style guide, tech spec and DoD doc exist; asset matches the brief's engine, platform, quality tier and
   verification method [Lemonsky].
2. Concept and blockout were approved at their gates; no proportion change since blockout [Ratloop, Lemonsky].
3. Geometry within tri budget; no n-gons, holes, flipped normals; duplicates merged; transforms applied; history
   cleaned; mesh name = object name [Skills Canada scoresheet, Blender Studio modeling, Team-Swamp].
4. Real-world scale, 1 unit = 1 m where the engine agrees; pivot at origin / bottom-centre; in-engine scaling is an
   override, not a correction [Khronos, Epic FBX, Allar].
5. UVs valid, no unintended overlaps, even texel density, seams on hard edges, lightmap UV non-overlapping if required
   [Skills Canada, Marmoset, Allar].
6. Bake clean, tangent space = engine; textures power-of-two within budget; metallic black/white; map names per
   convention [Marmoset, Khronos, Allar/Looman].
7. LODs for distance-visible meshes; collision for every mesh, named `UCX_/UBX_/USP_/UCP_` [Allar, Epic].
8. Names follow the project convention for files, objects, materials, textures; folder structure validated [Epic,
   Blender Studio, Lemonsky].
9. Review package delivered: locked-camera turntables (beauty, grey, wireframe); all annotated notes resolved
   [CAVE, The Rookies].
10. Imported into the engine on the development branch (prefab/asset exists), validators pass, verified on target
    hardware; supervisor sets Done [Team-Swamp, Epic Data Validation, Lemonsky, Kitsu].
11. Source files, exports and version numbers delivered as agreed; render side: publish version approved out of Review
    [Lemonsky, Blender Studio].

Sources: https://www.lemonskystudios.com/insights/game-art-outsourcing-pipeline · https://github.com/Team-Swamp/Codename-BDLMTW/wiki/Definition-of-done · https://studio.blender.org/tools/pipeline-overview/asset-creation/modeling · https://github.com/Allar/ue5-style-guide · https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine · https://mintlify.wiki/cgwire/kitsu/tasks/task-status · https://raw.githubusercontent.com/mlimper/3DC-Asset-Creation/main/asset-creation-guidelines/RealtimeAssetCreationGuidelines.md

## 11. Items still to verify
- Polycount wiki pages (Texture Baking, Polygon Count, Texel Density) were unreachable; shipped-game tri counts and the
  "UV seam = hard edge" rule are cited from Marmoset and the sibling files instead.
- `_ORM` suffix and 2.56 px/cm top-down texel density are common practice, not on a fetched primary page.
- Stray Spark tier budgets, LOD percentages, collision tri counts and the UE5 FBX preset are single-vendor claims.
- Polycount art-test numbers (50k tris, 6 textures, 2 weeks) come from a search snippet; the thread returned 403.
- Blender Studio task-review page is a WIP stub; the Review-state rule comes from the 2022 asset-pipeline blog.
- Riot, Blizzard, Ubisoft style guides are not public; Guerrilla and Naughty Dog GDC talks were read as abstracts only.
- QA as a named art-QA role was not found in a primary source; the integration-QA gate itself is sourced.

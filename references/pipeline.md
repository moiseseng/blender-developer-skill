# The pipeline: stages, gates, roles, definition of done

Distilled from `research/pipeline-and-review-gates.md` (Ratloop Games, Lemonsky, Zatun, 80.lv, Blender
Studio, CAVE Academy, Kitsu, Epic, Khronos; sources there). This is the studio process the skills
reproduce; each phase skill tells you how to run its stage.

## Stages and what each gate checks

| # | Stage | Output | Gate before the next stage |
|---|---|---|---|
| 0 | Brief and references | `docs/brief.md`: function, context, exact size, viewing distance, style, references (on-target and off-target), tier, budgets, deliverables, review plan | **G0 brief approval** by the user. Nothing is modeled before it. |
| 1 | Blockout (white-box) | Primitive proxy with correct silhouette, proportions and material groupings, at real scale, pivot decided | **G1 blockout approval**: silhouette and proportions read at the viewing distance; material groups visible; size confirmed; pivot and orientation marked; budgets allocated. Proportion changes after G1 are rework. |
| 2 | Modeling (high and low, or mid-poly) | Delivery mesh within budget; LODs and collision where the brief asks | **G2/G3 geometry review** before any texturing: tri count vs budget, no n-gons / holes / flipped faces, transforms applied, pivot, naming, shading intent. The audit script is the gate. |
| 3 | UV, bake, texture | UV0 (and UV1 for lightmaps when the target bakes lighting), baked or procedural PBR set, textures on disk | **G4/G5 texture review**: seams on hard edges, even texel density, padding, PBR value ranges, style match. |
| 4 | Review and QA | `docs/qa/<date>-<scope>.md` with severities | **G6 integration QA**: audit pass, export verified against the target's conventions, renders reviewed by the art director. Blockers and majors go back to the owning stage. |
| 5 | Export and delivery | Packet (`references/delivery-packet.md`): exports, textures, renders, README, manifest, changelog | **G7 sign-off** by the user; status `done`. |

Hard-surface work usually goes low or mid-poly first (bevel + weighted normals, no bake); organic work
goes high-poly first (sculpt, then retopo), which code cannot do alone (see `references/topology.md`).
The brief decides.

## What "approved blockout" means (all seven)

1. Silhouette reads at the intended viewing distance and proportions match the reference numbers.
2. Material groupings are visible as separate blocks.
3. Placed at real scale and checked against its surroundings (the brief's context).
4. Exact size, surrounding height and viewing distance confirmed.
5. Pivot and orientation decided and applied.
6. Interaction or animation needs noted (hinges, sockets, moving parts).
7. Triangle and texture budgets allocated per the brief.

## Roles and authority

| Role | Owns | Decides |
|---|---|---|
| Art director | Visual direction: style, palette, detail level, read; approves the look | G0 look, G1, G5, final renders |
| Modeler | Blockout → model → LODs/collision; build script; naming | Submits for review with the render sheet |
| Texture artist | UVs, bakes, materials, variants | Submits for review with textures and beauty renders |
| Tech artist / QA lead | Budgets, validators, export conventions, engine readiness; writes the QA report | G3, G4, G6; the only one who sets `pass` |
| User (supervisor) | The brief and the gates | Approves G0, G1, G7; can waive a gate explicitly |

The review owner consolidates feedback into one decision per round; notes are location-specific and
measurable ("la tapa es 20% más gruesa que la referencia"), never "make it better". Expect 2–3 revision
rounds on a complex asset; a status model of `wip → waiting for approval → retake | done`, where only
the supervisor sets done, is what `state.md` encodes.

## Review-render conventions

Fixed cameras from the first version and reused for every version (so iterations are comparable):
3/4, front, side, top at 50 mm (85 mm for hero close-ups), neutral grey background (18–50%), beauty +
clay + wireframe passes, a 360° turntable. `render_review.py` does exactly this; the contact sheet is
the review artefact and lives in `renders/<stage>/`.

## Naming (engine side, what the audit expects)

`SM_<Asset>` static mesh, `SK_` skeletal, `T_<Asset>_<Map>` textures, `M_<Asset>` materials, `MI_`
instances; collision `UCX_<SM_Name>_00`; LODs `SM_<Asset>_LOD0…`; variants `_01`, `_02`. Mesh data named
like its object. Files and folders English, alphanumeric and underscores, under 140 characters. The
audit's default regex is `^(SM|SK|SMP|BLK)_[A-Z][A-Za-z0-9]*(_[A-Za-z0-9]+)*$` (`BLK_` for blockout
objects, `SMP_` for placeholders); the brief can override it.

## Definition of done (merged)

1. Brief approved; asset matches its engine, platform, tier and deliverables.
2. Blockout approved; no proportion change since.
3. Geometry within budget; no n-gons, holes, flipped normals, duplicates; transforms applied; mesh name
   equals object name.
4. Real-world scale, pivot per the brief, resting on the ground.
5. UVs valid, no unintended overlap, even texel density, seams on hard edges; lightmap UVs if required.
6. Textures within budget, power of two, metallic binary, normal convention stated, names per convention.
7. LODs and collision as the brief asks, named per the target.
8. Render package: contact sheet, turntable, wireframe; all review notes resolved.
9. Export verified (bbox, counts, materials) against the target's conventions.
10. Packet complete: README, manifest, changelog, licenses; QA report `pass`.

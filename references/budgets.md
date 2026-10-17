# Detail tiers and budgets

The brief picks a tier and a target; together they fix every number the audit checks. Numbers are
synthesised in `research/art-styles-and-presentation.md` §2 and `research/topology-and-modeling.md`
§5 from platform docs (Roblox, Meta Quest, Khronos 3DC, Epic, Unity), Dota 2 workshop budgets and
marketplace rules. Hard caps are quoted as published; ranges are working budgets.

## Tiers

| Tier | Use | Triangles (prop / character) | Textures | Materials | LODs | Review render | Code-driven time |
|---|---|---|---|---|---|---|---|
| **T0 Blockout / placeholder** | scale, silhouette, layout | 50–2 000 / ≤ 5 000 | none (object colour, clay) | 1 | none | Workbench clay | 5–20 min |
| **T1 Game-ready low** (mobile, VR, background, Roblox) | shipped on constrained targets | 300–1 500 / 1 500–5 000 | 256–512 px atlas; 256–512 px/m | 1 | LOD1 at 40–50% | EEVEE 16 spp | 20–60 min |
| **T2 Game-ready standard** (PC/console prop, NPC) | the typical shipped asset | 1 000–10 000 / 10 000–20 000 | 1 024–2 048 px; 512–1 024 px/m | 1–2 | 100 / 50 / 25% | EEVEE 64 spp | 1–3 h |
| **T3 Hero / high** (first-person weapon, main character, marketplace hero) | readable in close-up | 10 000–50 000 / 15 000–50 000 | 2 048–4 096 px; 1 024–2 048 px/m | 2–4 | 3–4 levels | Cycles 128–256 spp, denoised | 3–8 h |
| **T4 Offline / cinematic** | renders, archviz, film | subdivision, no cap | 4 096–8 192 px, UDIM; 2 048–5 120 px/m | unlimited | none | Cycles, noise threshold 0.01 | 8 h+ |

Time is an estimate for one asset built through code; organic characters at T3+ need a human sculpt
pass on top (see `references/topology.md`).

## Triangle budgets by asset class and target (LOD0)

| Asset class | Mobile / Roblox | PC / console | Web (three.js, glTF viewers) | VR standalone | Offline render |
|---|---|---|---|---|---|
| Small prop (mug, tool, bottle) | 100–500 | 500–3 000 | 500–3 000 | 300–1 500 | 5k–50k |
| Large prop (furniture, crate, machine) | 500–2 000 | 2 000–10 000 | 2 000–10 000 | 1 000–5 000 | 10k–100k |
| Modular kit piece | 200–2 000 | 1 000–10 000 | 1 000–10 000 | 500–5 000 | 10k–200k |
| Character (NPC / player) | 1 500–5 000 | 15 000–50 000 | 10 000–40 000 | 5 000–20 000 | 100k+ |
| Vehicle | 2 000–8 000 | 20 000–100 000 | 20 000–60 000 | 10 000–40 000 | 300k+ |
| Hero (first-person weapon, showcase) | 3 000–10 000 | 50 000–150 000 | 50 000–100 000 | 20 000–60 000 | unbounded |

Hard caps from platform docs: Roblox 20 000 tris per MeshPart, accessories 4 000, avatar body 10 742
total, one material per MeshPart, no n-gons, watertight; Unreal mobile 65 535 vertices per mesh; Unity
convex collider 255 tris; Meta Quest 2 under 750k tris and 100 draw calls per frame, Quest 3 1.5M and
200; Khronos 3DC web targets 30k–250k tris and 0.5–3 MB per asset; Fab/UEFN textures power of two,
8 192 max.

Cylinder sides: 8 for things under 10 px on screen, 16 for props, 24–32 for hero close-ups, 48+ render
only.

## Texture sizes and texel density

| Target or camera | Texel density | Typical texture per class |
|---|---|---|
| Mobile, Roblox | 256 px/m (Roblox: 512 px for most textures, 256 for minor) | small prop 256, large prop 512 |
| Third-person PC/console | 512 px/m | small prop 512, large prop / weapon 1K, character body 2K |
| First-person (weapons, hands) | 1 024 px/m | 2K, hero 4K |
| VR close inspection, cinematic | 2 048–4 096 px/m | 4K, UDIM |
| Modular environment | ~200 px/m (2K spans 10 m) | tileables and trims at 2K |

Hero assets get 2x the project density, background 0.5x; neighbouring assets stay within ±10%.
Square, power-of-two always: 512 / 1 024 / 2 048 / 4 096. VRAM at BC7: 1K ≈ 1.3 MB, 2K ≈ 5.3 MB,
4K ≈ 21 MB per map.

## How the audit uses this

`scripts/blender/mesh_audit.py` ships default budgets per class (`CLASS_BUDGETS`: placeholder,
small_prop, large_prop, modular_piece, character, vehicle, building, hero, cinematic). The brief's
numbers override them on the command line (`--max-tris`, `--max-texture`, `--max-materials`,
`--texture-size` for the density estimate). Over budget is a blocker; within 10% of it is a note.

# blender-3d-team

A professional 3D asset team as Claude Code skills, built on Blender 5.x. An art director interviews
you and writes the brief; a modeler builds the asset through a parametric Blender script (blockout
first, detail after, with an audit and a render review after every pass); a texture artist unwraps,
builds procedural PBR or palette materials and bakes the texture set; a tech artist audits, exports
with per-engine presets and verifies the files; QA writes the report with severities; the packet ships
with renders, README and manifest. Gates where a studio has them: brief approval, blockout approval,
final review.

> **En español:** este plugin convierte a Claude en un equipo de arte 3D. Primero te entrevista
> (qué es, para qué motor, estilo, referencias, nivel de detalle, presupuestos, entregables) y escribe
> el brief; con tu aprobación modela en Blender por código, se audita y se mira los renders en cada
> iteración, texturiza y hornea, pasa QA con revisores independientes y te entrega el paquete
> exportado para Unity, Unreal, Godot, Roblox, web o render. Solo te pregunta en las puertas: brief,
> blockout y revisión final. Las skills están en inglés (para el modelo); la conversación y los
> documentos del asset se escriben en tu idioma.

Inspired by [gamedev-team](https://github.com/moiseseng/roblox-developer-skill): small skills with
authority, explicit gates, a contract document before autonomy.

## Install

As a plugin:

```bash
claude plugin marketplace add moiseseng/blender-developer-skill
claude plugin install blender-3d-team@blender-3d-team
```

Or from a local clone, inside Claude Code: `/plugin marketplace add /path/to/blender-3d-team` then
`/plugin install blender-3d-team@blender-3d-team`. Install the whole repo: the skills read
`references/`, `agents/` and `scripts/` relative to the plugin root.

Requirements: Blender 4.2 LTS or newer (tested on 5.2.2 LTS), Python 3, git. Optional: the official
Blender MCP extension (Blender Lab) for live control of an open Blender, `ffmpeg` for turntable video,
`npx @gltf-transform/cli` for glTF validation. Check everything and smoke-test the bundled scripts:

```bash
bash scripts/doctor.sh
```

## Use

Start a session in your project and say what you need: "hazme un cofre del tesoro para mi juego",
"necesito una nave low-poly para Godot", "revisa este .blend para Unity". The `using-blender-3d-team`
skill is injected at session start and routes to the phase:

1. **asset-brief** interviews you (one question at a time, with options) and writes
   `assets/<Asset>/docs/brief.md`. You approve it.
2. **blockout** builds the proxy from `scripts/build.py`, renders the review sheet, compares it with
   your references, asks you to approve silhouette and proportions.
3. **modeling** adds the detail in audit-and-render loops; **uv-texturing** unwraps, builds materials
   and bakes textures; **review-qa** runs the audit and two independent reviewers (art director, tech
   artist) and writes the QA report; you approve the final renders.
4. **export-delivery** exports with the engine's preset, verifies the files, renders the presentation
   set and writes README, manifest and changelog.

Everything is reproducible: the build script is the source of truth, the `.blend` is an output.

## What's inside

```
skills/        using-blender-3d-team (router) · asset-brief · blockout · modeling · uv-texturing ·
               review-qa · export-delivery · extending-blender-3d-team
agents/        art-director · modeler · texture-artist · tech-artist (fresh-context reviewers/workers)
references/    pipeline · style-guide · budgets · topology · procedural-modeling · uv-texel-density ·
               pbr-texturing · review-renders · export-targets · delivery-packet · blender-python ·
               blender-mcp  (distilled rules with numbers; sources in research/)
research/      the sourced research notes behind every reference (URLs, (verify) marks)
scripts/       blender_run.sh (headless runner) · doctor.sh · make_manifest.py
scripts/blender/  mesh_audit.py (geometry/UV/material/naming/budget audit with severities)
               render_review.py (beauty + clay + wireframe contact sheet, turntable)
               bake_textures.py (procedural -> BaseColor/Roughness/Metallic/Normal/AO/ORM, rewire)
               export_asset.py (glb/gltf/fbx_unity/fbx_unreal/fbx_roblox/obj/usd presets + verification)
               material_kit.py (linear colour, PBR materials, edge wear, cavity dirt, palette textures, texture stats)
               scene_setup.py · _load.py · _tests/ (fixture + smoke test)
hooks/         SessionStart hook that injects the router skill
evals/         prompts for the skill-creator eval loop
```

## Blender execution modes

| Mode | When | How |
|---|---|---|
| Live MCP | Blender GUI open with the MCP extension running | the skills run the build script in the open file and take viewport looks |
| Background MCP | the MCP server can find Blender (`BLENDER_PATH`) | one headless Blender per call |
| Headless CLI | always, when Blender is installed | `scripts/blender_run.sh <script> [file.blend] -- args` |

The CLI is the default for autonomous work; it is deterministic and leaves nothing half-done in a GUI.

## Honest limits

Code-driven modeling reaches professional quality on hard-surface props, furniture, machines, sci-fi,
vehicles to mid-poly, modular kits, stylized low-poly, signage and terrain, and on every technical gate.
It does not produce animation-grade organic topology (faces, hands), cloth folds or hair; the brief
says so up front and offers a stylized interpretation or a base mesh for a human sculpt pass.

## Extend

`skills/extending-blender-3d-team/SKILL.md`: add a target engine (preset + reference row), a material
recipe, a QA check, a role. Scripts must pass `scripts/doctor.sh` before they ship.

## License

MIT.

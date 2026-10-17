# Question bank for the intake interview

Pick from here; never ask all of it. Each entry: the question (in the user's language when asked), the
options to offer, what the answer drives. Options go through AskUserQuestion with the recommended one
first and marked "(recomendado)".

## 1. Object and purpose

- "¿Qué es exactamente y para qué lo vas a usar?" — free text, then confirm in one sentence.
  Drives: asset class (budget row), pivot rule, interaction needs.
- "¿Dónde vive y desde qué distancia se ve normalmente?" — options: "en mano / primera persona",
  "a 2–5 m (tercera persona)", "a 10 m o más (fondo)", "render de producto (cualquier distancia)".
  Drives: texel density, tier recommendation, silhouette priority.
- "¿Tiene partes que se muevan o se usen (tapa, ruedas, bisagras, agarre)?" — options: "no, estático",
  "sí: <partes>". Drives: separate objects, pivots per part, naming.

## 2. Target

- "¿Para qué motor o salida?" — options: Unity, Unreal, Godot, Roblox, "web / visor glTF (three.js,
  Sketchfab)", "render en Blender (no motor)", "impresión 3D". Drives: presets, normal convention,
  caps, packing.
- "¿En qué plataforma correrá?" — options: móvil, PC/consola, VR, web. Drives: budgets row, texture
  sizes.
- "¿Qué cámara lo verá?" — options: primera persona, tercera persona, cenital/isométrica, cinemática.
  Drives: texel density tier, lens for renders, ortho vs persp.

## 3. Style

- "¿Qué estilo?" — options (one line each, from `references/style-guide.md`): low-poly facetado
  (paleta plana), low-poly suave/estilizado, pintado a mano, toon/cel, PBR estilizado (Overwatch),
  PBR realista, hard-surface sci-fi, voxel, isométrico/diorama, "como esta referencia".
- "¿Lenguaje de formas?" — options: "redondo y amable", "cuadrado y robusto", "anguloso y agresivo",
  "mezcla (indica %)". Drives: bevel radius, silhouette.
- "¿Paleta?" — options: "te paso hex / una imagen", "elige tú 3–5 colores coherentes con la referencia",
  "monocromo + un acento". Drives: material_kit colours, palette texture.
- "¿Nivel de desgaste?" — options: 0% (nuevo), 25% (usado), 50% (gastado), 75–100% (abandonado).
  Drives: edge wear / cavity dirt amounts.

## 4. References

- "¿Tienes imágenes de referencia? Pásame rutas o enlaces." — free. Then: "¿Qué tomo de cada una y
  qué no?" per image. Drives: proportion numbers, material callouts, palette.
- Without references: "Propongo estas tres referencias conocidas: A, B, C. ¿Cuál se acerca más?"
  Drives: a shared mental image before modeling.

## 5. Tier

- "¿Qué nivel de detalle?" — options with the numbers for this class and target already filled in:
  "T1 game-ready bajo: ~<N> tris, texturas <px>", "T2 estándar (recomendado para <target>): ~<N> tris,
  <px>", "T3 hero: ~<N> tris, <px>, 3–8 h", "T4 cinemático: subdivisión, 4–8K". Drives: every budget.

## 6. Dimensions and pivot

- "¿Tamaño real? Propongo <x × y × z m> (típico para <clase>)." — options: "ese", "otro: …".
- "¿Pivote?" — options with the default for the class first: base-centro, entre los pies, eje de
  bisagra, esquina de módulo (rejilla de <1/2/4> m), eje de giro.
- "¿Simétrico en X?" — sí / no. Drives: mirror workflow, UV mirroring allowance.

## 7. Textures

- "¿Cómo se texturiza?" — options: "paleta plana (una textura pequeña de colores)", "materiales
  procedurales horneados a un set PBR", "valores PBR sin texturas (render)", "trim/tileable (kit
  modular)". Drives: uv-texturing path.
- "¿Tamaño de textura?" — options from the tier. "¿Empaquetado?" — only for Unreal (ORM) / Unity
  (mask map) / Roblox (separados).
- "¿Necesitas segundo canal UV para lightmaps?" — only for Unity/Unreal static lighting.

## 8. Deliverables

- "¿Formatos?" — multi-select: glb, fbx_unity, fbx_unreal, fbx_roblox, usd, obj, "solo .blend".
- "¿LODs y colisión?" — options: "no", "LOD1 50%", "LOD1 + LOD2", "colisión convexa UCX", "ambos".
- "¿Renders de presentación?" — options: "hoja de contacto + turntable 24 frames (recomendado)",
  "solo hoja de contacto", "set de tienda (thumbnail 1200², 5 beauty 1080p, 2 wireframe, UV layout)".
- "¿Dónde dejo el paquete?" — default `assets/<Asset>/`.

## 9. Process

- "¿Paro en el blockout para que apruebes silueta y proporciones, o sigo hasta la revisión final?" —
  options: "para en blockout (recomendado)", "autónomo hasta la revisión final".
- "¿Hago commits por fase (sin push)?" — sí / no. Only inside a git repo.

## Follow-ups that save a remodel

- When the object has text, logos or decals: "¿Qué texto/logo y en qué cara?" (decal plane or baked).
- When it is modular: "¿Qué tamaño de rejilla y qué lado es el frente del módulo?"
- When it is a character: "¿Rig y animación después? Entonces el pivote va entre los pies y la pose en
  T/A." and the honesty line about organic topology.
- When the target is Roblox: "¿Un MeshPart o varios? Cada uno lleva un material."
- When the user says "lo más detallado posible": translate to a tier with numbers and the time it
  costs; "detallado" without a camera distance wastes budget where nobody looks.

# <Asset> · v<1.0.0> · <YYYY-MM-DD>

<Una frase: qué es, estilo, para qué motor.>

| Campo | Valor |
|---|---|
| Autor | <usuario> (modelado por código con blender-3d-team) |
| Blender | <versión> · render de previews: <EEVEE/Cycles> |
| Tier / clase | <T2 · large_prop> |
| Licencia | <ver LICENSE.txt> |

## Geometría

| Objeto | Tris | Verts | Dims (m, ancho × profundo × alto) | Pivote | Materiales |
|---|---|---|---|---|---|
| SM_<Asset> | | | | base-centro | |
| SM_<Asset>_LOD1 | | | | | |
| UCX_SM_<Asset>_00 | | | | | |

- Escala real, 1 unidad = 1 m; transformaciones aplicadas; frente −Y en Blender (+Z en glTF/Godot/Unity).
- Topología: quads dominante, sin n-gons, cerrada; sombreado por aristas marcadas (30°).
- No pensado para subdivisión (asset de tiempo real) · Pensado para subdivisión (render).

## Texturas

| Mapa | Archivo | Tamaño | Bits | Espacio de color | Notas |
|---|---|---|---|---|---|
| BaseColor | T_<Asset>_BaseColor.png | 2048 | 8 | sRGB | |
| Normal | T_<Asset>_Normal.png | 2048 | 16 | Non-Color | OpenGL (+Y); Unreal: Flip Green Channel |
| ORM | T_<Asset>_ORM.png | 2048 | 8 | Non-Color | R = AO, G = rugosidad, B = metálico |

Flujo metal/rugosidad. Densidad de téxeles <N> px/m.

## Formatos

| Carpeta | Formato | Preset | Notas de importación |
|---|---|---|---|
| export/glb | glTF 2.0 binario | glb | Godot / three.js / visores: sin ajustes |
| export/fbx_unity | FBX | fbx_unity | Unity: Bake Axis Conversion si hubiera rotación; texturas en `textures/` |
| export/fbx_unreal | FBX | fbx_unreal | Unreal: 1 UU = 1 cm; Flip Green Channel en la normal; colisión UCX incluida |

## Presentación

`renders/final/`: hoja de contacto, turntable <N> frames (`turntable_00..`), thumbnail 1200², wireframe.

## Cómo se hizo

`scripts/build.py` regenera la malla (parámetros al inicio del archivo); `source/<Asset>.blend`
contiene el material procedural y el horneado; `docs/brief.md`, `docs/decisions.md` y `docs/qa/`
documentan el proceso.

## Terceros

Ver `THIRD_PARTY_NOTICES.txt`.

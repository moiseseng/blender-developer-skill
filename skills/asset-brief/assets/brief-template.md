# Brief · <Asset>

estado: borrador | aprobado (YYYY-MM-DD)
autor: <usuario> · art director: Claude
proyecto: <ruta del proyecto> · carpeta: `assets/<Asset>/`

## 1. Qué es y para qué

- **Objeto:** <una frase: qué es, qué hace, dónde vive>
- **Contexto:** <escena o nivel, qué lo rodea, altura del espacio, distancia típica de la cámara>
- **Interacción / animación:** <partes móviles, cómo se sostiene, nada>
- **Prioridad visual:** hero | modular | prop | fondo

## 2. Objetivo técnico

| Campo | Valor |
|---|---|
| Motor / salida | Unity · Unreal · Godot · Roblox · web (glTF) · render offline · impresión |
| Plataforma | móvil · PC/consola · VR · web |
| Cámara | primera persona · tercera persona · cenital/iso · cinemática |
| Tier | T0 · T1 · T2 · T3 · T4 |
| Presupuesto de triángulos (LOD0) | <N> (máximo) |
| Texturas | <tamaño> px, <set: BaseColor/Normal/ORM…>, densidad <N> px/m |
| Materiales | <N> máximo |
| Normal map | OpenGL (+Y) · DirectX (−Y) |
| LODs | ninguno · LOD1 50% · LOD1 50% + LOD2 25% |
| Colisión | ninguna · UCX convex · caja · n/a |
| Caps de plataforma | <p. ej. Roblox 20 000 tris por malla, 1 material por MeshPart> |

## 3. Estilo

**Línea de estilo:** *<estilo>*; lenguaje de formas <% redondo / cuadrado / triangular>; proporciones
<alturas de cabeza o ratios clave>; paleta <3–5 hex> en 60/30/10; materiales <por superficie: hex,
rugosidad a–b, metálico 0/1>; aristas <bisel en mm o horneado>; desgaste <0–100%> en <aristas / cavidades /
contactos>; orden de lectura <1, 2, 3>; cámara <persp 50 mm / orto iso>; transformación de vista
<Standard / PBR Neutral / AgX>.

| Superficie | Material | Base (hex) | Rugosidad | Metálico | Tratamiento de aristas |
|---|---|---|---|---|---|
| <tapa> | <madera pintada> | #…… | 0.45–0.6 | 0 | bisel 4 mm |

**Paleta:** <hex dominante 60%> · <hex secundario 30%> · <hex acento 10%>

## 4. Referencias

| # | Archivo / URL | Qué tomar de ella | Qué NO tomar |
|---|---|---|---|
| 1 | `docs/references/ref_01.jpg` | silueta y proporciones | el color |

**Silueta:** <2–3 formas que sobreviven al relleno negro>
**Proporciones (ratios):** alto : ancho : profundo = <a : b : c>; <parte> = <x%> de <todo>
**Jerarquía de lectura:** 1) <…> 2) <…> 3) <…>
**Historia de desgaste:** <qué le pasó al objeto; dónde se ve>

## 5. Dimensiones y pivote

| Campo | Valor |
|---|---|
| Tamaño real (m) | ancho <x> × profundo <y> × alto <z> |
| Pivote | base-centro · entre pies · eje de bisagra · esquina de módulo · eje de giro |
| Frente | −Y en Blender (convención de los presets) |
| Simetría | X · ninguna |
| Escala de bisel | primario <mm>, líneas de panel <mm>, micro <mm> |
| Partes | <lista de objetos: SM_<Asset>_Body, SM_<Asset>_Lid…> |

## 6. Texturas y materiales

- **Enfoque:** paleta plana · procedural horneado a PBR · valores PBR a mano · trim/tileable
- **Set a entregar:** <T_<Asset>_BaseColor, _Normal, _ORM …> a <tamaño> px
- **Densidad de téxeles objetivo:** <N> px/m (±10% entre partes)
- **UV:** única (horneado) · atlas · espejo permitido en <partes> · segundo canal lightmap sí/no

## 7. Lo que el código puede y no puede hacer aquí

<Frase honesta: qué se construye por script con calidad profesional y qué quedaría para un pase manual
de escultura/pintura, y la interpretación acordada.>

## 8. Entregables

- `source/<Asset>.blend` (texturas empaquetadas) y `scripts/build.py`
- `export/<preset>/…` para: <glb · fbx_unity · fbx_unreal · fbx_roblox · usd · obj>
- `textures/` <set>
- `renders/`: hoja de contacto, turntable <N> frames, thumbnail <px>, wireframe
- `README.md` (manifiesto), `CHANGELOG.md`, `LICENSE.txt`, `THIRD_PARTY_NOTICES.txt`
- Destino del paquete: <ruta>

## 9. Proceso y puertas

| Puerta | Quién aprueba | Criterio |
|---|---|---|
| Brief | usuario | esta tabla |
| Blockout | usuario (o automático si "autónomo") | silueta y proporciones vs referencias en vistas orto |
| Revisión final | usuario | audit `pass`, renders aprobados por el art director |
| Entrega | usuario | paquete completo |

- Modo autónomo tras el brief: sí · no (parar en blockout)
- Commits por fase: sí · no
- Rondas de revisión previstas: 2–3

## 10. Aceptación

- Audit técnico `pass` con los presupuestos de § 2
- Renders coinciden con § 3 y § 4 a juicio del art director (hallazgos mayores: 0)
- Exportaciones verificadas (bbox, conteos) para cada preset de § 8
- README con conteos, dimensiones, lista de texturas, convención de normales, licencia

## Cambios

| Fecha | Cambio | Afecta a | Aprobado |
|---|---|---|---|

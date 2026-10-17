# Style guide: the styles, what each demands, and how to describe one

Distilled from `research/art-styles-and-presentation.md` (sources there: Valve's TF2 papers, Overwatch
GDC talks, Dota 2 workshop rules, Blender Studio, Blender 5.x manual).

## The nine styles the brief can name

| Style | Geometry and shading | Textures | Light that flatters it | Pitfalls |
|---|---|---|---|---|
| **Low-poly flat-shaded** | Visible facets, all faces flat (sharp angle 0), under ~1 000 tris per prop | One palette texture (tiny image of colour squares, every face UV'd into its swatch) or vertex colours; bake AO and multiply | One strong key plus coloured ambient; light angle matters more than texture | Skinny triangles spike the shading; mixing smooth and flat; too many colours; several materials |
| **Low-poly smooth / stylized** (Monument Valley, Alto's) | Smooth shading, simple quads, silhouette first; often orthographic camera | No textures: flat materials or vertex colours plus a world-space height gradient; limited hues per zone | Unlit or soft key plus rim; foreground purer, background tinted to the sky | Over-detailing; a perspective camera that breaks the diorama |
| **Hand-painted stylized** (WoW, Dota 2) | Medium poly (Dota 2: 1 500 to 4 000 tris per slot, LOD1 = 40%), chunky scaled-up forms | Diffuse only with light painted in: top light, baked AO, edge highlights; value gradient dark feet, light head; big crisp patterns | Flat in-engine light; presentation: warm key, faint cool fill | Double lighting (painted plus strong dynamic); noisy small detail |
| **Toon / cel** | Clean quads, deliberate creases where lines should appear | Flat colours plus a 2–3 step ramp (Shader to RGB → Color Ramp in EEVEE) | Single key, hard terminator; view transform **Standard** | AgX flattening the colours; inverted hull breaking on concave corners |
| **PBR stylized** (Overwatch, Fortnite) | Silhouette first, big readable shapes, no micro bumps; bevel everything, no raw 90° edges; density where it is seen (hands, face, weapon) | Metal/rough PBR; lighten base colour on convex edges; clear material contrast; metals never perfectly clean | Bright optimistic key, strong fill; view transform **Khronos PBR Neutral** | Noise that does not read at distance; over-shiny metals; no value hierarchy |
| **PBR realistic** | Support loops or baked high→low; real-world scale mandatory | Scan-like albedo, roughness variation from imperfection maps, wear placed by rules | HDRI plus soft key; view transform **AgX** | One flat roughness; uniform wear; wrong scale; 4K where 2K would do |
| **Hard-surface sci-fi / mech** | Primary → secondary → tertiary forms; panel cuts by boolean; Bevel + Weighted Normal; greebles instanced | Trim sheets and tileables plus decals; edge wear from curvature; panel-line AO | Studio HDRI with strong speculars so bevels catch light | Inconsistent bevel widths; boolean n-gon shading; greeble soup with no rest areas |
| **Voxel** | Cubes on a grid; 32³ characters often read better than 64³ | Palette-indexed colour (256 entries max), palette decided first | Soft sun plus AO and cavity | One-voxel edges alias; too many colours |
| **Isometric / diorama** | Orthographic camera; 2:1 dimetric = rotation X 60°, Z 45°; true iso X 54.736°, Z 45° | Any of the above; scene composed to the frame | One fixed key matching the camera; shadows on-grid | Accidental perspective camera; tile scale mismatch |

## Rules that hold across styles

- **Silhouette first.** Fill the asset black at gameplay distance: it must still be identifiable and
  distinct from everything else in its class. Interior detail echoes the silhouette shapes.
- **Read hierarchy.** Decide what is seen first, second, third; give the first the biggest shape and
  the highest contrast. Big shapes near the top of characters.
- **Value before hue.** Three-value notan (dark, mid, light) before picking colours. Shadows cool, never
  black; lights warm; saturation peaks near the terminator.
- **Palette 60/30/10** with 3 to 5 hex values; the 10% accent goes to gameplay-relevant parts.
- **Areas of rest.** Leave 30–40% of the surface low-detail. Density where the player looks.
- **Material definition before texture.** Correct roughness and metallic per surface; metals never
  roughness 0; roughness breakup everywhere; stylized work lightens base colour on convex edges.
- **Wear tells a story** at a stated 0 / 25 / 50 / 75 / 100% intensity: convex edges polished, crevices
  dark, rust on horizontals and bottoms, contact wear where hands and feet touch. Add one asymmetry.
- **Consistent edge treatment.** One bevel width per detail level across the whole asset (primary
  5–20 mm, panel lines 1–3 mm, micro 0.5–1 mm at 1 m scale; scale with the asset).
- **Colour-manage on purpose.** Standard for flat / toon / voxel, Khronos PBR Neutral for stylized PBR
  and product shots, AgX for realism. The wrong transform makes a correct palette look wrong.

## Describing a style precisely (the brief's style line)

"*{style}*; silhouette language {e.g. 70% round / 30% square}; proportions {heads tall or key ratios};
palette {3–5 hex} in 60/30/10; materials {base hex, roughness a–b, metallic 0/1} per surface; edges
{bevel width or baked}; wear {0–100%} at {edges / crevices / contacts}; read order {1, 2, 3}; camera
{persp 50 mm / ortho iso}; view transform {Standard / PBR Neutral / AgX}."

## Reading references

Group them as Blender Studio does: style (films, other games), design (concept art, photos),
technical (topology, polycount, material setups), real life (anatomy, fabric, the real object). From
each reference extract, in this order: silhouette (2–3 shapes that survive a black fill), proportions
(heads-tall, width:height, where the biggest mass sits), shape language (round = friendly, square =
stable, triangle = dynamic), material callouts per surface (name, hex, roughness range, metallic, edge
treatment), palette with roles, wear story, read hierarchy. Write the numbers into the brief; the
blockout gate compares orthographic renders against them.

In Blender, references go in as image empties (`bpy.data.images.load` → empty with
`empty_display_type='IMAGE'`, depth Front, low opacity, in the asset's `Reference` collection, never
rendered or exported) or as camera background images for a fixed viewpoint. `scene_setup.py` places
them.

## Outlines (toon)

Inverted hull (Solidify + flipped normals + backface-culled black emission) is real-time and exports
as geometry; Freestyle works with EEVEE and Cycles at render time only; the Grease Pencil Line Art
modifier gives the most control (contour, crease, intersections, material borders) and needs the
active camera. For a game target, inverted hull or a shader-side outline is the deliverable; Freestyle
and Line Art are presentation only.

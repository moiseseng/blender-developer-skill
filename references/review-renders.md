# Review renders: how to look, what to check, how to present

`scripts/blender/render_review.py` produces the sheet; this file says what to do with it. Rendering
conventions come from `research/art-styles-and-presentation.md` §5 and `research/delivery-standards.md` §3.

## The contact sheet

`render_review.py --modes beauty,clay,wireframe --views three_quarter,front,right,top` gives one PNG
with three rows (beauty, clay with cavity, wireframe over clay) and one column per view, plus
`turntable_sheet.png` when `--turntable N` is set. Open it with the Read tool every iteration. Judge
in this order and stop at the first row that fails:

1. **Clay row, orthographic views: form.** Proportions against the brief's numbers (measure on the
   image: the front view is to scale, the object fills the frame the same way every time). Silhouette
   readable. Primary / secondary / tertiary forms present in the tier's proportion. Pinching, dents,
   faceting on surfaces that should be smooth, soft edges that should be hard.
2. **Wireframe row: topology.** Even density, loops following the form, bevels consistent, no fans of
   triangles on curved areas, no dense patches on flat ones.
3. **Beauty row: material and read.** Can you tell what each surface is made of? Albedo plausible,
   roughness varied, metals read as metal. Seams, stretching, uneven texel density, texture noise that
   does not read at distance. Sits on the ground, shadow contact, pivot where the brief says.
4. **Turntable sheet:** a bad angle, a hole, an intersecting part, a face that flips dark.

Write the findings as measurable statements ("lid 20% too thick", "bevel on the base twice the width of
the body's") so the next build-script edit is a parameter change.

## Settings per style

| Style | Engine for beauty | View transform | Notes |
|---|---|---|---|
| Low-poly flat, toon, voxel | EEVEE | Standard | Flat colours stay flat; one key, coloured ambient |
| Stylized PBR, hand-painted | EEVEE (review), Cycles (final) | Khronos PBR Neutral | Swatches read as authored under grey light |
| Realistic PBR, hard-surface | EEVEE (review), Cycles 128+ spp denoised (final) | AgX | HDRI plus soft key; bevels need strong speculars |

`render_review.py --view-transform "Khronos PBR Neutral"` etc. Review resolution 1280x720 or 640x360
for fast loops; final presentation 1920x1080.

## Presentation set for delivery (what `export-delivery` renders)

From marketplace specs (TurboSquid, Fab, Unity, Superhive): a square thumbnail at least 1200x1200 on
neutral grey (RGB 247 for stores), at least 5 beauty shots at 1920x1080 (angles, close-up, context,
scale reference), at least 2 wireframe shots, a UV layout over base colour when UVs are declared, a
turntable of 12 to 36 evenly spaced frames numbered `_00`, `_01`... Lighting: 3-point at 2:1 key:fill
for a soft commercial look (4:1 for drama), or a CC0 studio HDRI from Poly Haven (`studio_small_0x`,
`brown_photostudio_0x`). Camera 50 mm general, 85 mm hero, never under 35 mm; object fills 60–75% of
the frame, camera height at a third to half of the object's height. No logos, borders, watermarks or
text over 25% of the image.

`render_review.py` covers the review sheet and turntable frames; for the delivery set run it at
1920x1080 with `--turntable 24 --views three_quarter,three_quarter_back,front,right` and
`--modes beauty,wireframe`, then add close-ups by hand (camera and `focal_mm=85`) if the tier is T3+.

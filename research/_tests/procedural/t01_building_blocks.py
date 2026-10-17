import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math
from mathutils import Vector, Matrix
reset_scene(); col = ensure_collection("SM_Primitives")

def prim(name, fn, **kw):
    bm = bmesh.new(); fn(bm, **kw); ob = obj_from_bmesh(bm, name, col); report(ob, name); return ob

prim("cube_size1", bmesh.ops.create_cube, size=1.0)
prim("cylinder_seg32_r0.5_d2", bmesh.ops.create_cone, segments=32, radius1=0.5, radius2=0.5, depth=2.0, cap_ends=True, cap_tris=False)
prim("cylinder_captris", bmesh.ops.create_cone, segments=32, radius1=0.5, radius2=0.5, depth=2.0, cap_ends=True, cap_tris=True)
prim("cone_r0.5_to_0_d1", bmesh.ops.create_cone, segments=32, radius1=0.5, radius2=0.0, depth=1.0, cap_ends=True)
prim("circle_seg16_r0.5_cap", bmesh.ops.create_circle, segments=16, radius=0.5, cap_ends=True)
prim("uvsphere_32x16_r0.5", bmesh.ops.create_uvsphere, u_segments=32, v_segments=16, radius=0.5)
prim("icosphere_sub2_r0.5", bmesh.ops.create_icosphere, subdivisions=2, radius=0.5)
prim("grid_10x10_size1", bmesh.ops.create_grid, x_segments=10, y_segments=10, size=1.0)
prim("cube_matrix_2x1x1_on_ground", bmesh.ops.create_cube, size=1.0,
     matrix=Matrix.Translation((0, 0, 0.5)) @ Matrix.Diagonal((2, 1, 1, 1)))

# ---- Panel build: cube -> inset_region -> extrude inward -> bevel -> bisect -> fill
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.translate(bm, verts=bm.verts[:], vec=(0, 0, 0.5))      # sit on ground
top = max(bm.faces, key=lambda f: f.calc_center_median().z)
a0 = top.calc_area()
r = bmesh.ops.inset_region(bm, faces=[top], thickness=0.08, depth=0.0, use_even_offset=True)
print("INSET_REGION returns rim faces:", len(r['faces']), "input face shrank:", round(a0, 3), "->", round(top.calc_area(), 3))
report(snapshot(bm, "stage1_inset"), "panel_stage1_inset")
bm_bad = bm.copy(); f_bad = max(bm_bad.faces, key=lambda f: f.calc_center_median().z)
bmesh.ops.extrude_face_region(bm_bad, geom=[f_bad])          # faces only -> original face is KEPT (non-manifold)
report(obj_from_bmesh(bm_bad, 'stage2_faces_only'), 'panel_stage2_extrude_GEOM_FACES_ONLY_gotcha')
r = bmesh.ops.extrude_face_region(bm, geom=[top] + list(top.edges) + list(top.verts))   # pass verts+edges+faces
new_verts = [g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)]
bmesh.ops.translate(bm, verts=new_verts, vec=(0, 0, -0.03))     # recess 3 cm
report(snapshot(bm, "stage2_extrude"), "panel_stage2_extrude_in")
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.01, offset_type='OFFSET', segments=2, profile=0.5,
                affect='EDGES', clamp_overlap=True)
report(snapshot(bm, "stage3_bevel"), "panel_stage3_bevel_all_edges")
r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=(0, 0, 0.6), plane_no=(0, 0, 1), clear_outer=True)
cut_edges = [g for g in r['geom_cut'] if isinstance(g, bmesh.types.BMEdge)]
report(snapshot(bm, "stage4_bisect_open"), "panel_stage4_bisect_clear_outer_open")
bmesh.ops.contextual_create(bm, geom=cut_edges)                # cap the cut with one ngon
report(snapshot(bm, "stage5_capped"), "panel_stage5_bisect_capped")
# cleanup ops
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
report(snapshot(bm, "stage6_tri"), "panel_stage6_triangulate")
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts[:], edges=bm.edges[:])
report(snapshot(bm, "stage7_dissolve"), "panel_stage7_dissolve_limit_1deg")
bm.free()

# ---- inset_individual: paneled block, two routes to a recessed panel
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
r = bmesh.ops.inset_individual(bm, faces=bm.faces[:], thickness=0.08, depth=0.0, use_even_offset=True)
inner = [f for f in bm.faces if f not in set(r['faces'])]
print("INSET_INDIVIDUAL rim faces:", len(r['faces']), "inner (original) faces:", len(inner))
bmesh.ops.inset_individual(bm, faces=inner, thickness=0.0, depth=-0.02)   # thickness 0 + depth = straight push-in
report(obj_from_bmesh(bm, "paneled_block"), "inset_individual_6_panels_recessed")

# ---- remove_doubles + recalc_face_normals
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((-0.5, 0, 0)))
bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0.5, 0, 0)))
ob = obj_from_bmesh(bm, "two_cubes_touching", free=False); report(ob, "two_cubes_before_remove_doubles")
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
# interior coincident faces remain -> delete faces whose both sides are shared (they're duplicates at x=0)
dupes = [f for f in bm.faces if abs(f.calc_center_median().x) < 1e-6]
bmesh.ops.delete(bm, geom=dupes, context='FACES')
bmesh.ops.reverse_faces(bm, faces=bm.faces[:3])          # deliberately flip 3 faces
ob2 = obj_from_bmesh(bm, "merged_flipped", free=False); report(ob2, "merged_with_3_flipped_faces")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
report(obj_from_bmesh(bm, "merged_fixed"), "merged_after_recalc_face_normals")
print("DONE t01")

import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
reset_scene(); random.seed(3)
ASSET = 2.0   # longest dimension in metres -> bevel/panel widths derive from it
BEVEL = ASSET * 0.005          # 1 cm chamfer on a 2 m hull (0.5% of asset size)
PANEL_BORDER = ASSET * 0.02    # 4 cm
PANEL_DEPTH = ASSET * 0.004    # 8 mm

# ---- hull with panel lines on every large face
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, 0.25)) @ Matrix.Diagonal((2.0, 1.0, 0.5, 1)))
report(snapshot(bm, "hull0"), "greeble_0_hull_2x1x0.5")
big = [f for f in bm.faces if f.calc_area() > 0.3]
r = bmesh.ops.inset_individual(bm, faces=big, thickness=PANEL_BORDER, depth=0.0, use_even_offset=True)
inner = [f for f in big]                                   # inset_individual keeps the input faces as the inner panels
# split each inner panel into 2x? sub-panels: inset again then recess
r2 = bmesh.ops.inset_individual(bm, faces=inner, thickness=0.0, depth=-PANEL_DEPTH)   # recess straight in
report(snapshot(bm, "hull1"), "greeble_1_panel_lines_inset+recess")
# ---- chamfer only the outer hull edges (face angle > 30 deg), keep panel edges crisp
sharp = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0.0) > math.radians(30) and all(abs(f.normal.z) < 0.01 or f.calc_center_median().z > 0.49 or f.calc_center_median().z < 0.01 for f in e.link_faces)]
bmesh.ops.bevel(bm, geom=sharp, offset=BEVEL, segments=1, profile=0.5, affect='EDGES', clamp_overlap=True)
report(snapshot(bm, "hull2"), f"greeble_2_chamfer_{len(sharp)}_edges_{BEVEL:.3f}m")
hull = obj_from_bmesh(bm, "SM_Hull_Body")

# ---- bolts: one cylinder mesh, instanced at panel corners via bmesh create_cone(matrix=...)
bm = bmesh.new()
bolt_r = ASSET * 0.006; bolt_h = ASSET * 0.004
placed = 0
for f in [f for f in hull.data.polygons if f.area > 0.3 * 0.8]:      # the recessed panel floors
    n = f.normal; c = f.center
    rot = n.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    # corners: shrink polygon verts toward center
    for vi in f.vertices:
        p = hull.data.vertices[vi].co
        pos = c + (p - c) * 0.85 + n * (bolt_h * 0.5)
        bmesh.ops.create_cone(bm, segments=6, radius1=bolt_r, radius2=bolt_r * 0.85, depth=bolt_h, cap_ends=True,
                              matrix=Matrix.Translation(pos) @ rot)
        placed += 1
bolts = obj_from_bmesh(bm, "SM_Hull_Bolts"); report(bolts, f"greeble_3_bolts_{placed}_hex")

# ---- linked duplicates alternative: one mesh datablock, many objects (zero extra geometry memory)
bm = bmesh.new(); bmesh.ops.create_cone(bm, segments=8, radius1=0.02, radius2=0.02, depth=0.05, cap_ends=True)
proto = obj_from_bmesh(bm, "SM_Greeble_Vent")
col = ensure_collection("SM_Hull_Greebles")
for i in range(6):
    dup = bpy.data.objects.new(f"SM_Greeble_Vent.{i:03d}", proto.data); dup.location = (-0.8 + i * 0.3, 0.55, 0.3)
    dup.rotation_euler = (math.radians(90), 0, 0); col.objects.link(dup)
print("linked duplicates share mesh users:", proto.data.users)

# ---- boolean cutouts: array of slots (one cutter mesh with many boxes) then EXACT difference + cleanup
bm = bmesh.new()
for i in range(5):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((-0.4 + i * 0.2, -0.5, 0.25)) @ Matrix.Diagonal((0.08, 0.2, 0.25, 1)))
cut = obj_from_bmesh(bm, "Cutter_Slots"); cut.display_type = 'WIRE'; cut.hide_render = True
m = hull.modifiers.new("Slots", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.solver = 'EXACT'; m.object = cut
report(hull, "greeble_4_boolean_slots_evaluated", evaluated=True)
apply_stack(hull); cut.hide_set(True)
bm = bmesh.new(); bm.from_mesh(hull.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(hull.data); bm.free()
report(hull, "greeble_5_boolean_applied+cleanup")
hull.data.shade_smooth(); bpy.context.view_layer.objects.active = hull; hull.select_set(True)
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out"); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "t07.blend"))
print("DONE t07")
